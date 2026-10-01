from ontorepo.check import run_check


def test_onto_check_vert_en_mode_ci(project):
    problems = run_check(project, ci=True)
    assert [p for p in problems if p.severity == "error"] == []
