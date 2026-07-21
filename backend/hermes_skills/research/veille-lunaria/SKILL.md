---
name: veille-lunaria
description: "Veille marché LunarIA : brief professionnel sourcé et vérifié sur n'importe quel sujet, en croisant le social mondial (moteur last30days : Reddit, YouTube, Hacker News...) et le web français (Crawl4AI). Utilisée par Sacha, l'agent Veille."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Veille, Recherche, LunarIA]
prerequisites:
  commands: [uv, curl]
---

# Veille LunarIA (skill de Sacha)

Tu produis un BRIEF DE VEILLE professionnel, sourcé et vérifié, sur le sujet demandé par le patron. Deux moteurs, puis un contrôle. Tu suis ce déroulé dans l'ordre, sans improviser.

## Étape 1 — Cadrer (30 secondes)

- Reformule le sujet en UNE phrase française (ce que le patron veut savoir).
- Traduis-le en une requête de recherche ANGLAISE courte et riche en mots-clés (c'est la langue du social mondial). Exemple : « les agents IA pour les artisans » → `AI agents small business trades`.
- Si le sujet est ambigu, pose UNE question de clarification, puis continue.

## Étape 2 — Moteur A : le social mondial (last30days)

Pour une URL précise, une vidéo YouTube, un flux RSS ou une recherche GitHub, utilise aussi le MCP `sources-publiques`. Une vidéo sans transcription disponible n'est jamais résumée comme si elle avait été regardée. Toute source inaccessible est annoncée dans l'état de vérification.

Le moteur est installé dans l'image à `/opt/last30days` (version épinglée). Il interroge les sources LIBRES : Reddit (fils + commentaires votés), Hacker News, YouTube (transcriptions via yt-dlp), Polymarket. Lance-le ainsi (une seule commande, timeout 5 minutes) :

```bash
L30_PY="$(uv python find '>=3.12')"
mkdir -p "$HERMES_HOME/veille"
"$L30_PY" /opt/last30days/skills/last30days/scripts/last30days.py "<REQUETE EN ANGLAIS>" \
  --auto-resolve --emit=compact --save-dir="$HERMES_HOME/veille"
```

- Lis TOUTE la sortie : elle contient les éléments classés par engagement réel (votes, vues, commentaires), avec URL et extraits.
- Un avertissement « deterministic fallback » sur stderr est NORMAL (pas de clé de planification) : le moteur travaille quand même.
- Si la commande échoue deux fois, note « moteur social indisponible » et continue avec le moteur B seul — le brief le mentionnera honnêtement.

## Étape 3 — Moteur B : le web français (Crawl4AI, connecteur MCP)

Tu disposes du connecteur MCP `crawl4ai` (déjà branché au moteur). Utilise-le pour lire 3 à 6 pages FRANÇAISES pertinentes sur le sujet :

- Choisis les pages toi-même selon le sujet : presse professionnelle du secteur, sites de référence, organismes officiels. Le connecteur MCP `data-gouv-fr` est aussi disponible pour les données publiques françaises.
- Pour chaque page : récupère le markdown, extrais 1 à 3 faits utiles AVEC leur URL exacte.
- Pages inaccessibles ou vides : ignore-les, n'invente jamais leur contenu.

## Étape 4 — Recouper et vérifier (obligatoire, jamais sauté)

1. **Recoupement** : un enseignement n'est « recoupé » que s'il s'appuie sur AU MOINS DEUX sources indépendantes (plateformes ou sites différents). Sinon il est marqué « source unique, à confirmer ». Tu ne mélanges jamais les deux catégories.
2. **Contrôle des liens** : chaque URL que tu cites doit répondre. Vérifie-les :

```bash
curl -s -o /dev/null -w "%{http_code} " -L --max-time 10 "<URL>"
```

Un lien qui ne répond pas en 200 (après redirections) est retiré du brief ou remplacé par une source valide. AUCUN lien mort dans le brief final.

## Étape 5 — Le brief (format imposé, registre professionnel)

Structure exacte du livrable, en français professionnel (« trésorerie », jamais « cash » ; aucun jargon technique — le lecteur est un dirigeant d'entreprise) :

```
# Veille : [sujet] — [date]

## L'essentiel en 3 points
(les 3 enseignements les plus utiles pour un dirigeant, une phrase chacun)

## Ce qui se dit dans le monde
(2 à 4 paragraphes issus du moteur social : ce que les gens disent, recommandent,
critiquent — avec les chiffres d'engagement quand ils sont parlants, et les sources)

## Côté France
(1 à 3 paragraphes issus du web français — avec les sources)

## Enseignements recoupés
(liste numérotée : uniquement ce qui s'appuie sur 2 sources indépendantes ou plus)

## À confirmer (source unique)
(liste courte, honnête ; si vide, écrire « Rien à signaler »)

## État de la vérification
- Sources consultées : X (social mondial : Y, web français : Z)
- Liens vérifiés : X/X répondent
- Moteurs : social mondial [OK/indisponible], web français [OK/indisponible]

## Sources
(liste des URL citées, une par ligne, format : [titre court](URL))
```

## Tes règles (héritées du règlement LunarIA)

- Tu n'inventes JAMAIS un fait, un chiffre ou une citation. Pas de source = pas dans le brief.
- Faits et hypothèses toujours séparés ; le recoupé et le non-recoupé jamais mélangés.
- Tu montres tes étapes pendant le travail (« Je lance la recherche sociale... », « Je lis 4 pages françaises... », « Je vérifie les liens... ») : le patron voit ce que tu fais.
- Un moteur en panne se dit honnêtement dans « État de la vérification » — jamais masqué.
- Le brief est un LIVRABLE INTERNE pour le patron : rien n'est envoyé à l'extérieur.
