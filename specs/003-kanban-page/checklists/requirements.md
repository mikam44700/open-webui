# Specification Quality Checklist: Page Kanban

**Purpose**: Valider que la spécification est complète et exploitable avant de passer au plan
**Created**: 2026-08-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Aucun détail d'implémentation (langages, cadriciels, API)
- [x] Centrée sur la valeur pour l'utilisateur et le besoin métier
- [x] Rédigée pour un lecteur non technique
- [x] Toutes les sections obligatoires sont remplies

## Requirement Completeness

- [x] Aucune question ouverte ne subsiste — **Q1, Q2, Q3 tranchées le 3 août (D1, D2, D3)**
- [x] Les exigences sont testables et sans ambiguïté
- [x] Les critères de réussite sont mesurables
- [x] Les critères de réussite sont indépendants de la technique
- [x] Tous les scénarios d'acceptation sont définis
- [x] Les cas limites sont identifiés
- [x] Le périmètre est délimité
- [x] Les dépendances et hypothèses sont explicites

## Feature Readiness

- [x] Chaque exigence fonctionnelle a un critère d'acceptation clair
- [x] Les parcours utilisateurs couvrent les flux principaux
- [x] La fonctionnalité répond aux critères de réussite mesurables
- [x] Aucun détail d'implémentation ne fuit dans la spécification — le tableau de
  correspondance de D2 nomme les états du moteur, ce qui est assumé : c'est un contrat
  d'affichage, pas un choix technique

## Notes

**Validation du 3 août 2026, itération 2 — toutes les cases passent. Spec prête pour
`/speckit.plan`.**

Les trois questions ont été tranchées par Mike et figées en section « Décisions » :

- **D1 — périmètre** : voir et débloquer. La création de tâche (P3, FR-016) est
  reportée : elle a déjà une voie, la conversation.
- **D2 — six colonnes**, avec le tableau de correspondance des neuf états. « Bloqué »
  et « À valider » restent séparés (décider ≠ relire), et une tâche programmée affiche
  sa date.
- **D3 — page dédiée** de premier niveau, pas un onglet.

Deux exigences méritent d'être signalées parce qu'elles viennent de défauts constatés
ailleurs, pas d'une préférence :

- **FR-002** (aucun état fondu sans que le client le voie) et le cas limite « état
  inconnu » viennent directement du rapport d'écart de hermes-desktop, où `scheduled`
  et `review` tombaient silencieusement dans « todo ».
- **FR-009**, **FR-013** et **SC-005** appliquent la règle d'honnêteté des états : une
  source injoignable n'est pas une panne, et une coupure unique ne produit qu'une seule
  alerte.
