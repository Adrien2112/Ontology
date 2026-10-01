import shutil
import subprocess
from pathlib import Path

import pytest

from ontorepo.config import Project
from ontorepo.graph import Ontology

ROOT = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns(".git", "build", "__pycache__", "*.egg-info", ".pytest_cache", ".ontorepo")


@pytest.fixture(scope="session")
def project() -> Project:
    return Project.load(ROOT)


@pytest.fixture(scope="session")
def onto(project) -> Ontology:
    return Ontology(project)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def sandbox(tmp_path) -> Project:
    """Copie isolée du dépôt (avec un commit git initial) que les tests peuvent modifier."""
    dest = tmp_path / "repo"
    shutil.copytree(ROOT, dest, ignore=IGNORE)
    shutil.rmtree(dest / "memory", ignore_errors=True)
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(dest, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return Project.load(dest)


def commit(project: Project, message: str = "wip") -> None:
    _git(project.root, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(project.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message)
