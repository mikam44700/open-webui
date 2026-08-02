# Spécification : brancher les intégrations par Composio

**Feature Branch**: `002-composio-integrations`

**Created**: 2026-08-02

**Status**: En cours

**Input**: Demande utilisateur : plutôt que de refaire toutes les connexions à la main, passer par Composio. Chaque client reçoit sa propre clé API Composio, la colle dans son écran, puis connecte les applications qu’il veut.

## Le problème

L’onglet Intégrations existe mais ne branche presque rien. Dans
`src/lib/apis/integrations/index.ts`, sept fonctions sur quatorze renvoient
`{ unavailable: true }` ou `null` : `getOAuthAuthUrl`, `exchangeOAuth`,
`getOAuthStatus`, `disconnectOAuth`, `setEmailCredentials`,
`setGoogleClientSecret`, `getGoogleAuthUrl`.

Concrètement, un client **ne peut pas** connecter Google Workspace ni Microsoft 365
depuis cet écran. Seules les intégrations à clé (Notion, Airtable, GitHub) marchent,
et elles obligent le client à aller chercher une clé chez chaque éditeur.

Le catalogue MCP du moteur ne comble pas le trou : il contient six serveurs
(`blender`, `comfy-cloud`, `figma`, `linear`, `n8n`, `unreal-engine`), tous
orientés développement et création, et sa politique impose de fusionner une PR
dans `hermes-agent` — dépôt tiers sur lequel nous n’avons pas les droits.

## Le choix

Composio fournit un catalogue d’applications déjà authentifiables et gère
l’OAuth par utilisateur. Le travail restant de notre côté est l’écran, pas les
connecteurs.

**Contrepartie assumée** : les jetons OAuth des clients sont détenus par Composio,
hébergé hors d’Europe. Cette phrase doit être visible dans l’écran, pas cachée.

## Scénarios utilisateur

### User Story 1 — Poser la clé du client (Priorité : P1)

En tant qu’installateur, je colle la clé Composio dédiée à ce client dans un bloc
en haut de l’onglet Intégrations, pour que ses applications deviennent connectables.

**Test indépendant** : ouvrir Intégrations sur une instance neuve, coller une clé
valide, l’enregistrer, et voir la liste des applications apparaître en dessous.

### User Story 2 — Connecter une application (Priorité : P1)

En tant que client, je clique sur « Connecter » en face de Gmail, je m’authentifie
chez Google, et je reviens sur un écran qui affiche Gmail comme connecté.

**Test indépendant** : depuis une instance dont la clé est posée, connecter une
application et vérifier que son état passe à « connecté » sans rechargement manuel.

### User Story 3 — Retirer une connexion (Priorité : P2)

En tant que client, je peux retirer une application connectée, avec une confirmation
avant que quoi que ce soit ne parte.

## Exigences

- **E1** — La clé Composio reste côté serveur. Le navigateur ne la reçoit jamais,
  même masquée, et ne joint jamais `backend.composio.dev` directement. Tout passe
  par le proxy du backend, comme pour Hermes.
- **E2** — Une seule URL : `localhost:3000`. La fenêtre d’autorisation OAuth s’ouvre
  chez le fournisseur, le retour revient sur `localhost:3000`.
- **E3** — Le bloc clé ne dit « connectée » que si une clé est réellement enregistrée
  (règle établie par `src/lib/providers/etat.ts`).
- **E4** — Trois états distincts pour une application : `connectée`, `non connectée`,
  `indisponible`. Une source injoignable n’est jamais présentée comme une panne.
- **E5** — L’écran nomme Composio et dit où vivent les jetons. Pas de formulation
  qui laisse croire que la connexion reste chez le client.
- **E6** — Réservé à l’administrateur, comme le reste du proxy moteur.

## Hors périmètre de cette tranche

- Faire **utiliser** ces outils par l’agent (branchement du point MCP de Composio
  dans le moteur). Traité à la tranche suivante : la clé doit exister d’abord.
- La facturation et le suivi de consommation par client, qui se lisent dans le
  tableau de bord Composio.

## Ce qui ne peut pas être vérifié maintenant

Aucune clé Composio n’existe encore pour ce projet. Le code est écrit d’après la
référence publique de l’API v3 (`https://backend.composio.dev/api/v3`, en-tête
`x-api-key`). **Les formes de réponse exactes restent à confirmer contre l’API
réelle** dès qu’une clé sera disponible.
