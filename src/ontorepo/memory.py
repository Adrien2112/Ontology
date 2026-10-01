"""Mémoire persistante des agents : graphe PROV-O typé, validé, versionné dans git.

- Un fichier Turtle canonique par entrée (memory/entries/<année>/<id>.ttl) : pas de conflit de fusion.
- Écriture uniquement via ce module (CLI `onto memory` ou outil MCP) : validation SHACL avant écriture.
- Une entrée concerne toujours des termes EXISTANTS de l'ontologie (mem:about).
- Statuts : proposed (agent) → validated (humain) → superseded / retracted.
- Rappel sémantique : par l'ontologie (sous-/super-classes, propriétés liées), pas par similarité vectorielle.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from rdflib import Graph, Literal, URIRef

from .canonical import serialize
from .config import Project
from .graph import Ontology, parse, rdf_files
from .namespaces import DCTERMS, MEM, PROV, RDF, RDFS, XSD, bind_all
from .report import Problem
from .validate import shacl

TYPES = {"decision": MEM.Decision, "lesson": MEM.Lesson, "convention": MEM.Convention,
         "question": MEM.OpenQuestion, "fact": MEM.Fact}
TYPE_PREFIX = {"decision": "D", "lesson": "L", "convention": "C", "question": "Q", "fact": "F"}
TYPE_NAME = {v: k for k, v in TYPES.items()}
STATUSES = {"proposed": MEM.Proposed, "validated": MEM.Validated,
            "superseded": MEM.Superseded, "retracted": MEM.Retracted}
STATUS_NAME = {v: k for k, v in STATUSES.items()}
ENTRY_NS = "https://adrien2112.github.io/memory/entry/"
SESSION_NS = "https://adrien2112.github.io/memory/session/"
AGENT_NS = "https://adrien2112.github.io/memory/agent/"


class MemoryError(ValueError):
    """Écriture mémoire refusée (avec explication actionnable)."""


@dataclass
class Entry:
    id: str
    type: str
    statement: str
    about: list[str]
    status: str
    session: str
    agent: str
    created: str
    evidence: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    review_by: str = ""
    validated_by: str = ""
    proposes_amendment: str = ""

    @property
    def iri(self) -> URIRef:
        return URIRef(ENTRY_NS + self.id)

    def to_graph(self) -> Graph:
        g = bind_all(Graph())
        g.bind("entry", ENTRY_NS)
        g.bind("session", SESSION_NS)
        g.bind("agent", AGENT_NS)
        s = self.iri
        g.add((s, RDF.type, TYPES[self.type]))
        g.add((s, MEM.statement, Literal(self.statement)))
        for a in self.about:
            g.add((s, MEM.about, URIRef(a)))
        g.add((s, MEM.status, STATUSES[self.status]))
        g.add((s, PROV.wasGeneratedBy, URIRef(SESSION_NS + self.session)))
        g.add((s, PROV.wasAttributedTo, URIRef(AGENT_NS + self.agent)))
        g.add((s, DCTERMS.created, Literal(self.created, datatype=XSD.dateTime)))
        for e in self.evidence:
            g.add((s, MEM.evidence, Literal(e)))
        for sup in self.supersedes:
            g.add((s, MEM.supersedes, URIRef(ENTRY_NS + sup)))
        if self.review_by:
            g.add((s, MEM.reviewBy, Literal(self.review_by, datatype=XSD.date)))
        if self.validated_by:
            g.add((s, MEM.validatedBy, Literal(self.validated_by)))
        if self.proposes_amendment:
            g.add((s, MEM.proposesAmendment, URIRef("https://adrien2112.github.io/ontology/amendments/" + self.proposes_amendment)))
        return g


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git(project: Project, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=project.root, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# --- Sessions -------------------------------------------------------------------------------------


def _state_file(project: Project) -> Path:
    return project.state_dir / "session.json"


def current_session(project: Project) -> dict | None:
    f = _state_file(project)
    if f.is_file():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def start_session(project: Project, tool: str, session_id: str | None = None) -> dict:
    """Démarre (ou reprend) une session de travail. État local, non versionné, jusqu'à la première écriture."""
    existing = current_session(project)
    if existing and (session_id is None or existing.get("external_id") == session_id):
        return existing
    started = _now()
    sid = started[:10].replace("-", "") + "-" + hashlib.sha1(f"{tool}{session_id}{started}".encode()).hexdigest()[:6]
    state = {"id": sid, "tool": tool, "external_id": session_id, "started": started,
             "branch": _git(project, "rev-parse", "--abbrev-ref", "HEAD"),
             "commit": _git(project, "rev-parse", "--short", "HEAD"), "entries": [], "reminded": False,
             "stop_blocks": 0}
    project.state_dir.mkdir(parents=True, exist_ok=True)
    _state_file(project).write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def _save_state(project: Project, state: dict) -> None:
    project.state_dir.mkdir(parents=True, exist_ok=True)
    _state_file(project).write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_state(project: Project, **changes) -> dict:
    state = current_session(project) or start_session(project, os.environ.get("ONTO_AGENT", "cli"))
    state.update(changes)
    _save_state(project, state)
    return state


