# Feature Specification: Page Kanban

**Feature Branch**: `003-kanban-page`

**Created**: 2026-08-03

**Status**: Draft

**Input**: Nouvelle page « Kanban » dans la navigation de LunarIA, qui donne au client une vue sur le tableau de tâches durable de Hermes Agent.

## Contexte

Aujourd'hui, quand l'assistant travaille en arrière-plan, le client ne voit rien. Il
lui parle, l'assistant répond, et ce qui se passe entre deux conversations lui est
invisible. Si une tâche prend deux heures, échoue, se met en attente d'une réponse
ou se reprogramme toute seule, personne ne le sait.

Le moteur tient pourtant déjà ce registre : un tableau de tâches durable, qui survit
aux redémarrages, où l'assistant inscrit lui-même ce qu'il a à faire, ce qui le
bloque et ce qu'il a terminé. Cette page rend ce registre visible.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Voir ce que l'assistant est en train de faire (Priority: P1)

Le dirigeant ouvre la page et comprend en quelques secondes où en est le travail :
ce qui tourne maintenant, ce qui attend, ce qui est terminé, et surtout ce qui est
arrêté faute d'une réponse de sa part.

**Why this priority**: c'est la raison d'être de la page. Sans elle, le travail de
fond de l'assistant est invisible, donc invérifiable — et un travail invérifiable
n'inspire pas confiance. C'est aussi la seule partie qui a de la valeur seule : un
tableau qu'on ne peut que lire répond déjà à la question « qu'est-ce qu'il fabrique ? ».

**Independent Test**: ouvrir la page sur une installation où l'assistant a des tâches
en cours, et vérifier qu'on identifie sans aide extérieure ce qui tourne, ce qui
attend et ce qui est bloqué.

**Acceptance Scenarios**:

1. **Given** l'assistant a des tâches dans plusieurs états, **When** le client ouvre
   la page, **Then** chaque tâche apparaît dans une colonne qui correspond à son état
   réel, et aucune tâche n'est rangée dans une colonne qui ne lui correspond pas.
2. **Given** une tâche est programmée pour plus tard, **When** le client la regarde,
   **Then** la date prévue est visible sur la carte.
3. **Given** une tâche est bloquée, **When** le client la regarde, **Then** la raison
   du blocage est lisible sans avoir à ouvrir la tâche.
4. **Given** le client ouvre une tâche, **When** il consulte son détail, **Then** il
   voit ce que l'assistant a écrit à son sujet : la consigne, l'avancement, le
   résultat et les échanges.

---

### User Story 2 - Débloquer une tâche qui attend une réponse (Priority: P2)

Une tâche s'est arrêtée parce que l'assistant a besoin d'un arbitrage humain. Le
client répond depuis la page, et le travail reprend.

**Why this priority**: c'est ce qui transforme un tableau d'affichage en outil de
travail. Sans cela, le client voit qu'une tâche est bloquée mais doit sortir de la
page pour la débloquer — et en pratique, elle reste bloquée.

**Independent Test**: prendre une tâche en attente, y répondre depuis la page, et
vérifier qu'elle repart sans intervention par un autre moyen.

**Acceptance Scenarios**:

1. **Given** une tâche est bloquée en attente d'une réponse, **When** le client écrit
   sa réponse et la valide, **Then** la tâche quitte l'état bloqué et le travail
   reprend.
2. **Given** le client répond à une tâche, **When** il revient sur la page plus tard,
   **Then** sa réponse est toujours visible dans l'historique de la tâche.
3. **Given** l'action échoue côté moteur, **When** le client la déclenche, **Then**
   il en est informé et l'état affiché n'est pas modifié à tort.

---

### User Story 3 - Confier une tâche à l'assistant (Priority: P3 — reporté, voir D1)

Le client inscrit lui-même une tâche sur le tableau, sans passer par une conversation.

**Why this priority**: utile mais pas indispensable au départ — la voie normale reste
la conversation, où l'assistant crée ses tâches lui-même. Cette entrée directe sert
surtout aux demandes récurrentes et à ce qu'on veut noter sans discuter.

**Independent Test**: créer une tâche depuis la page et vérifier que l'assistant la
prend en charge comme si elle venait d'une conversation.

**Acceptance Scenarios**:

1. **Given** le client rédige une tâche, **When** il la valide, **Then** elle apparaît
   sur le tableau et entre dans la file de travail de l'assistant.
2. **Given** le client laisse le titre vide, **When** il tente de valider, **Then**
   la page l'en empêche et lui dit ce qui manque.

---

### Edge Cases

- **Le moteur ne répond pas.** La page dit qu'elle ne sait pas, pas que tout est en
  panne. Un tableau injoignable et un tableau vide sont deux choses différentes et
  doivent se lire différemment.
