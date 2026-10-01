# ─────────────────────────────────────────────────────────────────────────────
# FICHIER GÉNÉRÉ PAR `onto codegen` À PARTIR DE L'ONTOLOGIE — NE PAS MODIFIER.
# Pour changer ce code : modifier l'ontologie (via un amendement), puis `onto codegen`.
# ─────────────────────────────────────────────────────────────────────────────

"""Contexte borné « Supervision » — Collecte des métriques des équipements et détection des dépassements de seuils."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from .organisation import TypeDeSite

__all__ = ['Metrique', 'Alerte', 'Observation', 'Seuil']

class Metrique(Enum):
    """Métrique — Grandeur mesurée sur un équipement."""

    JOURS_SANS_CONNEXION = "https://adrien2112.github.io/ontology/supervision#JoursSansConnexion"  # Jours sans connexion
    TEMPERATURE_CPU = "https://adrien2112.github.io/ontology/supervision#TemperatureCPU"  # Température processeur (°C)
    UTILISATION_CPU = "https://adrien2112.github.io/ontology/supervision#UtilisationCPU"  # Utilisation processeur (%)
    UTILISATION_DISQUE = "https://adrien2112.github.io/ontology/supervision#UtilisationDisque"  # Occupation disque (%)


@dataclass(frozen=True, kw_only=True)
class Alerte:
    """Alerte — Événement émis lorsqu'une observation dépasse le seuil applicable au type de site de l'équipement.

    Stéréotype DDD : Événement de domaine.
    Invariants : AlerteJustifiee.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/supervision#Alerte"
    iri: str = field(metadata={"kind": "id"})
    declenchee_par: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#declencheePar", "kind": "ref", "range": "https://adrien2112.github.io/ontology/supervision#Observation"})  # déclenchée par
    selon_seuil: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#selonSeuil", "kind": "ref", "range": "https://adrien2112.github.io/ontology/supervision#Seuil"})  # selon le seuil


@dataclass(frozen=True, kw_only=True)
class Observation:
    """Observation — Mesure horodatée d'une métrique sur un équipement.

    Stéréotype DDD : Entité.
    Invariants : ObservationComplete, ValeurPlausible.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/supervision#Observation"
    iri: str = field(metadata={"kind": "id"})
    horodatage: datetime = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#horodatage", "kind": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#dateTime"})  # horodatage
    metrique: Metrique = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#metrique", "kind": "enum"})  # métrique
    sur_equipement: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#surEquipement", "kind": "ref", "range": "https://adrien2112.github.io/ontology/parc#Equipement"})  # sur l'équipement
    valeur: Decimal = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#valeur", "kind": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#decimal"})  # valeur


@dataclass(frozen=True, kw_only=True)
class Seuil:
    """Seuil — Valeur maximale tolérée d'une métrique pour un type de site donné.

    Stéréotype DDD : Objet-valeur.
    Invariants : SeuilBienForme, SeuilUnique.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/supervision#Seuil"
    iri: str = field(metadata={"kind": "id"})
    pour_metrique: Metrique = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#pourMetrique", "kind": "enum"})  # pour la métrique
    pour_type_de_site: TypeDeSite = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#pourTypeDeSite", "kind": "enum"})  # pour le type de site
    valeur_max: Decimal = field(metadata={"iri": "https://adrien2112.github.io/ontology/supervision#valeurMax", "kind": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#decimal"})  # valeur maximale
