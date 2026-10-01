"""Lecture de `ontorepo.toml` et résolution des chemins du projet."""

from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "ontorepo.toml"


@dataclass(frozen=True)
class ProtectRule:
    level: int
    patterns: tuple[str, ...]


@dataclass
class Project:
    root: Path
    raw: dict = field(repr=False)

    # --- construction --------------------------------------------------------------------

    @classmethod
    def discover(cls, start: Path | str | None = None) -> "Project":
        here = Path(start or Path.cwd()).resolve()
        for candidate in (here, *here.parents):
            if (candidate / CONFIG_FILE).is_file():
                return cls.load(candidate)
        raise FileNotFoundError(f"{CONFIG_FILE} introuvable depuis {here}")

    @classmethod
    def load(cls, root: Path | str) -> "Project":
        root = Path(root).resolve()
        with open(root / CONFIG_FILE, "rb") as fh:
            return cls(root=root, raw=tomllib.load(fh))

    # --- chemins ---------------------------------------------------------------------------

    def path(self, rel: str) -> Path:
        return self.root / rel

    def _section(self, name: str) -> dict:
        return self.raw.get(name, {})

    @property
    def base_iri(self) -> str:
        return self._section("ontology")["base_iri"]

    @property
    def external_dir(self) -> Path:
        return self.path(self._section("ontology")["external"])

    @property
    def meta_dir(self) -> Path:
        return self.path(self._section("ontology")["meta"])

    @property
    def domain_dir(self) -> Path:
        return self.path(self._section("ontology")["domain"])

    @property
    def alignment_dir(self) -> Path:
        return self.path(self._section("ontology")["alignment"])

    @property
    def data_dirs(self) -> list[Path]:
        return [self.path(p) for p in self._section("ontology").get("data", [])]

    @property
    def meta_shapes_dir(self) -> Path:
        return self.path(self._section("shapes")["meta"])

    @property
    def domain_shapes_dir(self) -> Path:
        return self.path(self._section("shapes")["domain"])

    @property
    def fixtures_dir(self) -> Path:
        return self.path(self._section("shapes")["fixtures"])

    @property
    def codegen_output(self) -> Path:
        return self.path(self._section("codegen")["output"])

    @property
    def codegen_package(self) -> str:
        return self._section("codegen")["package"]

    @property
    def memory_dir(self) -> Path:
        return self.path(self._section("memory")["dir"])

    @property
    def amendments_dir(self) -> Path:
        return self.path(self._section("governance")["amendments"])

    @property
    def lock_file(self) -> Path:
        return self.path(self._section("governance")["lock"])

    @property
    def policy_file(self) -> Path:
        return self.path(self._section("governance")["policy"])

    @property
    def state_dir(self) -> Path:
        return self.path(self._section("governance").get("state", ".ontorepo"))

    @property
    def policy(self) -> dict:
        if not self.policy_file.is_file():
            return {}
        with open(self.policy_file, "rb") as fh:
            return tomllib.load(fh)

    # --- protection ------------------------------------------------------------------------

    @property
    def protect_rules(self) -> list[ProtectRule]:
        return [ProtectRule(int(r["level"]), tuple(r["paths"])) for r in self.raw.get("protect", [])]

    @property
    def cli_only(self) -> tuple[str, ...]:
        return tuple(self._section("guard").get("cli_only", []))

    @property
    def forbidden_commands(self) -> tuple[str, ...]:
        return tuple(self._section("guard").get("forbidden_commands", []))

    def relpath(self, path: Path | str) -> str | None:
        """Chemin relatif POSIX à la racine, ou None si hors du dépôt."""
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        try:
            return p.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return None

    def protection_level(self, rel: str) -> int:
        """Niveau minimal d'amendement requis pour modifier `rel` (0 = libre)."""
        level = 0
        for rule in self.protect_rules:
            if matches(rel, rule.patterns):
                level = max(level, rule.level)
        return level

    def protected_files(self) -> dict[str, int]:
        """Tous les fichiers existants couverts par une règle de protection, avec leur niveau."""
        out: dict[str, int] = {}
        for rule in self.protect_rules:
            for pattern in rule.patterns:
                # Path.glob("dir/**") ne renvoie que des répertoires : élargir à "dir/**/*"
                for f in self.root.glob(pattern + "/*" if pattern.endswith("**") else pattern):
                    if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                        rel = f.relative_to(self.root).as_posix()
                        out[rel] = max(out.get(rel, 0), rule.level)
        return dict(sorted(out.items()))

    def is_generated(self, rel: str) -> bool:
        gen = self.codegen_output.relative_to(self.root).as_posix()
        return rel == gen or rel.startswith(gen + "/")


def matches(rel: str, patterns: tuple[str, ...] | list[str]) -> bool:
    """Correspondance glob où `**` traverse les répertoires et `dir/**` couvre tout `dir/`."""
    for pattern in patterns:
        if fnmatch.fnmatchcase(rel, pattern):
            return True
        if pattern.endswith("/**") and (rel == pattern[:-3] or rel.startswith(pattern[:-2])):
            return True
    return False
