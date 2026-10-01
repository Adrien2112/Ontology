"""Chargement des graphes du projet : TBox, formes, données, mémoire, amendements."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Iterable

from rdflib import Graph

from .config import Project
from .namespaces import DDD, RDF, bind_all

RDF_SUFFIXES = {".ttl": "turtle", ".trig": "trig", ".rdf": "xml", ".owl": "xml", ".nt": "nt"}


def rdf_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    if directory.is_file():
        return [directory]
    return sorted(p for p in directory.rglob("*") if p.suffix in RDF_SUFFIXES and p.is_file())


def parse(paths: Iterable[Path], graph: Graph | None = None) -> Graph:
    g = graph if graph is not None else bind_all(Graph())
    for p in paths:
        g.parse(p, format=RDF_SUFFIXES[p.suffix])
    return g


class Ontology:
    """Vue paresseuse (et mise en cache) des graphes d'un projet."""

    def __init__(self, project: Project):
        self.project = project

    # --- TBox --------------------------------------------------------------------------------

    @cached_property
    def external(self) -> Graph:
        return parse(rdf_files(self.project.external_dir))

    @cached_property
    def internal(self) -> Graph:
        p = self.project
        return parse([*rdf_files(p.meta_dir), *rdf_files(p.domain_dir), *rdf_files(p.alignment_dir)])

    @cached_property
    def tbox(self) -> Graph:
        g = bind_all(Graph())
        for part in (self.external, self.internal):
            for t in part:
                g.add(t)
            for prefix, ns in part.namespaces():
                g.bind(prefix, ns, override=False)
        return g

    # --- Formes ------------------------------------------------------------------------------

    @cached_property
    def meta_shapes(self) -> Graph:
        return parse(rdf_files(self.project.meta_shapes_dir))

    @cached_property
    def domain_shapes(self) -> Graph:
        return parse(rdf_files(self.project.domain_shapes_dir))

    # --- ABox --------------------------------------------------------------------------------

    @cached_property
    def data(self) -> Graph:
        files: list[Path] = []
        for d in self.project.data_dirs:
            files.extend(rdf_files(d))
        return parse(files)

    @cached_property
    def memory(self) -> Graph:
        return parse(rdf_files(self.project.memory_dir))

    @cached_property
    def amendments(self) -> Graph:
        return parse(rdf_files(self.project.amendments_dir))

    # --- Utilitaires --------------------------------------------------------------------------

    def domain_namespaces(self) -> list[str]:
        return sorted(str(ns) for ns in self.tbox.objects(None, DDD.namespaceIri)
                      if any(self.tbox.triples((None, RDF.type, DDD.DomainOntology))))

    def union(self, *graphs: Graph) -> Graph:
        g = bind_all(Graph())
        for part in graphs:
            for t in part:
                g.add(t)
            for prefix, ns in part.namespaces():
                g.bind(prefix, ns, override=False)
        return g
