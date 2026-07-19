#!/usr/bin/env python3
"""Moteur de prospection LunarIA — outil de Léa (l'agent prospection).

Deux commandes déterministes, sur des sources publiques officielles (RGPD-clean) :

  search  : trouve des entreprises réelles via l'API officielle recherche-entreprises
            (données SIRENE/INSEE/INPI/BODACC). Filtres : activité, département,
            effectif, nombre d'établissements. Renvoie une liste structurée.

  enrich  : pour une entreprise, trouve son site web (recherche) puis en extrait
            les coordonnées publiques (email, téléphone) via Crawl4AI.

Le SCORING (chaud/tiède/froid + raison) N'EST PAS dans cet outil : c'est le jugement
de Léa, à partir des données renvoyées ici. L'outil fournit les faits, Léa décide.

Dépendances : bibliothèque standard + ddgs (déjà présent dans la stack).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

RECHERCHE_API = "https://recherche-entreprises.api.gouv.fr/search"
TIMEOUT = 25


def _fail(msg: str) -> None:
    print(f"ERREUR : {msg}", file=sys.stderr)
    sys.exit(1)


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── search : sourcing via l'API officielle ───────────────────────────────────


def cmd_search(args: argparse.Namespace) -> None:
    params = {"page": 1, "per_page": min(args.limit * 2 if args.etabs_min else args.limit, 25)}
    if args.naf:
        params["activite_principale"] = args.naf
    if args.q:
        params["q"] = args.q
    if args.departement:
        params["departement"] = args.departement
    if args.effectif:
        params["tranche_effectif_salarie"] = args.effectif
    url = f"{RECHERCHE_API}?{urllib.parse.urlencode(params)}"
    try:
        data = _get_json(url)
    except Exception as exc:  # noqa: BLE001 - source externe, message clair pour Léa
        _fail(f"Source entreprises injoignable : {exc}")

    results = data.get("results", [])
    # Filtre local : nombre minimum d'établissements (multi-sites), si demandé.
    if args.etabs_min:
        results = [e for e in results if (e.get("nombre_etablissements_ouverts") or 0) >= args.etabs_min]
    results = results[: args.limit]

    if not results:
        print("Aucune entreprise ne correspond à ces critères.")
        return

    print(f"{len(results)} entreprise(s) trouvée(s) (source officielle) :")
    for e in results:
        s = e.get("siege", {})
        dirs = [d.get("nom_complet") or d.get("denomination") for d in e.get("dirigeants", [])]
        dirs = [d for d in dirs if d]
        print(json.dumps({
            "nom": e.get("nom_complet"),
            "ville": s.get("libelle_commune"),
            "activite": e.get("activite_principale"),
            "etablissements_ouverts": e.get("nombre_etablissements_ouverts"),
            "tranche_effectif": e.get("tranche_effectif_salarie"),
            "date_creation": e.get("date_creation"),
            "dirigeant": dirs[0] if dirs else None,
        }, ensure_ascii=False))


# ── enrich : site web + coordonnées publiques ────────────────────────────────


def _find_website(query: str) -> str | None:
    try:
        from ddgs import DDGS
    except Exception:  # noqa: BLE001
        return None
    try:
        for r in DDGS().text(query, max_results=5):
            href = r.get("href", "")
            # on écarte les annuaires génériques, on cherche un vrai site d'entreprise
            if href and not re.search(
                r"societe\.com|pappers|linkedin|facebook|instagram|tripadvisor|annuaire|infogreffe"
                r"|tourisme|mairie|wikipedia|youtube|yelp|petitfute|thefork|ubereats|deliveroo",
                href,
            ):
                return href
    except Exception:  # noqa: BLE001
        return None
    return None


def _crawl_contacts(url: str) -> dict:
    base = os.environ.get("CRAWL4AI_BASE_URL", "http://crawl4ai:11235").rstrip("/")
    token = os.environ.get("CRAWL4AI_API_TOKEN", "")
    payload = json.dumps({"urls": [url]}).encode("utf-8")
    req = urllib.request.Request(f"{base}/crawl", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    res = (data.get("results") or [data])[0]
    md = res.get("markdown") or {}
    text = md.get("raw_markdown", "") if isinstance(md, dict) else str(md)
    emails = sorted(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)))
    tels = sorted(set(re.findall(r"0[1-9](?:[ .]?[0-9]{2}){4}", text)))
    return {"emails": emails[:3], "telephones": tels[:3]}


def cmd_enrich(args: argparse.Namespace) -> None:
    query = args.nom + (f" {args.ville}" if args.ville else "")
    site = _find_website(query)
    out = {"nom": args.nom, "site": site, "emails": [], "telephones": []}
    if site:
        contacts = _crawl_contacts(site)
        out["emails"] = contacts.get("emails", [])
        out["telephones"] = contacts.get("telephones", [])
        # beaucoup de coordonnées sont sur la page contact : deuxième essai ciblé
        if not out["emails"] and not out["telephones"]:
            for suffix in ("contact", "nous-contacter", "contact.html"):
                extra = _crawl_contacts(site.rstrip("/") + "/" + suffix)
                if extra.get("emails") or extra.get("telephones"):
                    out["emails"] = extra.get("emails", [])
                    out["telephones"] = extra.get("telephones", [])
                    break
    print(json.dumps(out, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prospection_cli", description="Moteur de prospection LunarIA (Léa).")
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("search", help="Trouve des entreprises via la source officielle.")
    ps.add_argument("--naf", help="Code activité NAF (ex. 56.10C pour restauration rapide).")
    ps.add_argument("--q", help="Recherche texte libre (nom, mots-clés).")
    ps.add_argument("--departement", help="Numéro de département (ex. 34).")
    ps.add_argument("--effectif", help="Tranche d'effectif salarié (code, ex. 12 / 21).")
    ps.add_argument("--etabs-min", type=int, default=0, help="Nombre minimum d'établissements ouverts.")
    ps.add_argument("--limit", type=int, default=10, help="Nombre de résultats (max 25).")
    ps.set_defaults(func=cmd_search)

    pe = sub.add_parser("enrich", help="Trouve site + coordonnées publiques d'une entreprise.")
    pe.add_argument("--nom", required=True)
    pe.add_argument("--ville")
    pe.set_defaults(func=cmd_enrich)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
