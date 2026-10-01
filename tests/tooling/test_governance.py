"""Gouvernance : verrou, amendements gradués, conservativité N1, approbation N2 en CI."""

import pytest

from ontorepo import amendments as A
from ontorepo import lock
from ontorepo.check import conservativity
from ontorepo.graph import Ontology
from ontorepo.validate import validate_meta

from ..conftest import commit

NEW_CLASS = """
fleet:Imprimante a owl:Class ;
    rdfs:subClassOf fleet:Equipement ;
    rdfs:label "Imprimante d'étiquettes"@fr , "Label printer"@en ;
    skos:definition "Imprimante d'étiquettes de traçabilité des vêtements."@fr ;
    ddd:boundedContext fleet:ContexteParc ;
    ddd:stereotype ddd:AggregateRoot .
"""


def _append(project, rel, text):
    p = project.root / rel
    p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")


def _amend_n1(project, why="Ajouter les imprimantes d'étiquettes"):
    return A.open_amendment(project, level=1, covers=["ontology/domain/parc.ttl"], about=[], why=why,
                            alternatives="Aucun type d'équipement existant ne les représente", author="agent")


def test_verrou_initial_coherent(project):
    assert lock.check(project, ci=True) == []


def test_modification_sans_amendement_detectee(sandbox):
    _append(sandbox, "ontology/domain/parc.ttl", NEW_CLASS)
    assert any(pb.where == "ontology/domain/parc.ttl" for pb in lock.check(sandbox))
    with pytest.raises(PermissionError):
        lock.update(sandbox, A.get(sandbox, "AMD-0001"))  # amendement fondateur appliqué : plus actif


def test_extension_n1_conservative(sandbox):
    amd = _amend_n1(sandbox)
    _append(sandbox, "ontology/domain/parc.ttl", NEW_CLASS)
    lock.update(sandbox, amd)
    assert lock.check(sandbox, ci=True) == []  # N1 : la revue de PR suffit
    assert conservativity(sandbox, "HEAD") == []


def test_n1_qui_modifie_des_triplets_doit_etre_requalifie(sandbox):
    amd = _amend_n1(sandbox, why="Renommer le libellé du poste fixe")
    p = sandbox.root / "ontology/domain/parc.ttl"
    p.write_text(p.read_text(encoding="utf-8").replace('"Poste fixe"@fr', '"Ordinateur fixe"@fr'), encoding="utf-8")
    lock.update(sandbox, amd)
    problems = conservativity(sandbox, "HEAD")
    assert problems and "requalify" in problems[0].hint
    # requalifié en N2 : autorisé localement, mais la CI refuse la fusion sans approbation humaine
    amd.level, amd.requalified_from = 2, 1
    A.save(sandbox, amd)
    assert conservativity(sandbox, "HEAD") == []
    assert lock.check(sandbox, ci=False) == []
    assert any("approuvé" in pb.message for pb in lock.check(sandbox, ci=True))
    A.set_status(sandbox, amd.id, "approved", approved_by="Adrien")
    assert lock.check(sandbox, ci=True) == []


def test_amendement_n1_ne_couvre_pas_un_fichier_n3(sandbox):
    with pytest.raises(ValueError):
        A.open_amendment(sandbox, level=1, covers=["shapes/meta/quality.ttl"], about=[], why="x" * 25,
                         alternatives="y" * 25, author="agent")


def test_amendement_mal_justifie_refuse_par_les_meta_regles(sandbox):
    A.open_amendment(sandbox, level=1, covers=["ontology/data/reference.ttl"], about=[], why="trop court",
                     alternatives="idem", author="agent")
    assert any("Amendement" in p.where for p in validate_meta(Ontology(sandbox)))


def test_verrou_trace_l_amendement_apres_commit(sandbox):
    amd = _amend_n1(sandbox)
    _append(sandbox, "ontology/domain/parc.ttl", NEW_CLASS)
    lock.update(sandbox, amd)
    commit(sandbox)
    assert lock.check(sandbox) == []
    assert lock.read(sandbox)["ontology/domain/parc.ttl"]["amendment"] == amd.id
