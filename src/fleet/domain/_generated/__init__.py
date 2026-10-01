# ─────────────────────────────────────────────────────────────────────────────
# FICHIER GÉNÉRÉ PAR `onto codegen` À PARTIR DE L'ONTOLOGIE — NE PAS MODIFIER.
# Pour changer ce code : modifier l'ontologie (via un amendement), puis `onto codegen`.
# ─────────────────────────────────────────────────────────────────────────────

"""Modèle de domaine généré depuis l'ontologie."""

from .organisation import Site, TypeDeSite
from .parc import Equipement, Portable, PosteFixe, StationRFID, TerminalAtelier
from .supervision import Alerte, Metrique, Observation, Seuil

__all__ = ['Alerte', 'Equipement', 'Metrique', 'Observation', 'Portable', 'PosteFixe', 'Seuil', 'Site', 'StationRFID', 'TerminalAtelier', 'TypeDeSite']

CLASSES = {c.__iri__: c for c in (Alerte, Equipement, Observation, Portable, PosteFixe, Seuil, Site, StationRFID, TerminalAtelier)}
ENUMS = (Metrique, TypeDeSite,)
