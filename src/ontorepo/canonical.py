"""Sérialisation Turtle canonique (déterministe) pour les fichiers écrits par l'outillage.

Même graphe ⇒ mêmes octets : diffs git stables, aucun bruit dû à l'ordre des triplets.
Réservée aux graphes sans nœud anonyme (mémoire, amendements).
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF


def _key(term) -> tuple:
    kind = 0 if isinstance(term, URIRef) else 1
    if isinstance(term, Literal):
        return (kind, str(term), str(term.datatype or ""), term.language or "")
    return (kind, str(term), "", "")


def serialize(graph: Graph, header: str = "") -> str:
    nm = graph.namespace_manager
    used: dict[str, str] = {}

    def fmt(term) -> str:
        if isinstance(term, BNode):
            raise ValueError("La sérialisation canonique n'accepte pas de nœud anonyme.")
        if isinstance(term, URIRef):
            if term == RDF.type:
                return "a"
            try:
                prefix, ns, local = nm.compute_qname(term, generate=False)
                if local and all(c.isalnum() or c in "-_." for c in local) and not local.endswith("."):
                    used[prefix] = str(ns)
                    return f"{prefix}:{local}"
            except (KeyError, ValueError):
                pass
            return f"<{term}>"
        if isinstance(term, Literal) and term.datatype is not None:
            dt = fmt(term.datatype)
            lex = Literal(str(term)).n3()
            return f"{lex}^^{dt}"
        return term.n3()

    blocks = []
    for s in sorted(set(graph.subjects()), key=_key):
        preds = sorted(set(graph.predicates(s)), key=lambda p: (p != RDF.type, str(p)))
        lines = []
        for p in preds:
            objs = sorted(graph.objects(s, p), key=_key)
            lines.append(f"    {fmt(p)} " + " ,\n        ".join(fmt(o) for o in objs))
        blocks.append(f"{fmt(s)}\n" + " ;\n".join(lines) + " .\n")
    prefixes = "".join(f"@prefix {p}: <{ns}> .\n" for p, ns in sorted(used.items()))
    head = "".join(f"# {line}\n" if line else "#\n" for line in header.splitlines()) if header else ""
    return head + prefixes + "\n" + "\n".join(blocks)
