#!/usr/bin/env python3
"""Serveur MCP « recherche-entreprises » — la porte entreprises de data.gouv pour Léa.

Le MCP officiel data.gouv (mcp.data.gouv.fr) n'expose que le CATALOGUE de datasets :
aucun outil pour lister des entreprises. Ce mini-serveur comble ce trou en interrogeant
l'API publique officielle recherche-entreprises.api.gouv.fr (données SIRENE/INSEE/INPI,
sans clé API, RGPD-clean) — la même source que l'ancien prospection_cli.py, dont il
reprend la logique, mais exposée en outil MCP natif que les agents appellent directement.

Transport stdio : lancé par le moteur Hermes via le python du venv Hermes (seul à avoir
le SDK ``mcp``). Déclaré automatiquement dans la config au démarrage de la stack par
``open_webui.hermes_bridge.entreprises_adapter`` (même esprit que Crawl4AI pré-connecté).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

RECHERCHE_API = "https://recherche-entreprises.api.gouv.fr/search"
TIMEOUT = 25
# L'API officielle plafonne per_page à 25.
MAX_PAR_PAGE = 25

mcp = FastMCP("recherche-entreprises")


def _get_json(params: dict) -> dict:
    url = f"{RECHERCHE_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resume(e: dict) -> dict:
    """Résumé d'une entreprise : uniquement des faits renvoyés par l'API, jamais complétés."""
    siege = e.get("siege") or {}
    dirigeants = [
        d.get("nom_complet") or d.get("denomination") for d in (e.get("dirigeants") or [])
    ]
    return {
        "nom": e.get("nom_complet"),
        "siren": e.get("siren"),
        "ville": siege.get("libelle_commune"),
        "code_postal": siege.get("code_postal"),
        "activite_naf": e.get("activite_principale"),
        "etablissements_ouverts": e.get("nombre_etablissements_ouverts"),
        "tranche_effectif_code": e.get("tranche_effectif_salarie"),
        "date_creation": e.get("date_creation"),
        "dirigeants": [d for d in dirigeants if d][:3],
    }


@mcp.tool()
def rechercher_entreprises(
    quoi: str = "",
    naf: str = "",
    departement: str = "",
    code_postal: str = "",
    etablissements_min: int = 0,
    limite: int = 10,
) -> str:
    """Recherche d'entreprises françaises RÉELLES dans le registre officiel (SIRENE/INSEE).

    Au moins un critère parmi `quoi` ou `naf` est requis. Paramètres :
    - quoi : recherche texte libre (nom d'entreprise, mots-clés d'activité).
    - naf : code activité NAF/APE (ex. 56.10C restauration rapide, 56.10A traditionnelle,
      10.71C boulangerie, 96.02A coiffure, 55.10Z hôtels).
    - departement : numéro de département (ex. 34 pour l'Hérault).
    - code_postal : filtre sur un code postal précis.
    - etablissements_min : ne garder que les entreprises d'au moins N établissements
      ouverts (multi-sites).
    - limite : nombre maximum de résultats (défaut 10, max 25).

    Renvoie du JSON : {total_api, entreprises: [{nom, siren, ville, code_postal,
    activite_naf, etablissements_ouverts, tranche_effectif_code, date_creation,
    dirigeants}]}. Toute donnée absente vaut null : elle est « à vérifier », jamais
    à compléter de mémoire.

    ATTENTION géographie : `departement`/`code_postal` retiennent toute entreprise ayant
    AU MOINS UN établissement dans la zone, mais `ville`/`code_postal` renvoyés sont ceux
    du SIÈGE (parfois hors zone — ex. une chaîne nationale). Le préciser dans la liste.
    """
    if not (quoi.strip() or naf.strip()):
        return json.dumps(
            {"erreur": "Donner au moins un critère : `quoi` (texte libre) ou `naf` (code activité)."},
            ensure_ascii=False,
        )
    limite = max(1, min(int(limite or 10), MAX_PAR_PAGE))
    # Marge quand on filtre localement sur le nombre d'établissements.
    params: dict = {"page": 1, "per_page": MAX_PAR_PAGE if etablissements_min else limite}
    if quoi.strip():
        params["q"] = quoi.strip()
    if naf.strip():
        params["activite_principale"] = naf.strip()
    if departement.strip():
        params["departement"] = departement.strip()
    if code_postal.strip():
        params["code_postal"] = code_postal.strip()
    try:
        data = _get_json(params)
    except Exception as exc:  # noqa: BLE001 — source externe : message honnête, pas d'invention
        return json.dumps(
            {"erreur": f"Source officielle injoignable ({exc}). Réessayer, ne rien inventer."},
            ensure_ascii=False,
        )
    results = data.get("results") or []
    if etablissements_min:
        results = [
            e for e in results
            if (e.get("nombre_etablissements_ouverts") or 0) >= int(etablissements_min)
        ]
    return json.dumps(
        {
            "total_api": data.get("total_results"),
            "entreprises": [_resume(e) for e in results[:limite]],
        },
        ensure_ascii=False,
    )


@mcp.tool()
def fiche_entreprise(siren: str) -> str:
    """Fiche détaillée d'UNE entreprise du registre officiel, à partir de son SIREN (9 chiffres).

    Renvoie du JSON : identité, adresse complète du siège, activité, effectifs,
    dirigeants, nombre d'établissements, et `finances` (chiffre d'affaires `ca` et
    `resultat_net` par année, source INPI) quand l'entreprise a déposé ses comptes —
    sinon `finances` vaut null : dire « comptes non publiés », JAMAIS inventer un chiffre.
    Données absentes = null (« à vérifier »).
    """
    siren = "".join(c for c in str(siren) if c.isdigit())
    if len(siren) != 9:
        return json.dumps({"erreur": "SIREN invalide : 9 chiffres attendus."}, ensure_ascii=False)
    try:
        data = _get_json({"q": siren, "page": 1, "per_page": 1})
    except Exception as exc:  # noqa: BLE001 — source externe : message honnête, pas d'invention
        return json.dumps(
            {"erreur": f"Source officielle injoignable ({exc}). Réessayer, ne rien inventer."},
            ensure_ascii=False,
        )
    results = data.get("results") or []
    match = next((e for e in results if e.get("siren") == siren), None)
    if match is None:
        return json.dumps(
            {"erreur": f"Aucune entreprise trouvée pour le SIREN {siren}."}, ensure_ascii=False
        )
    siege = match.get("siege") or {}
    fiche = _resume(match)
    fiche.update(
        {
            "adresse_siege": siege.get("adresse"),
            "nature_juridique": match.get("nature_juridique"),
            "etat_administratif": match.get("etat_administratif"),
            "categorie_entreprise": match.get("categorie_entreprise"),
            "finances": match.get("finances"),
        }
    )
    return json.dumps(fiche, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
