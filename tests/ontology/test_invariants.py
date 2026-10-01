"""TDD des invariants : chaque exemple valide est conforme, chaque contre-exemple isole son invariant."""

from pathlib import Path

import pytest

from ontorepo.config import Project
from ontorepo.fixtures import invariants
from ontorepo.graph import Ontology, parse
from ontorepo.validate import domain_violations

ROOT = Path(__file__).resolve().parents[2]
_ONTO = Ontology(Project.load(ROOT))
_INV = invariants(_ONTO)
CASES = sorted(
    (name, kind, f)
    for name in _INV
    for kind in ("valid", "invalid")
    for f in (_ONTO.project.fixtures_dir / name / kind).glob("*.ttl")
)


def test_chaque_invariant_a_des_exemples():
    for name in _INV:
        kinds = {k for n, k, _ in CASES if n == name}
        assert kinds == {"valid", "invalid"}, f"{name} : exemples manquants"


@pytest.mark.parametrize("name,kind,path", CASES, ids=[f"{n}/{k}/{p.stem}" for n, k, p in CASES])
def test_exemple(name, kind, path):
    shapes_hit = {v.shape for v in domain_violations(_ONTO, parse([path]))}
    if kind == "valid":
        assert shapes_hit == set()
    else:
        assert shapes_hit == {_INV[name]}
