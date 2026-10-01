"""Lecture des exports CSV de l'agent de supervision installé sur les PC."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LigneMetrique:
    numero_serie: str
    metrique: str        # nom local d'une valeur de mon:Metrique, ex. "TemperatureCPU"
    valeur: str
    horodatage: str      # ISO 8601


def lire(chemin: Path) -> list[LigneMetrique]:
    with open(chemin, newline="", encoding="utf-8") as fh:
        return [LigneMetrique(r["numero_serie"].strip(), r["metrique"].strip(), r["valeur"].strip(), r["horodatage"].strip())
                for r in csv.DictReader(fh)]
