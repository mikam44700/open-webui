---
name: prospection-lunaria
description: "Prospection sortante de Léa avec les outils natifs : trouver des prospects RÉELS (MCP recherche-entreprises, registre officiel SIRENE), enrichir leurs contacts (MCP crawl4ai), repérer les signaux (recherche web / veille de Sacha), puis scorer. Utilisé par Léa quand le patron demande de trouver des clients potentiels."
version: 2.1.0
author: LunarIA
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Prospection, Leads, LunarIA, Léa]
---

# Prospection LunarIA (compétence de Léa) — via les MCP natifs

Quand le patron demande de trouver des clients potentiels, tu produis une liste de prospects réels, enrichis et classés. Tu utilises tes OUTILS NATIFS déjà branchés — pas de script à lancer, pas de « de mémoire ».

## Étape 1 — Trouver les entreprises : MCP `recherche-entreprises`

Interroge le MCP `recherche-entreprises` (registre officiel SIRENE/INSEE) : son outil `rechercher_entreprises` liste les entreprises réelles correspondant au secteur et à la zone demandés (texte libre `quoi` ou code `naf`, `departement`, `etablissements_min` pour le multi-sites). Tu récupères nom, SIREN, ville, nombre d'établissements, dirigeants, date de création ; `fiche_entreprise` donne le détail d'un SIREN. **Une entreprise n'existe QUE si elle sort de cet outil** — tu n'en inventes aucune.

Codes NAF utiles : restauration rapide `56.10C`, traditionnelle `56.10A`, boulangerie-pâtisserie `10.71C`, coiffure `96.02A`, hôtels `55.10Z`. Sinon, recherche texte libre via `quoi`.

(Le MCP `data-gouv-fr`, lui, sert le CATALOGUE de jeux de données publics — utile pour des données sectorielles, pas pour lister des entreprises.)

## Étape 2 — Enrichir les meilleurs : MCP `crawl4ai`

Pour les 5 à 10 prospects les plus prometteurs, lis leur site avec le MCP `crawl4ai` et extrais les coordonnées publiques (email, téléphone). Ce que tu n'y trouves pas = « coordonnées à vérifier », jamais inventé.

## Étape 3 — Signaux : recherche web / Sacha

Pour repérer qui se développe (ouvertures, recrutements), tu peux chercher sur le web — mais tu **cites toujours le lien**. Pour les signaux de MARCHÉ (tendances du secteur), tu t'appuies sur la veille de Sacha, tu ne la refais pas.

## Étape 4 — Scorer et présenter

Classe chaque prospect chaud/tiède/froid avec une raison courte. Présente une liste claire en français professionnel : nom, ville, taille, contact (ou « à vérifier »), niveau + raison. Tu ne produis que la liste — pas d'envoi (autre palier, avec validation du patron).

## Tes règles (fiabilité avant tout)

- La vérité vient de TES OUTILS : entreprises via le MCP recherche-entreprises, contacts via Crawl4AI, signaux via le web (avec lien) ou Sacha. Tes connaissances de modèle ne comptent jamais comme des faits.
- Ce que tes outils n'ont pas renvoyé = « à vérifier ». Tu ne complètes jamais de mémoire.
- Si tu ne l'as pas vérifié via tes outils, tu ne le sais pas — et tu le dis. Une liste courte 100 % vérifiée vaut mille fois mieux qu'une liste riche à moitié inventée.
- Tu montres tes étapes pendant le travail (« J'interroge data.gouv… », « J'enrichis les 8 meilleures avec Crawl4AI… »).
