"""Point d'entrée : `python -m ontorepo.hooks <claude|cursor> <événement>` (payload JSON sur stdin)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("claude", "cursor"):
        print("usage: python -m ontorepo.hooks <claude|cursor> <événement>", file=sys.stderr)
        return 1
    tool, event = argv
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    from ..config import Project

    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or (payload.get("workspace_roots") or [None])[0]
    try:
        project = Project.discover(Path(root) if root else None)
    except FileNotFoundError:
        return 0  # hors d'un dépôt ontorepo : ne rien faire
    from . import claude, cursor

    adapter = claude if tool == "claude" else cursor
    try:
        out, code = adapter.handle(event, payload, project)
    except Exception as exc:  # fail closed pour les décisions de permission, ouvert pour le reste
        if event in ("PreToolUse", "preToolUse", "beforeShellExecution"):
            reason = f"Garde-fou ontologique en erreur ({exc!r}) : action refusée par sécurité."
            out = ({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                            "permissionDecisionReason": reason}} if tool == "claude"
                   else {"permission": "deny", "agent_message": reason})
            code = 0 if tool == "claude" else 2
        else:
            print(f"ontorepo hook {event} : {exc!r}", file=sys.stderr)
            return 0
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
