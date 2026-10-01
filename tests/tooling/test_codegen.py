from decimal import Decimal

from rdflib import Graph

from ontorepo import codegen
from ontorepo.graph import Ontology
from ontorepo.runtime import from_graph, to_graph


def test_generation_deterministe(onto):
    assert codegen.generate(onto) == codegen.generate(onto)


def test_code_genere_a_jour(onto):
    assert codegen.check(onto) == []


def test_edition_manuelle_du_code_genere_detectee(sandbox):
    f = sandbox.codegen_output / "parc.py"
    f.write_text(f.read_text(encoding="utf-8") + "\n# retouche manuelle\n", encoding="utf-8")
    assert any(p.check == "codegen" for p in codegen.check(Ontology(sandbox)))


def test_aller_retour_rdf(onto):
    from fleet.domain import ENUMS, Seuil
    seuils = from_graph(onto.data, Seuil, ENUMS)
    assert len(seuils) == 16
    assert all(isinstance(s.valeur_max, Decimal) for s in seuils)
    g = to_graph(seuils, Graph())
    assert from_graph(g, Seuil, ENUMS) == seuils
