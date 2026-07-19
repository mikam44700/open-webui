#!/usr/bin/env python3
"""Serveur MCP « bodacc » — les événements légaux des entreprises (SPEC-bodacc-finances).

Le BODACC (Bulletin officiel des annonces civiles et commerciales) publie les événements
qui comptent : procédures collectives (redressements, liquidations — l'alerte qui sauve
une créance), immatriculations nouvelles et ventes/cessions de fonds (le timing d'or de
la prospection). Source : API officielle DILA/Premier ministre (opendatasoft), publique,
sans clé, RGPD-clean.

Utilisateurs : Victor (vérifier un débiteur) et Léa (prospects au bon timing).
Même modèle que entreprises_mcp.py : stdio, lancé par le moteur Hermes via le python du
venv Hermes, déclaré au démarrage par entreprises_adapter AVANT le moteur.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

BODACC_API = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.0"
    "/catalog/datasets/annonces-commerciales/records"
)
TIMEOUT = 25
MAX_LIMITE = 20

# Familles d'avis BODACC acceptées (clé simple -> libellé officiel exact).
FAMILLES = {
    "procedures-collectives": "Procédures collectives",
    "immatriculations": "Immatriculations",
    "ventes-cessions": "Ventes et cessions",
    "radiations": "Radiations",
}

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bodacc")


def _get_json(params: dict) -> dict:
    url = f"{BODACC_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _texte(brut, n: int = 260):
    """Tronque proprement un champ JSON encodé en texte (jugement, acte)."""
    if brut is None:
        return None
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except Exception:  # noqa: BLE001 — champ déjà textuel
            return brut[:n]
    return json.dumps(brut, ensure_ascii=False)[:n]


def _resume(f: dict) -> dict:
    """Résumé d'une annonce : uniquement les faits publiés, jamais complétés."""
    registre = f.get("registre") or []
    siren = next((r.replace(" ", "") for r in registre if r and r.replace(" ", "").isdigit()), None)
    return {
        "date_parution": f.get("dateparution"),
        "famille": f.get("familleavis_lib"),
        "type_avis": f.get("typeavis_lib"),
        "entreprise": f.get("commercant"),
        "siren": siren,
        "ville": f.get("ville"),
        "code_postal": f.get("cp"),
        "tribunal": f.get("tribunal"),
        "jugement": _texte(f.get("jugement")),
        "acte": _texte(f.get("acte")),
        "annonce_officielle": f.get("url_complete"),
    }


def _erreur(msg: str) -> str:
    return json.dumps({"erreur": msg}, ensure_ascii=False)


@mcp.tool()
def annonces_entreprise(siren: str, limite: int = 10) -> str:
    """Toutes les annonces BODACC officielles d'UNE entreprise, à partir de son SIREN.

    Sert surtout à vérifier si une entreprise est en PROCÉDURE COLLECTIVE (redressement,
    liquidation, sauvegarde) : la réponse liste les annonces publiées (les plus récentes
    d'abord) avec date, famille, nature du jugement et tribunal. Une liste vide signifie
    « aucune annonce BODACC publiée » — jamais « entreprise saine », on ne conclut pas
    au-delà de ce qui est publié.

    Renvoie du JSON : {total, annonces: [{date_parution, famille, type_avis, entreprise,
    siren, ville, tribunal, jugement, annonce_officielle}]}.
    """
    siren = "".join(c for c in str(siren) if c.isdigit())
    if len(siren) != 9:
        return _erreur("SIREN invalide : 9 chiffres attendus.")
    limite = max(1, min(int(limite or 10), MAX_LIMITE))
    try:
        data = _get_json(
            {"where": f'registre="{siren}"', "order_by": "dateparution DESC", "limit": limite}
        )
    except Exception as exc:  # noqa: BLE001 — source externe : message honnête
        return _erreur(f"BODACC injoignable ({exc}). Réessayer, ne rien inventer.")
    annonces = [_resume(r.get("record", {}).get("fields", {})) for r in data.get("records", [])]
    return json.dumps({"total": data.get("total_count"), "annonces": annonces}, ensure_ascii=False)


@mcp.tool()
def annonces_recentes(famille: str, departement: str = "", limite: int = 10) -> str:
    """Les annonces BODACC les plus récentes d'une famille, filtrables par département.

    `famille` (obligatoire) : "procedures-collectives" (redressements/liquidations),
    "immatriculations" (nouvelles entreprises — prospects tout frais), "ventes-cessions"
    (fonds de commerce vendus — repreneurs qui s'équipent), "radiations".
    `departement` : numéro (ex. 33). `limite` : max 20.

    Renvoie du JSON : {total, annonces: [...]}. Le BODACC ne donne pas le secteur
    d'activité de façon fiable : pour qualifier une entreprise repérée ici, TOUJOURS
    croiser son SIREN avec la fiche du registre (outil fiche_entreprise).
    """
    cle = famille.strip().lower().replace(" ", "-").replace("_", "-")
    if cle not in FAMILLES:
        return _erreur(f"famille inconnue « {famille} » — choisir parmi : {', '.join(FAMILLES)}.")
    limite = max(1, min(int(limite or 10), MAX_LIMITE))
    where = f'familleavis_lib="{FAMILLES[cle]}"'
    departement = departement.strip()
    if departement:
        if not (departement.isdigit() or departement.upper() in ("2A", "2B")):
            return _erreur("département invalide : numéro attendu (ex. 33).")
        where += f' AND numerodepartement="{departement}"'
    try:
        data = _get_json({"where": where, "order_by": "dateparution DESC", "limit": limite})
    except Exception as exc:  # noqa: BLE001 — source externe : message honnête
        return _erreur(f"BODACC injoignable ({exc}). Réessayer, ne rien inventer.")
    annonces = [_resume(r.get("record", {}).get("fields", {})) for r in data.get("records", [])]
    return json.dumps({"total": data.get("total_count"), "annonces": annonces}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
