"""Amendements : le changement ontologique est permis, tracé, justifié et proportionné au risque.

Niveaux : N1 extension conservative, N2 modification, N3 méta-garde-fous (voir ontology/meta/repo.ttl).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.compare import graph_diff, to_isomorphic

from .canonical import serialize
from .config import Project, matches
from .graph import parse, rdf_files
from .namespaces import BASE, DCTERMS, RDF, REPO, XSD, bind_all

LEVELS = {1: REPO.N1, 2: REPO.N2, 3: REPO.N3}
RANK = {v: k for k, v in LEVELS.items()}
STATUSES = {"open": REPO.Open, "approved": REPO.Approved, "applied": REPO.Applied, "rejected": REPO.Rejected}
STATUS_NAME = {v: k for k, v in STATUSES.items()}
AMD_NS = BASE + "amendments/"


@dataclass
class Amendment:
    id: str
    level: int
    status: str
    covers: list[str]
    about: list[str] = field(default_factory=list)
    justification: str = ""
    alternatives: str = ""
    author: str = ""
    approved_by: str = ""
    created: str = ""
    requalified_from: int | None = None

    @property
    def active(self) -> bool:
        return self.status in ("open", "approved")

    def covers_path(self, rel: str) -> bool:
        return matches(rel, self.covers)

    def authorizes_edit(self, rel: str, required_level: int) -> bool:
        """Un amendement autorise l'édition s'il est actif, couvre le fichier et a un niveau suffisant.
        Les zones N3 exigent en plus une approbation humaine préalable."""
        if not self.active or not self.covers_path(rel) or self.level < required_level:
            return False
        return required_level < 3 or self.status == "approved"

    def to_graph(self) -> Graph:
        g = bind_all(Graph())
        g.bind("amd", AMD_NS)
        s = URIRef(AMD_NS + self.id)
        g.add((s, RDF.type, REPO.Amendment))
        g.add((s, DCTERMS.identifier, Literal(self.id)))
        g.add((s, REPO.level, LEVELS[self.level]))
        g.add((s, REPO.status, STATUSES[self.status]))
        for c in self.covers:
            g.add((s, REPO.covers, Literal(c)))
        for a in self.about:
            g.add((s, REPO.about, URIRef(a)))
        g.add((s, REPO.justification, Literal(self.justification)))
        g.add((s, REPO.alternativesConsidered, Literal(self.alternatives)))
        g.add((s, REPO.author, Literal(self.author)))
        if self.approved_by:
            g.add((s, REPO.approvedBy, Literal(self.approved_by)))
        if self.requalified_from:
            g.add((s, REPO.requalifiedFrom, LEVELS[self.requalified_from]))
        g.add((s, DCTERMS.created, Literal(self.created, datatype=XSD.dateTime)))
        return g


def _str(g: Graph, s, p) -> str:
    v = g.value(s, p)
    return str(v) if v is not None else ""


def load(project: Project) -> list[Amendment]:
    g = parse(rdf_files(project.amendments_dir))
    out = []
    for s in g.subjects(RDF.type, REPO.Amendment):
        req = g.value(s, REPO.requalifiedFrom)
        out.append(Amendment(
            id=_str(g, s, DCTERMS.identifier),
            level=RANK.get(g.value(s, REPO.level), 0),
            status=STATUS_NAME.get(g.value(s, REPO.status), "open"),
            covers=sorted(str(c) for c in g.objects(s, REPO.covers)),
            about=sorted(str(a) for a in g.objects(s, REPO.about)),
            justification=_str(g, s, REPO.justification),
            alternatives=_str(g, s, REPO.alternativesConsidered),
            author=_str(g, s, REPO.author),
            approved_by=_str(g, s, REPO.approvedBy),
            created=_str(g, s, DCTERMS.created),
            requalified_from=RANK.get(req) if req is not None else None,
        ))
    return sorted(out, key=lambda a: a.id)


def get(project: Project, amd_id: str) -> Amendment:
    for a in load(project):
        if a.id == amd_id:
            return a
    raise KeyError(f"Amendement inconnu : {amd_id}")


def save(project: Project, amd: Amendment) -> Path:
    path = project.amendments_dir / f"{amd.id}.ttl"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"Amendement {amd.id} — écrit par `onto amend`, ne pas éditer à la main.\n"
              "Le changement ontologique est permis mais doit rester l'exception.")
    path.write_text(serialize(amd.to_graph(), header), encoding="utf-8")
    return path


def next_id(project: Project) -> str:
    nums = [int(a.id.split("-")[1]) for a in load(project) if a.id.startswith("AMD-")]
    return f"AMD-{(max(nums) + 1) if nums else 1:04d}"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def open_amendment(project: Project, *, level: int, covers: list[str], about: list[str],
                   why: str, alternatives: str, author: str, amd_id: str | None = None,
                   status: str = "open", approved_by: str = "") -> Amendment:
    if level not in LEVELS:
        raise ValueError("Niveau d'amendement attendu : 1, 2 ou 3 (N0 ne nécessite aucun amendement).")
    for c in covers:
        required = project.protection_level(c) if "*" not in c else 0
        if required > level:
            raise ValueError(f"{c} est protégé au niveau N{required} : un amendement N{level} ne suffit pas.")
    amd = Amendment(id=amd_id or next_id(project), level=level, status=status, covers=sorted(covers),
                    about=sorted(about), justification=why, alternatives=alternatives, author=author,
                    approved_by=approved_by, created=now())
    save(project, amd)
    return amd


def set_status(project: Project, amd_id: str, status: str, approved_by: str = "") -> Amendment:
    amd = get(project, amd_id)
    amd.status = status
    if approved_by:
        amd.approved_by = approved_by
    save(project, amd)
    return amd


# --- Conservativité (N1) et impact (N2) ---------------------------------------------------------


def _git_show(project: Project, ref: str, rel: str) -> str | None:
    try:
        return subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=project.root, capture_output=True,
                              text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_ref_exists(project: Project, ref: str) -> bool:
    try:
        subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], cwd=project.root,
                       capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def covered_files(project: Project, amd: Amendment, base: str) -> list[str]:
    files = {rel for rel in project.protected_files() if amd.covers_path(rel)}
    try:
        listed = subprocess.run(["git", "ls-tree", "-r", "--name-only", base], cwd=project.root,
                                capture_output=True, text=True, check=True).stdout.split()
        files |= {rel for rel in listed if amd.covers_path(rel) and project.protection_level(rel) > 0}
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return sorted(f for f in files if Path(f).suffix in (".ttl", ".trig"))


def removed_triples(project: Project, amd: Amendment, base: str) -> dict[str, list[tuple]]:
    """Triplets présents dans `base` et absents de l'arbre de travail, par fichier couvert."""
    out = {}
    for rel in covered_files(project, amd, base):
        before_text = _git_show(project, base, rel)
        if before_text is None:
            continue  # fichier nouveau : ajout pur
        before = Graph().parse(data=before_text, format="turtle")
        current = project.root / rel
        after = Graph().parse(current, format="turtle") if current.exists() else Graph()
        _, gone, _ = graph_diff(to_isomorphic(before), to_isomorphic(after))
        if len(gone):
            out[rel] = sorted((str(s), str(p), str(o)) for s, p, o in gone)
    return out


def impact(project: Project, amd: Amendment, base: str) -> dict[str, list[str]]:
    """Fichiers du dépôt qui mentionnent les termes retirés ou modifiés par l'amendement."""
    terms = set(amd.about)
    for triples in removed_triples(project, amd, base).values():
        terms |= {s for s, _, _ in triples if s.startswith("http")}
    locals_ = sorted({t.rsplit("#", 1)[-1].rsplit("/", 1)[-1] for t in terms if t})
    hits: dict[str, list[str]] = {}
    for d in ("src", "tests", "memory", "examples", "ontology", "shapes"):
        root = project.root / d
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if not f.is_file() or f.suffix not in (".py", ".ttl", ".md", ".csv"):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            found = [t for t in locals_ if t and t in text]
            if found:
                hits[f.relative_to(project.root).as_posix()] = found
    return hits
