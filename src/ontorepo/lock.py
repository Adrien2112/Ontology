"""Verrou des zones protégées : empreinte sha256 de chaque fichier protégé et amendement qui l'a validée."""

from __future__ import annotations

import hashlib
import tomllib

from .amendments import Amendment, load as load_amendments
from .config import Project
from .report import Problem

HEADER = """# Verrou des zones protégées — écrit par `onto lock`, ne pas éditer à la main.
# Chaque entrée : niveau de protection, empreinte sha256, amendement ayant autorisé l'état actuel.
"""


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(project: Project) -> dict[str, dict]:
    if not project.lock_file.is_file():
        return {}
    with open(project.lock_file, "rb") as fh:
        return tomllib.load(fh).get("files", {})


def write(project: Project, entries: dict[str, dict]) -> None:
    lines = [HEADER]
    for rel in sorted(entries):
        e = entries[rel]
        lines.append(f'\n[files."{rel}"]\nlevel = {e["level"]}\nsha256 = "{e["sha256"]}"\namendment = "{e["amendment"]}"\n')
    project.lock_file.parent.mkdir(parents=True, exist_ok=True)
    project.lock_file.write_text("".join(lines), encoding="utf-8")


def drift(project: Project) -> dict[str, str]:
    """Écarts entre l'état des fichiers protégés et le verrou : chemin → 'modifié' | 'nouveau' | 'supprimé'."""
    locked = read(project)
    current = project.protected_files()
    out = {}
    for rel, level in current.items():
        if rel not in locked:
            out[rel] = "nouveau"
        elif locked[rel]["sha256"] != sha256(project.root / rel) or locked[rel]["level"] != level:
            out[rel] = "modifié"
    for rel in locked:
        if rel not in current:
            out[rel] = "supprimé"
    return dict(sorted(out.items()))


def check(project: Project, ci: bool = False) -> list[Problem]:
    problems = []
    amendments = {a.id: a for a in load_amendments(project)}
    for rel, kind in drift(project).items():
        level = project.protection_level(rel)
        problems.append(Problem(
            "lock", f"fichier protégé (N{level}) {kind} sans verrou à jour",
            where=rel,
            hint=("Ouvrir un amendement (`onto amend open --level N --covers <fichier> ...`) puis "
                  "`onto lock --update --amendment AMD-xxxx`. Si la modification n'était pas voulue : `git checkout -- <fichier>`."),
        ))
    for rel, entry in read(project).items():
        amd: Amendment | None = amendments.get(entry.get("amendment", ""))
        if amd is None:
            problems.append(Problem("lock", f"verrou référençant un amendement inconnu ({entry.get('amendment')})", where=rel))
            continue
        if not amd.covers_path(rel) or amd.level < entry["level"]:
            problems.append(Problem("lock", f"{amd.id} (N{amd.level}) ne couvre pas ce fichier de niveau N{entry['level']}", where=rel))
        if amd.status == "rejected":
            problems.append(Problem("lock", f"{amd.id} est rejeté : l'état verrouillé n'est pas autorisé", where=rel))
        if ci and amd.level >= 2 and amd.status not in ("approved", "applied"):
            problems.append(Problem(
                "lock", f"{amd.id} (N{amd.level}) n'est pas approuvé : fusion refusée",
                where=rel, hint="Un humain doit relire puis exécuter `onto amend approve AMD-xxxx --by <nom>`.",
            ))
    return problems


def update(project: Project, amd: Amendment, *, init: bool = False) -> list[str]:
    """Met à jour le verrou pour les fichiers en écart couverts par `amd`. Renvoie les fichiers mis à jour."""
    entries = read(project)
    current = project.protected_files()
    # sans --init : seuls les écarts couverts par l'amendement sont traités ; les autres restent signalés
    targets = list(current) if init else [rel for rel in drift(project) if amd.covers_path(rel)]
    refused = []
    updated = []
    for rel in targets:
        level = current.get(rel, project.protection_level(rel))
        if not init:
            if not amd.authorizes_edit(rel, max(level, 1)):
                refused.append(f"{rel} (N{level})")
                continue
        if rel in current:
            entries[rel] = {"level": level, "sha256": sha256(project.root / rel), "amendment": amd.id}
        else:
            entries.pop(rel, None)
        updated.append(rel)
    if refused:
        raise PermissionError(f"{amd.id} (N{amd.level}, {amd.status}) ne couvre pas : " + ", ".join(refused))
    write(project, entries)
    return updated
