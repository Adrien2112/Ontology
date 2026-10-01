"""Interrogation de l'ontologie : explication d'un terme, glossaire, SPARQL."""

from __future__ import annotations

from rdflib import URIRef

from . import memory
from .graph import Ontology
from .namespaces import DDD, OWL, RDF, RDFS, SH, SKOS


def _labels(g, s) -> str:
    labels = sorted(f"{o} @{o.language}" for o in g.objects(s, RDFS.label) if getattr(o, "language", None))
    return " | ".join(labels)


def _def(g, s) -> str:
    for o in g.objects(s, SKOS.definition):
        if getattr(o, "language", None) == "fr":
            return str(o)
    return ""


def explain(onto: Ontology, term: str) -> str:
    iri = URIRef(memory.resolve_term(onto, term))
    g = onto.tbox
    s = memory.short
    lines = [f"# {s(onto, str(iri))}", f"IRI : {iri}"]
    if _labels(g, iri):
        lines.append(f"Labels : {_labels(g, iri)}")
    if _def(g, iri):
        lines.append(f"Définition : {_def(g, iri)}")
    types = sorted(s(onto, str(t)) for t in set(g.objects(iri, RDF.type)) | set(onto.data.objects(iri, RDF.type)))
    if types:
        lines.append(f"Types : {', '.join(types)}")
    ctx = g.value(iri, DDD.boundedContext)
    if ctx is not None:
        lines.append(f"Contexte borné : {s(onto, str(ctx))} ; stéréotype : {s(onto, str(g.value(iri, DDD.stereotype)))}")
    supers = sorted(s(onto, str(x)) for x in g.transitive_objects(iri, RDFS.subClassOf) if x != iri)
    if supers:
        lines.append(f"Super-classes (alignement inclus) : {', '.join(supers)}")
    subs = sorted(s(onto, str(x)) for x in g.transitive_subjects(RDFS.subClassOf, iri) if x != iri)
    if subs:
        lines.append(f"Sous-classes : {', '.join(subs)}")
    sup_props = sorted(s(onto, str(x)) for x in g.transitive_objects(iri, RDFS.subPropertyOf) if x != iri)
    if sup_props:
        lines.append(f"Super-propriétés (alignement inclus) : {', '.join(sup_props)}")
    for p, label in ((RDFS.domain, "Domaine"), (RDFS.range, "Portée")):
        v = g.value(iri, p)
        if v is not None:
            lines.append(f"{label} : {s(onto, str(v))}")
    props = sorted(set(g.subjects(RDFS.domain, iri)), key=str)
    if props:
        lines.append("Propriétés :")
        lines += [f"  - {s(onto, str(p))} → {s(onto, str(g.value(p, RDFS.range)))}" for p in props]
    incoming = sorted(set(g.subjects(RDFS.range, iri)), key=str)
    if incoming:
        lines.append("Référencé par : " + ", ".join(s(onto, str(p)) for p in incoming))
    members = sorted(set(g.subjects(RDF.type, iri)), key=str)
    if members and (iri, RDF.type, OWL.Class) in g:
        lines.append("Valeurs : " + ", ".join(s(onto, str(m)) for m in members))
    shapes = onto.domain_shapes
    scope = {iri} | set(g.transitive_objects(iri, RDFS.subClassOf))
    invs = sorted({x for c in scope for x in set(shapes.subjects(SH.targetClass, c)) | set(shapes.subjects(DDD.constrains, c))
                   if (x, RDF.type, DDD.Invariant) in shapes}, key=str)
    if invs:
        lines.append("Invariants applicables :")
        for x in invs:
            lines.append(f"  - {shapes.namespace_manager.normalizeUri(x)} : {_def(shapes, x)}")
    entries = memory.recall(onto, about=str(iri), limit=8)
    if entries:
        lines.append("Mémoire :")
        lines.append(memory.render_entries(onto, entries))
    return "\n".join(lines)


def glossary(onto: Ontology, context: str | None = None) -> str:
    g = onto.tbox
    rows = []
    for c in sorted(set(g.subjects(DDD.boundedContext, None)), key=str):
        ctx = g.value(c, DDD.boundedContext)
        ctx_name = memory.short(onto, str(ctx))
        if context and context not in (ctx_name, str(ctx), str(g.value(ctx, DDD.codeName))):
            continue
        fr = next((str(o) for o in g.objects(c, RDFS.label) if getattr(o, "language", None) == "fr"), "")
        en = next((str(o) for o in g.objects(c, RDFS.label) if getattr(o, "language", None) == "en"), "")
        rows.append(f"| {memory.short(onto, str(c))} | {fr} | {en} | {ctx_name} | {_def(g, c)} |")
    head = "| Terme | FR | EN | Contexte | Définition |\n|---|---|---|---|---|"
    return head + "\n" + "\n".join(rows)


def sparql(onto: Ontology, query: str) -> list[dict]:
    g = onto.union(onto.tbox, onto.data, onto.memory, onto.amendments)
    result = g.query(query)
    if result.type == "ASK":
        return [{"ask": bool(result.askAnswer)}]
    rows = []
    for row in result:
        rows.append({str(var): (memory.short(onto, str(row[var])) if isinstance(row[var], URIRef) else
                                (str(row[var]) if row[var] is not None else None)) for var in result.vars})
    return rows
