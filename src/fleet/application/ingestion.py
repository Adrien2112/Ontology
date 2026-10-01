"""Cas d'usage : transformer des lignes de métriques brutes en observations du domaine.

Toute ligne qui ne correspond pas au langage ubiquitaire (équipement inconnu, métrique hors
énumération, valeur ou date illisible) est rejetée avec son motif — jamais « devinée ».
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ..domain import Metrique, Observation
from ..infrastructure.metriques_csv import LigneMetrique
from ..infrastructure.referentiel import Referentiel

DATA = "https://adrien2112.github.io/data/"


@dataclass(frozen=True)
class Rejet:
    ligne: LigneMetrique
    motif: str


def metrique_depuis_nom(nom: str) -> Metrique | None:
    return next((m for m in Metrique if m.value.rsplit("#", 1)[-1] == nom), None)


def iri_observation(numero: str, metrique: Metrique, horodatage: datetime) -> str:
    stamp = re.sub(r"[^0-9]", "", horodatage.isoformat())[:14]
    return f"{DATA}obs-{numero.lower()}-{metrique.value.rsplit('#', 1)[-1].lower()}-{stamp}"


def ingerer(lignes: list[LigneMetrique], referentiel: Referentiel) -> tuple[list[Observation], list[Rejet]]:
    observations, rejets = [], []
    for ligne in lignes:
        equipement = referentiel.equipement_par_numero(ligne.numero_serie)
        if equipement is None:
            rejets.append(Rejet(ligne, f"équipement inconnu de l'inventaire : {ligne.numero_serie}"))
            continue
        metrique = metrique_depuis_nom(ligne.metrique)
        if metrique is None:
            rejets.append(Rejet(ligne, f"métrique hors ontologie : {ligne.metrique}"))
            continue
        try:
            valeur = Decimal(ligne.valeur)
        except InvalidOperation:
            rejets.append(Rejet(ligne, f"valeur non numérique : {ligne.valeur!r}"))
            continue
        try:
            horodatage = datetime.fromisoformat(ligne.horodatage.replace("Z", "+00:00"))
        except ValueError:
            rejets.append(Rejet(ligne, f"horodatage illisible : {ligne.horodatage!r}"))
            continue
        observations.append(Observation(
            iri=iri_observation(ligne.numero_serie, metrique, horodatage), sur_equipement=equipement.iri,
            metrique=metrique, valeur=valeur, horodatage=horodatage))
    return observations, rejets
