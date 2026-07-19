#!/usr/bin/env python3
"""Seed de la clé d'accès interne LunarIA (pont agents → API de l'app).

Idempotent, sûr à relancer. Au démarrage de la stack :
  1. Active le système de clés API de l'application (auth.enable_api_keys).
  2. Enregistre la clé interne (fournie par l'environnement LUNARIA_INTERNAL_API_KEY)
     comme clé du patron (premier compte admin), pour que les agents puissent appeler
     l'API officielle des Notes en son nom.

La clé n'est JAMAIS écrite en dur ni journalisée : elle vient de l'environnement
(généré par up.sh dans deploy/.env, hors versionnement). Ce script ne l'affiche pas.

Le compte admin n'existe qu'après que le patron a créé son compte au premier login :
ce script est donc conçu pour être relancé en boucle par l'entrypoint jusqu'à ce
qu'un admin soit présent. Il renvoie le code 0 uniquement une fois la clé en place.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time

DB_PATH = os.environ.get("LUNARIA_DB_PATH", "/app/backend/data/webui.db")
KEY_ID = "lunaria-internal"


def main() -> int:
    api_key = os.environ.get("LUNARIA_INTERNAL_API_KEY", "").strip()
    if not api_key:
        print("seed_api_key: LUNARIA_INTERNAL_API_KEY absent — pont Notes non configuré.", file=sys.stderr)
        return 1

    if not os.path.exists(DB_PATH):
        return 1

    try:
        con = sqlite3.connect(DB_PATH)
    except sqlite3.Error:
        return 1

    try:
        # Les tables doivent exister (migrations open-webui appliquées).
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"config", "api_key", "user"}.issubset(tables):
            return 1

        # Le patron (premier compte admin) doit exister.
        admin = con.execute("SELECT id FROM user WHERE role='admin' ORDER BY created_at LIMIT 1").fetchone()
        if not admin:
            return 1
        admin_id = admin[0]

        now = int(time.time())

        # 1. Activer le système de clés API (idempotent).
        con.execute(
            "UPDATE config SET value='true', updated_at=? WHERE key='auth.enable_api_keys'",
            (now,),
        )

        # 2. Enregistrer / mettre à jour la clé interne du patron (idempotent).
        existing = con.execute("SELECT key, user_id FROM api_key WHERE id=?", (KEY_ID,)).fetchone()
        if existing is None:
            con.execute(
                "INSERT INTO api_key (id, user_id, key, created_at, updated_at) VALUES (?,?,?,?,?)",
                (KEY_ID, admin_id, api_key, now, now),
            )
        elif existing[0] != api_key or existing[1] != admin_id:
            con.execute(
                "UPDATE api_key SET user_id=?, key=?, updated_at=? WHERE id=?",
                (admin_id, api_key, now, KEY_ID),
            )
        con.commit()
        print("seed_api_key: clé interne du pont Notes en place, clés API activées.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
