# 04 — Adopter ces techniques sur un dépôt existant

Un dépôt réel a déjà du code, un vocabulaire implicite et des règles cachées dans des `if`. Tout
réécrire n'est pas réaliste. La stratégie recommandée est **progressive** (« étrangleur ») : on encadre
d'abord, on contraint ensuite, on génère enfin.

## Étape 0 — Installer l'outillage sans rien contraindre (1 jour)

- Copier `src/ontorepo/` et adapter `ontorepo.toml` (chemins, espaces de noms, zones protégées vides).
- Ajouter `onto check` en CI en mode informatif (job autorisé à échouer).

## Étape 1 — Rétro-ingénierie du vocabulaire (quelques jours)

```sh
onto adopt scan src/mon_module --namespace https://exemple.org/draft# --out build/adopt
```

Produit `draft.ttl` (classes, énumérations, champs du code Python) et `ecarts.md` (couverture code ↔
ontologie). Le brouillon n'est **pas** l'ontologie : un humain du métier le relit, renomme selon le
langage du métier, écrit les définitions, choisit les contextes bornés.

## Étape 2 — Aligner et publier le noyau (1 à 2 semaines)

- Choisir les standards de référence du domaine (SOSA, PROV-O, schema.org, FIBO, HL7 FHIR…).
- Aligner chaque terme ; ce qui ne s'aligne pas est souvent mal compris ou mal nommé.
- Amendement fondateur + `onto lock --init`.

## Étape 3 — Règles en avertissement, puis en blocage

- Écrire les invariants les plus coûteux en incidents d'abord, avec exemples valides/invalides.
- Les passer d'abord en `sh:severity sh:Warning`, mesurer, puis en `sh:Violation`.
- Valider les **données réelles** (exports, fichiers de configuration) : c'est souvent là que les
  premiers gains apparaissent.

## Étape 4 — Garde-fous des agents

- Ajouter `.claude/settings.json`, `.cursor/hooks.json`, `AGENTS.md`, le serveur MCP.
- Protéger d'abord l'ontologie et les règles (N1/N3) ; laisser le code en N0.

## Étape 5 — Générer le modèle pour le code neuf uniquement

- Nouveaux modules : types générés + publication revalidée.
- Code existant : adaptateurs (anti-corruption layer) qui convertissent vers les types générés ; le
  rapport d'écart de `onto adopt` suit la progression.

## Ce qui rend l'adoption difficile

| Difficulté | Atténuation |
|---|---|
| Personne ne « possède » le vocabulaire | nommer un propriétaire par contexte borné (CODEOWNERS) |
| Coût de modélisation initial | commencer par 1 contexte borné, celui qui a le plus d'incidents |
| Langages autres que Python | l'outillage RDF/SHACL est indépendant du langage ; seul `codegen` et `adopt` sont à porter |
| Données volumineuses | valider par lots ou à l'entrée (ingestion), pas tout le graphe à chaque commit |
| Résistance à la friction | N1 reste léger (revue de PR) ; seuls N2/N3 exigent une approbation |
