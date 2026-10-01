import io
import json

from rdflib import Graph

from ontorepo import adopt, mcp_server
from ontorepo.cli import main
from ontorepo.query import explain, glossary, sparql


def test_mcp_initialise_liste_et_appelle(project):
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "onto_explain", "arguments": {"term": "fleet:StationRFID"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "onto_validate_turtle", "arguments": {
            "turtle": "@prefix d: <https://adrien2112.github.io/data/> . "
                      "@prefix fleet: <https://adrien2112.github.io/ontology/parc#> . "
                      "d:x a fleet:StationRFID ; fleet:numeroSerie \"RF-PAR-0009\" ; fleet:installeSur d:site-paris ."}}},
    ]
    out = io.StringIO()
    mcp_server.serve(project, io.StringIO("\n".join(json.dumps(m) for m in msgs) + "\n"), out)
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3, 4]
    assert {t["name"] for t in replies[1]["result"]["tools"]} >= {"onto_explain", "onto_memory_add", "onto_check"}
    assert "inv:StationRFIDSurSiteCompatible" in replies[2]["result"]["content"][0]["text"]
    assert replies[3]["result"]["isError"] is True  # station RFID au siège : refusée


def test_explain_glossaire_sparql(onto):
    text = explain(onto, "mon:Alerte")
    assert "prov:Entity" in text and "inv:AlerteJustifiee" in text
    assert "fleet:StationRFID" in glossary(onto)
    rows = sparql(onto, "SELECT (COUNT(?s) AS ?n) WHERE { ?s a <https://adrien2112.github.io/ontology/supervision#Seuil> }")
    assert rows == [{"n": "16"}]


def test_adopt_sur_le_code_genere(project, onto):
    classes = adopt.scan(project.codegen_output)
    assert "Couverture : 11/11" in adopt.gap_report(classes, onto)
    Graph().parse(data=adopt.draft_turtle(classes, "https://example.org/draft#"), format="turtle")


def test_cli_explain(capsys):
    assert main(["explain", "orga:Blanchisserie"]) == 0
    assert "Blanchisserie industrielle" in capsys.readouterr().out
