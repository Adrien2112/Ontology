"""Chargement du référentiel (sites, seuils, inventaire) depuis les graphes RDF du dépôt."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph

from ontorepo.graph import Ontology
from ontorepo.runtime import from_graph

from ..domain import ENUMS, Equipement, Portable, PosteFixe, Seuil, Site, StationRFID, TerminalAtelier

TYPES_EQUIPEMENT = (PosteFixe, Portable, TerminalAtelier, StationRFID)


@dataclass(frozen=True)
class Referentiel:
    sites: dict[str, Site]
    equipements: dict[str, Equipement]
    seuils: list[Seuil]

    def equipement_par_numero(self, numero: str) -> Equipement | None:
        return next((e for e in self.equipements.values() if e.numero_serie == numero), None)


def depuis_graphe(graph: Graph) -> Referentiel:
    sites = {s.iri: s for s in from_graph(graph, Site, ENUMS)}
    equipements = {e.iri: e for cls in TYPES_EQUIPEMENT for e in from_graph(graph, cls, ENUMS)}
    seuils = from_graph(graph, Seuil, ENUMS)
    return Referentiel(sites, equipements, seuils)


def charger(onto: Ontology) -> Referentiel:
    return depuis_graphe(onto.data)
