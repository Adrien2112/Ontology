"""Scénario de bout en bout : `python -m fleet.demo [chemin.csv]`."""

from __future__ import annotations

import sys
from pathlib import Path

from ontorepo.config import Project
from ontorepo.graph import Ontology

from .application.evaluation import evaluer
from .application.ingestion import ingerer
from .application.publication import ResultatInvalide, publier
from .application.rapport import rediger
from .infrastructure import metriques_csv, referentiel


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    project = Project.discover()
    onto = Ontology(project)
    ref = referentiel.charger(onto)
    chemin = Path(argv[0]) if argv else project.root / "examples" / "metriques.csv"
    observations, rejets = ingerer(metriques_csv.lire(chemin), ref)
    alertes = evaluer(observations, ref)
    try:
        publication = publier(onto, [*observations, *alertes])
    except ResultatInvalide as exc:
        print("Résultat REFUSÉ par les invariants du domaine :\n" + str(exc))
        return 1
    print(rediger(observations, alertes, rejets, ref))
    out = project.root / "build" / "supervision.ttl"
    out.parent.mkdir(exist_ok=True)
    publication.graphe.serialize(out, format="turtle")
    print(f"\nGraphe validé ({publication.nb_objets} objets publiés) : {project.relpath(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
