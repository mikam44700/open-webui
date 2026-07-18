#!/usr/bin/env python3
"""Amorçage du moteur Hermes dans la stack (SPEC-chat-agentique).

Deux sous-commandes idempotentes, appelées par deploy/entrypoint.sh :

  python hermes_boot.py env         # garantit API_SERVER_* dans $HERMES_HOME/.env
  python hermes_boot.py connection  # branche open-webui sur le serveur API Hermes

`env` ne dépend de rien (tourne avant le lancement du gateway Hermes).
`connection` exige que les migrations open-webui aient créé la table `config`
(l'entrypoint boucle dessus, comme pour seed_agents.py).

Le serveur API Hermes est OpenAI-compatible (gateway/platforms/api_server.py) :
il exige API_SERVER_ENABLED=true + API_SERVER_KEY, port par défaut 8642. On le
déclare ensuite comme connexion OpenAI standard d'open-webui — aucun détournement
du pipeline de chat (recette V1 confirmée par l'audit du câblage).
"""

import argparse
import json
import os
import secrets
import sqlite3
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes")))
ENV_PATH = HERMES_HOME / ".env"
DB_PATH = Path(__file__).parent / "data" / "webui.db"
DEFAULT_PORT = 8642


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def ensure_env() -> int:
    """Complète $HERMES_HOME/.env (jamais de réécriture des lignes existantes)."""
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    values = _read_env()
    missing: list[str] = []
    if values.get("API_SERVER_ENABLED", "").lower() != "true":
        if "API_SERVER_ENABLED" in values:
            print("hermes_boot: API_SERVER_ENABLED présent mais pas à true — on respecte le choix existant.")
        else:
            missing.append("API_SERVER_ENABLED=true")
    if not values.get("API_SERVER_KEY"):
        missing.append(f"API_SERVER_KEY={secrets.token_hex(32)}")
    if not values.get("API_SERVER_PORT"):
        missing.append(f"API_SERVER_PORT={DEFAULT_PORT}")
    if missing:
        with ENV_PATH.open("a", encoding="utf-8") as fh:
            fh.write("\n# Serveur API Hermes pour le chat LunarIA (ajouté par hermes_boot.py)\n")
            fh.write("\n".join(missing) + "\n")
        os.chmod(ENV_PATH, 0o600)
        print(f"hermes_boot: .env complété ({', '.join(m.split('=')[0] for m in missing)})")
    else:
        print("hermes_boot: .env déjà complet.")
    return 0


def ensure_connection() -> int:
    """Ajoute la connexion OpenAI-compatible du serveur Hermes dans la config open-webui."""
    values = _read_env()
    key = values.get("API_SERVER_KEY", "")
    port = values.get("API_SERVER_PORT", str(DEFAULT_PORT))
    if not key:
        print("hermes_boot: API_SERVER_KEY absent — lancer d'abord `hermes_boot.py env`.", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}/v1"

    con = sqlite3.connect(DB_PATH)
    try:
        rows = dict(
            con.execute(
                "select key, value from config where key in ('openai.enable','openai.api_base_urls','openai.api_keys')"
            )
        )
        if "openai.api_base_urls" not in rows:
            print("hermes_boot: table config pas encore migrée.", file=sys.stderr)
            return 1
        urls = json.loads(rows["openai.api_base_urls"])
        keys = json.loads(rows.get("openai.api_keys", "[]"))
        while len(keys) < len(urls):
            keys.append("")

        now = int(time.time())
        if url in urls:
            idx = urls.index(url)
            if keys[idx] == key:
                print("hermes_boot: connexion Hermes déjà en place.")
                return 0
            keys[idx] = key  # la clé a tourné (nouveau .env) : on la met à jour
        else:
            urls.append(url)
            keys.append(key)

        for cfg_key, payload in (
            ("openai.enable", json.dumps(True)),
            ("openai.api_base_urls", json.dumps(urls)),
            ("openai.api_keys", json.dumps(keys)),
        ):
            con.execute(
                "insert into config (key, value, updated_at) values (?, ?, ?) "
                "on conflict(key) do update set value=excluded.value, updated_at=excluded.updated_at",
                (cfg_key, payload, now),
            )
        con.commit()
        print(f"hermes_boot: connexion Hermes branchée ({url}).")
        return 0
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["env", "connection"])
    args = parser.parse_args()
    return ensure_env() if args.command == "env" else ensure_connection()


if __name__ == "__main__":
    sys.exit(main())
