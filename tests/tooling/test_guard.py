import json

from ontorepo import amendments as A
from ontorepo.guard import Action, decide
from ontorepo.hooks import claude, cursor


def edit(project, rel):
    return decide(project, Action("edit", [str(project.root / rel)]))


def shell(project, cmd):
    return decide(project, Action("shell", command=cmd))


def test_code_applicatif_libre(project):
    assert not edit(project, "src/fleet/application/evaluation.py").denied
    assert not edit(project, "tests/domain/test_x.py").denied


def test_hors_depot_ignore(project):
    assert not decide(project, Action("edit", ["/tmp/ailleurs.ttl"])).denied


def test_code_genere_refuse(project):
    d = edit(project, "src/fleet/domain/_generated/parc.py")
    assert d.denied and "onto codegen" in d.reason


def test_memoire_et_gouvernance_via_cli_uniquement(project):
    assert edit(project, "memory/entries/2026/D-x.ttl").denied
    assert edit(project, "governance/amendments/AMD-0099.ttl").denied
    assert edit(project, "governance/protected.lock.toml").denied


def test_ontologie_protegee_mais_pas_verrouillee(sandbox):
    d = edit(sandbox, "ontology/domain/parc.ttl")
    assert d.denied and "PERMIS" in d.reason and "onto amend open" in d.reason
    A.open_amendment(sandbox, level=1, covers=["ontology/domain/parc.ttl"], about=[],
                     why="Ajout d'un type d'équipement imprimante", alternatives="Aucune sous-classe existante ne convient",
                     author="test")
    assert not edit(sandbox, "ontology/domain/parc.ttl").denied
    assert edit(sandbox, "ontology/domain/supervision.ttl").denied  # non couvert


def test_meta_garde_fou_exige_approbation_prealable(sandbox):
    amd = A.open_amendment(sandbox, level=3, covers=["shapes/meta/alignment.ttl"], about=[],
                           why="Ajouter schema.org aux ontologies externes",
                           alternatives="SOSA et PROV-O ne couvrent pas ce besoin", author="agent")
    assert edit(sandbox, "shapes/meta/alignment.ttl").denied
    A.set_status(sandbox, amd.id, "approved", approved_by="humain")
    assert not edit(sandbox, "shapes/meta/alignment.ttl").denied


def test_niveau_insuffisant(sandbox):
    A.open_amendment(sandbox, level=2, covers=["ontology/**"], about=[], why="Refonte large de l'ontologie",
                     alternatives="L'existant est incohérent sur ce point", author="agent")
    assert not edit(sandbox, "ontology/domain/parc.ttl").denied
    assert edit(sandbox, "ontology/meta/ddd.ttl").denied  # N3


def test_shell(project):
    assert shell(project, "onto amend approve AMD-0002 --by moi").denied
    assert shell(project, "cd /x && onto memory validate D-1 --by moi").denied
    assert shell(project, "git push --force origin main").denied
    assert shell(project, "onto lock --update").denied
    assert shell(project, "echo x >> ontology/domain/parc.ttl").denied
    assert shell(project, "sed -i 's/a/b/' src/fleet/domain/_generated/parc.py").denied
    assert not shell(project, "cat ontology/domain/parc.ttl").denied
    assert not shell(project, "onto check").denied
    assert not shell(project, "pytest -q").denied


def test_shell_texte_cite_dans_un_heredoc_non_bloque(project):
    """Un document qui CITE une commande interdite n'est pas l'exécution de cette commande."""
    cmd = "cat > docs/note.md <<'EOF'\nUn humain exécute `onto amend approve AMD-0002 --by nom`.\nEOF"
    assert not shell(project, cmd).denied


def test_adaptateur_claude(project):
    out, code = claude.handle("PreToolUse", {"tool_name": "Write", "tool_input": {
        "file_path": str(project.root / "src/fleet/domain/_generated/parc.py")}}, project)
    assert code == 0 and out["hookSpecificOutput"]["permissionDecision"] == "deny"
    out, _ = claude.handle("PreToolUse", {"tool_name": "Edit", "tool_input": {
        "file_path": str(project.root / "README.md")}}, project)
    assert out is None


def test_adaptateur_cursor(project):
    out, code = cursor.handle("preToolUse", {"tool_name": "Write", "tool_input": {
        "file_path": str(project.root / "shapes/domain/parc.ttl")}}, project)
    assert code == 2 and out["permission"] == "deny" and out["agent_message"]
    out, code = cursor.handle("beforeShellExecution", {"command": "onto check"}, project)
    assert code == 0 and out["permission"] == "allow"
    json.dumps(out)
