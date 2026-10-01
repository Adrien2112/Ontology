"""Adaptateur Claude Code (.claude/settings.json → `python -m ontorepo.hooks claude <Event>`)."""

from __future__ import annotations

import json

from ..config import Project
from ..guard import Action, decide
from . import common

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def to_action(payload: dict) -> Action:
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        return Action("edit", [p for p in (data.get("file_path"), data.get("notebook_path")) if p])
    if tool == "Bash":
        return Action("shell", command=data.get("command", ""))
    return Action("other")


def handle(event: str, payload: dict, project: Project) -> tuple[dict | None, int]:
    if event == "PreToolUse":
        d = decide(project, to_action(payload))
        if d.denied:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": d.reason}}, 0
        return None, 0
    if event == "PostToolUse":
        action = to_action(payload)
        if action.kind == "edit":
            report = common.post_edit(project, action.paths)
            if report:
                return {"decision": "block", "reason": "Validation ontologique après écriture :\n" + report}, 0
        return None, 0
    if event == "Stop":
        block, message = common.stop_gate(project)
        if block:
            return {"decision": "block", "reason": message}, 0
        return ({"systemMessage": message} if message else None), 0
    if event == "SessionStart":
        ctx = common.session_context(project, "claude-code", payload.get("session_id"))
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}, 0
    return None, 0


def dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)
