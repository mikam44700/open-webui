---
name: notes-lunaria
description: "Pont vers les Notes de l'application LunarIA : permet à un agent de LIRE et d'ÉCRIRE dans la page Notes du patron (lister, lire, créer une note). C'est le SEUL moyen correct d'enregistrer un document dans LunarIA — jamais Obsidian, Apple Notes ni un fichier local. Utilisé par tous les agents quand le patron demande de sauvegarder, ranger ou consulter une note."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Notes, LunarIA, Application]
prerequisites:
  commands: [python3]
---

# Notes LunarIA (pont vers l'application)

Quand le patron te demande de **sauvegarder / ranger / noter** quelque chose, ou de **consulter / lire** ses notes, tu utilises CE pont — et lui seul. Il écrit dans la vraie page Notes de LunarIA, celle que le patron voit dans son application. Tu n'utilises JAMAIS une autre skill de notes (Obsidian, Apple Notes) ni un fichier local : elles ne mènent nulle part pour le patron.

L'outil est un script à `$HERMES_HOME/skills/lunaria-app/notes-lunaria/notes_cli.py`. Lance-le avec `python3`. L'authentification est automatique (clé interne lue dans l'environnement) : tu n'as aucun jeton à saisir ni à afficher.

## Lister les notes du patron

```bash
python3 "$HERMES_HOME/skills/lunaria-app/notes-lunaria/notes_cli.py" list
```

Renvoie chaque note sous la forme `- [identifiant] Titre`. Utilise l'identifiant pour lire ensuite.

## Lire une note

```bash
python3 "$HERMES_HOME/skills/lunaria-app/notes-lunaria/notes_cli.py" read --id <identifiant>
```

## Créer une note

Rédige d'abord le contenu (markdown, registre professionnel — le lecteur est un dirigeant) dans un fichier temporaire, puis crée la note à partir de ce fichier. C'est la méthode fiable, même pour un texte long :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/notes-lunaria/notes_cli.py" \
  create --title "Titre clair et court" --content-file /tmp/ma-note.md
```

Le script confirme la création avec l'identifiant de la note. Annonce alors au patron que la note est disponible dans sa page Notes.

## Supprimer une note — INTERDIT sans le feu vert du patron

Effacer une note est irréversible. Le pont **bloque** toute suppression par défaut. Tu ne supprimes JAMAIS de ta propre initiative. Si — et seulement si — le patron a demandé explicitement, en toutes lettres, de supprimer une note précise, tu peux exécuter :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/notes-lunaria/notes_cli.py" delete --id <identifiant> --confirm-human
```

Sans validation explicite du patron, tu n'ajoutes jamais `--confirm-human`. Dans le doute, tu ne supprimes pas : tu demandes.

## Tes règles

- Une seule maison pour les notes : la page Notes de LunarIA, via ce pont. Rien d'autre.
- Tu ne montres jamais la clé d'accès ni les détails techniques au patron ; tu parles de « ta page Notes ».
- Tu n'inventes pas le contenu d'une note : pour lire, tu utilises `read` ; tu ne devines pas.
- Suppression = action du patron, jamais la tienne.
