#!/usr/bin/env python3
"""Pont Notes LunarIA — outil en ligne de commande pour les agents.

Permet à un agent d'agir sur les Notes de l'application via son API officielle
(jamais d'accès direct à la base). L'authentification passe par une clé API interne
lue dans l'environnement (LUNARIA_INTERNAL_API_KEY) — jamais écrite en dur.

Commandes :
  list                      liste les notes (titre + identifiant)
  read   --id <id>          affiche le contenu d'une note
  create --title <t> [--content <md> | --content-file <path>]
                            crée une note et renvoie son identifiant
  update --id <id> [--content <md> | --content-file <path>]
                            met à jour le CONTENU d'une note — garde-fou par
                            construction : seulement les notes de travail des agents
                            (titre commençant par « Pipeline prospection »), jamais
                            les notes personnelles du patron
  delete --id <id>          BLOQUÉ par défaut (garde-fou) : exige une validation
                            humaine explicite via --confirm-human

Sortie : texte simple sur stdout, code de sortie 0 si succès, 1 sinon.
Dépendances : bibliothèque standard uniquement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_APP_URL = "http://localhost:8080"
TIMEOUT_SECONDS = 30


def _config() -> tuple[str, str]:
    """Renvoie (base_url, api_key) ou termine proprement si la clé manque."""
    api_key = os.environ.get("LUNARIA_INTERNAL_API_KEY", "").strip()
    base_url = os.environ.get("LUNARIA_APP_URL", DEFAULT_APP_URL).rstrip("/")
    if not api_key:
        _fail(
            "Clé d'accès interne absente (LUNARIA_INTERNAL_API_KEY). "
            "Le pont Notes n'est pas configuré sur cet environnement."
        )
    return base_url, api_key


def _request(method: str, path: str, api_key: str, base_url: str, payload: dict | None = None) -> object:
    url = f"{base_url}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        _fail(f"L'application a refusé la requête ({exc.code}). {detail}")
    except urllib.error.URLError as exc:
        _fail(f"Application injoignable ({exc.reason}). La stack est-elle démarrée ?")
    return None


def _fail(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    notes = _request("GET", "/api/v1/notes/", api_key, base_url) or []
    if not notes:
        print("Aucune note dans l'espace du patron.")
        return
    print(f"{len(notes)} note(s) :")
    for note in notes:
        print(f"- [{note.get('id')}] {note.get('title', '(sans titre)')}")


def cmd_read(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    note = _request("GET", f"/api/v1/notes/{args.id}", api_key, base_url)
    if not note:
        _fail("Note introuvable.")
    print(f"# {note.get('title', '(sans titre)')}\n")
    content = (note.get("data") or {}).get("content") or {}
    print(content.get("md") or "(note vide)")


def cmd_create(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    if args.content_file:
        try:
            with open(args.content_file, encoding="utf-8") as handle:
                md = handle.read()
        except OSError as exc:
            _fail(f"Fichier de contenu illisible : {exc}")
    elif args.content is not None:
        md = args.content
    else:
        md = sys.stdin.read()
    if not args.title.strip():
        _fail("Le titre est obligatoire.")
    payload = {"title": args.title, "data": {"content": {"json": None, "html": None, "md": md}}}
    note = _request("POST", "/api/v1/notes/create", api_key, base_url, payload)
    if not note or not note.get("id"):
        _fail("La note n'a pas pu être créée.")
    print(f"Note créée : [{note['id']}] {note.get('title')}")


# Titres de notes que les agents ont le droit de MODIFIER (leurs notes de travail).
# Tout le reste (les notes personnelles du patron) est immodifiable par construction :
# écraser le contenu d'une note revient à effacer l'ancien — même famille de risque que
# delete, donc même philosophie (limité à la source, pas juste interdit par consigne).
_UPDATABLE_TITLE_PREFIXES = ("Pipeline prospection",)


def cmd_update(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    note = _request("GET", f"/api/v1/notes/{args.id}", api_key, base_url)
    if not note:
        _fail("Note introuvable.")
    title = str(note.get("title") or "")
    if not title.startswith(_UPDATABLE_TITLE_PREFIXES):
        _fail(
            "Mise à jour REFUSÉE : cette note n'est pas une note de travail d'agent "
            f"(titres autorisés : {', '.join(_UPDATABLE_TITLE_PREFIXES)}…). Les notes du "
            "patron ne se modifient pas — crée une nouvelle note ou demande-lui."
        )
    if args.content_file:
        try:
            with open(args.content_file, encoding="utf-8") as handle:
                md = handle.read()
        except OSError as exc:
            _fail(f"Fichier de contenu illisible : {exc}")
    elif args.content is not None:
        md = args.content
    else:
        md = sys.stdin.read()
    payload = {"title": title, "data": {"content": {"json": None, "html": None, "md": md}}}
    updated = _request("POST", f"/api/v1/notes/{args.id}/update", api_key, base_url, payload)
    if not updated or not updated.get("id"):
        _fail("La note n'a pas pu être mise à jour.")
    print(f"Note mise à jour : [{updated['id']}] {title}")


def cmd_delete(args: argparse.Namespace) -> None:
    # Garde-fou (SPEC critère 3) : une suppression ne part JAMAIS sans validation humaine.
    if not args.confirm_human:
        _fail(
            "Suppression BLOQUÉE. Effacer une note est une action irréversible qui exige "
            "la validation explicite du patron. Ne relance avec --confirm-human que si le "
            "patron a dit oui, en toutes lettres, pour cette note précise."
        )
    base_url, api_key = _config()
    _request("DELETE", f"/api/v1/notes/{args.id}/delete", api_key, base_url)
    print(f"Note supprimée : {args.id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notes_cli", description="Pont Notes LunarIA pour les agents.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Liste les notes.").set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="Affiche une note.")
    p_read.add_argument("--id", required=True)
    p_read.set_defaults(func=cmd_read)

    p_create = sub.add_parser("create", help="Crée une note.")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--content", help="Contenu markdown en argument.")
    p_create.add_argument("--content-file", help="Chemin d'un fichier markdown.")
    p_create.set_defaults(func=cmd_create)

    p_update = sub.add_parser("update", help="Met à jour une note de travail d'agent (garde-fou).")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--content", help="Nouveau contenu markdown en argument.")
    p_update.add_argument("--content-file", help="Chemin d'un fichier markdown.")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="Supprime une note (garde-fou).")
    p_delete.add_argument("--id", required=True)
    p_delete.add_argument("--confirm-human", action="store_true", help="Validation humaine explicite.")
    p_delete.set_defaults(func=cmd_delete)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
