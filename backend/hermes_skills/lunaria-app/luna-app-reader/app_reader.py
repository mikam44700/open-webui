#!/usr/bin/env python3
"""GPS de l'application LunarIA — outil de LECTURE pour Luna (l'orchestratrice).

Donne à Luna les yeux sur toute l'application : elle lit l'état réel de n'importe
quelle page via l'API officielle (jamais la base). LECTURE SEULE — aucune commande
ici ne modifie quoi que ce soit (uniquement des requêtes GET).

L'authentification passe par le badge interne (LUNARIA_INTERNAL_API_KEY), le même
que le pont Notes — jamais écrit en dur.

Commandes :
  pages                  liste les pages lisibles (nom → à quoi ça correspond)
  overview               panorama de l'app (les pages clés d'un coup)
  page <nom>             état réel d'une page précise (voir `pages`)
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

# Chaque page → (chemin de lecture GET, libellé lisible). LECTURE SEULE.
VIEWS: dict[str, tuple[str, str]] = {
    "agents": ("/api/v1/models/export", "Équipe d'agents"),
    "fournisseurs": ("/api/v1/providers/active", "Fournisseurs IA actifs"),
    "outils": ("/api/v1/tools/", "Outils"),
    "integrations": ("/api/v1/configs/connections", "Intégrations (connexions)"),
    "mcp": ("/api/v1/configs/tool_servers", "Serveurs MCP / outils externes"),
    "connaissances": ("/api/v1/knowledge/", "Bases de connaissances"),
    "prompts": ("/api/v1/prompts/", "Prompts"),
    "automatisations": ("/api/v1/automations/list", "Automatisations"),
    "messagerie": ("/api/v1/channels/", "Canaux de messagerie"),
    "calendrier": ("/api/v1/calendar/events", "Événements du calendrier"),
    "notes": ("/api/v1/notes/", "Notes"),
    "memoire": ("/api/v1/memories/", "Mémoire d'entreprise"),
    "fonctions": ("/api/v1/functions/", "Fonctions"),
    "utilisateurs": ("/api/v1/users/", "Utilisateurs"),
    "moteur": ("/api/v1/hermes/status", "Moteur Hermes"),
}

# Panorama : le sous-ensemble le plus parlant pour un « état de l'app » d'un coup.
OVERVIEW_KEYS = ["agents", "fournisseurs", "integrations", "mcp", "outils", "automatisations", "connaissances", "notes"]


def _config() -> tuple[str, str]:
    api_key = os.environ.get("LUNARIA_INTERNAL_API_KEY", "").strip()
    base_url = os.environ.get("LUNARIA_APP_URL", DEFAULT_APP_URL).rstrip("/")
    if not api_key:
        _fail("Badge d'accès interne absent (LUNARIA_INTERNAL_API_KEY). Le GPS n'est pas configuré ici.")
    return base_url, api_key


def _get(path: str, api_key: str, base_url: str):
    req = urllib.request.Request(f"{base_url}{path}", method="GET")
    req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return True, None
            try:
                return True, json.loads(body)
            except json.JSONDecodeError:
                return False, "format inattendu (page non exposée en lecture directe)"
    except urllib.error.HTTPError as exc:
        return False, f"non lisible ({exc.code})"
    except urllib.error.URLError as exc:
        return False, f"application injoignable ({exc.reason})"


def _fail(message: str) -> None:
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def _summarize(data) -> str:
    """Résumé lisible d'une réponse JSON quelconque (liste ou objet)."""
    if data is None:
        return "vide"
    if isinstance(data, list):
        if not data:
            return "aucun élément"
        names = []
        for item in data[:12]:
            if isinstance(item, dict):
                names.append(str(item.get("name") or item.get("title") or item.get("id") or "?"))
            else:
                names.append(str(item))
        suffix = "" if len(data) <= 12 else f" (+{len(data) - 12} autres)"
        return f"{len(data)} élément(s) : " + ", ".join(names) + suffix
    if isinstance(data, dict):
        # Objet d'état (ex. statut moteur) : on montre les paires clés/valeurs simples.
        pairs = [f"{k}={v}" for k, v in data.items() if isinstance(v, (str, int, float, bool))][:10]
        if pairs:
            return "; ".join(pairs)
        return f"objet ({', '.join(list(data.keys())[:8])})"
    return str(data)


def cmd_pages(args: argparse.Namespace) -> None:
    print("Pages lisibles par Luna :")
    for name, (_, label) in VIEWS.items():
        print(f"- {name} : {label}")


