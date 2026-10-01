# 01 — Faisabilité : un dépôt « 100 % ontologique » est-il possible ?

## Réponse courte

**Oui, pour le cadre ; non, pour le LLM lui-même.** On ne rend pas un LLM déterministe. On rend
**déterministe ce qu'on accepte de lui** : tout ce qu'il produit (données, termes, code du domaine,
mémoire, changements de règles) passe par des contrôles qui donnent toujours la même réponse pour la
même entrée. Ce dépôt le démontre de bout en bout.

## Ce qui est déterministe ici

| Élément | Mécanisme | Même entrée ⇒ même verdict |
|---|---|---|
| Vocabulaire autorisé | ontologie OWL + méta-règles SHACL (labels, définitions, contexte borné) | oui |
| Rattachement aux standards | règle SHACL-SPARQL d'alignement sur des termes externes **déclarés** | oui |
| Données métier | invariants SHACL (11 règles, 32 exemples) | oui |
| Code du domaine | généré depuis l'ontologie, octet pour octet (`onto codegen --check`) | oui |
| Résultats d'exécution | revalidés par SHACL avant publication (`fleet.application.publication`) | oui |
| Mémoire | entrées typées, validées, sérialisation canonique, résumé trié | oui |
| Changement de l'ontologie | verrou sha256 + amendement gradué + contrôle de conservativité | oui |

## Ce qui ne l'est pas (et ne peut pas l'être)

- **Le texte produit par le LLM** (code applicatif, choix d'implémentation) : il est contraint par les
  tests et les types générés, pas par l'ontologie seule.
- **La pertinence d'un amendement** : la machine vérifie qu'il est justifié, borné et additif (N1) ;
  qu'il soit *bon* reste un jugement humain.
- **L'intention** : un agent peut appeler l'API Python au lieu de la CLI (voir limites, document 06).

## Monde ouvert vs monde fermé

OWL raisonne en « monde ouvert » (ce qui n'est pas dit n'est pas faux) ; un garde-fou a besoin d'un
« monde fermé » (ce qui n'est pas autorisé est refusé). Le choix fait ici : **OWL pour décrire, SHACL pour
contrôler**. Aucun raisonneur OWL n'est exécuté ; les sous-classes sont simplement fusionnées au graphe
validé. C'est plus simple, plus rapide et entièrement prévisible.

## Coût mesuré sur ce dépôt

- `onto check` complet : ~8 s (dont ~4 s pour les 32 exemples d'invariants).
- 80 tests : ~50 s.
- Volume : ~2 000 triplets de TBox (dont ~1 500 venant des standards), 16 seuils, 9 équipements.

Le coût dominant n'est pas la machine mais **la discipline de modélisation** : chaque concept demande
labels FR/EN, définition, contexte borné, alignement et exemples. C'est voulu : c'est ce qui rend le
changement exceptionnel.

## Conclusion

Faisable et utile dès qu'un domaine a un vocabulaire stable et des règles métier explicites. Moins utile
pour du code purement technique (UI, plomberie), qui reste en N0 et n'est encadré que par les tests.
