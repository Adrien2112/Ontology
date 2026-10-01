"""CLI `onto` : interface unique des humains, des agents, des hooks et de la CI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__


def _project():
    from .config import Project
    return Project.discover()


def _onto(project=None):
    from .graph import Ontology
    return Ontology(project or _project())


def _report(problems, ok_message: str = "") -> int:
    from .report import has_errors, render
    print(render(problems) if problems or not ok_message else ok_message)
    return 1 if has_errors(problems) else 0


# --- commandes -------------------------------------------------------------------------------------


def cmd_check(a) -> int:
    from .check import run_check
    return _report(run_check(_project(), ci=a.ci, base=a.base), "onto check : OK — tous les garde-fous sont verts.")


def cmd_validate(a) -> int:
    from .fixtures import run_fixtures, traceability
    from .graph import parse
    from .validate import validate_data, validate_meta
    onto = _onto()
    if a.files:
        g = onto.union(onto.data, parse([Path(f) for f in a.files]))
        return _report(validate_data(onto, g), "Données conformes aux invariants.")
    problems = []
    if a.scope in ("meta", "all"):
        problems += validate_meta(onto)
    if a.scope in ("data", "all"):
        problems += validate_data(onto)
    if a.scope in ("fixtures", "all"):
        problems += traceability(onto) + run_fixtures(onto)
    return _report(problems, "Validation : OK.")


def cmd_lint(a) -> int:
    from .lint import lint
    return _report(lint(_project()), "Lint RDF : OK.")


def cmd_codegen(a) -> int:
    from . import codegen
    onto = _onto()
    if a.check:
        return _report(codegen.check(onto), "Code généré à jour.")
    written = codegen.write(onto)
    print("\n".join(f"écrit : {onto.project.relpath(p)}" for p in written) or "Code généré déjà à jour.")
    return 0


def cmd_lock(a) -> int:
    from . import amendments, lock
    project = _project()
    if a.update or a.init:
        if not a.amendment:
            print("--amendment AMD-xxxx est obligatoire.", file=sys.stderr)
            return 2
        try:
            amd = amendments.get(project, a.amendment)
            updated = lock.update(project, amd, init=a.init)
        except (KeyError, PermissionError) as exc:
            print(f"Refusé : {exc}", file=sys.stderr)
            return 1
        print(f"Verrou mis à jour ({len(updated)} fichier(s)) par {amd.id}.")
        return 0
    return _report(lock.check(project, ci=a.ci), "Verrou des zones protégées : OK.")


def cmd_amend(a) -> int:
    from . import amendments as A
    project = _project()
    if a.action == "open":
        author = a.author or os.environ.get("ONTO_AGENT") or os.environ.get("USER", "inconnu")
        try:
            amd = A.open_amendment(project, level=a.level, covers=a.covers, about=_resolve(a.about),
                                   why=a.why, alternatives=a.alternatives, author=author)
        except ValueError as exc:
            print(f"Refusé : {exc}", file=sys.stderr)
            return 1
        print(f"{amd.id} ouvert (N{amd.level}). Fichiers autorisés : {', '.join(amd.covers)}")
        if amd.level >= 3:
            print("N3 : l'édition reste bloquée tant qu'un humain n'a pas exécuté `onto amend approve`.")
        elif amd.level == 2:
            print("N2 : édition autorisée ; la fusion exigera une approbation humaine (`onto amend approve`).")
        print("Ensuite : éditer, `onto lock --update --amendment " + amd.id + "`, `onto codegen`, `onto check`.")
        return 0
    if a.action == "list":
        for amd in A.load(project):
            print(f"{amd.id}  N{amd.level}  {amd.status:<9} {', '.join(amd.covers)}  — {amd.justification[:70]}")
        return 0
    if a.action == "show":
        amd = A.get(project, a.id)
        print(json.dumps(amd.__dict__, ensure_ascii=False, indent=2))
        return 0
    if a.action == "approve":
        if not a.by:
            print("--by <nom> est obligatoire : l'approbation est un acte humain nominatif.", file=sys.stderr)
            return 2
        amd = A.set_status(project, a.id, "approved", approved_by=a.by)
        print(f"{amd.id} approuvé par {a.by}.")
        return 0
    if a.action == "close":
        amd = A.set_status(project, a.id, a.status)
        print(f"{amd.id} → {amd.status}.")
        return 0
    if a.action == "requalify":
        amd = A.get(project, a.id)
        if a.level <= amd.level:
            print("La requalification ne peut qu'augmenter le niveau.", file=sys.stderr)
            return 2
        amd.requalified_from, amd.level = amd.level, a.level
        amd.status = "open"
        A.save(project, amd)
        print(f"{amd.id} requalifié N{amd.requalified_from} → N{amd.level}.")
        return 0
    if a.action in ("check", "impact"):
        amd = A.get(project, a.id)
        removed = A.removed_triples(project, amd, a.base)
        if a.action == "check":
            if not removed:
                print(f"{amd.id} : changement purement additif par rapport à {a.base} (compatible N1).")
                return 0
            print(f"{amd.id} : {sum(len(v) for v in removed.values())} triplet(s) retiré(s) ou modifié(s) par rapport à {a.base} :")
            for f, triples in removed.items():
                print(f"  {f}")
                for t in triples[:10]:
                    print(f"    - {' '.join(t)}")
            if amd.level == 1:
                print(f"→ Ce n'est pas un ajout pur : `onto amend requalify {amd.id} --level 2`.")
                return 1
            return 0
        hits = A.impact(project, amd, a.base)
        print(f"Impact de {amd.id} ({len(hits)} fichier(s)) :")
        for f, terms in hits.items():
            print(f"  {f} : {', '.join(terms)}")
        return 0
    return 2


def _resolve(terms):
    if not terms:
        return []
    from .memory import resolve_term
    onto = _onto()
    return [resolve_term(onto, t) for t in terms]


def cmd_memory(a) -> int:
    from . import memory as M
    onto = _onto()
    project = onto.project
    try:
        if a.action == "add":
            e = M.add(onto, type=a.type, statement=a.statement, about=a.about, evidence=a.evidence or [],
                      supersedes=a.supersedes or [], review_by=a.review_by or "",
                      proposes_amendment=a.proposes_amendment or "")
            print(f"Entrée {e.id} enregistrée (statut : proposed — un humain peut la valider).")
        elif a.action == "recall":
            entries = M.recall(onto, about=a.about, types=a.type, statuses=a.status, limit=a.limit)
            print(M.render_entries(onto, entries) or "(aucune entrée)")
        elif a.action == "summary":
            print(M.summary(onto))
        elif a.action == "validate":
            e = M.set_status(project, a.id, "validated", by=a.by)
            print(f"{e.id} validée par {e.validated_by}.")
        elif a.action == "retract":
            e = M.set_status(project, a.id, "retracted")
            print(f"{e.id} retirée.")
        elif a.action == "lint":
            return _report(M.lint(onto), "Mémoire : OK.")
        elif a.action == "start-session":
            s = M.start_session(project, a.tool)
            print(f"Session {s['id']} ({s['tool']}).")
        elif a.action == "close-session":
            path = M.close_session(project, a.summary)
            print(f"Session close : {project.relpath(path)}")
    except M.MemoryError as exc:
        print(f"Refusé : {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_explain(a) -> int:
    from .memory import MemoryError
    from .query import explain
    try:
        print(explain(_onto(), a.term))
    except MemoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def cmd_glossary(a) -> int:
    from .query import glossary
    print(glossary(_onto(), a.context))
    return 0


def cmd_query(a) -> int:
    from .query import sparql
    q = Path(a.file).read_text(encoding="utf-8") if a.file else a.sparql
    print(json.dumps(sparql(_onto(), q), ensure_ascii=False, indent=2))
    return 0


def cmd_stats(a) -> int:
    from .stats import render
    print(render(_project()))
    return 0


def cmd_external(a) -> int:
    from .external import verify
    return _report(verify(_project(), online=a.online), "Ontologies externes : provenance OK.")


def cmd_adopt(a) -> int:
    from . import adopt
    classes = adopt.scan(Path(a.path))
    try:
        onto = _onto()
    except FileNotFoundError:
        onto = None
    draft = adopt.draft_turtle(classes, a.namespace)
    gaps = adopt.gap_report(classes, onto)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "draft.ttl").write_text(draft, encoding="utf-8")
        (out / "ecarts.md").write_text(gaps, encoding="utf-8")
        print(f"Brouillon : {out / 'draft.ttl'} — rapport : {out / 'ecarts.md'}")
    else:
        print(draft)
    print(gaps)
    return 0


def cmd_hook(a) -> int:
    from .hooks.__main__ import main
    return main([a.tool, a.event])


def cmd_mcp(a) -> int:
    from .mcp_server import serve
    serve(_project())
    return 0


# --- analyseur -------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="onto", description="Dépôt piloté par l'ontologie : garde-fous, codegen, mémoire, gouvernance.")
    p.add_argument("--version", action="version", version=f"ontorepo {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("check", help="tous les garde-fous (lint, SHACL, fixtures, codegen, verrou, amendements, mémoire)")
    s.add_argument("--ci", action="store_true", help="mode CI : amendements N2/N3 non approuvés = échec")
    s.add_argument("--base", default=os.environ.get("ONTO_BASE", "HEAD"), help="référence git pour la conservativité N1")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("validate", help="validation SHACL")
    s.add_argument("scope", nargs="?", default="all", choices=["meta", "data", "fixtures", "all"])
    s.add_argument("--file", dest="files", action="append", help="valider ce fichier de données (répétable)")
    s.set_defaults(func=cmd_validate)

    sub.add_parser("lint", help="hygiène des fichiers RDF").set_defaults(func=cmd_lint)

    s = sub.add_parser("codegen", help="générer le modèle Python depuis l'ontologie")
    s.add_argument("--check", action="store_true")
    s.set_defaults(func=cmd_codegen)

    s = sub.add_parser("lock", help="verrou des zones protégées")
    s.add_argument("--check", action="store_true")
    s.add_argument("--ci", action="store_true")
    s.add_argument("--update", action="store_true")
    s.add_argument("--init", action="store_true", help="(humain) verrouiller l'état initial")
    s.add_argument("--amendment")
    s.set_defaults(func=cmd_lock)

    s = sub.add_parser("amend", help="amendements de l'ontologie (permis, exceptionnels, tracés)")
    asub = s.add_subparsers(dest="action", required=True)
    o = asub.add_parser("open")
    o.add_argument("--level", type=int, required=True, choices=[1, 2, 3])
    o.add_argument("--covers", action="append", required=True, help="fichier ou glob autorisé (répétable)")
    o.add_argument("--about", action="append", default=[], help="terme concerné (répétable)")
    o.add_argument("--why", required=True)
    o.add_argument("--alternatives", required=True, help="pourquoi l'existant ne suffit pas")
    o.add_argument("--author")
    asub.add_parser("list")
    for name in ("show", "approve", "close", "requalify", "check", "impact"):
        x = asub.add_parser(name)
        x.add_argument("id")
        if name == "approve":
            x.add_argument("--by", required=True)
        if name == "close":
            x.add_argument("--status", required=True, choices=["applied", "rejected"])
        if name == "requalify":
            x.add_argument("--level", type=int, required=True, choices=[2, 3])
        if name in ("check", "impact"):
            x.add_argument("--base", default=os.environ.get("ONTO_BASE", "HEAD"))
    s.set_defaults(func=cmd_amend)

    s = sub.add_parser("memory", help="mémoire persistante (PROV-O)")
    msub = s.add_subparsers(dest="action", required=True)
    m = msub.add_parser("add")
    m.add_argument("--type", required=True, choices=["decision", "lesson", "convention", "question", "fact"])
    m.add_argument("--statement", required=True)
    m.add_argument("--about", action="append", required=True)
    m.add_argument("--evidence", action="append")
    m.add_argument("--supersedes", action="append")
    m.add_argument("--review-by")
    m.add_argument("--proposes-amendment")
    m = msub.add_parser("recall")
    m.add_argument("--about")
    m.add_argument("--type", action="append")
    m.add_argument("--status", action="append")
    m.add_argument("--limit", type=int)
    msub.add_parser("summary")
    m = msub.add_parser("validate")
    m.add_argument("id")
    m.add_argument("--by", required=True)
    m = msub.add_parser("retract")
    m.add_argument("id")
    msub.add_parser("lint")
    m = msub.add_parser("start-session")
    m.add_argument("--tool", default="human")
    m = msub.add_parser("close-session")
    m.add_argument("--summary", required=True)
    s.set_defaults(func=cmd_memory)

    s = sub.add_parser("explain", help="tout savoir d'un terme")
    s.add_argument("term")
    s.set_defaults(func=cmd_explain)

    s = sub.add_parser("glossary", help="langage ubiquitaire")
    s.add_argument("--context")
    s.set_defaults(func=cmd_glossary)

    s = sub.add_parser("query", help="requête SPARQL")
    s.add_argument("sparql", nargs="?")
    s.add_argument("--file")
    s.set_defaults(func=cmd_query)

    sub.add_parser("stats", help="rythme des amendements").set_defaults(func=cmd_stats)

    s = sub.add_parser("external", help="provenance des ontologies externes")
    s.add_argument("action", choices=["verify"])
    s.add_argument("--online", action="store_true")
    s.set_defaults(func=cmd_external)

    s = sub.add_parser("adopt", help="adoption sur un dépôt existant")
    s.add_argument("action", choices=["scan"])
    s.add_argument("path")
    s.add_argument("--namespace", default="https://example.org/draft#")
    s.add_argument("--out")
    s.set_defaults(func=cmd_adopt)

    s = sub.add_parser("hook", help="(interne) adaptateurs de hooks")
    s.add_argument("tool", choices=["claude", "cursor"])
    s.add_argument("event")
    s.set_defaults(func=cmd_hook)

    sub.add_parser("mcp", help="serveur MCP stdio").set_defaults(func=cmd_mcp)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
