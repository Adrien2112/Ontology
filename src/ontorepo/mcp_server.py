"""Serveur MCP (stdio, JSON-RPC 2.0) exposant l'ontologie aux agents : Claude Code, Cursor, etc.

Sans dépendance externe. Les outils sont les mêmes fonctions que la CLI : l'agent interroge et
valide au lieu d'improviser.
"""

from __future__ import annotations

import json
import sys
from typing import Callable

from rdflib import Graph

from . import __version__, memory, query
from .check import run_check
from .config import Project
from .graph import Ontology
from .report import render
from .validate import validate_data

PROTOCOL = "2025-06-18"


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties, "required": required}}


TOOLS = [
    _tool("onto_explain", "Explique un terme de l'ontologie (labels, définition, hiérarchie, alignements, propriétés, invariants, mémoire). À utiliser AVANT d'écrire du code ou des données.",
          {"term": {"type": "string", "description": "Terme préfixé, ex. fleet:StationRFID"}}, ["term"]),
    _tool("onto_glossary", "Glossaire du langage ubiquitaire (option : contexte borné).",
          {"context": {"type": "string"}}, []),
    _tool("onto_query", "Requête SPARQL SELECT/ASK sur TBox + données + mémoire + amendements.",
          {"sparql": {"type": "string"}}, ["sparql"]),
    _tool("onto_validate_turtle", "Valide un fragment Turtle (données) contre les invariants du domaine, avec les données de référence.",
          {"turtle": {"type": "string"}}, ["turtle"]),
    _tool("onto_memory_recall", "Rappel sémantique de la mémoire du dépôt (par terme de l'ontologie et/ou type).",
          {"about": {"type": "string"}, "type": {"type": "string", "enum": list(memory.TYPES)}}, []),
    _tool("onto_memory_add", "Ajoute une entrée mémoire (statut 'proposed'), validée avant écriture.",
          {"type": {"type": "string", "enum": list(memory.TYPES)}, "statement": {"type": "string"},
           "about": {"type": "array", "items": {"type": "string"}},
           "evidence": {"type": "array", "items": {"type": "string"}}}, ["type", "statement", "about"]),
    _tool("onto_check", "Exécute `onto check` (tous les garde-fous) et renvoie le rapport.", {}, []),
]


def call(project: Project, name: str, args: dict) -> tuple[str, bool]:
    onto = Ontology(project)
    try:
        if name == "onto_explain":
            return query.explain(onto, args["term"]), False
        if name == "onto_glossary":
            return query.glossary(onto, args.get("context")), False
        if name == "onto_query":
            return json.dumps(query.sparql(onto, args["sparql"]), ensure_ascii=False, indent=2), False
        if name == "onto_validate_turtle":
            g = Graph().parse(data=args["turtle"], format="turtle")
            problems = validate_data(onto, onto.union(onto.data, g))
            return render(problems), bool(problems)
        if name == "onto_memory_recall":
            entries = memory.recall(onto, about=args.get("about"), types=[args["type"]] if args.get("type") else None)
            return memory.render_entries(onto, entries) or "(aucune entrée)", False
        if name == "onto_memory_add":
            e = memory.add(onto, type=args["type"], statement=args["statement"], about=args["about"],
                           evidence=args.get("evidence") or [], agent="mcp")
            return f"Entrée {e.id} enregistrée (statut : proposed).", False
        if name == "onto_check":
            problems = run_check(project, quick=True)
            return render(problems), any(p.severity == "error" for p in problems)
        return f"Outil inconnu : {name}", True
    except Exception as exc:
        return f"Erreur : {exc}", True


def handle(project: Project, msg: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # notification
    if method == "initialize":
        result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL),
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "ontorepo", "version": __version__}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params", {})
        text, is_error = call(project, params.get("name", ""), params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Méthode inconnue : {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(project: Project, stdin=sys.stdin, stdout=sys.stdout, handler: Callable = handle) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handler(project, msg)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
