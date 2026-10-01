"""Les méta-règles protègent l'ontologie elle-même : qualité, alignement externe, traçabilité."""

import shutil

from ontorepo.fixtures import traceability
from ontorepo.graph import Ontology
from ontorepo.validate import validate_meta


def _edit(project, rel, old, new):
    p = project.root / rel
    text = p.read_text(encoding="utf-8")
    assert old in text, old
    p.write_text(text.replace(old, new), encoding="utf-8")


def test_ontologie_du_depot_conforme(onto):
    assert validate_meta(onto) == []
    assert traceability(onto) == []


def test_terme_non_aligne_refuse(sandbox):
    _edit(sandbox, "ontology/alignment/alignment.ttl",
          "fleet:Equipement rdfs:subClassOf sosa:Platform , sosa:FeatureOfInterest .", "")
    problems = validate_meta(Ontology(sandbox))
    assert any("AlignementObligatoire" in p.where and "Equipement" in p.message for p in problems)


def test_alignement_sur_terme_externe_inexistant_refuse(sandbox):
    # Hallucination typique : un terme SOSA qui n'existe pas.
    _edit(sandbox, "ontology/alignment/alignment.ttl", "mon:Observation rdfs:subClassOf sosa:Observation .",
          "mon:Observation rdfs:subClassOf sosa:Measurement .")
    problems = validate_meta(Ontology(sandbox))
    assert any("AlignementObligatoire" in p.where and "Observation" in p.message for p in problems)


def test_classe_sans_label_anglais_refusee(sandbox):
    _edit(sandbox, "ontology/domain/parc.ttl", 'rdfs:label "Poste fixe"@fr , "Desktop computer"@en ;',
          'rdfs:label "Poste fixe"@fr ;')
    problems = validate_meta(Ontology(sandbox))
    assert any("ClasseDeDomaine" in p.where and "PosteFixe" in p.where for p in problems)


def test_classe_sans_contexte_borne_refusee(sandbox):
    p = sandbox.root / "ontology/domain/parc.ttl"
    p.write_text(p.read_text(encoding="utf-8") + '\nfleet:Imprimante a owl:Class ; rdfs:label "Imprimante"@fr .\n',
                 encoding="utf-8")
    problems = validate_meta(Ontology(sandbox))
    assert any("Imprimante" in p.message for p in problems)


def test_invariant_sans_exemples_detecte(sandbox):
    shutil.rmtree(sandbox.fixtures_dir / "SeuilUnique" / "invalid")
    problems = traceability(Ontology(sandbox))
    assert any("SeuilUnique" in p.message and "invalid" in p.message for p in problems)
