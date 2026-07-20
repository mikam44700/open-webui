#!/usr/bin/env python3
"""Consultation entre collègues — outil commun des agents (SPEC-consultation-collegues).

Permet à un agent de poser UNE question à UN collègue via l'API officielle de
conversation de l'app (clé interne — même modèle que les ponts Notes et Fichiers).
Le collègue consulté travaille avec SES outils et sa réponse revient à l'appelant.

Garde-fous par construction :
- la question part TOUJOURS avec le marqueur [CONSULTATION D'UN COLLÈGUE] : le
  consulté répond directement et ne consulte personne à son tour (profondeur 1) ;
- collègues autorisés uniquement (liste fermée de l'équipe) ;
- délai plafonné : au-delà, échec propre — l'appelant le DIT au patron, il n'invente
  jamais la réponse du collègue.

Usage :
  python3 collegue_cli.py consulter --collegue clara --question "Ton analyse de R2C ?"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_APP_URL = "http://localhost:8080"
TIMEOUT_SECONDS = 150
MARQUEUR = (
    "[CONSULTATION D'UN COLLÈGUE — réponds directement avec tes outils et ton expertise ; "
    "tu ne consultes personne à ton tour sur cette demande ; aucune action de sortie]"
)
EQUIPE = ("luna", "mike", "victor", "lea", "sacha", "theo", "clara")


def _fail(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def cmd_consulter(args: argparse.Namespace) -> None:
    api_key = os.environ.get("LUNARIA_INTERNAL_API_KEY", "").strip()
    base_url = os.environ.get("LUNARIA_APP_URL", DEFAULT_APP_URL).rstrip("/")
    if not api_key:
        _fail("Clé interne absente (LUNARIA_INTERNAL_API_KEY) : consultation indisponible.")
    collegue = args.collegue.strip().lower()
    if collegue not in EQUIPE:
        _fail(f"Collègue inconnu « {args.collegue} » — équipe : {', '.join(EQUIPE)}.")
    question = args.question.strip()
    if not question:
        _fail("La question est vide.")
    payload = {
        "model": collegue,
        "stream": False,
        "messages": [{"role": "user", "content": f"{MARQUEUR}\n\n{question}"}],
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat/completions", data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _fail(f"Le collègue n'a pas pu être consulté ({exc.code}). Dis-le au patron, n'invente pas sa réponse.")
    except Exception as exc:  # noqa: BLE001 — timeout ou réseau : échec propre et honnête
        _fail(f"Consultation échouée ({exc}). Dis-le au patron, n'invente pas la réponse du collègue.")
    contenu = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    if not contenu:
        _fail("Réponse vide du collègue. Dis-le au patron, n'invente pas sa réponse.")
    nom = collegue.capitalize()
    print(f"=== Réponse de {nom} (à citer comme telle : « selon {nom}… ») ===")
    print(contenu)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="collegue_cli", description="Consultation entre collègues LunarIA.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("consulter", help="Pose une question à un collègue de l'équipe.")
    p.add_argument("--collegue", required=True, help=f"Un de : {', '.join(EQUIPE)}")
    p.add_argument("--question", required=True, help="La question, précise et autonome.")
    p.set_defaults(func=cmd_consulter)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
