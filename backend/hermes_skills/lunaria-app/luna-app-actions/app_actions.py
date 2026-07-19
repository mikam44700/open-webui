#!/usr/bin/env python3
"""Actions sûres sur l'application LunarIA — outil d'ACTION pour Luna.

Ne contient QUE des actions sûres et réversibles. Aucune suppression, aucun
écrasement destructif : ces opérations n'existent pas dans cet outil (palier
ultérieur). Toute action passe par l'API officielle (jamais la base), badge
interne (LUNARIA_INTERNAL_API_KEY) — jamais écrit en dur.

RÈGLE D'USAGE (portée par Luna) : Luna n'appelle cet outil qu'APRÈS que le patron
a validé l'action en toutes lettres. L'outil exécute ce qu'on lui demande ; c'est
Luna qui garantit la validation humaine en amont.

Commandes (toutes réversibles) :
  toggle-agent       --id <id>                 active / désactive un agent
  set-model          --provider <p> --model <m> change le modèle IA actif
  toggle-automation  --id <id>                 active / désactive une automatisation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_APP_URL = "http://localhost:8080"
TIMEOUT_SECONDS = 30


def _config() -> tuple[str, str]:
    api_key = os.environ.get("LUNARIA_INTERNAL_API_KEY", "").strip()
    base_url = os.environ.get("LUNARIA_APP_URL", DEFAULT_APP_URL).rstrip("/")
    if not api_key:
        _fail("Badge d'accès interne absent (LUNARIA_INTERNAL_API_KEY). Les actions ne sont pas configurées ici.")
    return base_url, api_key


def _post(path: str, api_key: str, base_url: str, payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{base_url}{path}", data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        _fail(f"L'application a refusé l'action ({exc.code}). {detail}")
    except urllib.error.URLError as exc:
        _fail(f"Application injoignable ({exc.reason}). La stack est-elle démarrée ?")
    return None


def _fail(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def cmd_toggle_agent(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    query = urllib.parse.urlencode({"id": args.id})
    result = _post(f"/api/v1/models/model/toggle?{query}", api_key, base_url)
    if not result:
        _fail(f"Agent introuvable : {args.id}")
    state = "activé" if result.get("is_active") else "désactivé"
    print(f"Agent {result.get('name', args.id)} : {state}.")


def cmd_set_model(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    payload = {"provider_id": args.provider, "model_id": args.model}
    result = _post("/api/v1/providers/active", api_key, base_url, payload)
    if not result:
        _fail("Le modèle actif n'a pas pu être changé.")
    print(f"Modèle IA actif : {result.get('provider_id')} / {result.get('model_id')} (pour les nouvelles conversations).")


def cmd_toggle_automation(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    result = _post(f"/api/v1/automations/{urllib.parse.quote(args.id)}/toggle", api_key, base_url)
    if not result:
        _fail(f"Automatisation introuvable : {args.id}")
    state = "activée" if result.get("enabled", result.get("is_active")) else "désactivée"
    print(f"Automatisation {result.get('name', args.id)} : {state}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app_actions", description="Actions sûres sur LunarIA (pour Luna).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_agent = sub.add_parser("toggle-agent", help="Active / désactive un agent.")
    p_agent.add_argument("--id", required=True)
    p_agent.set_defaults(func=cmd_toggle_agent)

    p_model = sub.add_parser("set-model", help="Change le modèle IA actif.")
    p_model.add_argument("--provider", required=True)
    p_model.add_argument("--model", required=True)
    p_model.set_defaults(func=cmd_set_model)

    p_auto = sub.add_parser("toggle-automation", help="Active / désactive une automatisation.")
    p_auto.add_argument("--id", required=True)
    p_auto.set_defaults(func=cmd_toggle_automation)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
