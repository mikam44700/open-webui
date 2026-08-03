#!/usr/bin/env python3
"""Verifie que l'API de Composio repond encore comme LunarIA l'attend.

Composio change son API sans prevenir. Le 3 aout 2026, la creation d'un compte
connecte est passee d'un corps plat a un corps imbriquee : la connexion d'une
application echouait chez le client, et personne ne l'a su avant qu'il essaie.

Ce script rejoue chaque appel que fait `routers/composio.py` et verifie que la
reponse a toujours la forme attendue. Il sort en code 1 des qu'un controle
echoue, pour qu'une tache planifiee puisse alerter.

Lecture seule : rien n'est cree, rien n'est supprime. Le POST de creation de
compte n'est donc pas rejoue — sa forme est verifiee statiquement plus bas.

    docker exec open-webui python3 /app/backend/../scripts/verifier-composio.py

Ou, depuis le depot, avec la cle en variable d'environnement :

    COMPOSIO_API_KEY=... python3 scripts/verifier-composio.py
"""

import asyncio
import json
import os
import sqlite3
import sys

import aiohttp

V3 = "https://backend.composio.dev/api/v3"
V31 = "https://backend.composio.dev/api/v3.1"

BASE_WEBUI = "/app/backend/data/webui.db"
CLE_CONFIG = "lunaria.composio_api_key"

# Chaque entree : libelle, methode, base, chemin, corps, champ attendu.
# `champ` a None signifie qu'on attend un 404 : la route existe, l'objet non.
CONTROLES = [
    ("catalogue d'applications", "GET", V3, "/toolkits", None, "items"),
    ("comptes connectes", "GET", V31, "/connected_accounts?user_ids=verif", None, "items"),
    ("configs d'authentification", "GET", V3, "/auth_configs?toolkit_slug=gmail", None, "items"),
    ("detail d'un compte", "GET", V31, "/connected_accounts/ca_inexistant", None, None),
    ("session MCP du moteur", "POST", V31, "/tool_router/session", {"user_id": "verif"}, "mcp"),
]


def lire_cle() -> str:
    """La cle vient de l'environnement, sinon de la base de l'installation."""
    depuis_env = os.environ.get("COMPOSIO_API_KEY", "").strip()
    if depuis_env:
        return depuis_env
    if not os.path.exists(BASE_WEBUI):
        return ""
    con = sqlite3.connect(BASE_WEBUI)
    try:
        for (nom, valeur) in con.execute("select key, value from config"):
            if "composio" not in str(nom).lower():
                continue
            brut = str(valeur or "").strip()
            try:
                charge = json.loads(brut)
                if isinstance(charge, str) and charge:
                    return charge
            except Exception:
                if brut:
                    return brut
    finally:
        con.close()
    return ""


async def verifier(cle: str) -> tuple[int, int]:
    """Rend (nombre d'echecs, nombre de refus d'authentification).

    Distinguer les deux importe : une cle refusee est une erreur de
    configuration, un format qui change est une panne a corriger dans le code.
    """
    entetes = {"x-api-key": cle, "Content-Type": "application/json"}
    echecs = 0
    refuses = 0
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for libelle, methode, base, chemin, corps, champ in CONTROLES:
            try:
                async with session.request(
                    methode, f"{base}{chemin}", headers=entetes, json=corps
                ) as reponse:
                    charge = await reponse.json(content_type=None)
                    statut = reponse.status
            except Exception as exc:
                print(f"  INJOIGNABLE  {libelle:28} {exc}")
                echecs += 1
                continue

            statut_ok = statut < 400 or (champ is None and statut == 404)
            forme_ok = True
            if champ and statut < 400:
                forme_ok = isinstance(charge, dict) and champ in charge

            if statut_ok and forme_ok:
                print(f"  OK           {libelle:28} {statut}")
                continue

            echecs += 1
            if statut in (401, 403):
                refuses += 1
            motif = f"statut {statut}"
            if champ and statut < 400 and not forme_ok:
                motif = f"champ « {champ} » absent de la reponse"
            print(f"  ECHEC        {libelle:28} {motif}")
            print(f"               {json.dumps(charge)[:200]}")
    return echecs, refuses


def main() -> int:
    cle = lire_cle()
    if not cle:
        print("Aucune cle Composio trouvee (ni COMPOSIO_API_KEY, ni en base).")
        return 1

    print("Verification de l'API Composio\n")
    echecs, refuses = asyncio.run(verifier(cle))

    print()
    if refuses == echecs and echecs:
        print("Cle Composio refusee. Ce n'est pas une panne de l'API :")
        print("verifier la cle du projet de ce client dans son tableau de bord.")
        return 1
    if echecs:
        print(f"{echecs} controle(s) en echec — l'API de Composio a change.")
        print("Comparer avec backend/open_webui/routers/composio.py avant de deployer.")
        return 1
    print("Tous les controles passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
