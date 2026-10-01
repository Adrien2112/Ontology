"""Vérification de la provenance des ontologies externes vendorisées."""

from __future__ import annotations

import hashlib
import tomllib
import urllib.request

from rdflib import Graph

from .config import Project
from .report import Problem


def sources(project: Project) -> list[dict]:
    f = project.external_dir / "SOURCES.toml"
    if not f.is_file():
        return []
    with open(f, "rb") as fh:
        return tomllib.load(fh).get("source", [])


def verify(project: Project, online: bool = False) -> list[Problem]:
    problems = []
    declared = {s["file"] for s in sources(project)}
    for p in sorted(project.external_dir.glob("*.ttl")):
        if p.name not in declared:
            problems.append(Problem("external", "ontologie externe sans provenance déclarée", where=p.name))
    if not online:
        return problems
    for s in sources(project):
        local = project.external_dir / s["file"]
        try:
            with urllib.request.urlopen(s["retrieved_from"], timeout=20) as resp:
                upstream = resp.read()
        except Exception as exc:
            problems.append(Problem("external", f"amont injoignable ({exc})", where=s["file"], severity="warning"))
            continue
        if s["kind"] == "verbatim":
            if hashlib.sha256(upstream).hexdigest() != hashlib.sha256(local.read_bytes()).hexdigest():
                problems.append(Problem("external", "copie différente de l'amont", where=s["file"], severity="warning",
                                        hint="Mettre à jour = amendement N3."))
        else:
            fmt = "xml" if s["retrieved_from"].endswith(".rdf") else "turtle"
            up = Graph().parse(data=upstream, format=fmt)
            missing = [t for t in Graph().parse(local) if t not in up and "source" not in str(t[1]) and "versionInfo" not in str(t[1])]
            if missing:
                problems.append(Problem("external", f"{len(missing)} triplet(s) de l'extrait absents de l'amont",
                                        where=s["file"], hint=str(missing[:3])))
    return problems
