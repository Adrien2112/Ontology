import pytest

from ontorepo import memory as M
from ontorepo.graph import Ontology


def add(onto, **kw):
    base = dict(type="lesson", statement="Le seuil dépend du type de site, jamais de l'équipement.",
                about=["mon:Seuil"], agent="claude-code")
    base.update(kw)
    return M.add(onto, **base)


def test_terme_inexistant_refuse(sandbox):
    with pytest.raises(M.MemoryError, match="n'existe pas"):
        add(Ontology(sandbox), about=["fleet:Imprimante"])


def test_ajout_et_rappel_semantique(sandbox):
    e = add(Ontology(sandbox), about=["fleet:StationRFID"],
            statement="Les stations RFID chauffent en été dans les blanchisseries.")
    assert e.status == "proposed"
    path = next((sandbox.memory_dir / "entries").rglob(f"{e.id}.ttl"))
    assert "ne pas éditer à la main" in path.read_text(encoding="utf-8")
    onto = Ontology(sandbox)
    # chercher sur la super-classe retrouve l'entrée posée sur la sous-classe
    assert [x.id for x in M.recall(onto, about="fleet:Equipement")] == [e.id]
    assert M.recall(onto, about="orga:Site") == []


def test_resume_deterministe(sandbox):
    add(Ontology(sandbox))
    add(Ontology(sandbox), type="decision", statement="Les observations sont immuables (événements).",
        about=["mon:Observation"])
    onto = Ontology(sandbox)
    assert M.summary(onto) == M.summary(onto)
    assert "Décisions et conventions" in M.summary(onto)


def test_doublon_refuse(sandbox):
    add(Ontology(sandbox))
    with pytest.raises(M.MemoryError, match="identique"):
        add(Ontology(sandbox))


def test_validation_humaine_et_remplacement(sandbox):
    e1 = add(Ontology(sandbox))
    with pytest.raises(M.MemoryError):
        M.set_status(sandbox, e1.id, "validated")
    M.set_status(sandbox, e1.id, "validated", by="Adrien")
    e2 = add(Ontology(sandbox), statement="Le seuil dépend du type de site ET de la métrique.", supersedes=[e1.id])
    assert M.get(sandbox, e1.id).status == "superseded"
    assert [x.id for x in M.recall(Ontology(sandbox), about="mon:Seuil")] == [e2.id]


def test_lint_terme_disparu(sandbox):
    add(Ontology(sandbox), about=["fleet:Portable"], statement="Les portables du siège sortent souvent du réseau.")
    p = sandbox.root / "ontology/domain/parc.ttl"
    text = p.read_text(encoding="utf-8")
    start = text.index("fleet:Portable a owl:Class")
    end = text.index("fleet:TerminalAtelier a owl:Class")
    p.write_text(text[:start] + text[end:], encoding="utf-8")
    assert any("disparu" in pb.message for pb in M.lint(Ontology(sandbox)))


def test_session(sandbox):
    M.start_session(sandbox, "cursor")
    add(Ontology(sandbox))
    path = M.close_session(sandbox, "Ajout d'une leçon sur les seuils.")
    assert path.exists() and M.current_session(sandbox) is None
