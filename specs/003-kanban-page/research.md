# Phase 0 — Recherche

Décisions techniques prises avant la conception, avec ce qui a été écarté et pourquoi.
Tout ce qui suit a été lu dans le code, pas supposé.

---

## R1 — Fraîcheur de l'affichage : sondage, pas de flux temps réel

**Décision** : la page interroge le tableau toutes les **5 secondes**, et suspend le
sondage quand l'onglet n'est pas visible.

**Rationale** :

- **SC-003 tolère 10 secondes.** Un sondage à 5 s satisfait le critère avec de la marge.
- Le flux temps réel du plugin (`@router.websocket("/events")`, canal `task_events`)
  imposerait un **relais dans le proxy** : une connexion persistante par navigateur
  ouvert, maintenue côté FastAPI, avec sa reconnexion, ses fuites de sockets et son
  comportement à la coupure du moteur. C'est un composant de plus à faire vivre, pour
  gagner quelques secondes que la spec ne réclame pas.
- Le sondage échoue proprement : une requête ratée est un `unknown` ponctuel, pas une
  connexion morte dont il faut deviner l'état. Cela sert directement FR-009.
- **FR-011** (ne pas perdre ce que le client lit ou écrit) est plus simple à tenir avec
  un rafraîchissement discret qu'avec un flux qui pousse des événements pendant la
  frappe.

**Alternatives écartées** :

- *Relais WebSocket* — gardé comme évolution une fois la page en service et le besoin
  réel mesuré. Le plugin l'expose déjà, rien n'est perdu.
- *Sondage à 2 s* — inutilement bavard pour un tableau qui bouge à l'échelle de la
  minute ; le répartiteur de Hermes tourne lui-même toutes les 60 secondes.
- *Rafraîchissement manuel seul* — contredit FR-010.

**Conséquence pour la suite** : la page expose quand même un bouton de rafraîchissement,
parce qu'un client qui vient d'agir veut voir tout de suite, sans attendre le tour
suivant.

---

## R2 — Débloquer une tâche : `PATCH`, pas de route dédiée

**Décision** : débloquer = `PATCH /tasks/{id}` avec `{"status": "ready"}`. Le message
qui accompagne la décision part séparément en `POST /tasks/{id}/comments`.

**Rationale** : lu dans `plugins/kanban/dashboard/plugin_api.py`. Le corps accepté
(`UpdateTaskBody`) porte `status`, `assignee`, `priority`, `title`, `body`, `result`,
`block_reason`. Et la branche `status` fait exactement ce qu'il faut :

> `# Re-open a blocked/scheduled task, or just an explicit status set.`
> `if current and current.status in ("blocked", "scheduled"): ok = kanban_db.unblock_task(conn, task_id)`

Autrement dit, **c'est le moteur qui décide** que passer une tâche bloquée à `ready`
signifie « débloquer ». On ne réimplémente pas cette règle côté page : on écrit le
statut voulu et le moteur applique sa propre transition.

**Alternatives écartées** :

- *Chercher une route `/unblock`* — elle n'existe pas dans le plugin. La CLI a bien
  `hermes kanban unblock`, mais elle passe par la même fonction de base.
- *Écrire directement dans le SQLite* — hors de question : la vérité reste au moteur, et
  contourner son API contournerait aussi ses règles de transition.

---

## R3 — Regroupement des états : une table, et un cas par défaut visible

**Décision** : une correspondance explicite des neuf états vers six colonnes
(spec, D2), plus un **cas par défaut qui rend visible tout état inconnu**.

**Rationale** : c'est le défaut exact du client de bureau, documenté dans
`Repos/hermes-desktop/KANBAN_GAP_REPORT.md` :

> **`scheduled`** ✓ canonical, ✗ our columns — *Missing column — `scheduled` tasks fall
> through to `todo` bucket.*

Le piège n'est pas le regroupement, c'est le **repli silencieux**. Une tâche programmée
rangée dans « à faire » sans sa date est une tâche qu'on croit en attente immédiate.

La table de correspondance vit donc dans `src/lib/kanban/colonnes.ts`, et son test
vérifie deux choses qu'aucune relecture ne garantit :

1. **les neuf états canoniques sont couverts** — le test les liste en dur, donc l'ajout
   d'un état côté moteur fait tomber le test plutôt que de disparaître à l'écran ;
2. **un état inconnu ne tombe dans aucune colonne existante** — il est signalé.

**Alternatives écartées** :

