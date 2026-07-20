---
name: collegues-lunaria
description: "Consultation entre collègues (SPEC-consultation-collegues) : permet à chaque agent de poser UNE question à UN collègue de l'équipe (Luna, Mike, Victor, Léa, Sacha, Théo, Clara) et d'intégrer sa réponse à son propre travail, en la citant. Utilisé quand l'expertise d'un collègue enrichit la tâche en cours (ex. Léa demande une radiographie à Clara, Luna demande un point à Victor)."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Équipe, Consultation, LunarIA]
prerequisites:
  commands: [python3]
---

# Consulter un collègue (capacité commune de l'équipe)

Quand l'expertise d'un collègue enrichirait TON travail en cours, tu peux le consulter directement — sans faire passer le patron par la case facteur.

```bash
python3 "$HERMES_HOME/skills/lunaria-app/collegues-lunaria/collegue_cli.py" consulter \
  --collegue clara --question "Ta radiographie complète de la société R2C (SIREN 834217853) ?"
```

Collègues : `luna` (coordination), `mike` (mémoire), `victor` (impayés), `lea` (prospection), `sacha` (veille), `theo` (documents), `clara` (analyse d'entreprise).

## Les règles (non négociables)

1. **Une question précise et AUTONOME** : le collègue ne voit pas ta conversation — mets tout le contexte nécessaire dans la question (noms, SIREN, période).
2. **Tu cites toujours ta source** : sa contribution apparaît ATTRIBUÉE dans ta réponse au patron (« selon l'analyse de Clara… », « Victor m'indique que… ») — jamais fondue anonymement.
3. **Jamais en cascade** : si la demande que TU as reçue porte le marqueur [CONSULTATION D'UN COLLÈGUE], tu réponds directement — tu ne consultes personne à ton tour.
4. **Consulter n'est pas déléguer** : tu demandes son EXPERTISE (analyse, vérification, point d'état), pas qu'il fasse ta mission. Ton métier reste le tien.
5. **Échec honnête** : collègue injoignable ou trop long → tu le DIS au patron et tu livres quand même ton travail. Tu n'inventes JAMAIS la réponse d'un collègue.
6. **Aucune action de sortie par consultation** : le règlement commun (validation du patron pour tout envoi) s'applique inchangé, chez toi comme chez le consulté.
