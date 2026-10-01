# Contrat de travail des agents (Claude Code, Cursor, autres)

Ce dépôt fonctionne **à partir d'une ontologie**. L'ontologie dit ce qui existe, les règles SHACL disent ce
qui est permis, le code du domaine en est généré. Ton rôle : travailler **avec** ce cadre, pas autour.

## 1. Avant d'écrire quoi que ce soit

- Cherche le terme : `onto explain <terme>` (ex. `onto explain fleet:StationRFID`) ou `onto glossary`.
  Outils MCP équivalents : `onto_explain`, `onto_glossary`, `onto_query`.
- Consulte la mémoire : `onto memory recall --about <terme>`.
- N'invente **aucun** concept, propriété, métrique ou valeur. Si le langage du domaine ne permet pas
  d'exprimer le besoin, c'est une question ouverte ou un amendement — pas une improvisation.

## 2. Boucle TDD

1. Si une règle métier est en jeu : écrire d'abord un contre-exemple dans
   `tests/ontology/fixtures/<Invariant>/invalid/`, puis un exemple dans `.../valid/`.
2. Écrire le test pytest (rouge).
3. `onto codegen` si l'ontologie a changé (le code de `src/fleet/domain/_generated/` ne s'édite jamais).
4. Implémenter dans `src/fleet/application/` ou `src/fleet/infrastructure/`.
5. `onto check` doit être vert, puis `pytest -q`.

## 3. Zones et niveaux

| Niveau | Où | Comment modifier |
|---|---|---|
| N0 libre | `src/fleet/application`, `src/fleet/infrastructure`, `tests/`, `docs/`, `examples/*.csv` | directement |
| N1 extension | `ontology/domain`, `ontology/alignment/alignment.ttl`, `ontology/data`, `shapes/domain` | `onto amend open --level 1 …` (ajout pur) |
| N2 modification | idem + `src/ontorepo/` (outillage) | `onto amend open --level 2 …` ; un humain approuve avant fusion |
| N3 méta-garde-fous | `ontology/external`, `ontology/meta`, `shapes/meta`, `ontorepo.toml`, hooks, CI | proposition seulement ; un humain approuve **avant** l'édition |
| CLI seulement | `memory/`, `governance/amendments/`, `governance/protected.lock.toml` | `onto memory …`, `onto amend …`, `onto lock …` |

**Changer l'ontologie est permis, mais c'est l'exception.** Avant d'ouvrir un amendement, explique dans
`--alternatives` pourquoi les termes existants ne suffisent pas. Un amendement N1 qui retire ou modifie un
triplet est détecté et doit être requalifié en N2.

Procédure type :

```sh
onto amend open --level 1 --covers ontology/domain/parc.ttl --about fleet:Equipement \
  --why "…" --alternatives "pourquoi l'existant ne suffit pas"
# éditer, puis :
onto lock --update --amendment AMD-xxxx
onto codegen && onto check
```

Tu ne peux pas approuver toi-même (`onto amend approve`, `onto memory validate` sont réservés aux humains).

## 4. Mémoire

- Consigne ce qui mérite d'être retenu : `onto memory add --type decision|lesson|convention|question|fact
  --about <terme existant> --statement "…" [--evidence fichier]`.
- Tes entrées sont `proposed` ; un humain les valide. Pour corriger une entrée : `--supersedes <id>`.
- En fin de session : `onto memory close-session --summary "…"`.

## 5. Fin de tâche

`onto check` vert. Le hook de fin de tâche le vérifie et te relance sinon. Ne contourne jamais une règle :
si elle te semble fausse, ouvre un amendement ou une question ouverte.
