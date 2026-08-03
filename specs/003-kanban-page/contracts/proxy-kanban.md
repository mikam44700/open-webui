# Contrat — routes du proxy Kanban

`backend/open_webui/routers/kanban.py`, monté sous `/api/v1/kanban`.

Le navigateur ne connaît que ces cinq routes. Il ne connaît ni l'adresse de Hermes, ni
sa clé, ni l'existence du plugin. Toutes sont réservées à l'administrateur
(`get_admin_user`), comme le reste du pilotage du moteur.

---

## GET `/api/v1/kanban/config`

Ce qui existe : les tableaux disponibles, et si le registre est là.

**Relaie** : `GET /api/plugins/kanban/config`

**Réponse (200)**

```json
{ "tableaux": ["default", "clients"], "tableauCourant": "default" }
```

**Réponses d'échec** — la distinction porte tout le reste de la page :

| Code | Ce que ça veut dire | Ce que la page affiche |
|------|---------------------|------------------------|
| 404 | Le moteur répond, mais n'a pas de registre de tâches | Une phrase d'explication, **aucune alerte** |
| 503 | Le moteur ne répond pas | L'alerte chapeau unique |
| 504 | Le moteur met trop de temps | Idem 503 |

---

## GET `/api/v1/kanban/board`

Les tâches du tableau.

**Relaie** : `GET /api/plugins/kanban/board`

**Paramètres** : `tableau` (optionnel), `inclure_archivees` (booléen, défaut `false`)

**Réponse (200)** — champs retenus au regard de data-model.md ; le proxy **élague** le
reste plutôt que de le transmettre au navigateur :

```json
{
  "taches": [
    {
      "id": "t_01H...",
      "titre": "Relancer la facture 2411",
      "statut": "blocked",
      "typeBlocage": "needs_input",
      "responsable": "adv",
      "priorite": 2,
      "creeLe": 1754200000,
      "demarreLe": null,
      "termineLe": null,
      "echecsConsecutifs": 0,
      "reblocages": 2
    }
  ],
  "liens": [{ "parent": "t_01H...", "enfant": "t_02K..." }]
}
```

---

## GET `/api/v1/kanban/tasks/{id}`

La fiche d'une tâche.

**Relaie** : `GET /api/plugins/kanban/tasks/{id}`

**Réponse (200)** : les champs ci-dessus, plus `consigne` (`body`), `resultat`
(`result`), `derniereErreur` (`last_failure_error`) et `messages`.

**404** : la tâche n'existe plus (archivée ou supprimée côté moteur). La page le dit et
referme la fiche plutôt que d'afficher une coquille vide.

---

## PATCH `/api/v1/kanban/tasks/{id}`

Débloquer. **C'est la seule écriture de cette version.**

**Relaie** : `PATCH /api/plugins/kanban/tasks/{id}`

**Corps accepté — un seul champ, et une seule valeur** :

```json
{ "statut": "ready" }
```

**Règles du proxy, appliquées côté serveur et non côté navigateur** :

1. **Seul `statut` est transmis.** Tout autre champ du corps est ignoré, jamais relayé.
   Le corps accepté par Hermes (`UpdateTaskBody`) porte aussi `title`, `body`, `result`,
   `assignee`, `priority`, `block_reason`, `metadata` : rien de tout cela ne doit pouvoir
   être écrit depuis cette page.
2. **Seule la valeur `ready` est acceptée.** Un `statut` valant `done`, `archived` ou
   autre est refusé en 400. Cette version débloque, elle ne pilote pas le cycle de vie.
3. Le moteur applique ensuite sa propre transition : voir `plugin_api.py`, qui appelle
   `kanban_db.unblock_task()` quand la tâche courante est `blocked` ou `scheduled`. La
   page ne réimplémente pas cette règle.

**Réponses** : `200` (état réel de la tâche renvoyé, jamais supposé), `400` (champ ou
valeur refusés), `404`, `409` (le moteur a refusé la transition — la tâche a changé
entre-temps), `503`.

Sur `409`, la page recharge et affiche l'état réel plutôt que d'insister.

---

## POST `/api/v1/kanban/tasks/{id}/comments`

Le message qui accompagne la décision.

**Relaie** : `POST /api/plugins/kanban/tasks/{id}/comments`

**Corps** : `{ "texte": "..." }` — non vide, 4000 caractères maximum.

**Réponse (200)** : le message créé, avec son horodatage.

---

## Ce qui n'est **pas** relayé, et pourquoi

Le plugin expose une trentaine de routes. Vingt-cinq restent hors d'atteinte du
navigateur :

| Route | Raison |
|-------|--------|
| `DELETE /tasks/{id}` | Destructeur. Hors périmètre (D1), et rien ne le justifie ici. |
| `POST /tasks/bulk` | Destructeur en masse. |
| `POST /tasks` | Création — reportée (FR-016, D1). |
| `POST|DELETE /links` | Édition des dépendances — lecture seule dans cette version. |
| `POST /runs/{id}/terminate` | Arrêt d'une exécution — pilotage, pas consultation. |
| `POST /tasks/{id}/reassign|specify|estimate` | Hors périmètre. |
| pièces jointes (4 routes) | Hors périmètre, et 25 Mo à travers le proxy demande son propre travail. |
| `GET /diagnostics`, `/workers/active`, `/stats`, `/assignees`, `/runs/{id}` | Utiles plus tard ; non nécessaires aux parcours P1 et P2. |

**Le principe** : une route relayée est une route testée. Ouvrir un tunnel générique
vers le moteur annulerait l'intérêt d'avoir un proxy.
