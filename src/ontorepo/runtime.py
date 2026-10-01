"""Pont générique entre le modèle Python généré et RDF (aller-retour sans perte)."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Iterable

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF


def to_graph(objects: Iterable, graph: Graph | None = None) -> Graph:
    g = graph if graph is not None else Graph()
    for obj in objects:
        if not is_dataclass(obj):
            raise TypeError(f"Objet de domaine attendu, reçu {type(obj).__name__}")
        s = URIRef(obj.iri)
        g.add((s, RDF.type, URIRef(type(obj).__iri__)))
        for f in fields(obj):
            meta = f.metadata
            if meta.get("kind") in (None, "id"):
                continue
            value = getattr(obj, f.name)
            if value is None:
                continue
            p = URIRef(meta["iri"])
            if meta["kind"] == "literal":
                g.add((s, p, Literal(value, datatype=URIRef(meta["datatype"]))))
            elif meta["kind"] == "enum":
                g.add((s, p, URIRef(value.value)))
            else:
                g.add((s, p, URIRef(value)))
    return g


def from_graph(graph: Graph, cls, enums: Iterable[type[Enum]] = ()) -> list:
    """Instancie tous les sujets dont le type EXACT est `cls`."""
    enum_by_iri = {m.value: m for e in enums for m in e}
    out = []
    for s in sorted(set(graph.subjects(RDF.type, URIRef(cls.__iri__))), key=str):
        kwargs = {}
        for f in fields(cls):
            meta = f.metadata
            if meta.get("kind") == "id":
                kwargs[f.name] = str(s)
                continue
            o = graph.value(s, URIRef(meta["iri"]))
            if o is None:
                raise ValueError(f"{s} : propriété {meta['iri']} absente (le graphe devrait être validé avant).")
            if meta["kind"] == "literal":
                kwargs[f.name] = o.toPython()
            elif meta["kind"] == "enum":
                kwargs[f.name] = enum_by_iri[str(o)]
            else:
                kwargs[f.name] = str(o)
        out.append(cls(**kwargs))
    return out
