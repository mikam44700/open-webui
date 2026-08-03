# Phase 1 — Modèle de données

Ce que le moteur expose réellement, lu dans `hermes_cli/kanban_db.py` et
`plugins/kanban/dashboard/plugin_api.py`. La page n'invente aucun champ et n'en déduit
aucun : ce qui n'est pas là ne s'affiche pas.

---

## Tâche

Champs utilisés par la page, sur les ~40 que porte la ligne.

| Champ | Type | Usage à l'écran |
|-------|------|-----------------|
| `id` | texte | Clé de rendu, cible des actions |
| `title` | texte | Le titre de la carte |
| `body` | texte, optionnel | La consigne, dans la fiche |
| `status` | texte | Range la tâche en colonne (voir la correspondance) |
| `block_kind` | texte, optionnel | **Ce qui rend la colonne « Bloqué » lisible** (voir plus bas) |
| `assignee` | texte, optionnel | Qui s'en occupe |
| `priority` | entier | Ordre dans la colonne |
| `result` | texte, optionnel | Ce qui est ressorti, dans la fiche |
| `created_at` | horodatage | Âge de la tâche |
| `started_at` | horodatage, optionnel | Depuis quand elle tourne |
| `completed_at` | horodatage, optionnel | Quand elle s'est terminée |
| `consecutive_failures` | entier | Signale une tâche qui échoue en boucle |
| `last_failure_error` | texte, optionnel | Pourquoi, dans la fiche |
| `block_recurrences` | entier | Signale une tâche débloquée puis re-bloquée en boucle |

**Champs volontairement ignorés** : `workspace_kind`, `workspace_path`, `claim_lock`,
`claim_expires`, `worker_pid`, `branch_name`, `model_override`, `provider_override`,
`idempotency_key`, `workflow_template_id`, `current_step_key`, `goal_mode`, `skills`,
`tenant`, `session_id`, `project_id`. Ce sont des rouages du moteur ; les montrer à un
dirigeant ajouterait du bruit sans rien lui apprendre.

---

## Les neuf états, et les six colonnes

Source : `kanban_db.VALID_STATUSES` (ligne 102).

| Colonne affichée | États du moteur | Note |
|------------------|-----------------|------|
| À trier | `triage` | L'assistant n'a pas encore décidé quoi en faire |
| À faire | `todo`, `scheduled`, `ready` | `scheduled` porte un libellé distinct sur la carte |
| En cours | `running` | |
| Bloqué | `blocked` | Le libellé dépend de `block_kind` (voir ci-dessous) |
| À valider | `review` | Attend une relecture humaine |
| Terminé | `done` | |
| *(masqué)* | `archived` | Consultable sur bascule |
| *(signalé)* | tout autre | **Reste visible, marqué comme état inconnu** |

La dernière ligne est le garde-fou : un état ajouté côté moteur apparaît à l'écran
signalé comme inconnu, au lieu de disparaître. C'est ce qui distingue ce regroupement du
défaut de la version Desktop.

---

## Le type de blocage : quatre situations, pas une

Source : `kanban_db.VALID_BLOCK_KINDS` (ligne 125).

C'est la découverte qui change l'écran. « Bloqué » ne veut pas dire la même chose selon
le type, et **une seule de ces quatre situations appelle une action du client** :

| `block_kind` | Ce que ça veut dire | Le client doit-il agir ? |
|--------------|---------------------|--------------------------|
| `needs_input` | L'assistant attend une décision humaine | **Oui.** C'est le seul cas où débloquer a un sens. |
| `dependency` | Attend qu'une autre tâche se termine | Non. C'est le fonctionnement normal. |
| `capability` | Il manque un outil ou un accès | Non, mais l'administrateur doit voir. |
| `transient` | Incident passager | Non. Ça repart tout seul. |
| *(absent)* | Blocage ancien, sans type | Indéterminé — traité comme `needs_input`, parce que dans le doute on montre la porte plutôt que de la cacher. |

**Conséquence pour l'écran** : la carte porte le motif en clair, et **le bouton
« Débloquer » n'apparaît que sur `needs_input` et sur les blocages sans type**. Proposer
de débloquer une tâche qui attend simplement sa dépendance reviendrait à inviter le
client à casser l'ordre de travail que l'assistant a lui-même établi.

Cette dérivation vit dans `src/lib/kanban/colonnes.ts` avec son test.

---

## Le compteur de re-blocages

`block_recurrences` compte les cycles blocage → déblocage → re-blocage pour le même
motif. Le moteur s'en sert comme coupe-circuit (`BLOCK_RECURRENCE_LIMIT`).

À l'écran, il sert à dire une chose utile : *« cette tâche a déjà été débloquée trois
fois et se re-bloque »*. Sans ça, le client débloque en boucle sans comprendre que le
problème est ailleurs.

---

## Message

Rattaché à une tâche, écrit par l'assistant ou par un humain. C'est le fil de discussion
de la tâche, et c'est là que la réponse du client atterrit quand il débloque.

Créé par `POST /tasks/{id}/comments`.

---

## Lien

Dépendance parent → enfant. Une tâche dont les parents ne sont pas terminés ne démarre
pas ; quand tous le sont, le moteur la promeut de `todo` vers `ready` tout seul.

En lecture seule dans cette version : la page montre les liens (FR-006) mais ne permet
pas de les modifier.

---

## Tableau

File de travail isolée. Plusieurs tableaux peuvent coexister. La page affiche celui en
cours et permet d'en changer (FR-007).

---

## Écart constaté avec la spécification

**Il n'existe aucune date de programmation dans le moteur.**

`schedule_task()` gare la tâche dans `scheduled` avec ce commentaire :

> *Park a task in `scheduled` so it is waiting on time, not human input. `scheduled`
> tasks are intentionally not dispatchable; an external cron, human action, or automation
> can later call `unblock_task` to re-gate them.*

Aucun champ `scheduled_at`, `due_at` ou équivalent n'existe — vérifié sur
`kanban_db.py` et sur l'API du plugin. Le réveil vient d'un cron externe ou d'une action,
pas d'une date inscrite sur la tâche.

**Conséquence** : **FR-003 est infaisable tel qu'écrit** et doit être reformulé. Ce que
la page peut dire, et qui reste utile, c'est *que* la tâche attend le temps plutôt qu'une
réponse humaine — ce qui la distingue d'une tâche bloquée. Pas *quand* elle repartira.

La correction est portée dans la spec (FR-003 et D2).