def _session_graph(state: dict, summary: str = "", ended: str = "") -> Graph:
    g = bind_all(Graph())
    g.bind("session", SESSION_NS)
    g.bind("agent", AGENT_NS)
    s = URIRef(SESSION_NS + state["id"])
    g.add((s, RDF.type, MEM.Session))
    g.add((s, MEM.tool, Literal(state["tool"])))
    g.add((s, PROV.startedAtTime, Literal(state["started"], datatype=XSD.dateTime)))
    g.add((s, PROV.wasAssociatedWith, URIRef(AGENT_NS + state["tool"])))
    if state.get("branch"):
        g.add((s, MEM.branch, Literal(state["branch"])))
    if state.get("commit"):
        g.add((s, MEM.startCommit, Literal(state["commit"])))
    if summary:
        g.add((s, MEM.summary, Literal(summary)))
    if ended:
        g.add((s, PROV.endedAtTime, Literal(ended, datatype=XSD.dateTime)))
    agent = URIRef(AGENT_NS + state["tool"])
    g.add((agent, RDF.type, PROV.SoftwareAgent if state["tool"] != "human" else PROV.Person))
    g.add((agent, RDFS.label, Literal(state["tool"])))
    return g


def _write_session(project: Project, state: dict, summary: str = "", ended: str = "") -> Path:
    path = project.memory_dir / "sessions" / f"{state['id']}.ttl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(_session_graph(state, summary, ended),
                              "Session de travail — écrite par `onto memory`, ne pas éditer à la main."), encoding="utf-8")
    return path


def close_session(project: Project, summary: str) -> Path:
    state = current_session(project)
    if not state:
        raise MemoryError("Aucune session en cours.")
    if len(summary.strip()) < 10:
        raise MemoryError("Résumé de session trop court (10 caractères minimum).")
    path = _write_session(project, state, summary, _now())
    _state_file(project).unlink(missing_ok=True)
    return path


# --- Entrées -----------------------------------------------------------------------------------------


def _entry_path(project: Project, entry: Entry) -> Path:
    return project.memory_dir / "entries" / entry.created[:4] / f"{entry.id}.ttl"


def _write_entry(project: Project, entry: Entry) -> Path:
    path = _entry_path(project, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(entry.to_graph(), f"Entrée mémoire {entry.id} — écrite par `onto memory`, ne pas éditer à la main."),
                    encoding="utf-8")
    return path


def load(project: Project) -> list[Entry]:
    g = parse(rdf_files(project.memory_dir / "entries"))
    out = []
    for t, name in TYPE_NAME.items():
        for s in g.subjects(RDF.type, t):
            def v(p):
                x = g.value(s, p)
                return str(x) if x is not None else ""
            out.append(Entry(
                id=str(s)[len(ENTRY_NS):], type=name, statement=v(MEM.statement),
                about=sorted(str(a) for a in g.objects(s, MEM.about)),
                status=STATUS_NAME.get(g.value(s, MEM.status), "proposed"),
                session=v(PROV.wasGeneratedBy)[len(SESSION_NS):], agent=v(PROV.wasAttributedTo)[len(AGENT_NS):],
                created=v(DCTERMS.created), evidence=sorted(str(e) for e in g.objects(s, MEM.evidence)),
                supersedes=sorted(str(x)[len(ENTRY_NS):] for x in g.objects(s, MEM.supersedes)),
                review_by=v(MEM.reviewBy), validated_by=v(MEM.validatedBy),
                proposes_amendment=v(MEM.proposesAmendment).rsplit("/", 1)[-1],
            ))
    return sorted(out, key=lambda e: e.id)


def get(project: Project, entry_id: str) -> Entry:
    for e in load(project):
        if e.id == entry_id:
            return e
    raise MemoryError(f"Entrée mémoire inconnue : {entry_id}")


