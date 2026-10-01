# 03 — Gouvernance : changer l'ontologie, permis mais exceptionnel

Principe : **l'ontologie n'est jamais verrouillée, elle est protégée.** Le chemin par défaut est de
faire avec l'existant ; le changement reste toujours possible, mais il coûte une justification
proportionnée au risque.

## Les quatre niveaux

| Niveau | Exemples | Qui | Condition |
|---|---|---|---|
| N0 libre | code applicatif, tests, docs | agent | `onto check` vert |
| N1 extension | nouvelle sous-classe alignée, nouvel invariant sur un nouveau terme | agent | amendement ouvert ; **ajout pur** vérifié par la machine ; revue de PR |
| N2 modification | renommer, supprimer, relâcher une règle ; outillage `src/ontorepo` | agent | amendement ouvert ; **approbation humaine avant fusion** (CI) |
| N3 méta-garde-fous | standards externes, méta-règles, hooks, CI, configuration | humain | **approbation humaine avant édition** (hook) |

## Le cycle d'un amendement

```
onto amend open --level N --covers <fichiers> --about <termes> --why "…" --alternatives "…"
        │  (le hook autorise désormais l'édition des fichiers couverts — sauf N3 non approuvé)
        ▼
édition → onto lock --update --amendment AMD-xxxx → onto codegen → onto check
        │  N1 : `onto check` compare à la branche de base ; si un triplet a disparu → requalifier en N2
        │  N2 : `onto amend impact AMD-xxxx` liste code, tests, mémoire concernés
        ▼
PR → CI `onto check --ci` : N2/N3 sans `repo:approvedBy` = échec → humain : `onto amend approve`
        ▼
fusion → `onto amend close AMD-xxxx --status applied`
```

Chaque amendement est un fichier RDF (`governance/amendments/AMD-xxxx.ttl`) validé par
`shapes/meta/amendment.ttl` : justification et **alternatives envisagées** obligatoires (≥ 20 caractères),
fichiers couverts explicites, approbation nominative pour N2/N3.

## Garder l'exception exceptionnelle

- Le refus du hook n'est jamais sec : il rappelle d'abord `onto explain` / `onto glossary`.
- Le champ `alternativesConsidered` force à argumenter contre l'existant.
- `onto stats` et `governance/policy.toml` : au-delà de 3 amendements sur 50 commits, `onto check`
  affiche un avertissement aux humains (sans bloquer).
- Le verrou garde la trace de l'amendement qui a autorisé chaque état de chaque fichier protégé.

## Vécu pendant la construction de ce dépôt

Les hooks se sont activés **pendant** la session qui construisait le dépôt. L'agent a été bloqué deux fois :
par un faux positif (une commande interdite citée dans un texte) et par l'absence d'approbation pour des
fichiers N3. Il a ouvert l'amendement `AMD-0002`, demandé l'accord du propriétaire, puis corrigé et
verrouillé. C'est exactement le comportement visé.
