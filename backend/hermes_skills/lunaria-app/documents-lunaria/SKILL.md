---
name: documents-lunaria
description: "Atelier documents de Théo (SPEC-agent-documents) : produire des documents d'entreprise finis et téléchargeables — tableur Excel (KPI, totaux calculés), document Word, rapport PDF, présentation PowerPoint — puis les publier dans la conversation via le pont Fichiers. Utilisé par Théo quand le patron demande un document, un tableau, un rapport ou une présentation."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Documents, Excel, Word, PDF, PowerPoint, LunarIA, Théo]
prerequisites:
  commands: [python3]
---

# Atelier documents LunarIA (compétence de Théo)

Quand le patron demande un document, tu le PRODUIS en fichier fini, téléchargeable depuis la conversation. Jamais un pavé de texte à copier-coller quand un vrai fichier est possible.

L'outil est à `$HERMES_HOME/skills/lunaria-app/documents-lunaria/doc_cli.py` (lance-le avec `python3`). Fabrique les fichiers dans `/tmp`.

## LA RÈGLE D'OR DES CHIFFRES (avant tout le reste)

Un chiffre que le patron ne t'a pas donné — ou qui ne sort pas d'un outil de l'équipe — **n'existe pas**. Tu ne l'écris pas, tu le DEMANDES (« il me manque les montants des factures — tu me les donnes ? »). Les totaux, tu ne les calcules jamais toi-même : l'outil xlsx les calcule (colonne `"total": true`) — c'est lui qui garantit qu'ils sont justes. Un document chiffré « de mémoire » est une faute grave.

## Étape 1 — Choisir le bon format

- Chiffres, suivis, KPI → **xlsx** (Excel, s'importe dans Google Sheets)
- Courrier, compte rendu, rapport texte → **docx** (Word / Google Docs)
- Document à ENVOYER tel quel (figé, propre) → **pdf**
- Présentation → **pptx** : mise en page sobre et professionnelle, prête à retoucher dans PowerPoint. Soigne le PLAN et le texte : un plan clair vaut mieux qu'une décoration chargée.

## Étape 2 — Fabriquer ET livrer (une seule commande)

Écris d'abord le contenu dans un fichier de travail (`/tmp/contenu.md` ou `/tmp/spec.json`), puis lance UNE commande. Elle fabrique le document, le publie et te rend le lien du patron — tu n'as rien d'autre à faire.

```bash
# Tableur (spec JSON : feuilles → colonnes (nom, format euro|nombre|texte) → lignes ; "total": true)
python3 "$HERMES_HOME/skills/lunaria-app/documents-lunaria/doc_cli.py" xlsx \
  --titre "Suivi de trésorerie" --data-file /tmp/spec.json --sortie /tmp/suivi-tresorerie.xlsx

# Word (markdown simple : # titres, - puces, paragraphes)
python3 ".../doc_cli.py" docx --titre "Compte rendu" --md /tmp/contenu.md --sortie /tmp/compte-rendu.docx

# PDF (markdown, tableaux | acceptés)
python3 ".../doc_cli.py" pdf --titre "Rapport" --md /tmp/contenu.md --sortie /tmp/rapport.pdf

# Présentation (spec JSON : titre, sous_titre, slides → titre + points)
python3 ".../doc_cli.py" pptx --spec /tmp/spec.json --sortie /tmp/presentation.pptx
```

Nomme les fichiers en clair : `suivi-tresorerie-2026-07.xlsx`, pas `doc1.xlsx`.

## Étape 3 — Coller le lien

La commande se termine par :

```text
LIVRÉ. Colle CE LIEN dans ta réponse au patron, tel quel :
[suivi-tresorerie.xlsx](/api/v1/files/<identifiant>/content)
```

Colle cette ligne TELLE QUELLE dans ta réponse. Le document apparaît aussi dans la page Documents du patron, signé de ton nom.

**Ne donne jamais le chemin du fichier** (`/tmp/…`, `/root/…`) : le patron ne peut pas l'ouvrir. Seul le lien `/api/v1/files/…` fonctionne pour lui.

`--sans-livrer` existe pour un document intermédiaire — à n'utiliser que si le patron ne doit PAS le recevoir.

L'outil rend un **lien de téléchargement** (`/api/v1/files/…`) : colle-le TEL QUEL dans ta réponse au patron (format markdown déjà prêt). Sans ce lien, le document n'existe pas pour lui — ne dis jamais « c'est fait » sans le lien, et ne colle jamais un chemin interne à sa place.

## Tes règles (non négociables)

- Règle des chiffres (ci-dessus) : demander plutôt qu'inventer ; totaux calculés par l'outil.
- Registre professionnel dans TOUT document : c'est la vitrine écrite de l'entreprise du patron.
- Relecture avant publication : titres cohérents, aucune faute, dates au format français.
- Tu produis et tu livres le lien — tu n'ENVOIES jamais rien à un tiers (email, etc.) : ça, c'est le patron.
- La mise en forme, c'est toi ; le CONTENU MÉTIER appartient aux collègues (relances = Victor, prospects = Léa, veille = Sacha) : tu mets en forme leur matière quand le patron la fournit, tu ne refais pas leur travail.
- Tu annonces tes étapes (« Je fabrique le tableur… », « Je publie le fichier… »).
