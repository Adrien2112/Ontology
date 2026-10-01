"""Cas d'usage : publier un résultat de supervision UNIQUEMENT s'il respecte les invariants."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph

from ontorepo.graph import Ontology
from ontorepo.report import Problem
from ontorepo.runtime import to_graph
from ontorepo.validate import validate_data


class ResultatInvalide(Exception):
    def __init__(self, problemes: list[Problem]):
        self.problemes = problemes
        super().__init__("\n".join(p.render() for p in problemes))


@dataclass(frozen=True)
class Publication:
    graphe: Graph
    nb_objets: int


def publier(onto: Ontology, objets: list) -> Publication:
    graphe = onto.union(onto.data, to_graph(objets))
    problemes = validate_data(onto, graphe)
    if problemes:
        raise ResultatInvalide(problemes)
    return Publication(graphe, len(objets))
