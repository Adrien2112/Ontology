"""TDD des invariants : chaque invariant a des exemples valides et invalides qui le prouvent.

Arborescence : <fixtures>/<NomInvariant>/{valid,invalid}/*.ttl
- un exemple valide doit être conforme à TOUS les invariants de domaine ;
- un exemple invalide doit violer l'invariant de son répertoire, et UNIQUEMENT lui
  (sinon l'exemple prouve autre chose que ce qu'il prétend).
"""

from __future__ import annotations

from pathlib import Path

from .graph import Ontology, parse
from .namespaces import DDD, RDF
from .report import Problem
from .validate import domain_violations


def invariants(onto: Ontology) -> dict[str, str]:
    """Nom local → forme abrégée (ex. 'NumeroSerieUnique' → 'inv:NumeroSerieUnique')."""
    shapes = onto.domain_shapes
    out = {}
    for s in shapes.subjects(RDF.type, DDD.Invariant):
        local = str(s).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        out[local] = shapes.namespace_manager.normalizeUri(s)
    return dict(sorted(out.items()))


def fixture_files(onto: Ontology, name: str, kind: str) -> list[Path]:
    d = onto.project.fixtures_dir / name / kind
    return sorted(d.glob("*.ttl")) if d.is_dir() else []


def traceability(onto: Ontology) -> list[Problem]:
    problems = []
    known = invariants(onto)
    for name in known:
        for kind in ("valid", "invalid"):
            if not fixture_files(onto, name, kind):
                problems.append(Problem(
                    "traceability", f"l'invariant {known[name]} n'a aucun exemple {kind}",
                    where=f"{onto.project.relpath(onto.project.fixtures_dir)}/{name}/{kind}/",
                    hint="TDD : écrire d'abord un exemple invalide puis un exemple valide (fichiers .ttl).",
                ))
    root = onto.project.fixtures_dir
    if root.is_dir():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            if d.name not in known:
                problems.append(Problem(
                    "traceability", f"répertoire d'exemples sans invariant correspondant : {d.name}",
                    where=onto.project.relpath(d) or str(d),
                    hint="Renommer le répertoire selon le nom local d'une forme typée ddd:Invariant.",
                ))
    return problems


def run_fixtures(onto: Ontology) -> list[Problem]:
    problems = []
    for name, shape in invariants(onto).items():
        for f in fixture_files(onto, name, "valid"):
            rel = onto.project.relpath(f) or str(f)
            for v in domain_violations(onto, parse([f])):
                problems.append(Problem(
                    "fixtures", f"exemple valide non conforme : {v.shape} — {v.message}",
                    where=rel, hint="Un exemple valide doit satisfaire tous les invariants (compléter les nœuds référencés).",
                ))
        for f in fixture_files(onto, name, "invalid"):
            rel = onto.project.relpath(f) or str(f)
            violations = domain_violations(onto, parse([f]))
            shapes_hit = {v.shape for v in violations}
            if shape not in shapes_hit:
                problems.append(Problem(
                    "fixtures", f"exemple invalide accepté par {shape} : l'invariant ne détecte pas ce cas",
                    where=rel, hint="Soit la règle est trop laxiste, soit l'exemple n'est pas un contre-exemple.",
                ))
            others = sorted(shapes_hit - {shape})
            if others:
                problems.append(Problem(
                    "fixtures", f"exemple invalide qui viole aussi {', '.join(others)}",
                    where=rel, hint="Un contre-exemple doit isoler un seul invariant.",
                ))
    return problems
