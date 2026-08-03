# Implementation Plan: Page Kanban

**Branch**: `feat/engine-dashboard` (le script n'a pas créé de branche dédiée ; le chantier
reste celui de la navigation du Moteur) | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-kanban-page/spec.md`

## Summary

Rendre visible le registre de tâches durable que Hermes tient déjà, dans une page dédiée
de la navigation. Six colonnes couvrant les neuf états du moteur sans en perdre aucun, une
fiche par tâche, et une seule action d'écriture : débloquer une tâche qui attend une
réponse humaine.

Approche : une page assembleur qui compose des cartes, toute la logique de regroupement et
d'état dans des fonctions pures testées, et un routeur backend dédié qui relaie vers le
plugin kanban de Hermes en gardant l'adresse et la clé côté serveur.

## Technical Context

**Language/Version**: TypeScript 5 (front), Python 3.11 (proxy backend)

**Primary Dependencies**: SvelteKit + Svelte 5 en mode compatibilité, Tailwind, i18next
(front) ; FastAPI + aiohttp (backend, déjà en place dans `routers/hermes.py`)

**Storage**: aucune. La page ne persiste rien : la vérité vit dans le SQLite de Hermes
(`~/.hermes/kanban.db`). Aucune table, aucun cache serveur.

**Testing**: Vitest pour les fonctions pures, chaque `.ts` de logique ayant son `.test.ts`
à côté. Vérification de compilation Svelte via `compile()` depuis la racine du dépôt.

**Target Platform**: navigateur, servi par le conteneur unique sur `localhost:3000`

**Project Type**: application web — front SvelteKit + proxy backend dans le même déploiement

**Performance Goals**: un changement du tableau visible en moins de 10 secondes (SC-003) ;
page utilisable à 200 tâches (SC-006)

**Constraints**: le navigateur ne joint jamais Hermes directement (FR-020) ; une seule URL ;
états `ok` / `down` / `unknown` distincts (FR-009, règle D27) ; chaque source chargée
indépendamment (FR-012)

**Scale/Scope**: une page, six composants, deux modules de logique pure, un routeur backend
de cinq routes. Un seul tableau visible à la fois, plusieurs tableaux commutables.

## Constitution Check

*GATE: à passer avant la phase 0, à revérifier après la phase 1.*

Le fichier `.specify/memory/constitution.md` n'a **jamais été rempli** : il ne contient que
les placeholders du gabarit. Les règles réellement en vigueur sur ce dépôt sont celles de
`CLAUDE.md` (racine du projet et `Apps/OpenWebUI`). Ce sont elles qui servent de barrières
ici, faute de mieux.

| Barrière | Source | Statut |
|----------|--------|--------|
| Une seule URL, `localhost:3000`, pas de second port | CLAUDE.md projet | **Respectée** — la page est servie par le conteneur existant |
| Le navigateur ne joint jamais Hermes directement | CLAUDE.md projet | **Respectée** — tout passe par le routeur backend |
| Écran = assembleur court + cartes + logique pure testée | CLAUDE.md projet | **Respectée** — voir la structure ci-dessous |
| Chaque source chargée indépendamment | CLAUDE.md projet | **Respectée** — chargements séparés, échec isolé |
| Honnêteté des états (`ok` / `down` / `unknown`), une seule alerte chapeau | Décision D27 | **Respectée** — module `etat.ts` dédié et testé |
| Textes via `$i18n.t`, clés en `en-US` **et** `fr-FR` | CLAUDE.md OpenWebUI | **Respectée** |
| Indentation par tabulations, messages de commit en anglais | CLAUDE.md OpenWebUI | **Respectée** |
| Tests d'abord sur la logique métier | CLAUDE.md utilisateur (TDD) | **Partiellement** — voir Complexity Tracking |

**Verdict : aucun blocage.** Une réserve assumée, tracée plus bas.

## Project Structure

### Documentation (this feature)

```text
specs/003-kanban-page/
├── spec.md              # Spécification (fait)
├── checklists/
│   └── requirements.md  # Contrôle qualité de la spec (fait)
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques et alternatives écartées
├── data-model.md        # Phase 1 — entités et transitions
├── contracts/
│   └── proxy-kanban.md  # Phase 1 — contrat des routes du proxy
├── quickstart.md        # Phase 1 — comment vérifier à l'écran
└── tasks.md             # Phase 2 — produit par /speckit.tasks, PAS par ce plan
```

### Source Code (repository root)

```text
Apps/OpenWebUI/
├── backend/open_webui/routers/
│   └── kanban.py                       # NOUVEAU — relais vers le plugin kanban de Hermes
│
├── src/lib/kanban/                     # NOUVEAU — logique pure, testée
│   ├── colonnes.ts                     # 9 états du moteur → 6 colonnes, état inconnu compris
│   ├── colonnes.test.ts
│   ├── etat.ts                         # ok / down / unknown, alerte chapeau unique
│   └── etat.test.ts
│
├── src/lib/apis/kanban/
│   └── index.ts                        # NOUVEAU — appels au proxy, jamais à Hermes
│
├── src/lib/components/kanban/          # NOUVEAU — les cartes de l'écran
│   ├── ColonneKanban.svelte            # une colonne et sa pile de cartes
│   ├── CarteTache.svelte               # une tâche : titre, date prévue, motif de blocage
│   ├── FicheTache.svelte               # le détail : consigne, avancement, résultat, échanges
│   ├── BandeauEtat.svelte              # l'alerte chapeau quand le pont est coupé
│   └── SelecteurTableau.svelte         # quel tableau on regarde
│
├── src/routes/(app)/kanban/
│   └── +page.svelte                    # NOUVEAU — assembleur court
│
├── src/lib/components/layout/
│   └── Sidebar.svelte                  # MODIFIÉ — une entrée de premier niveau
│
├── src/lib/i18n/locales/en-US/translation.json   # MODIFIÉ
└── src/lib/i18n/locales/fr-FR/translation.json   # MODIFIÉ
```

**Structure Decision**: on suit le modèle de `src/routes/(app)/hermes/+page.svelte`, déjà en
place et validé sur ce dépôt : la page charge et compose, les cartes vivent dans
`src/lib/components/<domaine>/`, et toute dérivation part en fonction pure sous
`src/lib/<domaine>/` avec son test à côté — exactement le schéma de
`src/lib/composio/doublons.ts` + `doublons.test.ts`.

Le proxy est un **fichier neuf** plutôt qu'un ajout à `routers/hermes.py` : ce dernier fait
déjà 900 lignes et couvre le pilotage du moteur. Le kanban est un autre domaine, avec son
propre cycle de vie côté Hermes (un plugin qui peut être absent).

## Complexity Tracking

| Réserve | Pourquoi elle est prise | Ce qui a été écarté |
|---------|-------------------------|---------------------|
| TDD partiel | Les fonctions pures (`colonnes.ts`, `etat.ts`) partent en test-d'abord, elles portent toute la logique et tous les cas limites. Les composants Svelte et le routeur backend sont couverts par vérification de compilation et essai à l'écran, pas par des tests automatisés. | Des tests de composants (Testing Library) : le dépôt n'en a aucun aujourd'hui, en introduire pour cette page seule créerait un précédent isolé et non tenu. |
| Sondage plutôt que flux temps réel | Voir `research.md` — le WebSocket du plugin imposerait une connexion persistante par client dans le proxy, alors que SC-003 tolère 10 secondes. | Le relais WebSocket, gardé comme évolution une fois la page en service. |