- **Le registre de tâches n'est pas installé sur ce moteur.** C'est un état normal,
  pas une erreur : la page l'explique en une phrase et n'affiche pas de tableau vide
  qui laisserait croire à une perte de données.
- **Le tableau est vide.** L'assistant n'a simplement rien en cours. La page le dit
  clairement plutôt que d'afficher des colonnes vides.
- **Une tâche porte un état inconnu de la page.** Elle reste visible et signalée comme
  telle, jamais rangée d'office dans une colonne au hasard. Perdre une tâche
  silencieusement est le défaut exact qu'on corrige ici.
- **Plusieurs tableaux existent.** Le client voit lequel il regarde et peut changer.
- **Une tâche dépend d'une autre.** Le lien est visible : on comprend pourquoi une
  tâche attend sans que rien ne semble se passer.
- **Le tableau change pendant qu'on le regarde.** L'écran suit sans que le client ait
  à recharger, et sans perdre ce qu'il est en train de lire ou d'écrire.
- **Deux personnes regardent le même tableau.** Ce que l'une fait devient visible pour
  l'autre.

## Requirements *(mandatory)*

### Functional Requirements

**Voir**

- **FR-001**: La page MUST présenter les tâches réparties par état, chaque tâche
  n'apparaissant qu'à un seul endroit.
- **FR-002**: La page MUST couvrir tous les états que le moteur sait produire. Aucun
  état ne doit être fondu dans un autre sans que le client puisse le voir.
- **FR-003**: La page MUST distinguer une tâche qui attend le temps d'une tâche qui
  attend une réponse humaine. *(Reformulé le 3 août : le moteur ne stocke aucune date
  de démarrage — voir data-model.md. La page ne peut donc pas dire quand une tâche
  repartira, seulement qu'elle n'attend rien de la part du client.)*
- **FR-004**: La page MUST afficher, pour une tâche bloquée, le type de blocage en
  clair, et MUST NOT proposer de débloquer une tâche dont le blocage ne relève pas d'une
  décision humaine.
- **FR-005**: La page MUST permettre d'ouvrir une tâche et d'y lire sa consigne, son
  avancement, son résultat et les échanges qui la concernent.
- **FR-006**: La page MUST rendre visibles les dépendances entre tâches.
- **FR-007**: La page MUST indiquer quel tableau est affiché et permettre d'en changer
  quand plusieurs existent.
- **FR-008**: Les tâches archivées MUST être masquées par défaut et consultables à la
  demande.

**Rester juste**

- **FR-009**: La page MUST distinguer trois situations et ne jamais les confondre :
  le tableau répond, le tableau est injoignable, l'état est inconnu.
- **FR-010**: La page MUST refléter les changements du tableau sans que le client ait
  à recharger.
- **FR-011**: La page MUST conserver ce que le client est en train de lire ou d'écrire
  lorsqu'une mise à jour arrive.
- **FR-012**: Chaque source de données MUST se charger indépendamment : l'indisponibilité
  de l'une ne doit pas empêcher les autres de s'afficher.
- **FR-013**: La page MUST afficher une seule alerte lorsqu'une coupure unique rend
  plusieurs sources indisponibles, plutôt qu'une alerte par source.

**Agir**

- **FR-014**: Le client MUST pouvoir répondre à une tâche bloquée et la remettre en
  marche.
- **FR-015**: Le client MUST pouvoir écrire un message sur une tâche, conservé dans
  son historique.
- **FR-016**: *(hors périmètre de cette version — voir D1)* Le client MUST pouvoir
  créer une tâche.
- **FR-017**: Toute action MUST être confirmée par l'état réel du tableau, jamais
  supposée réussie. Un échec doit être visible et ne pas laisser l'écran mentir.
- **FR-018**: Toute action destructrice MUST demander confirmation en nommant ce qui
  va disparaître.

**Cadre**

- **FR-019**: La page MUST être une entrée de premier niveau de la navigation, au même
  rang que « Moteur », et non un onglet d'un autre écran.
- **FR-020**: Le navigateur MUST NOT joindre le moteur directement : tout passe par
  le serveur de l'application, qui seul détient l'adresse et la clé.
- **FR-021**: Tous les textes visibles MUST exister en français et en anglais.
- **FR-022**: La page MUST rester lisible sur un écran étroit.

### Key Entities

- **Tableau** : une file de travail isolée. Un client peut en avoir plusieurs, sans
  qu'ils se mélangent.
- **Tâche** : une unité de travail portant un titre, une consigne, un état, une
  priorité, un responsable, éventuellement une date de démarrage et un motif de
  blocage.
