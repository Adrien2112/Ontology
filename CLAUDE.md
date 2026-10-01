@AGENTS.md

## Spécifique à Claude Code

- Les hooks de `.claude/settings.json` appliquent ce contrat : refus explicatif avant une édition en zone
  protégée, validation RDF après chaque écriture, `onto check` à la fin de chaque tâche, résumé de la
  mémoire injecté au démarrage.
- Le serveur MCP `ontorepo` (`.mcp.json`) expose `onto_explain`, `onto_glossary`, `onto_query`,
  `onto_validate_turtle`, `onto_memory_recall`, `onto_memory_add`, `onto_check`.
- Si `onto` n'est pas installé : `scripts/onto <commande>` fonctionne sans installation.
