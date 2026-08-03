# Vérifier la page à l'écran

## Avant de commencer

Tout se passe sur `http://localhost:3000`. Aucun second port, aucun serveur de
développement. Pour voir un changement, on reconstruit et on redémarre :

```bash
cd "Apps/OpenWebUI"
docker compose -f docker-compose.fr.yaml build
docker compose -f docker-compose.fr.yaml up -d
```

**Committer avant de reconstruire** : sinon l'onglet garde l'ancien JavaScript, et la
version affichée ne correspond à rien.

## Les tests qui ne demandent pas d'écran

```bash
npm run test:frontend -- src/lib/kanban/
npm run lint:frontend
npm run format
```

Vérification de compilation d'un composant, **depuis la racine du dépôt** (les modules ne
se résolvent pas depuis `/tmp`) :

```bash
node --input-type=module -e "
import { compile } from 'svelte/compiler';
import { readFileSync } from 'node:fs';
const f = 'src/lib/components/kanban/CarteTache.svelte';
const { warnings } = compile(readFileSync(f, 'utf8'), { filename: f, generate: 'client' });
console.log('OK —', warnings.length, 'avertissement(s)');
"
```

## Ce qu'il faut regarder, dans cet ordre

### 1. Le moteur est coupé

C'est le premier cas à vérifier, pas le dernier : c'est celui qui trahit une page mal
faite.

```bash
docker compose -f docker-compose.fr.yaml stop hermes
```

**Attendu** : une alerte chapeau, **une seule**, qui dit que le moteur ne répond pas.
Aucune colonne affirmant que le travail est terminé, aucune mention de tableau vide,
aucun message de panne empilé par source (FR-013, SC-005).

### 2. Le moteur tourne mais n'a pas de registre de tâches

**Attendu** : une phrase qui explique que le registre n'est pas installé. **Pas d'alerte,
pas de rouge.** Ce n'est pas une panne (règle D27).

### 3. Le tableau est vide

**Attendu** : une phrase, pas six colonnes vides alignées.

### 4. Le tableau a des tâches

Créer de quoi remplir les six colonnes, depuis le moteur :

```bash
docker compose -f docker-compose.fr.yaml exec hermes hermes kanban create "Relancer la facture 2411"
docker compose -f docker-compose.fr.yaml exec hermes hermes kanban list
```

**Attendu** :

- chaque tâche dans la colonne qui correspond à son état ;
- une tâche `scheduled` porte un libellé disant qu'elle attend le temps, **pas** une
  date (le moteur n'en a pas) ;
- **le compte total à l'écran égale le compte de `hermes kanban list`** — c'est la
  vérification qui attrape le défaut de la version Desktop, où des tâches tombaient
  silencieusement dans la mauvaise colonne (SC-002).

### 5. Le type de blocage

Le point le plus facile à rater.

**Attendu** :

- une tâche bloquée sur `needs_input` affiche « attend votre réponse » **et** le bouton
  de déblocage ;
- une tâche bloquée sur `dependency` affiche « attend une autre tâche » **sans** bouton
  de déblocage ;
- `capability` et `transient` : pas de bouton non plus.

Proposer de débloquer une tâche qui attend sa dépendance inviterait le client à casser
l'ordre de travail que l'assistant a établi (FR-004).

### 6. Débloquer

**Attendu** : la tâche quitte « Bloqué », le message écrit reste visible dans la fiche,
et l'écran affiche **l'état réel renvoyé par le moteur**, pas l'état espéré (FR-017).

Vérifier aussi le refus : si la tâche a changé entre-temps, la page recharge et montre
la réalité plutôt que d'insister.

### 7. La fraîcheur

Modifier une tâche depuis la ligne de commande pendant que la page est ouverte.

**Attendu** : le changement apparaît en moins de 10 secondes sans recharger (SC-003), et
**ce qui était en train d'être lu ou écrit n'est pas perdu** (FR-011). Ouvrir la fiche
d'une tâche, commencer à taper un message, attendre deux tours de sondage : le texte doit
toujours être là.

### 8. La navigation et les langues

**Attendu** : une entrée de premier niveau, au même rang que « Moteur » (D3). Basculer
en anglais : aucune chaîne française ne doit rester à l'écran.

### 9. L'écran étroit

Réduire la fenêtre à la largeur d'un téléphone.

**Attendu** : les six colonnes restent atteignables, et **la page ne défile pas
horizontalement dans son ensemble** — seul le tableau défile, dans son propre conteneur.
