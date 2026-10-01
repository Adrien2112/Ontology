"""Génération déterministe du modèle de domaine Python à partir de l'ontologie.

Un module par contexte borné (ddd:codeName). Énumérations → Enum ; autres classes → dataclasses
gelées, avec en métadonnées l'IRI de chaque propriété (aller-retour RDF sans perte).
Même ontologie ⇒ mêmes octets : `onto codegen --check` le vérifie en CI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef

from .graph import Ontology
from .namespaces import DDD, OWL, RDF, RDFS, SKOS, SH, XSD
from .report import Problem

HEADER = '''# ─────────────────────────────────────────────────────────────────────────────
# FICHIER GÉNÉRÉ PAR `onto codegen` À PARTIR DE L'ONTOLOGIE — NE PAS MODIFIER.
# Pour changer ce code : modifier l'ontologie (via un amendement), puis `onto codegen`.
# ─────────────────────────────────────────────────────────────────────────────
'''

PY_TYPES = {
    XSD.string: ("str", None), XSD.decimal: ("Decimal", "from decimal import Decimal"),
    XSD.integer: ("int", None), XSD.boolean: ("bool", None),
    XSD.dateTime: ("datetime", "from datetime import datetime"), XSD.date: ("date", "from datetime import date"),
}


def local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1]


def snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def upper_snake(name: str) -> str:
    return snake(name).upper()


def label(g: Graph, s, lang="fr") -> str:
    for o in g.objects(s, RDFS.label):
        if getattr(o, "language", None) == lang:
            return str(o)
    return local(s)


def definition(g: Graph, s) -> str:
    for o in g.objects(s, SKOS.definition):
        if getattr(o, "language", None) == "fr":
            return str(o)
    return ""


@dataclass
class Ctx:
    iri: URIRef
    module: str
    classes: list[URIRef]


def contexts(onto: Ontology) -> list[Ctx]:
    g = onto.tbox
    out = []
    for c in sorted(set(g.subjects(RDF.type, DDD.BoundedContext)), key=str):
        module = str(g.value(c, DDD.codeName) or snake(local(c)))
        classes = sorted(set(g.subjects(DDD.boundedContext, c)), key=str)
        out.append(Ctx(c, module, classes))
    return out


def is_enum(g: Graph, cls) -> bool:
    return (cls, DDD.stereotype, DDD.Enumeration) in g


def internal_parents(g: Graph, cls) -> list[URIRef]:
    return sorted((p for p in g.objects(cls, RDFS.subClassOf) if (p, DDD.boundedContext, None) in g), key=str)


def own_properties(g: Graph, cls) -> list[URIRef]:
    props = {p for p in g.subjects(RDFS.domain, cls)
             if (p, RDF.type, OWL.ObjectProperty) in g or (p, RDF.type, OWL.DatatypeProperty) in g}
    return sorted(props, key=lambda p: local(p))


def invariants_for(onto: Ontology, cls) -> list[str]:
    s = onto.domain_shapes
    found = set(s.subjects(DDD.constrains, cls)) | set(s.subjects(SH.targetClass, cls))
    return sorted(local(x) for x in found if (x, RDF.type, DDD.Invariant) in s)


def topo(g: Graph, classes: list[URIRef]) -> list[URIRef]:
    ordered, seen = [], set()

    def visit(c):
        if c in seen:
            return
        seen.add(c)
        for p in internal_parents(g, c):
            if p in classes:
                visit(p)
        ordered.append(c)

    for c in sorted(classes, key=lambda c: local(c)):
        visit(c)
    return ordered


def generate(onto: Ontology) -> dict[str, str]:
    g = onto.tbox
    ctxs = contexts(onto)
    owner = {c: ctx.module for ctx in ctxs for c in ctx.classes}
    files: dict[str, str] = {}
    for ctx in ctxs:
        imports = {"from __future__ import annotations", "from typing import ClassVar"}
        cross: dict[str, set[str]] = {}
        body: list[str] = []
        enums = [c for c in ctx.classes if is_enum(g, c)]
        others = topo(g, [c for c in ctx.classes if not is_enum(g, c)])
        if enums:
            imports.add("from enum import Enum")
        if others:
            imports.add("from dataclasses import dataclass, field")
        for cls in enums:
            members = sorted(set(g.subjects(RDF.type, cls)), key=lambda m: local(m))
            body.append(f"\nclass {local(cls)}(Enum):")
            body.append(f'    """{label(g, cls)} — {definition(g, cls)}"""\n')
            for m in members:
                body.append(f'    {upper_snake(local(m))} = "{m}"  # {label(g, m)}')
            body.append("")
        for cls in others:
            parents = [local(p) for p in internal_parents(g, cls)]
            stereo = label(g, g.value(cls, DDD.stereotype)) if g.value(cls, DDD.stereotype) else ""
            invs = invariants_for(onto, cls)
            body.append("\n@dataclass(frozen=True, kw_only=True)")
            body.append(f"class {local(cls)}({', '.join(parents)}):" if parents else f"class {local(cls)}:")
            doc = [f"{label(g, cls)} — {definition(g, cls)}", "", f"Stéréotype DDD : {stereo}."]
            if invs:
                doc.append("Invariants : " + ", ".join(invs) + ".")
            body.append('    """' + "\n".join(("    " + d) if d and i else d for i, d in enumerate(doc)) + '\n    """\n')
            body.append(f'    __iri__: ClassVar[str] = "{cls}"')
            if not parents:
                body.append('    iri: str = field(metadata={"kind": "id"})')
            for p in own_properties(g, cls):
                rng = g.value(p, RDFS.range)
                meta = {"iri": str(p)}
                if rng in PY_TYPES:
                    py, imp = PY_TYPES[rng]
                    if imp:
                        imports.add(imp)
                    meta.update(kind="literal", datatype=str(rng))
                elif rng is not None and is_enum(g, rng):
                    py = local(rng)
                    if owner.get(rng) != ctx.module:
                        cross.setdefault(owner[rng], set()).add(py)
                    meta.update(kind="enum")
                else:
                    py = "str"
                    meta.update(kind="ref", range=str(rng))
                meta_txt = ", ".join(f'"{k}": "{v}"' for k, v in meta.items())
                body.append(f"    {snake(local(p))}: {py} = field(metadata={{{meta_txt}}})  # {label(g, p)}")
            body.append("")
        all_names = [local(c) for c in enums + others]
        lines = [HEADER, f'"""Contexte borné « {label(g, ctx.iri)} » — {definition(g, ctx.iri)}"""\n']
        lines += sorted(i for i in imports if i.startswith("from __future__"))
        lines += [""] + sorted(i for i in imports if not i.startswith("from __future__"))
        if cross:
            lines.append("")
        for mod in sorted(cross):
            lines.append(f"from .{mod} import {', '.join(sorted(cross[mod]))}")
        lines.append("")
        lines.append(f"__all__ = {all_names!r}")
        lines += body
        files[f"{ctx.module}.py"] = "\n".join(lines).rstrip() + "\n"
    init = [HEADER, '"""Modèle de domaine généré depuis l\'ontologie."""\n']
    exports = []
    for ctx in ctxs:
        names = [local(c) for c in ctx.classes]
        names = sorted(names)
        init.append(f"from .{ctx.module} import {', '.join(names)}")
        exports += names
    init.append("")
    init.append(f"__all__ = {sorted(exports)!r}")
    init.append("")
    init.append("CLASSES = {c.__iri__: c for c in (" + ", ".join(
        sorted(local(c) for ctx in ctxs for c in ctx.classes if not is_enum(g, c))) + ")}")
    init.append("ENUMS = (" + ", ".join(sorted(local(c) for ctx in ctxs for c in ctx.classes if is_enum(g, c))) + ",)")
    files["__init__.py"] = "\n".join(init) + "\n"
    return dict(sorted(files.items()))


def write(onto: Ontology) -> list[Path]:
    out_dir = onto.project.codegen_output
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = generate(onto)
    for stale in out_dir.glob("*.py"):
        if stale.name not in expected:
            stale.unlink()
    written = []
    for name, text in expected.items():
        path = out_dir / name
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            written.append(path)
    return written


def check(onto: Ontology) -> list[Problem]:
    out_dir = onto.project.codegen_output
    expected = generate(onto)
    problems = []
    rel = onto.project.relpath(out_dir)
    actual = {p.name for p in out_dir.glob("*.py")} if out_dir.exists() else set()
    for name, text in expected.items():
        path = out_dir / name
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            problems.append(Problem("codegen", "code généré désynchronisé de l'ontologie", where=f"{rel}/{name}",
                                    hint="Exécuter `onto codegen` (ne jamais éditer le code généré à la main)."))
    for name in sorted(actual - set(expected)):
        problems.append(Problem("codegen", "fichier généré orphelin", where=f"{rel}/{name}", hint="Exécuter `onto codegen`."))
    return problems
