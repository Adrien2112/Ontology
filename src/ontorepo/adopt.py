"""Adoption sur un dépôt existant : rétro-ingénierie du code Python en brouillon d'ontologie + rapport d'écart.

Le brouillon n'est PAS l'ontologie : c'est un point de départ que des humains relisent, définissent,
alignent sur les ontologies externes puis promeuvent (amendement N1) — voir docs/etude/04.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from .graph import Ontology
from .namespaces import DDD, RDFS

PY_TO_XSD = {"str": "xsd:string", "int": "xsd:integer", "float": "xsd:decimal", "Decimal": "xsd:decimal",
             "bool": "xsd:boolean", "datetime": "xsd:dateTime", "date": "xsd:date"}


@dataclass
class CodeClass:
    name: str
    file: str
    bases: list[str]
    is_enum: bool = False
    is_frozen: bool = False
    fields: dict[str, str] = field(default_factory=dict)
    members: list[str] = field(default_factory=list)


def _ann(node) -> str:
    return ast.unparse(node) if node is not None else ""


def scan(path: Path) -> list[CodeClass]:
    root = path if path.is_dir() else path.parent
    files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
    out = []
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                continue
            bases = [_ann(b) for b in node.bases]
            c = CodeClass(node.name, f.relative_to(root).as_posix(), bases)
            c.is_enum = any(b.split(".")[-1] in ("Enum", "StrEnum", "IntEnum") for b in bases)
            for d in node.decorator_list:
                if "frozen=True" in _ann(d):
                    c.is_frozen = True
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    if "ClassVar" not in _ann(stmt.annotation):
                        c.fields[stmt.target.id] = _ann(stmt.annotation)
                elif c.is_enum and isinstance(stmt, ast.Assign):
                    c.members += [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            out.append(c)
    return out


def camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def draft_turtle(classes: list[CodeClass], namespace: str) -> str:
    names = {c.name for c in classes}
    lines = [
        "# BROUILLON généré par `onto adopt scan` — à relire, définir et aligner avant toute promotion.",
        f"@prefix draft: <{namespace}> .",
        "@prefix ddd:   <https://adrien2112.github.io/ontology/ddd#> .",
        "@prefix owl:   <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]
    for c in sorted(classes, key=lambda c: c.name):
        stereo = ("ddd:Enumeration" if c.is_enum else "ddd:Entity" if {"id", "iri", "uuid", "pk"} & set(c.fields)
                  else "ddd:ValueObject" if c.is_frozen else "ddd:Entity")
        parents = [b for b in c.bases if b in names]
        lines.append(f"draft:{c.name} a owl:Class ;")
        for p in parents:
            lines.append(f"    rdfs:subClassOf draft:{p} ;")
        lines.append(f'    rdfs:label "{c.name}"@en ;')
        lines.append(f'    skos:definition "TODO : définir dans le langage du métier (source : {c.file})."@fr ;')
        lines.append(f"    ddd:stereotype {stereo} .")
        lines.append("")
        for m in c.members:
            lines.append(f'draft:{c.name}_{m} a draft:{c.name} ; rdfs:label "{m}"@en .')
        for fname, ann in sorted(c.fields.items()):
            if fname in ("id", "iri"):
                continue
            base = ann.split("[")[0].split(".")[-1].strip("'\"")
            if base in names:
                kind, rng = "owl:ObjectProperty", f"draft:{base}"
            else:
                kind, rng = "owl:DatatypeProperty", PY_TO_XSD.get(base, "xsd:string")
            lines.append(f"draft:{camel(fname)} a {kind} ; rdfs:label \"{fname}\"@en ; "
                         f"rdfs:domain draft:{c.name} ; rdfs:range {rng} .")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def gap_report(classes: list[CodeClass], onto: Ontology | None) -> str:
    code = {norm(c.name): c for c in classes}
    onto_terms: dict[str, str] = {}
    if onto is not None:
        for s in onto.tbox.subjects(DDD.boundedContext, None):
            local = re.split(r"[#/]", str(s))[-1]
            onto_terms[norm(local)] = local
            for lbl in onto.tbox.objects(s, RDFS.label):
                onto_terms.setdefault(norm(str(lbl)), local)
    matched = sorted(code[k].name for k in code if k in onto_terms)
    code_only = sorted(code[k].name for k in code if k not in onto_terms)
    onto_only = sorted({v for k, v in onto_terms.items() if k not in code})
    total = len(code) or 1
    return "\n".join([
        "# Rapport d'écart code ↔ ontologie",
        f"Couverture : {len(matched)}/{len(code)} classes du code ont un terme ontologique ({100 * len(matched) // total} %).",
        "",
        "## Alignés", *(f"- {n}" for n in matched or ["(aucun)"]),
        "", "## Code sans terme ontologique (candidats à définir — ou code à renommer)", *(f"- {n}" for n in code_only or ["(aucun)"]),
        "", "## Termes ontologiques sans code (concepts non implémentés)", *(f"- {n}" for n in onto_only or ["(aucun)"]),
    ]) + "\n"
