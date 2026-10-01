"""Hygiène des fichiers RDF : syntaxe, fins de ligne, espaces — pour des diffs déterministes."""

from __future__ import annotations

from rdflib import Graph

from .config import Project
from .graph import RDF_SUFFIXES
from .report import Problem

RDF_DIRS = ("ontology", "shapes", "tests/ontology", "examples", "memory", "governance")


def rdf_files(project: Project):
    for d in RDF_DIRS:
        root = project.root / d
        if root.exists():
            yield from sorted(p for p in root.rglob("*") if p.suffix in RDF_SUFFIXES and p.is_file())


def lint(project: Project) -> list[Problem]:
    problems = []
    for f in rdf_files(project):
        rel = f.relative_to(project.root).as_posix()
        raw = f.read_bytes()
        if b"\r\n" in raw:
            problems.append(Problem("lint", "fins de ligne CRLF (LF attendu)", where=rel))
        text = raw.decode("utf-8", errors="replace")
        verbatim = f.parent == project.external_dir  # copies amont : ne jamais les reformater
        if verbatim:
            pass
        elif text and not text.endswith("\n"):
            problems.append(Problem("lint", "pas de saut de ligne final", where=rel))
        trailing = [i + 1 for i, line in enumerate(text.splitlines()) if line != line.rstrip()]
        if trailing and not verbatim:
            problems.append(Problem("lint", f"espaces en fin de ligne (lignes {trailing[:5]})", where=rel))
        try:
            Graph().parse(f, format=RDF_SUFFIXES[f.suffix])
        except Exception as exc:
            problems.append(Problem("lint", f"syntaxe RDF invalide : {exc}", where=rel))
    return problems