def resolve_term(onto: Ontology, term: str) -> str:
    """'fleet:StationRFID' ou IRI complet → IRI complet, s'il existe dans la TBox ou les données."""
    g = onto.tbox
    if term.startswith("http://") or term.startswith("https://"):
        iri = URIRef(term)
    elif ":" in term:
        prefix, local = term.split(":", 1)
        ns = dict((p, str(n)) for p, n in g.namespaces()).get(prefix) \
            or dict((p, str(n)) for p, n in onto.data.namespaces()).get(prefix)
        if ns is None:
            raise MemoryError(f"Préfixe inconnu dans '{term}'. Utiliser `onto glossary` pour lister les termes.")
        iri = URIRef(ns + local)
    else:
        raise MemoryError(f"Terme '{term}' ambigu : utiliser la forme préfixée (ex. fleet:StationRFID).")
    if (iri, None, None) not in g and (iri, None, None) not in onto.data:
        raise MemoryError(f"'{term}' n'existe pas dans l'ontologie : une entrée mémoire ne peut concerner qu'un terme existant."
                          " Si le concept manque vraiment, c'est une question ouverte ou un amendement, pas un fait.")
    return str(iri)


def _validate(onto: Ontology, graphs: list[Graph]) -> list[str]:
    data = onto.union(onto.tbox, onto.data, onto.memory, *graphs)
    return [f"{v.shape} @ {v.focus} : {v.message}" for v in shacl(data, onto.meta_shapes)
            if "Memoire" in v.shape]


def add(onto: Ontology, *, type: str, statement: str, about: list[str], evidence: list[str] = (),
        supersedes: list[str] = (), review_by: str = "", proposes_amendment: str = "",
        agent: str | None = None) -> Entry:
    project = onto.project
    if type not in TYPES:
        raise MemoryError(f"Type inconnu '{type}'. Types : {', '.join(TYPES)}.")
    if not about:
        raise MemoryError("Une entrée mémoire doit concerner au moins un terme (--about).")
    iris = [resolve_term(onto, a) for a in about]
    existing = {e.id: e for e in load(project)}
    for sup in supersedes:
        if sup not in existing:
            raise MemoryError(f"--supersedes {sup} : entrée inconnue.")
    if review_by:
        date.fromisoformat(review_by)
    state = current_session(project) or start_session(project, agent or os.environ.get("ONTO_AGENT", "cli"))
    created = _now()
    digest = hashlib.sha1(f"{type}|{statement}|{'|'.join(sorted(iris))}".encode()).hexdigest()[:6]
    entry_id = f"{TYPE_PREFIX[type]}-{created[:10].replace('-', '')}-{digest}"
    if entry_id in existing:
        raise MemoryError(f"Entrée identique déjà enregistrée : {entry_id}.")
    entry = Entry(id=entry_id, type=type, statement=statement.strip(), about=sorted(iris), status="proposed",
                  session=state["id"], agent=agent or state["tool"], created=created,
                  evidence=sorted(evidence), supersedes=sorted(supersedes), review_by=review_by,
                  proposes_amendment=proposes_amendment)
    session_graph = _session_graph(state)
    errors = _validate(onto, [entry.to_graph(), session_graph])
    if errors:
        raise MemoryError("Entrée refusée par les règles de la mémoire :\n  - " + "\n  - ".join(errors))
    _write_session(project, state) if not (project.memory_dir / "sessions" / f"{state['id']}.ttl").exists() else None
    path = _write_entry(project, entry)
    for sup in supersedes:
        old = existing[sup]
        old.status = "superseded"
        _write_entry(project, old)
    state.setdefault("entries", []).append(entry.id)
    _save_state(project, state)
    del path
    return entry


def set_status(project: Project, entry_id: str, status: str, by: str = "") -> Entry:
    entry = get(project, entry_id)
    if status == "validated" and not by:
        raise MemoryError("La validation est un acte humain : préciser --by <nom>.")
    entry.status = status
    if by:
        entry.validated_by = by
    _write_entry(project, entry)
    return entry


# --- Rappel ------------------------------------------------------------------------------------------