def cmd_page(args: argparse.Namespace) -> None:
    view = VIEWS.get(args.nom)
    if not view:
        _fail(f"Page inconnue : {args.nom}. Fais `pages` pour la liste.")
    base_url, api_key = _config()
    path, label = view
    ok, data = _get(path, api_key, base_url)
    if not ok:
        print(f"{label} : {data}")
        return
    print(f"{label} : {_summarize(data)}")


def cmd_taches(args: argparse.Namespace) -> None:
    """Le tableau de bord du travail, colonne par colonne (SPEC-luna-tableau-taches)."""
    base_url, api_key = _config()
    ok, data = _get("/api/v1/kanban/board", api_key, base_url)
    if not ok or not isinstance(data, dict):
        print(f"Tableau des tâches : {data if not ok else 'indisponible'}")
        return

    taches = data.get("taches") or []
    print(f"Tableau de bord du travail — {data.get('total', len(taches))} tâche(s) :")
    for colonne in data.get("colonnes") or []:
        dedans = [t for t in taches if t.get("colonne") == colonne.get("cle")]
        print(f"\n[{colonne.get('titre')}] {len(dedans)} tâche(s)")
        for t in dedans:
            marques = []
            if t.get("priorite"):
                marques.append({"urgent": "URGENT", "eleve": "priorité élevée", "bas": "priorité basse"}.get(t["priorite"], t["priorite"]))
            if t.get("bloquee"):
                marques.append("décision attendue")
            if t.get("agent"):
                marques.append(f"confiée à {t['agent']}")
            suffixe = f"  ({', '.join(marques)})" if marques else ""
            print(f"  - {t.get('titre')} [{t.get('id')}]{suffixe}")


def cmd_tache(args: argparse.Namespace) -> None:
    """Détail d'une tâche : ce qui s'est réellement passé dessus."""
    base_url, api_key = _config()
    ok, data = _get(f"/api/v1/kanban/tasks/{urllib.parse.quote(args.id)}", api_key, base_url)
    if not ok or not isinstance(data, dict):
        print(f"Tâche {args.id} : {data if not ok else 'introuvable'}")
        return

    t = data.get("tache") or {}
    print(f"Tâche : {t.get('titre')} [{t.get('id')}]")
    print(f"Colonne : {t.get('colonne')}")
    if t.get("priorite"):
        print(f"Priorité : {t['priorite']}")
    if t.get("agent"):
        print(f"Confiée à : {t['agent']}")
    if t.get("description"):
        print(f"Description : {t['description']}")
    if data.get("dernier_resume"):
        print(f"Dernier point : {data['dernier_resume']}")
    if data.get("resultat"):
        print(f"Résultat : {data['resultat']}")
    executions = data.get("executions") or []
    if executions:
        print("Passages d'agents :")
        for ex in executions:
            ligne = f"  - {ex.get('agent') or 'agent non identifié'}"
            if ex.get("issue"):
                ligne += f" : {ex['issue']}"
            if ex.get("erreur"):
                ligne += f" (erreur : {ex['erreur']})"
            print(ligne)

    commentaires = data.get("commentaires") or []
    if commentaires:
        print("Commentaires :")
        for c in commentaires:
            print(f"  - {c.get('auteur') or 'anonyme'} : {c.get('texte')}")

    etapes = [e.get("libelle") for e in (data.get("historique") or [])]
    if etapes:
        print("Historique : " + " → ".join(etapes))


def cmd_overview(args: argparse.Namespace) -> None:
    base_url, api_key = _config()
    print("État de l'application LunarIA :")
    for name in OVERVIEW_KEYS:
        path, label = VIEWS[name]
        ok, data = _get(path, api_key, base_url)
        print(f"- {label} : {_summarize(data) if ok else data}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app_reader", description="GPS de LunarIA (lecture seule) pour Luna.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pages", help="Liste les pages lisibles.").set_defaults(func=cmd_pages)
    sub.add_parser("overview", help="Panorama de l'app.").set_defaults(func=cmd_overview)
    p_page = sub.add_parser("page", help="État d'une page précise.")
    p_page.add_argument("nom", help="Nom de la page (voir `pages`).")
    p_page.set_defaults(func=cmd_page)

    # Tableau de bord du travail (SPEC-luna-tableau-taches) : affichage dédié, car un
    # résumé générique ne rendrait pas les colonnes lisibles.
    sub.add_parser("taches", help="Le tableau des tâches, colonne par colonne.").set_defaults(
        func=cmd_taches
    )
    p_tache = sub.add_parser("tache", help="Détail d'une tâche (historique, passages d'agents).")
    p_tache.add_argument("--id", required=True)
    p_tache.set_defaults(func=cmd_tache)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