- **Lien** : une dépendance entre deux tâches. Une tâche dont les prérequis ne sont
  pas terminés ne peut pas démarrer.
- **Message** : un échange écrit rattaché à une tâche, par l'assistant ou par un
  humain. C'est le fil de discussion d'une tâche.
- **Exécution** : une tentative de traitement d'une tâche, avec son issue. Une tâche
  peut en compter plusieurs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un dirigeant qui n'a jamais vu la page identifie en moins de 30 secondes
  ce qui est en cours et ce qui attend une réponse de sa part.
- **SC-002**: 100 % des tâches du moteur sont visibles sur la page. Aucune tâche
  n'est absente ni rangée dans un état qui n'est pas le sien.
- **SC-003**: Un changement sur le tableau devient visible en moins de 10 secondes
  sans action du client.
- **SC-004**: Débloquer une tâche depuis la page prend moins de 3 clics.
- **SC-005**: Lorsque le moteur est injoignable, aucun écran n'affirme que le travail
  est terminé, vide ou en panne. L'incertitude est dite comme telle.
- **SC-006**: La page reste utilisable avec 200 tâches sur un tableau.
- **SC-007**: Aucune tâche n'est modifiée sans confirmation visible de l'état réel.

## Assumptions

- **Le registre de tâches est fourni par le moteur**, pas réimplémenté ici. La page en
  est une vue ; la vérité reste côté moteur. Si le moteur ajoute un état, la page doit
  le montrer plutôt que de l'ignorer.
- **Le registre peut être absent** d'une installation. Ce n'est pas une panne, et la
  page doit le dire sans dramatiser.
- **Portée initiale : un seul assistant partagé.** Le moteur ne distingue pas encore
  les utilisateurs entre eux : toute personne qui accède à la page voit le même
  tableau. Le cloisonnement par personne est un chantier distinct.
- **Les états techniques sont regroupés pour la lecture**, sans jamais en perdre. Le
  regroupement retenu est le tableau de D2.
- **La page est réservée à l'administrateur** au premier jet, comme les autres écrans
  de pilotage du moteur.
- **Les pièces jointes sont hors périmètre** de la première version.

## Décisions tranchées

Arbitrées par Mike le 3 août 2026, avant le plan.

### D1 — Périmètre de la première version : voir et débloquer

Les parcours **P1 (voir)** et **P2 (débloquer)** partent ensemble. **P3 (créer une
tâche) est reporté.**

Raison : un tableau qu'on ne peut que lire montre le problème sans permettre de le
résoudre, et une tâche bloquée le reste. La création, elle, a déjà une voie — la
conversation, où l'assistant inscrit ses tâches lui-même.

Conséquence : **FR-016 sort du périmètre** de cette version. Une seule écriture est à
sécuriser (débloquer, et le message qui l'accompagne), pas quatre.

### D2 — Six colonnes, aucun état perdu

| Colonne affichée | États du moteur regroupés |
|------------------|---------------------------|
| À trier | `triage` |
| À faire | `todo`, `scheduled`, `ready` |
| En cours | `running` |
| Bloqué | `blocked` |
| À valider | `review` |
| Terminé | `done` |
| *(masqué, sur demande)* | `archived` |

Trois règles qui accompagnent ce regroupement :

- Une tâche `scheduled` **porte un libellé distinct** sur sa carte : elle attend le
  temps, pas une réponse du client. C'est ce qui distingue ce regroupement du défaut de
  la version Desktop, où la tâche disparaissait dans « à faire » sans que rien ne le
  signale. *(Corrigé le 3 août : il était prévu d'afficher une date de démarrage, mais
  le moteur n'en stocke aucune — voir data-model.md.)*
- **« Bloqué » et « À valider » restent séparés.** L'un demande une décision, l'autre
  une relecture : ce sont deux sollicitations différentes, et les confondre reviendrait
  à dire au client « occupe-toi de ça » sans lui dire quoi faire.
- **La colonne « Bloqué » se lit par type.** Le moteur distingue quatre motifs
  (`needs_input`, `dependency`, `capability`, `transient`) et un seul appelle une action
  du client. Le bouton de déblocage n'apparaît que sur celui-là.

Un état que la page ne connaît pas reste visible et signalé comme tel (cas limite
« état inconnu »), jamais rangé d'office.

### D3 — Une page dédiée

**Entrée de premier niveau dans la navigation**, au même rang que « Moteur ». Pas un
onglet.

Raison : le tableau se consulte tous les jours, la page Moteur est un écran de réglage
qu'on ouvre rarement. Enterrer l'un dans l'autre reviendrait à cacher l'usage quotidien
derrière l'usage exceptionnel.
