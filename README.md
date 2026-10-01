# Ontology — un dépôt piloté par l'ontologie

Ce dépôt est une étude **et** une implémentation complète d'un fonctionnement où :

- une **ontologie** (OWL/RDF) est la source de vérité du domaine (Domain-Driven Design) ;
- elle est **alignée sur des standards externes** (W3C SOSA, PROV-O, ORG, SKOS, DCMI), et cet alignement est vérifié ;
- des **règles SHACL** servent de **garde-fou déterministe** : un LLM ne peut pas produire n'importe quoi ;
- le **changement ontologique est permis mais exceptionnel** (amendements gradués N1/N2/N3, tracés, approuvés) ;
- les agents ont une **mémoire persistante** elle-même ontologique (PROV-O), validée et versionnée ;
- le développement suit le **TDD** : chaque règle a ses exemples valides et invalides.

Cas d'usage : le département IT d'une entreprise de **vêtements industriels** supervise sa flotte de PC
(blanchisseries, ateliers de confection, entrepôts, siège ; stations de lecture RFID des vêtements).

## Démarrer

```sh
pip install -e ".[dev]"
onto check            # tous les garde-fous
pytest -q             # 80 tests
python -m fleet.demo  # ingestion de métriques → alertes, résultat revalidé par SHACL
onto explain fleet:StationRFID
onto glossary
```

## Où regarder

| Dossier | Contenu |
|---|---|
| `ontology/external/` | ontologies standard vendorisées (+ `SOURCES.toml`) |
| `ontology/meta/` | méta-ontologies : DDD, gouvernance, mémoire |
| `ontology/domain/` | domaine : Organisation, Parc, Supervision |
| `ontology/alignment/` | alignement obligatoire sur les standards |
| `shapes/meta/`, `shapes/domain/` | règles SHACL : qualité, alignement, mémoire, amendements, invariants métier |
| `tests/ontology/fixtures/` | exemples valides / invalides de chaque invariant (TDD) |
| `src/ontorepo/` | outillage générique `onto` (validation, codegen, verrou, amendements, mémoire, hooks, MCP, adoption) |
| `src/fleet/` | application : modèle **généré**, services de supervision |
| `governance/` | amendements, verrou des zones protégées, politique |
| `memory/` | mémoire des agents (créée par `onto memory add`) |
| `docs/etude/` | **l'étude** : faisabilité, architecture, gouvernance, adoption, cas d'usage, Cursor/Claude |

Contrat des agents : [`AGENTS.md`](AGENTS.md). Étude : [`docs/etude/`](docs/etude/).
