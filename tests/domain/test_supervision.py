"""Cas d'usage de supervision, écrits avant le code (TDD) et adossés aux invariants."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from fleet.application.evaluation import evaluer
from fleet.application.ingestion import ingerer
from fleet.application.publication import ResultatInvalide, publier
from fleet.domain import Alerte, Metrique, Observation
from fleet.infrastructure import referentiel
from fleet.infrastructure.metriques_csv import LigneMetrique

D = "https://adrien2112.github.io/data/"


@pytest.fixture(scope="module")
def ref(onto):
    return referentiel.charger(onto)


def obs(equipement_iri, metrique, valeur):
    return Observation(iri=f"{D}obs-test-{equipement_iri.rsplit('/', 1)[-1]}-{metrique.name.lower()}",
                       sur_equipement=equipement_iri, metrique=metrique, valeur=Decimal(valeur),
                       horodatage=datetime(2026, 10, 1, tzinfo=timezone.utc))


def test_referentiel(ref):
    assert len(ref.sites) == 4 and len(ref.equipements) == 9 and len(ref.seuils) == 16


def test_seuil_depend_du_type_de_site(ref):
    blanchisserie = obs(f"{D}pc-cor-rfid-01", Metrique.TEMPERATURE_CPU, "88")  # seuil 90
    siege = obs(f"{D}pc-par-pt-01", Metrique.TEMPERATURE_CPU, "88")            # seuil 75
    assert [a.declenchee_par for a in evaluer([blanchisserie, siege], ref)] == [siege.iri]


def test_egalite_au_seuil_ne_declenche_pas(ref):
    assert evaluer([obs(f"{D}pc-cor-rfid-01", Metrique.TEMPERATURE_CPU, "90")], ref) == []


def test_ingestion_rejette_ce_qui_sort_du_langage(ref):
    lignes = [
        LigneMetrique("RF-COR-0001", "TemperatureCPU", "70", "2026-10-01T08:00:00Z"),
        LigneMetrique("INCONNU-01", "TemperatureCPU", "70", "2026-10-01T08:00:00Z"),
        LigneMetrique("RF-COR-0001", "Humidite", "70", "2026-10-01T08:00:00Z"),
        LigneMetrique("RF-COR-0001", "TemperatureCPU", "chaud", "2026-10-01T08:00:00Z"),
        LigneMetrique("RF-COR-0001", "TemperatureCPU", "70", "hier"),
    ]
    observations, rejets = ingerer(lignes, ref)
    assert len(observations) == 1 and len(rejets) == 4


def test_publication_valide(onto, ref):
    o = obs(f"{D}pc-par-pt-01", Metrique.TEMPERATURE_CPU, "80")
    assert publier(onto, [o, *evaluer([o], ref)]).nb_objets == 2


def test_publication_refuse_une_alerte_injustifiee(onto):
    """Garde-fou d'exécution : même si le code (ou un LLM) fabrique une alerte, SHACL la refuse."""
    o = obs(f"{D}pc-cor-rfid-01", Metrique.TEMPERATURE_CPU, "70")
    fausse = Alerte(iri=f"{D}alerte-fausse", declenchee_par=o.iri, selon_seuil=f"{D}seuil-temp-blanchisserie")
    with pytest.raises(ResultatInvalide, match="AlerteJustifiee"):
        publier(onto, [o, fausse])


def test_publication_refuse_une_valeur_impossible(onto):
    with pytest.raises(ResultatInvalide, match="ValeurPlausible"):
        publier(onto, [obs(f"{D}pc-par-pt-01", Metrique.UTILISATION_DISQUE, "140")])
