# ─────────────────────────────────────────────────────────────────────────────
# FICHIER GÉNÉRÉ PAR `onto codegen` À PARTIR DE L'ONTOLOGIE — NE PAS MODIFIER.
# Pour changer ce code : modifier l'ontologie (via un amendement), puis `onto codegen`.
# ─────────────────────────────────────────────────────────────────────────────

"""Contexte borné « Organisation » — Implantation physique de l'entreprise : sites de production, de logistique et sièges."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

__all__ = ['TypeDeSite', 'Site']

class TypeDeSite(Enum):
    """Type de site — Catégorie d'activité d'un site, qui détermine notamment les seuils de supervision applicables."""

    ATELIER_CONFECTION = "https://adrien2112.github.io/ontology/organisation#AtelierConfection"  # Atelier de confection
    BLANCHISSERIE = "https://adrien2112.github.io/ontology/organisation#Blanchisserie"  # Blanchisserie industrielle
    ENTREPOT = "https://adrien2112.github.io/ontology/organisation#Entrepot"  # Entrepôt logistique
    SIEGE = "https://adrien2112.github.io/ontology/organisation#Siege"  # Siège


@dataclass(frozen=True, kw_only=True)
class Site:
    """Site — Lieu physique de l'entreprise où des équipements informatiques sont installés.

    Stéréotype DDD : Racine d'agrégat.
    Invariants : SiteComplet.
    """

    __iri__: ClassVar[str] = "https://adrien2112.github.io/ontology/organisation#Site"
    iri: str = field(metadata={"kind": "id"})
    nom: str = field(metadata={"iri": "https://adrien2112.github.io/ontology/organisation#nom", "kind": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#string"})  # nom
    type_de_site: TypeDeSite = field(metadata={"iri": "https://adrien2112.github.io/ontology/organisation#typeDeSite", "kind": "enum"})  # type de site
