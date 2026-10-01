# 06 — Intégration avec Claude Code et Cursor, et limites connues

## Un seul cœur, deux adaptateurs

La décision (autoriser / refuser, et pourquoi) est dans `src/ontorepo/guard.py`, sans dépendre de l'outil.
Deux adaptateurs traduisent les formats :

| Garde-fou | Claude Code (`.claude/settings.json`) | Cursor (`.cursor/hooks.json`) |
|---|---|---|
| Avant une édition | `PreToolUse` → `permissionDecision: deny` | `preToolUse` → `{"permission":"deny"}` + code 2 |
| Avant une commande shell | `PreToolUse` (Bash) | `beforeShellExecution` |
| Après une édition | `PostToolUse` → rapport renvoyé à l'agent | `postToolUse` → `additional_context` |
| Fin de tâche | `Stop` → `decision: block` si `onto check` échoue | `stop` → `followup_message` (relance) |
| Démarrage | `SessionStart` → règles + résumé mémoire | `sessionStart` → `additional_context` |

Les deux appellent `scripts/onto hook <claude|cursor> <événement>`, qui installe les dépendances si besoin.
Les consignes sont dans `AGENTS.md` (lu par Cursor et d'autres agents) ; `CLAUDE.md` l'importe ;
`.cursor/rules/ontology.mdc` y renvoie. Le serveur MCP est déclaré dans `.mcp.json` et `.cursor/mcp.json`.

Les adaptateurs sont testés avec des payloads simulés. **Le fonctionnement réel dans l'IDE Cursor n'a pas
pu être testé depuis l'environnement de construction** : à vérifier sur ton poste (noms exacts des outils
d'édition de Cursor, répertoire courant des hooks). Si Cursor charge aussi `.claude/settings.json`
(option « third-party configs »), les hooks s'exécutent deux fois : c'est sans effet, ils sont idempotents.

## Limites connues (honnêtement)

1. **Les hooks sont une première ligne, pas une garantie.** Ils se désactivent, et un agent peut appeler
   l'API Python directement (`python -c "from ontorepo import amendments …"`) au lieu de la CLI interdite.
   Cela s'est produit pendant la construction de ce dépôt — pour enregistrer une approbation donnée par
   le propriétaire dans la conversation. La vraie garantie est **la CI + la protection de branche +
   CODEOWNERS** : l'approbation est un fichier relu en PR.
2. **Le filtrage shell est heuristique** (marqueurs d'écriture, chemins protégés, corps de heredoc ignorés).
   Il réduit les erreurs de bonne foi ; il n'arrête pas un contournement délibéré.
3. **Extraits d'ontologies externes** (ORG, SKOS, DCMI) : à vérifier en ligne (`onto external verify --online`).
4. **Pas de raisonneur OWL** : les incohérences logiques OWL (classes disjointes, etc.) ne sont pas
   détectées ; seules les règles SHACL écrites le sont.
5. **Performance** : pySHACL est adapté à des milliers de triplets, pas à des millions ; au-delà, valider
   à l'ingestion ou utiliser un moteur SHACL dédié.