def related_terms(onto: Ontology, iri: str) -> set[str]:
    """Le terme, ses super-/sous-classes (transitives), les propriétés qui l'ont pour domaine/portée, son type."""
    g = onto.tbox
    t = URIRef(iri)
    out = {t}
    out |= set(g.transitive_objects(t, RDFS.subClassOf))
    out |= set(g.transitive_subjects(RDFS.subClassOf, t))
    out |= set(g.subjects(RDFS.domain, t)) | set(g.subjects(RDFS.range, t))
    out |= set(g.objects(t, RDFS.domain)) | set(g.objects(t, RDFS.range))
    out |= set(onto.data.objects(t, RDF.type)) | set(g.objects(t, RDF.type))
    return {str(x) for x in out if isinstance(x, URIRef)}


def recall(onto: Ontology, *, about: str | None = None, types: list[str] | None = None,
           statuses: list[str] | None = None, limit: int | None = None) -> list[Entry]:
    entries = load(onto.project)
    if about:
        scope = related_terms(onto, resolve_term(onto, about))
        entries = [e for e in entries if scope & set(e.about)]
    if types:
        entries = [e for e in entries if e.type in types]
    statuses = statuses or ["validated", "proposed"]
    entries = [e for e in entries if e.status in statuses]
    entries.sort(key=lambda e: (e.status != "validated", -int(e.created[:10].replace("-", "") or 0), e.id))
    return entries[:limit] if limit else entries


def short(onto: Ontology, iri: str) -> str:
    try:
        return onto.tbox.namespace_manager.normalizeUri(URIRef(iri))
    except Exception:
        return iri


def render_entries(onto: Ontology, entries: list[Entry]) -> str:
    lines = []
    for e in entries:
        flag = "" if e.status == "validated" else f" _({e.status}, à confirmer)_" if e.status == "proposed" else f" _({e.status})_"
        about = ", ".join(short(onto, a) for a in e.about)
        lines.append(f"- **{e.type} {e.id}**{flag} — {e.statement} _[{about}]_")
    return "\n".join(lines)


def summary(onto: Ontology, max_entries: int | None = None) -> str:
    """Résumé déterministe injecté au démarrage d'une session."""
    max_entries = max_entries or onto.project.policy.get("memory", {}).get("summary_max_entries", 12)
    active = recall(onto)
    decisions = [e for e in active if e.type in ("decision", "convention")]
    lessons = [e for e in active if e.type in ("lesson", "fact")]
    questions = [e for e in active if e.type == "question"]
    parts = ["## Mémoire du dépôt (graphe PROV-O, `onto memory recall --about <terme>` pour approfondir)"]
    budget = max_entries
    for title, group in (("Décisions et conventions", decisions), ("Leçons et constats", lessons),
                         ("Questions ouvertes", questions)):
        if group and budget > 0:
            parts.append(f"\n### {title}\n" + render_entries(onto, group[:budget]))
            budget -= len(group[:budget])
    if len(parts) == 1:
        parts.append("\n(aucune entrée pour l'instant)")
    return "\n".join(parts)


# --- Hygiène -----------------------------------------------------------------------------------------


def lint(onto: Ontology) -> list[Problem]:
    project = onto.project
    problems = []
    entries = load(project)
    ids = {e.id: e for e in entries}
    max_age = project.policy.get("memory", {}).get("proposed_max_age_days", 30)
    today = date.today()
    known = {str(s) for s in onto.tbox.subjects()} | {str(s) for s in onto.data.subjects()}
    for e in entries:
        rel = project.relpath(_entry_path(project, e))
        for a in e.about:
            if a not in known and e.status in ("proposed", "validated"):
                problems.append(Problem("memory", f"{e.id} concerne un terme disparu de l'ontologie : {a}", where=rel,
                                        hint="Retirer (`onto memory retract`) ou remplacer l'entrée (`--supersedes`)."))
        if e.status == "proposed" and e.created:
            age = (today - date.fromisoformat(e.created[:10])).days
            if age > max_age:
                problems.append(Problem("memory", f"{e.id} proposée depuis {age} jours sans validation humaine",
                                        where=rel, severity="warning",
                                        hint="Un humain valide (`onto memory validate`) ou retire l'entrée."))
        if e.review_by and e.status in ("proposed", "validated") and date.fromisoformat(e.review_by[:10]) < today:
            problems.append(Problem("memory", f"{e.id} a dépassé sa date de revue ({e.review_by})", where=rel, severity="warning"))
        for sup in e.supersedes:
            if sup in ids and ids[sup].status != "superseded":
                problems.append(Problem("memory", f"{sup} est remplacée par {e.id} mais n'a pas le statut superseded",
                                        where=rel, severity="warning"))
    return problems
