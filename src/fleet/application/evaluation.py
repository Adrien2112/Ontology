"""Cas d'usage : détecter les dépassements de seuils (invariant inv:AlerteJustifiee).

La logique Python reproduit l'invariant ; le résultat est ensuite revalidé par SHACL
(`publier`) : si le code et la règle divergent, c'est la règle qui gagne.
"""

from __future__ import annotations

from ..domain import Alerte, Observation, Seuil
from ..infrastructure.referentiel import Referentiel


def seuil_applicable(observation: Observation, referentiel: Referentiel) -> Seuil | None:
    equipement = referentiel.equipements[observation.sur_equipement]
    site = referentiel.sites[equipement.installe_sur]
    return next((s for s in referentiel.seuils
                 if s.pour_metrique == observation.metrique and s.pour_type_de_site == site.type_de_site), None)


def evaluer(observations: list[Observation], referentiel: Referentiel) -> list[Alerte]:
    alertes = []
    for obs in sorted(observations, key=lambda o: o.iri):
        seuil = seuil_applicable(obs, referentiel)
        if seuil is not None and obs.valeur > seuil.valeur_max:
            alertes.append(Alerte(iri=obs.iri.replace("/obs-", "/alerte-"), declenchee_par=obs.iri, selon_seuil=seuil.iri))
    return alertes
