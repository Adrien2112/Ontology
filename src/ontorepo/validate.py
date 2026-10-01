"""Validation SHACL : méta-règles (qualité, alignement, mémoire, amendements) et invariants de domaine."""

from __future__ import annotations

from dataclasses import dataclass

from pyshacl import validate as shacl_validate
from rdflib import BNode, Graph, Literal, URIRef

from .graph import Ontology
from .namespaces import RDF, SH
from .report import Problem


@dataclass(frozen=True)
class Violation:
    shape: str            # forme « racine » (NodeShape) à l'origine de la violation
    focus: str
    path: str
    value: str
    message: str
    severity: str

    def as_problem(self, check: str) -> Problem:
        detail = self.message
        if self.path:
            detail = f"{self.path} : {detail}"
        if self.value:
            detail += f" [valeur : {self.value}]"
        return Problem(check, detail, where=f"{self.shape} @ {self.focus}",
                       severity="error" if self.severity == "Violation" else "warning")


def _short(graph: Graph, node) -> str:
    if node is None:
        return ""
    if isinstance(node, URIRef):
        try:
            return graph.namespace_manager.normalizeUri(node)
        except Exception:  # pragma: no cover - IRI non abrégeable
            return f"<{node}>"
    if isinstance(node, Literal):
        return str(node)
    return "[]" if isinstance(node, BNode) else str(node)


def _root_shape(shapes: Graph, shape):
    """Remonte d'une forme de propriété anonyme à la NodeShape qui la déclare."""
    seen = set()
    while isinstance(shape, BNode) and shape not in seen:
        seen.add(shape)
        parents = list(shapes.subjects(SH.property, shape)) or list(shapes.subjects(SH.sparql, shape))
        if not parents:
            break
        shape = parents[0]
    return shape


def shacl(data: Graph, shapes: Graph, ont: Graph | None = None) -> list[Violation]:
    if ont is not None:  # la TBox est fusionnée explicitement (sous-classes, énumérations)
        merged = Graph()
        for g in (data, ont):
            for t in g:
                merged.add(t)
        merged.namespace_manager = data.namespace_manager
        data = merged
    conforms, results, _ = shacl_validate(
        data, shacl_graph=shapes, inference="none",
        advanced=True, allow_warnings=True, meta_shacl=False,
    )
    if not isinstance(results, Graph):  # pyshacl renvoie un ValidationFailure si les formes sont invalides
        raise RuntimeError(f"Formes SHACL invalides : {results}")
    if conforms:
        return []
    out = []
    for r in results.subjects(RDF.type, SH.ValidationResult):
        source = results.value(r, SH.sourceShape)
        root = _root_shape(shapes, source)
        messages = sorted(str(m) for m in results.objects(r, SH.resultMessage))
        out.append(Violation(
            shape=_short(shapes, root),
            focus=_short(data, results.value(r, SH.focusNode)),
            path=_short(shapes, results.value(r, SH.resultPath)) if isinstance(results.value(r, SH.resultPath), URIRef) else "",
            value=_short(data, results.value(r, SH.value)),
            message=" / ".join(messages) or "violation",
            severity=str(results.value(r, SH.resultSeverity)).rsplit("#", 1)[-1],
        ))
    return sorted(set(out), key=lambda v: (v.shape, v.focus, v.path, v.value, v.message))


def validate_meta(onto: Ontology) -> list[Problem]:
    """TBox + données + mémoire + amendements contre les méta-règles."""
    data = onto.union(onto.tbox, onto.data, onto.memory, onto.amendments)
    return [v.as_problem("validate.meta") for v in shacl(data, onto.meta_shapes)]


def validate_data(onto: Ontology, data: Graph | None = None) -> list[Problem]:
    """Données (référence + exemples, ou graphe fourni) contre les invariants de domaine."""
    data = onto.data if data is None else data
    return [v.as_problem("validate.data") for v in shacl(data, onto.domain_shapes, ont=onto.tbox)]


def domain_violations(onto: Ontology, data: Graph) -> list[Violation]:
    return shacl(data, onto.domain_shapes, ont=onto.tbox)
