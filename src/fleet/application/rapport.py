"""Rapport lisible par le département IT, groupé par site."""

from __future__ import annotations

from collections import defaultdict

from ..domain import Alerte, Observation
from ..infrastructure.referentiel import Referentiel
from .ingestion import Rejet


def _local(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def rediger(observations: list[Observation], alertes: list[Alerte], rejets: list[Rejet], ref: Referentiel) -> str:
    obs = {o.iri: o for o in observations}
    seuils = {s.iri: s for s in ref.seuils}
    par_site: dict[str, list[str]] = defaultdict(list)
    for a in alertes:
        o = obs[a.declenchee_par]
        eq = ref.equipements[o.sur_equipement]
        s = seuils[a.selon_seuil]
        par_site[ref.sites[eq.installe_sur].nom].append(
            f"  - {eq.numero_serie} ({type(eq).__name__}) : {_local(o.metrique.value)} = {o.valeur} > {s.valeur_max} "
            f"[{o.horodatage:%Y-%m-%d %H:%M}]")
    lignes = [f"Rapport de supervision — {len(observations)} observation(s), {len(alertes)} alerte(s), {len(rejets)} rejet(s)"]
    for site in sorted(par_site):
        lignes.append(f"\n{site}")
        lignes += sorted(par_site[site])
    if rejets:
        lignes.append("\nLignes rejetées (non conformes au langage du domaine)")
        lignes += [f"  - {r.ligne.numero_serie},{r.ligne.metrique},{r.ligne.valeur} → {r.motif}" for r in rejets]
    return "\n".join(lignes)
