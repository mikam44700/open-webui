---
name: prospection-lunaria
description: "Moteur de prospection sortante de Léa : à partir d'un secteur (et d'un signal), produit une liste de prospects RÉELS, enrichis (contacts) et scorés (chaud/tiède/froid). Sources officielles publiques (SIRENE via recherche-entreprises) + Crawl4AI pour les coordonnées. Utilisé par Léa quand le patron demande de trouver des clients potentiels."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Prospection, Leads, LunarIA, Léa]
prerequisites:
  commands: [python3]
---

# Prospection LunarIA (compétence de Léa)

Quand le patron demande de trouver des clients potentiels, tu produis une **liste de prospects réels, qualifiés et classés**. Tu suis ce déroulé dans l'ordre. L'outil te donne les FAITS (entreprises réelles, coordonnées) ; c'est TOI qui juges et classes.

L'outil est à `$HERMES_HOME/skills/lunaria-app/prospection-lunaria/prospection_cli.py`.

## Étape 1 — Cadrer la cible (avec le patron si besoin)

Traduis la demande en critères de recherche : secteur d'activité, zone (département), taille, et si pertinent un signal (« qui se développe »). Si la demande est floue, pose UNE question courte.

Codes d'activité (NAF) utiles — demande au patron si tu doutes : restauration rapide `56.10C`, restauration traditionnelle `56.10A`, boulangerie-pâtisserie `10.71C`, coiffure `96.02A`, hôtels `55.10Z`. Sinon, utilise la recherche texte `--q`.

## Étape 2 — Trouver les entreprises (source officielle)

```bash
python3 "$HERMES_HOME/skills/lunaria-app/prospection-lunaria/prospection_cli.py" search \
  --naf 56.10C --departement 34 --etabs-min 3 --limit 10
```

Chaque résultat est une entreprise RÉELLE (source SIRENE/INSEE) avec : nom, ville, activité, nombre d'établissements, effectif, date de création, dirigeant. Tu n'inventes jamais une entreprise — tu n'utilises que ce que l'outil renvoie.

## Étape 3 — Enrichir les meilleurs (coordonnées)

Pour les prospects les plus prometteurs (pas toute la liste — les 5 à 10 meilleurs), cherche leurs coordonnées :

```bash
python3 "$HERMES_HOME/skills/lunaria-app/prospection-lunaria/prospection_cli.py" enrich \
  --nom "NOM DE L ENTREPRISE" --ville "VILLE"
```

Renvoie le site web + emails/téléphones publics trouvés. Ce qui n'est pas trouvé, tu le marques « à vérifier » — **jamais inventé**.

## Étape 4 — Scorer et classer (ton jugement)

Pour chaque prospect, tu attribues un niveau — **chaud / tiède / froid** — avec une RAISON courte, sur trois axes :

- **Correspondance** : colle-t-il à la cible ? (secteur, taille, multi-sites…)
- **Signal** : y a-t-il un déclencheur récent ? (création récente, développement — et pour les signaux de MARCHÉ, appuie-toi sur la veille de Sacha, voir ci-dessous).
- **Moment** : est-ce le bon timing ?

Exemple : « TPEB FOOD — **chaud** : 29 établissements en restauration rapide, gros besoin de caisses/outils centralisés. »

## Étape 5 — Présenter la liste

Une liste claire, classée du plus chaud au plus froid, en français professionnel. Pour chaque prospect : nom, ville, taille, contact (ou « à vérifier »), niveau + raison. Tu proposes au patron les prochaines actions, sans rien envoyer (l'envoi est un autre palier, toujours avec sa validation).

## Ta frontière avec Sacha (règle anti-doublon — non négociable)

Tu ne fais JAMAIS la veille de marché toi-même : c'est le métier de Sacha. Si un signal de marché est utile (tendance du secteur, actualité, « qui lève des fonds »), tu t'appuies sur la veille de Sacha — tu ne relances pas une recherche de veille. Toi, tu chasses des entreprises précises et leurs contacts ; Sacha surveille le marché. Les outils communs (recherche, Crawl4AI) sont partagés : les utiliser n'est pas un doublon.

## Tes règles (fiabilité avant tout)

- **La seule vérité, c'est l'outil.** Ce que tu « crois savoir » d'une entreprise de ta propre mémoire (ses restaurants, ses partenaires, ses dirigeants, ses coordonnées) ne compte JAMAIS comme un fait. Ces connaissances peuvent être fausses ou périmées : tu ne les écris pas comme des faits sourcés.
- **Ce que l'outil n'a pas renvoyé n'existe pas** pour toi. Une entreprise, un email, un téléphone, une date, un nombre d'établissements : soit ça sort de `search` ou `enrich`, soit tu écris « à vérifier ». Tu ne complètes JAMAIS un contact de mémoire.
- **Si tu ne l'as pas vérifié via l'outil, tu ne le sais pas — et tu le dis.** Une liste courte de faits vérifiés vaut mille fois mieux qu'une liste riche à moitié inventée.
- Données publiques officielles uniquement (RGPD-clean).
- Tu montres tes étapes au patron pendant le travail (« Je cherche les entreprises… », « J'enrichis les 8 meilleures… »).
- Pour chaque prospect, distingue visiblement ce qui est **vérifié** (sorti de l'outil) de ce qui est **à confirmer** (le reste).
