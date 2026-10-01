# ─────────────────────────────────────────────────────────────────────────────
# FICHIER GÉNÉRÉ PAR `onto codegen` À PARTIR DE L'ONTOLOGIE — NE PAS MODIFIER.
# Pour changer ce code : modifier l'ontologie (via un amendement), puis `onto codegen`.
# ─────────────────────────────────────────────────────────────────────────────

"""Contexte borné « Parc » — Inventaire des équipements informatiques et de leur implantation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

__all__ = ['Equipement', 'Portable', 'PosteFixe', 'StationRFID', 'TerminalAtelier']

@dataclass(frozen=True, kw_only=True)
class Equipement:
    """Équipement — Matériel informatique inventorié, identifié par son numéro de série et installé sur un site.

    Stéréotype DDD : Racine d'agrégat.
    Invariants : EquipementDeTypeConcret, EquipementInstalleSurUnSite, NumeroSerieObligatoire, NumeroSerieUnique.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/parc#Equipement"
    iri: str = field(metadata={"kind": "id"})
    installe_sur: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/parc#installeSur", "kind": "ref", "range": "https://adrien2112.github.io/ontology/organisation#Site"})  # installé sur
    numero_serie: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/parc#numeroSerie", "kind": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#string"})  # numéro de série


@dataclass(frozen=True, kw_only=True)
class Portable(Equipement):
    """Ordinateur portable — Ordinateur portable, typiquement utilisé par les commerciaux et l'encadrement.

    Stéréotype DDD : Racine d'agrégat.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/parc#Portable"


@dataclass(frozen=True, kw_only=True)
class PosteFixe(Equipement):
    """Poste fixe — Ordinateur de bureau à poste fixe.

    Stéréotype DDD : Racine d'agrégat.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/parc#PosteFixe"


@dataclass(frozen=True, kw_only=True)
class StationRFID(Equipement):
    """Station de lecture RFID — PC piloté d'un portique lisant les puces RFID cousues dans les vêtements pour en tracer les cycles de lavage et d'expédition.

    Stéréotype DDD : Racine d'agrégat.
    Invariants : StationRFIDSurSiteCompatible.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/parc#StationRFID"


@dataclass(frozen=True, kw_only=True)
class TerminalAtelier(Equipement):
    """Terminal d'atelier — PC durci installé en zone de production (poussière, chaleur, vibrations).

    Stéréotype DDD : Racine d'agrégat.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/parc#TerminalAtelier"
