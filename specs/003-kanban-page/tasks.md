# Tasks: Page Kanban

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-08-03

**Périmètre** : voir (US1) et débloquer (US2). La création de tâche (US3) est reportée.

## Ordre choisi

Les tâches sont rangées pour qu'**une page s'affiche à l'écran dès la fin de la phase 2**,
avant même qu'il y ait des tâches dedans. Une entrée dans la navigation qui ouvre un écran
disant honnêtement ce qu'elle sait vaut mieux qu'un lot de tests verts sans rien à montrer.

Les deux modules de logique pure partent en test-d'abord : ils portent toute la
correspondance des états et toute la règle d'honnêteté, et c'est là que les défauts se
cachent.

---

## Phase 1 — Setup

- [ ] T001 Vérifier que le plugin kanban répond sur l'instance de développement : `docker compose -f docker-compose.fr.yaml exec hermes hermes kanban list`, et noter si le registre est absent (le cas « pas installé » doit rester testable)

---

## Phase 2 — Fondations (bloquant pour toutes les histoires)

**Objectif : une entrée dans la navigation qui ouvre une page honnête sur ce qu'elle sait.**

- [ ] T002 [P] Écrire les tests de correspondance des états dans `src/lib/kanban/colonnes.test.ts` : les neuf états canoniques listés en dur, un état inconnu qui ne tombe dans aucune colonne, et la règle du bouton de déblocage par type de blocage
- [ ] T003 [P] Écrire les tests d'honnêteté dans `src/lib/kanban/etat.test.ts` : `ok`, `absent` (404) et `injoignable` (503) distincts, et une seule alerte chapeau quand plusieurs sources tombent pour la même coupure
- [ ] T004 [P] Implémenter `src/lib/kanban/colonnes.ts` : table des six colonnes, cas par défaut visible pour un état inconnu, et `peutEtreDebloquee()` qui ne rend vrai que sur `needs_input` ou un blocage sans type
- [ ] T005 [P] Implémenter `src/lib/kanban/etat.ts` : dérivation des trois états et de l'alerte chapeau unique
- [ ] T006 Créer le routeur `backend/open_webui/routers/kanban.py` avec les cinq routes du contrat, en important la session authentifiée et le traitement d'erreurs de `routers/hermes.py` plutôt qu'en les recopiant
- [ ] T007 Filtrer le corps du `PATCH` dans `backend/open_webui/routers/kanban.py` : seul le champ `statut` est transmis, seule la valeur `ready` est acceptée, tout le reste est refusé en 400
- [ ] T008 Enregistrer le routeur dans `backend/open_webui/main.py` sous `/api/v1/kanban`, à côté du routeur `hermes`
- [ ] T009 [P] Créer le client `src/lib/apis/kanban/index.ts` : un appel par route du contrat, aucune adresse de moteur côté navigateur
- [ ] T010 Ajouter l'entrée de premier niveau dans `src/lib/components/layout/Sidebar.svelte` : `getMenuItemMeta`, `menuItemPathPrefixes` et la règle de visibilité réservée à l'administrateur
- [ ] T011 Créer `src/routes/(app)/kanban/+page.svelte` : en-tête, chargement de l'état, et affichage des trois cas (tableau, registre absent, moteur injoignable). **Premier écran visible.**
- [ ] T012 [P] Ajouter les clés i18n du socle dans `src/lib/i18n/locales/en-US/translation.json` et `src/lib/i18n/locales/fr-FR/translation.json`

**Point de contrôle** : reconstruire, ouvrir `localhost:3000`, cliquer sur l'entrée Kanban. L'écran doit dire ce qu'il sait, même sans aucune tâche.

---

## Phase 3 — US1 : voir ce que l'assistant fait (P1)

**Objectif** : identifier en quelques secondes ce qui tourne, ce qui attend, ce qui bloque.

**Test indépendant** : ouvrir la page avec des tâches dans plusieurs états et vérifier que le compte affiché égale celui de `hermes kanban list`.

