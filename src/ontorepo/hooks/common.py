"""Logique commune aux hooks : contexte de session, validation après écriture, porte de fin de tâche."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import Project

MAX_STOP_BLOCKS = 3

RULES = """## Contrat ontologique du dépôt (rappel automatique)
- L'ontologie (`ontology/`) est la source de vérité ; les formes SHACL (`shapes/`) sont les garde-fous.
- Avant d'écrire du code ou des données : `onto explain <terme>` / `onto glossary`. N'invente aucun terme.
- TDD : exemple invalide puis valide (`tests/ontology/fixtures/<Invariant>/`), test rouge, `onto codegen`, code, `onto check`.
- Code généré (`src/fleet/domain/_generated/`) : jamais à la main. Mémoire : uniquement `onto memory add`.
- Changer l'ontologie est permis mais exceptionnel : `onto amend open --level N …` (N1 ajout, N2 modification, N3 méta).
- Fin de tâche : `onto check` doit être vert ; consigner décisions/leçons via `onto memory add`."""


def session_context(project: Project, tool: str, session_id: str | None) -> str:
    from .. import memory
    from ..graph import Ontology

    memory.start_session(project, tool, session_id)
    try:
        mem = memory.summary(Ontology(project))
    except Exception as exc:  # mémoire illisible : le dire plutôt que d'échouer silencieusement
        mem = f"(mémoire illisible : {exc} — exécuter `onto check`)"
    return RULES + "\n\n" + mem


def post_edit(project: Project, paths: list[str]) -> str:
    """Valide immédiatement un fichier RDF modifié ; renvoie un rapport ('' si tout va bien)."""
    from ..graph import Ontology
    from ..report import render
    from ..validate import validate_data, validate_meta

    rels = [r for r in (project.relpath(p) for p in paths) if r]
    rdf = [r for r in rels if Path(r).suffix in (".ttl", ".trig")]
    if not rdf:
        return ""
    problems_txt = []
    for rel in rdf:
        try:
            from rdflib import Graph
            Graph().parse(project.root / rel, format="trig" if rel.endswith(".trig") else "turtle")
        except Exception as exc:
            problems_txt.append(f"[ERROR] syntaxe RDF invalide dans {rel} : {exc}")
    if problems_txt:
        return "\n".join(problems_txt)
    onto = Ontology(project)
    problems = validate_meta(onto)
    if any(r.startswith(("shapes/domain", "ontology/data", "examples")) for r in rdf):
        problems += validate_data(onto)
    return render(problems) if problems else ""


def _changed_since_start(project: Project, state: dict) -> bool:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=project.root, capture_output=True, text=True).stdout
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=project.root, capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        return False
    return bool(out.strip()) or (bool(state.get("commit")) and head != state.get("commit"))


def stop_gate(project: Project) -> tuple[bool, str]:
    """(bloquer ?, message). Bloque si `onto check` échoue ; rappelle une fois de consigner la mémoire."""
    from .. import memory
    from ..check import run_check
    from ..report import has_errors, render

    state = memory.current_session(project) or memory.start_session(project, "unknown")
    if state.get("stop_blocks", 0) >= MAX_STOP_BLOCKS:
        memory.update_state(project, stop_blocks=0)
        return False, "Garde-fou : nombre maximal de relances atteint, `onto check` reste à corriger."
    problems = run_check(project, quick=True)
    if has_errors(problems):
        memory.update_state(project, stop_blocks=state.get("stop_blocks", 0) + 1)
        return True, ("`onto check` échoue : la tâche n'est pas terminée. Corriger sans contourner les règles "
                      "(si une règle semble fausse, ouvrir un amendement plutôt que de la contourner).\n\n" + render(problems))
    if _changed_since_start(project, state) and not state.get("entries") and not state.get("reminded"):
        memory.update_state(project, reminded=True)
        return True, ("`onto check` est vert. Avant de terminer : consigner ce qui mérite d'être retenu "
                      "(décision, leçon, convention, question ouverte) avec `onto memory add --type … --about <terme> "
                      "--statement \"…\"`, puis `onto memory close-session --summary \"…\"`. "
                      "S'il n'y a rien à retenir, terminer simplement.")
    memory.update_state(project, stop_blocks=0)
    return False, ""
