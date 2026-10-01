# 05 — Cas d'usage : supervision de la flotte de PC d'une entreprise de vêtements industriels

## Le métier

Une entreprise loue et entretient des vêtements de travail. Ses sites : **blanchisseries industrielles**
(chaudes et humides), **ateliers de confection**, **entrepôts logistiques**, **siège**. Les vêtements
portent une puce RFID ; des **stations de lecture RFID** tracent leurs passages en lavage et en expédition.
Le département IT supervise tous les PC : postes fixes, portables, terminaux d'atelier durcis, stations RFID.

## Contextes bornés

| Contexte | Termes | Rôle |
|---|---|---|
| Organisation | `orga:Site`, `orga:TypeDeSite` (Blanchisserie, AtelierConfection, Entrepot, Siege) | où sont les machines |
| Parc | `fleet:Equipement` → PosteFixe, Portable, TerminalAtelier, StationRFID | quelles machines |
| Supervision | `mon:Observation`, `mon:Metrique`, `mon:Seuil`, `mon:Alerte` | comment elles vont |

## Les 11 invariants

| Invariant | Règle |
|---|---|
| SiteComplet | un nom, un type |
| NumeroSerieObligatoire | un numéro au format constructeur |
| NumeroSerieUnique | jamais deux fois le même |
| EquipementInstalleSurUnSite | exactement un site connu |
| EquipementDeTypeConcret | jamais un « équipement » générique |
| StationRFIDSurSiteCompatible | seulement en blanchisserie ou entrepôt |
| ObservationComplete | équipement, métrique connue, valeur décimale, horodatage |
| ValeurPlausible | pas de disque à 140 %, pas de CPU à 300 °C |
| SeuilBienForme | par métrique et type de site, jamais par équipement |
| SeuilUnique | un seul seuil par couple (métrique, type de site) |
| AlerteJustifiee | même métrique, bon type de site, valeur strictement au-dessus du seuil |

## Pourquoi le seuil dépend du type de site

Un processeur à 88 °C est normal dans une blanchisserie (seuil 90 °C) mais anormal au siège (75 °C).
Cette connaissance est dans les données de référence (`ontology/data/reference.ttl`), pas dans le code.

## La démonstration

```sh
python -m fleet.demo
```

Sur `examples/metriques.csv` : 9 observations acceptées, 5 alertes justifiées, 3 lignes rejetées
(équipement inconnu, métrique « Humidite » absente de l'ontologie, valeur « beaucoup »). Le résultat est
revalidé par SHACL avant d'être écrit dans `build/supervision.ttl`. Si le code fabriquait une alerte
injustifiée, la publication serait refusée (test `test_publication_refuse_une_alerte_injustifiee`).