- [ ] T013 [P] [US1] Créer `src/lib/components/kanban/BandeauEtat.svelte` : l'alerte chapeau unique, et la phrase sans alerte quand le registre est simplement absent
- [ ] T014 [P] [US1] Créer `src/lib/components/kanban/CarteTache.svelte` : titre, responsable, type de blocage en clair, mention « attend le temps » pour une tâche programmée, signalement d'un état inconnu
- [ ] T015 [US1] Créer `src/lib/components/kanban/ColonneKanban.svelte` : titre, compte, pile de cartes, et message propre quand la colonne est vide
- [ ] T016 [US1] Assembler les six colonnes dans `src/routes/(app)/kanban/+page.svelte` à partir de `colonnes.ts`
- [ ] T017 [P] [US1] Créer `src/lib/components/kanban/SelecteurTableau.svelte` : quel tableau on regarde, et bascule quand plusieurs existent
- [ ] T018 [US1] Créer `src/lib/components/kanban/FicheTache.svelte` : consigne, avancement, résultat, échanges, dernière erreur, compteur de re-blocages
- [ ] T019 [US1] Ajouter le sondage à 5 secondes dans `src/routes/(app)/kanban/+page.svelte`, suspendu quand l'onglet n'est pas visible, plus un bouton de rafraîchissement immédiat
- [ ] T020 [US1] Préserver la fiche ouverte et le texte en cours de saisie lors d'un tour de sondage (FR-011)
- [ ] T021 [P] [US1] Ajouter la bascule « voir les archivées » dans `src/routes/(app)/kanban/+page.svelte`
- [ ] T022 [P] [US1] Rendre les dépendances visibles sur la carte et dans la fiche à partir des liens renvoyés par le tableau
- [ ] T023 [P] [US1] Ajouter les clés i18n de US1 dans les deux fichiers de traduction

**Point de contrôle** : reconstruire et suivre les étapes 4 et 5 de [quickstart.md](./quickstart.md).

---

## Phase 4 — US2 : débloquer une tâche qui attend (P2)

**Objectif** : une tâche arrêtée faute de réponse repart depuis la page.

**Test indépendant** : bloquer une tâche sur `needs_input`, y répondre depuis la page, vérifier qu'elle repart sans autre intervention.

- [ ] T024 [US2] Ajouter l'appel de déblocage et l'envoi de message dans `src/lib/apis/kanban/index.ts`
- [ ] T025 [US2] Ajouter dans `src/lib/components/kanban/FicheTache.svelte` la zone de réponse et le bouton de déblocage, **affiché uniquement quand `peutEtreDebloquee()` rend vrai**
- [ ] T026 [US2] Afficher l'état réel renvoyé par le moteur après l'action, jamais l'état espéré (FR-017)
- [ ] T027 [US2] Traiter le refus 409 dans `src/routes/(app)/kanban/+page.svelte` : recharger et montrer la réalité plutôt que d'insister
- [ ] T028 [P] [US2] Ajouter les clés i18n de US2 dans les deux fichiers de traduction

**Point de contrôle** : suivre les étapes 5 et 6 de [quickstart.md](./quickstart.md), en vérifiant qu'aucun bouton de déblocage n'apparaît sur un blocage de type `dependency`.

---

## Phase 5 — Finition

- [ ] T029 [P] Rendre le tableau utilisable sur écran étroit : seul le tableau défile horizontalement, jamais la page entière
- [ ] T030 [P] Vérifier la tenue à 200 tâches (SC-006)
- [ ] T031 Dérouler [quickstart.md](./quickstart.md) en entier, moteur coupé compris — l'étape 1 est celle qui trahit une page mal faite
- [ ] T032 Passer `npm run test:frontend`, `npm run lint:frontend`, `npm run format`, et la compilation Svelte de chaque composant depuis la racine du dépôt
- [ ] T033 Committer en anglais, reconstruire l'image, redémarrer le conteneur, puis donner l'URL à Mike

---

## Dépendances

```text
Phase 1 (T001)
   └─> Phase 2 (T002…T012)  ← premier écran visible en T011
          ├─> Phase 3 US1 (T013…T023)
          │      └─> Phase 4 US2 (T024…T028)   [US2 a besoin de la fiche de T018]
          └─> Phase 5 (T029…T033)
```

US1 se tient seule : livrée sans US2, la page montre déjà le travail de l'assistant.
US2 dépend de la fiche produite en T018.

## Parallélisable

| Groupe | Tâches | Pourquoi |
|--------|--------|----------|
| Logique pure | T002, T003, T004, T005 | Deux modules indépendants, fichiers distincts |
| Front / back | T006–T008 avec T009–T012 | Le proxy et l'écran ne se touchent pas |
| Cartes | T013, T014, T017 | Trois composants sans dépendance entre eux |
| Finition | T029, T030 | Fichiers différents |

## Compte

| Phase | Tâches |
|-------|--------|
| Setup | 1 |
| Fondations | 11 |
| US1 — voir | 11 |
| US2 — débloquer | 5 |
| Finition | 5 |
| **Total** | **33** |

## Stratégie

**Le plus petit livrable utile est la phase 2 + US1** : une page qui montre honnêtement le
travail de l'assistant. US2 s'ajoute derrière sans rien réécrire.

À chaque point de contrôle : committer, reconstruire, regarder. S'arrêter à « c'est codé »
ne compte pas comme terminé.
