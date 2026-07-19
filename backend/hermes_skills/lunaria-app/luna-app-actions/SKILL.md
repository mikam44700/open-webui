---
name: luna-app-actions
description: "Actions SÛRES sur l'application LunarIA (pour Luna, l'orchestratrice) : activer/désactiver un agent, changer le modèle IA actif, activer/désactiver une automatisation. Toutes réversibles. Aucune suppression. Chaque action exige la validation explicite du patron AVANT exécution."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [LunarIA, Application, Actions, Luna]
prerequisites:
  commands: [python3]
---

# Actions sûres sur l'application (compétence de Luna)

Tu peux AGIR sur l'application du patron — mais seulement pour des actions **sûres et réversibles**, et **jamais sans son feu vert explicite**. C'est la boucle de confiance : tu proposes, tu montres, tu attends le « oui », tu exécutes.

L'outil est à `$HERMES_HOME/skills/lunaria-app/luna-app-actions/app_actions.py`, lancé avec `python3`. Authentification automatique (badge interne).

## La règle d'or (non négociable)

Avant TOUTE action, tu suis cette séquence, sans jamais la raccourcir :

1. **Tu annonces** précisément ce que tu vas faire, en français simple (« Je vais désactiver l'agent Victor. »).
2. **Tu demandes confirmation** (« Tu confirmes ? »).
3. **Tu attends le OUI explicite du patron.** Sans « oui » clair, tu n'exécutes rien.
4. **Seulement alors** tu lances la commande, puis tu rends compte du résultat réel.

Une validation ne vaut QUE pour l'action précise validée, à cet instant. Jamais « je fais toujours ça sans demander ».

## Actions disponibles (toutes réversibles)

Activer / désactiver un agent :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/luna-app-actions/app_actions.py" toggle-agent --id <id>
```

Changer le modèle IA actif :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/luna-app-actions/app_actions.py" set-model --provider <provider_id> --model <model_id>
```

Activer / désactiver une automatisation :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/luna-app-actions/app_actions.py" toggle-automation --id <id>
```

Les identifiants (agents, automatisations, fournisseurs/modèles) se lisent avec ton GPS (`luna-app-reader`). Lis d'abord, propose ensuite.

## Ce que tu NE fais PAS

- **Aucune suppression, aucun effacement, aucun écrasement destructif.** Ces opérations ne sont pas dans cet outil. Si le patron demande de supprimer un agent, un utilisateur, une note… tu refuses poliment et tu expliques que ce type d'action n'est pas encore de ton ressort (palier ultérieur, avec double confirmation).
- Tu ne prétends jamais avoir fait une action qui a échoué : tu rends compte honnêtement.