- *Lire les statuts depuis `GET /config`* — le moteur ne les expose pas sous cette forme,
  et une table lue à l'exécution ne se teste pas.
- *Colonne « autre » fourre-tout* — masquerait le problème au lieu de le montrer.

---

## R4 — Détecter l'absence du plugin sans crier à la panne

**Décision** : trois états distincts, dérivés dans `src/lib/kanban/etat.ts` :

| État | Ce qui l'a produit | Ce que la page affiche |
|------|--------------------|------------------------|
| `ok` | Le tableau a répondu | Le tableau |
| `absent` | Le moteur répond, mais pas de registre de tâches (404 sur le plugin) | Une phrase d'explication, sans alerte |
| `injoignable` | Le moteur lui-même ne répond pas (503 du proxy) | Une alerte chapeau unique |

**Rationale** : la règle D27 dit qu'une source injoignable n'est pas une panne. Ici il y
a **deux non-réponses de nature opposée** : un moteur coupé (temporaire, ça revient) et
un plugin non installé (permanent, ça se règle par une installation). Les confondre ferait
afficher « le moteur ne répond pas » à quelqu'un dont le moteur va parfaitement bien.

Le proxy existant traduit déjà une injoignabilité réseau en **503** avec un message
lisible (`routers/hermes.py`, fonction `_appeler`). On s'appuie dessus plutôt que de
réinventer la détection.

**Alternatives écartées** :

- *Un seul état « erreur »* — c'est précisément ce que D27 interdit.
- *Sonder `GET /config` avant chaque chargement* — un aller-retour de plus à chaque tour
  de sondage, pour une information qui ne change qu'à l'installation.

---

## R5 — Un routeur backend neuf, pas un ajout à `hermes.py`

**Décision** : `backend/open_webui/routers/kanban.py`, distinct de `routers/hermes.py`.

**Rationale** :

- `hermes.py` fait déjà ~900 lignes et couvre le pilotage du moteur (modèles, outils,
  MCP, messagerie, compétences). Le kanban est un autre domaine.
- Surtout, il a un **cycle de vie différent** : c'est un plugin de Hermes, qui peut être
  absent. Mélanger ses routes à celles du pilotage rendrait plus difficile de distinguer
  « le moteur est coupé » de « le plugin n'est pas là » — la distinction de R4.
- La règle de `CLAUDE.md` sur ce dépôt privilégie beaucoup de petits fichiers.

Ce qui est **réutilisé** de `hermes.py` plutôt que recopié : la session authentifiée
(`_session_authentifiee`), la reconnexion sur 401, la traduction des erreurs réseau en
503/504 lisibles. Ces fonctions sont importées, pas dupliquées — deux copies d'un
client HTTP finiraient par diverger.

**Alternatives écartées** :

- *Tout dans `hermes.py`* — un dixième domaine dans un fichier déjà long.
- *Un client HTTP propre au kanban* — duplication du traitement d'erreurs et de la
  session, pour aucun gain.

---

## R6 — Périmètre des routes relayées

**Décision** : cinq routes seulement, celles que D1 exige.

| Route Hermes | Pourquoi elle est là |
|--------------|----------------------|
| `GET /board` | La liste des tâches. Le cœur de la page. |
| `GET /tasks/{id}` | La fiche d'une tâche : consigne, avancement, résultat, échanges. |
| `PATCH /tasks/{id}` | Débloquer (R2). **Seul champ accepté par le proxy : `status`.** |
| `POST /tasks/{id}/comments` | Le message qui accompagne la décision. |
| `GET /config` | Savoir quels tableaux existent, et si le registre est là. |

**Rationale** : le plugin expose une trentaine de routes. En relayer trente pour en
utiliser cinq, ce serait ouvrir vingt-cinq surfaces d'écriture que personne ne teste —
dont `DELETE /tasks/{id}` et `POST /tasks/bulk`.

Le proxy **filtre le corps du `PATCH`** et ne laisse passer que `status`. Un client qui
enverrait `title`, `result` ou `assignee` verrait ces champs ignorés. La liste blanche
porte donc sur les routes *et* sur les champs.

**Alternatives écartées** :

- *Relais générique `/{chemin:path}`* — transformerait le proxy en tunnel ouvert vers le
  moteur, ce qui annule l'intérêt d'avoir un proxy.
- *Ajouter `DELETE` et `bulk` « pour plus tard »* — du code non utilisé et non testé,
  destructeur de surcroît.
