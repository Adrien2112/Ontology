"""`onto check` : point d'entrée unique et identique pour l'agent (hook Stop), le développeur et la CI."""

from __future__ import annotations

from . import amendments as amd_mod
from . import codegen, fixtures, lint, lock, memory, stats
from .config import Project
from .graph import Ontology
from .report import Problem
from .validate import validate_data, validate_meta


def conservativity(project: Project, base: str) -> list[Problem]:
    """Un amendement N1 ne doit rien retirer ni modifier (ajout pur), sinon il relève du N2."""
    if not amd_mod.git_ref_exists(project, base):
        return []
    problems = []
    for a in amd_mod.load(project):
        if a.level != 1 or not a.active:
            continue
        removed = amd_mod.removed_triples(project, a, base)
        if removed:
            files = ", ".join(sorted(removed))
            problems.append(Problem(
                "amend", f"{a.id} est déclaré N1 (ajout pur) mais retire ou modifie des triplets ({files})",
                where=f"governance/amendments/{a.id}.ttl",
                hint=f"Requalifier : `onto amend requalify {a.id} --level 2` (approbation humaine requise avant fusion), "
                     "ou revenir à un changement purement additif."))
    return problems


def run_check(project: Project, *, ci: bool = False, base: str = "HEAD", quick: bool = False) -> list[Problem]:
    onto = Ontology(project)
    problems: list[Problem] = []
    problems += lint.lint(project)
    if any(p.severity == "error" and "syntaxe" in p.message for p in problems):
        return problems  # inutile de valider un graphe qui ne se parse pas
    problems += validate_meta(onto)
    problems += fixtures.traceability(onto)
    problems += fixtures.run_fixtures(onto)
    problems += validate_data(onto)
    problems += codegen.check(onto)
    problems += lock.check(project, ci=ci)
    problems += conservativity(project, base)
    problems += memory.lint(onto)
    if not quick:
        problems += stats.check(project)
    return problems
