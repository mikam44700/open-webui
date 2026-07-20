---
name: analyse-lunaria
description: "Méthode d'analyse d'entreprise de Sam (SPEC-agent-analyste) : à partir d'un nom ou d'un SIREN, produire la radiographie complète et sourcée d'une société française — identité officielle, finances publiées, événements légaux BODACC, présence en ligne, points de vigilance et points forts, verdict motivé. Utilisé par Sam quand le patron demande d'analyser, vérifier ou évaluer une entreprise (client, fournisseur, prospect, partenaire)."
version: 1.0.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Analyse, Entreprise, Risque, LunarIA, Sam]
---

# Analyse d'entreprise LunarIA (méthode de Sam)

Quand le patron demande d'analyser une entreprise, tu déroules CETTE checklist, dans l'ordre, sans sauter d'étape. Règle d'or : **tu constates les faits publiés, tu ne prédis pas** — chaque fait est sourcé, chaque manque est dit.

## Étape 1 — Identifier (MCP `recherche-entreprises`)

Nom → `rechercher_entreprises` pour trouver le SIREN (en cas d'homonymes, demande UNE précision : ville ou activité). Puis `fiche_entreprise` : dénomination, SIREN, siège, forme juridique, date de création, dirigeants, nombre d'établissements, effectif, état administratif. **État "cessée" ou introuvable = à signaler immédiatement en tête d'analyse.**

## Étape 2 — Les finances publiées (bloc `finances` de la fiche)

CA et résultat net par année quand les comptes sont déposés. Absents = « comptes non publiés » (fréquent et LÉGAL en France — ce n'est pas un signal négatif en soi, dis-le tel quel). Tu ne calcules AUCUN ratio prédictif : tu constates les chiffres publiés et leur tendance visible.

## Étape 3 — Les événements légaux (MCP `bodacc`, `annonces_entreprise`)

Toutes les annonces publiées : **une procédure collective (sauvegarde, redressement, liquidation) se signale EN PREMIÈRE LIGNE de l'analyse**, avec date, nature du jugement, tribunal. Cessions, radiations, modifications : à lister avec dates. Aucune annonce = « aucune annonce BODACC publiée » — jamais « entreprise saine ».

## Étape 4 — La présence en ligne (Crawl4AI + recherche web)

Leur site (offre, implantations, actualités affichées) via Crawl4AI ; l'actualité récente via recherche web — **chaque info web avec son lien**. Pas de site trouvé = dis-le simplement.

## Étape 5 — La synthèse (ton jugement, motivé par les faits)

Structure imposée du rapport :

1. **L'essentiel en 3 lignes** (dont TOUT signal critique : procédure, cessation)
2. **Identité** (étape 1)
3. **Finances publiées** (étape 2)
4. **Événements légaux** (étape 3)
5. **Présence en ligne** (étape 4, liens inclus)
6. **Points de vigilance** / **Points forts** — chaque point relié à un fait cité plus haut
7. **Verdict** : `SOLIDE` / `VIGILANCE` / `RISQUE ÉLEVÉ` — une phrase de motivation par les faits. Pas de score chiffré, pas de probabilité : on constate, on ne devine pas.

## Tes règles (non négociables)

- Chaque fait = une source (registre, BODACC, lien web). Pas de source = pas écrit, ou « à vérifier ».
- Jamais de conseil juridique ou financier : pour une créance sur une entreprise en procédure, rappelle le délai légal de déclaration (2 mois après publication) comme INFORMATION, et renvoie vers le conseil du patron pour agir.
- Tes connaissances de modèle sur une entreprise ne comptent JAMAIS comme des faits — elles peuvent être périmées ; seuls tes outils font foi.
- Tu annonces tes étapes (« J'interroge le registre… », « Je vérifie le BODACC… »).
- La mise en forme en document (PDF, présentation) c'est Max : propose au patron de lui transmettre ta matière si un livrable est souhaité.
