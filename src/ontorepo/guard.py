"""Cœur de décision des garde-fous, indépendant de l'outil (Claude Code, Cursor, pre-commit…).

Principe : l'ontologie n'est jamais verrouillée, elle est PROTÉGÉE. Modifier une zone protégée est
permis dès qu'un amendement actif, de niveau suffisant, couvre le fichier ; sinon le refus explique
précisément comment procéder. Le code généré, la mémoire et les amendements ne s'éditent que via `onto`.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from .config import Project, matches

WRITE_MARKERS = re.compile(
    r"(>>?|\bsed\s+-i|\btee\b|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bgit\s+(checkout|restore|rm|mv)\b|"
    r"\bwrite_text\b|\bopen\([^)]*['\"][wa]|\bunlink\b|\bperl\s+-[a-z]*i|\bawk\s+-i)"
)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)


def strip_heredocs(command: str) -> str:
    """Retire le CORPS des heredocs : un texte qui cite une commande n'exécute pas cette commande.
    La ligne d'ouverture (et donc la cible d'une redirection `cat > fichier <<EOF`) est conservée."""
    return HEREDOC.sub(lambda m: m.group(3), command)


@dataclass
class Action:
    kind: str                         # edit | shell | other
    paths: list[str] = field(default_factory=list)
    command: str = ""


@dataclass
class Decision:
    verdict: str                      # allow | deny
    reason: str = ""

    @property
    def denied(self) -> bool:
        return self.verdict == "deny"


ALLOW = Decision("allow")


def _load_amendments(project: Project):
    try:
        from .amendments import load
        return load(project), None
    except Exception as exc:  # rdflib absent, fichier corrompu… → refus par défaut (fail closed)
        return [], exc


def _edit_rule(project: Project, rel: str, amendments, load_error) -> Decision:
    if project.is_generated(rel):
        return Decision("deny", (
            f"{rel} est GÉNÉRÉ depuis l'ontologie : ne jamais l'éditer à la main.\n"
            "→ Modifier l'ontologie (via un amendement si besoin), puis exécuter `onto codegen`."))
    if matches(rel, project.cli_only):
        return Decision("deny", (
            f"{rel} ne s'édite que via la CLI, qui valide avant d'écrire :\n"
            "→ mémoire : `onto memory add|retract|close-session` ; amendements : `onto amend open` ; "
            "verrou : `onto lock --update --amendment AMD-xxxx`."))
    level = project.protection_level(rel)
    if level == 0:
        return ALLOW
    if load_error is not None:
        return Decision("deny", f"{rel} est protégé (N{level}) et les amendements sont illisibles ({load_error}) : refus par sécurité.")
    for amd in amendments:
        if amd.authorizes_edit(rel, level):
            return ALLOW
    if level >= 3:
        return Decision("deny", (
            f"{rel} est un MÉTA-GARDE-FOU (N3 : ontologies externes, méta-règles, outillage de garde).\n"
            "Le modifier est possible mais exige une approbation humaine AVANT l'édition :\n"
            f"  1. `onto amend open --level 3 --covers {rel} --about <terme> --why \"…\" --alternatives \"…\"`\n"
            "  2. demander à un humain de relire puis d'exécuter `onto amend approve AMD-xxxx --by <nom>`.\n"
            "En attendant, travailler avec les règles existantes."))
    return Decision("deny", (
        f"{rel} fait partie de l'ontologie protégée (N{level}). Le changement ontologique est PERMIS mais doit rester l'exception.\n"
        "  1. Vérifier d'abord si l'existant suffit : `onto explain <terme>`, `onto glossary`.\n"
        "  2. Si un changement est vraiment nécessaire, ouvrir un amendement :\n"
        f"     `onto amend open --level 1 --covers {rel} --about <terme> --why \"…\" --alternatives \"pourquoi l'existant ne suffit pas\"`\n"
        "     (N1 = ajout pur ; N2 = modification/suppression/relâchement, approbation humaine avant fusion).\n"
        "  3. Puis éditer, `onto lock --update --amendment AMD-xxxx`, `onto codegen`, `onto check`."))


def _shell_paths(project: Project, command: str) -> list[str]:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    rels = []
    for tok in tokens:
        for piece in re.split(r"[=:,;|&<>()'\"]", tok):
            if not piece or piece.startswith("-"):
                continue
            rel = project.relpath(piece)
            if rel and rel != "." and (project.protection_level(rel) or project.is_generated(rel) or matches(rel, project.cli_only)):
                rels.append(rel)
    return sorted(set(rels))


def decide(project: Project, action: Action) -> Decision:
    amendments, load_error = _load_amendments(project)
    if action.kind == "edit":
        for p in action.paths:
            rel = project.relpath(p)
            if rel is None:
                continue
            d = _edit_rule(project, rel, amendments, load_error)
            if d.denied:
                return d
        return ALLOW
    if action.kind == "shell":
        cmd = " ".join(strip_heredocs(action.command).split())
        for forbidden in project.forbidden_commands:
            if forbidden in cmd:
                return Decision("deny", f"Commande réservée aux humains ou interdite aux agents : `{forbidden}`.")
        if re.search(r"\bonto\s+lock\b.*--(update|init)\b", cmd) and "--amendment" not in cmd:
            return Decision("deny", "`onto lock --update` exige `--amendment AMD-xxxx` : tout changement protégé est rattaché à un amendement.")
        if re.search(r"\bonto\s+lock\b.*--init\b", cmd):
            return Decision("deny", "`onto lock --init` est réservé à l'initialisation humaine du dépôt.")
        if re.match(r"^\s*(onto|python3? -m ontorepo)\b", cmd):
            return ALLOW
        if WRITE_MARKERS.search(cmd):
            for rel in _shell_paths(project, cmd):
                d = _edit_rule(project, rel, amendments, load_error)
                if d.denied:
                    return Decision("deny", "Écriture shell sur une zone protégée refusée.\n" + d.reason)
        return ALLOW
    return ALLOW
