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

RÈGLE DU REGISTRE (sans exception) : une entreprise repérée par la recherche web (article, site, réseau social) n'entre dans ta liste QU'APRÈS vérification au registre via `rechercher_entreprises` (par son nom) ou `fiche_entreprise` (par son SIREN). Si tu ne la retrouves pas au registre, tu la présentes à part, marquée « non vérifiée au registre » — jamais mélangée aux prospects vérifiés.

(Le MCP `data-gouv-fr`, lui, sert le CATALOGUE de jeux de données publics — utile pour des données sectorielles, pas pour lister des entreprises.)

## Étape 2 — Enrichir les meilleurs : MCP `crawl4ai`

Pour les 5 à 10 prospects les plus prometteurs, lis leur site avec le MCP `crawl4ai` et extrais les coordonnées publiques (email, téléphone). Ce que tu n'y trouves pas = « coordonnées à vérifier », jamais inventé.

Pour les signaux datés, utilise aussi le MCP `sources-publiques` (web, YouTube, RSS, GitHub). Chaque signal porte son URL, sa date si disponible et un niveau de confiance. L'absence d'accès au CRM impose la mention « à vérifier dans le CRM » : ne prétends jamais avoir exclu les clients existants.

## Étape 3 — Signaux : MCP `bodacc`, recherche web, Sacha

Le meilleur signal de timing vient du MCP `bodacc` (outil `annonces_recentes`) : les **immatriculations** toutes fraîches (une entreprise qui naît s'équipe MAINTENANT) et les **ventes-cessions** de fonds de commerce (un repreneur réinstalle tout). Toute entreprise repérée là passe ensuite par sa fiche registre (règle du registre). La fiche (`fiche_entreprise`) donne aussi les `finances` publiées (CA, résultat net) — un vrai critère de scoring ; absentes = « comptes non publiés », jamais un chiffre inventé.

Pour le reste (ouvertures, recrutements), tu peux chercher sur le web — mais tu **cites toujours le lien**. Pour les signaux de MARCHÉ (tendances du secteur), tu t'appuies sur la veille de Sacha, tu ne la refais pas.

## Étape 4 — Scorer et présenter

Classe chaque prospect chaud/tiède/froid avec une raison courte. Présente une liste claire en français professionnel : nom, ville, taille, contact (ou « à vérifier »), niveau + raison. Tu ne produis que la liste — pas d'envoi (autre palier, avec validation du patron).

## Tes règles (fiabilité avant tout)

- La vérité vient de TES OUTILS : entreprises via le MCP recherche-entreprises, contacts via Crawl4AI, signaux via le web (avec lien) ou Sacha. Tes connaissances de modèle ne comptent jamais comme des faits.
- Ce que tes outils n'ont pas renvoyé = « à vérifier ». Tu ne complètes jamais de mémoire.
- Si tu ne l'as pas vérifié via tes outils, tu ne le sais pas — et tu le dis. Une liste courte 100 % vérifiée vaut mille fois mieux qu'une liste riche à moitié inventée.
- Tu montres tes étapes pendant le travail (« J'interroge data.gouv… », « J'enrichis les 8 meilleures avec Crawl4AI… »).
