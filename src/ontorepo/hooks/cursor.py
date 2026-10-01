"""Adaptateur Cursor (.cursor/hooks.json → `python -m ontorepo.hooks cursor <event>`).

Événements utilisés : sessionStart, preToolUse, beforeShellExecution, postToolUse, afterFileEdit, stop.
Un refus renvoie {"permission": "deny", ...} ET le code de sortie 2 (blocage Cursor).
"""

from __future__ import annotations

from ..config import Project
from ..guard import Action, decide
from . import common

PATH_KEYS = ("file_path", "path", "target_file", "filePath", "target_notebook", "file")
SHELL_TOOLS = {"Shell", "Bash", "run_terminal_cmd", "terminal"}


def _paths(data: dict) -> list[str]:
    out = [data[k] for k in PATH_KEYS if isinstance(data.get(k), str)]
    for k in ("paths", "files"):
        if isinstance(data.get(k), list):
            out += [p for p in data[k] if isinstance(p, str)]
    return out


def to_action(payload: dict) -> Action:
    tool = payload.get("tool_name", "") or ""
    data = payload.get("tool_input") or {}
    if isinstance(data, str):
        data = {"command": data}
    if tool in SHELL_TOOLS or ("command" in data and not _paths(data)):
        return Action("shell", command=data.get("command", ""))
    paths = _paths(data) or _paths(payload)
    if paths and tool.lower() not in ("read", "read_file", "grep", "glob", "list_dir", "codebase_search"):
        return Action("edit", paths)
    return Action("other")


def _permission(decision) -> tuple[dict, int]:
    if decision.denied:
        return {"permission": "deny", "user_message": "Bloqué par le garde-fou ontologique.",
                "agent_message": decision.reason}, 2
    return {"permission": "allow"}, 0


def handle(event: str, payload: dict, project: Project) -> tuple[dict | None, int]:
    if event == "preToolUse":
        return _permission(decide(project, to_action(payload)))
    if event == "beforeShellExecution":
        return _permission(decide(project, Action("shell", command=payload.get("command", ""))))
    if event in ("postToolUse", "afterFileEdit"):
        paths = _paths(payload) or _paths(payload.get("tool_input") or {})
        report = common.post_edit(project, paths)
        return ({"additional_context": "Validation ontologique après écriture :\n" + report} if report else {}), 0
    if event == "stop":
        if int(payload.get("loop_count", 0) or 0) >= common.MAX_STOP_BLOCKS:
            return {}, 0
        block, message = common.stop_gate(project)
        return ({"followup_message": message} if block else {}), 0
    if event == "sessionStart":
        ctx = common.session_context(project, "cursor", payload.get("session_id") or payload.get("conversation_id"))
        return {"additional_context": ctx}, 0
    return {}, 0
