"""Problèmes remontés par les contrôles, formatés pour un humain ET pour un LLM."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Problem:
    check: str                  # nom du contrôle (validate.meta, lock, fixtures, …)
    message: str                # explication actionnable
    where: str = ""             # fichier, nœud ou forme concernée
    severity: str = "error"     # error | warning
    hint: str = field(default="", compare=False)

    def render(self) -> str:
        head = f"[{self.severity.upper()}] {self.check}"
        loc = f" ({self.where})" if self.where else ""
        text = f"{head}{loc} : {self.message}"
        if self.hint:
            text += f"\n    → {self.hint}"
        return text


def render(problems: list[Problem]) -> str:
    if not problems:
        return "OK — aucun problème."
    errors = [p for p in problems if p.severity == "error"]
    warnings = [p for p in problems if p.severity != "error"]
    lines = [p.render() for p in sorted(errors)] + [p.render() for p in sorted(warnings)]
    lines.append(f"\n{len(errors)} erreur(s), {len(warnings)} avertissement(s).")
    return "\n".join(lines)


def has_errors(problems: list[Problem]) -> bool:
    return any(p.severity == "error" for p in problems)
