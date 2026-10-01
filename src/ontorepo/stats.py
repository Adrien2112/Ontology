"""Suivi du rythme de changement ontologique : l'exception doit rester l'exception."""

from __future__ import annotations

import subprocess
from collections import Counter

from .amendments import load
from .config import Project
from .report import Problem


def stats(project: Project) -> dict:
    amds = load(project)
    policy = project.policy.get("amendments", {})
    window = int(policy.get("window_commits", 50))
    rel = project.amendments_dir.relative_to(project.root).as_posix()
    try:
        log = subprocess.run(["git", "log", f"-n{window}", "--diff-filter=A", "--name-only", "--format=", "--", rel],
                             cwd=project.root, capture_output=True, text=True, check=True).stdout.split()
        commits = int(subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=project.root,
                                     capture_output=True, text=True, check=True).stdout.strip() or 0)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        log, commits = [], 0
    recent = sorted({p.rsplit("/", 1)[-1].removesuffix(".ttl") for p in log if p.endswith(".ttl")})
    return {
        "total": len(amds),
        "by_level": dict(sorted(Counter(f"N{a.level}" for a in amds).items())),
        "by_status": dict(sorted(Counter(a.status for a in amds).items())),
        "window_commits": window,
        "commits": commits,
        "recent": recent,
        "max_per_window": int(policy.get("max_per_window", 3)),
    }


def check(project: Project) -> list[Problem]:
    s = stats(project)
    # l'amendement fondateur (AMD-0001) ne compte pas : il crée l'ontologie
    recent = [r for r in s["recent"] if r != "AMD-0001"]
    if len(recent) > s["max_per_window"]:
        return [Problem("stats", (f"{len(recent)} amendements sur les {s['window_commits']} derniers commits "
                                  f"(politique : {s['max_per_window']} max) — l'ontologie bouge plus que l'exception"),
                        where="governance/policy.toml", severity="warning",
                        hint="Les humains devraient vérifier que les agents travaillent d'abord avec l'existant.")]
    return []


def render(project: Project) -> str:
    s = stats(project)
    return "\n".join([
        f"Amendements : {s['total']} au total — par niveau {s['by_level']} — par statut {s['by_status']}",
        f"Fenêtre : {s['window_commits']} derniers commits ({s['commits']} commits au total) → "
        f"{len(s['recent'])} amendement(s) récent(s) {s['recent']} ; seuil d'alerte {s['max_per_window']}",
    ])
