# 02 — Architecture

```
 Standards externes (N3)     SOSA · PROV-O · ORG · SKOS · DCMI        ontology/external/
          ▲  alignement obligatoire, vérifié (shapes/meta/alignment.ttl)
 Méta-ontologies (N3)        DDD · gouvernance · mémoire               ontology/meta/
          ▲
 Ontologie du domaine (N1/N2) Organisation · Parc · Supervision        ontology/domain/ + alignment/
          ▲  invariants SHACL + exemples valides/invalides             shapes/domain/ + tests/ontology/fixtures/
 Modèle Python GÉNÉRÉ        dataclasses + Enum, 1 module par contexte  src/fleet/domain/_generated/
          ▲
 Services applicatifs (N0)   ingestion · évaluation · publication      src/fleet/application/
          ▲  résultats revalidés par SHACL avant publication
 Mémoire (PROV-O)            décisions · leçons · sessions             memory/
```

## Choix des ontologies externes

| Standard | Pourquoi | Exemples d'alignement |
|---|---|---|
| **SOSA** (W3C) | référence des capteurs et observations | `mon:Observation ⊑ sosa:Observation`, `fleet:Equipement ⊑ sosa:Platform` |
| **PROV-O** (W3C) | provenance : alertes dérivées d'observations, mémoire, amendements | `mon:Alerte ⊑ prov:Entity`, `mon:declencheePar ⊑ prov:wasDerivedFrom` |
| **ORG** (W3C) | sites d'une organisation | `orga:Site ⊑ org:Site` |
| **SKOS** | énumérations, correspondances | `orga:TypeDeSite ⊑ skos:Concept` |
| **DCMI Terms** | identifiants, titres | `fleet:numeroSerie ⊑ dcterms:identifier` |

SOSA et PROV-O sont des copies exactes des dépôts W3C. ORG, SKOS et DCMI sont des **extraits fidèles**
(w3.org était inaccessible depuis l'environnement de construction) ; `onto external verify --online`
vérifie que chaque triplet de l'extrait existe bien en amont.

## Le pipeline `onto check`

Une seule commande, identique pour l'agent (hook de fin), le développeur (pre-commit) et la CI :

1. **lint** : syntaxe RDF, fins de ligne, espaces (diffs déterministes) ;
2. **méta-règles** : qualité des termes, alignement, forme de la mémoire et des amendements ;
3. **traçabilité** : chaque invariant a au moins un exemple valide et un invalide ;
4. **exemples** : valides conformes ; chaque invalide viole son invariant **et lui seul** ;
5. **données** : référentiel et exemples contre les invariants ;
6. **codegen** : le code généré correspond exactement à l'ontologie ;
7. **verrou** : chaque fichier protégé a l'empreinte autorisée par un amendement ;
8. **conservativité** : un amendement N1 n'a rien retiré ni modifié ;
9. **mémoire** : références cassées, entrées périmées ;
10. **rythme** : avertissement si les amendements deviennent fréquents.

## Le code généré

`onto codegen` lit les classes de chaque contexte borné (`ddd:codeName`) et produit des dataclasses
gelées (`frozen=True`) et des `Enum`. Chaque champ porte l'IRI de sa propriété en métadonnée ; le module
générique `ontorepo.runtime` fait l'aller-retour Python ↔ RDF sans perte. Les services applicatifs ne
manipulent que ces types, et `publier()` refuse tout résultat qui viole un invariant : **si le code et la
règle divergent, la règle gagne.**
