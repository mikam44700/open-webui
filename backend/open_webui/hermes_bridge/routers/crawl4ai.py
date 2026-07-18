"""Endpoints d'installation à la demande de Crawl4AI (lecture web approfondie).

  GET  /crawl4ai/status     → { installed, running, active }
  POST /crawl4ai/install    → démarre le conteneur + enregistre le connecteur MCP
  POST /crawl4ai/uninstall  → retire le connecteur MCP + arrête/supprime le conteneur et l'image

Le client déclenche ces endpoints depuis Capacités → Connecteurs MCP → Crawl4AI (bouton « Installer »).
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from .. import crawl4ai_adapter
from ..deps import require_bridge_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_bridge_key)])

# Message générique STABLE renvoyé au front : le détail réel (parfois du stderr Docker
# brut — chemins hôte, noms d'image, versions) ne part JAMAIS au client, sauf en debug
# explicite (AGENTOS_DEBUG=1), pour ne pas fuiter d'infos internes (cf. audit sécurité).
_GENERIC_500 = "Échec du démarrage de Crawl4AI, voir les logs du bridge."


def _debug_enabled() -> bool:
    return os.environ.get("AGENTOS_DEBUG", "").strip().lower() in ("1", "true", "yes")


def _as_http_500(exc: Exception, *, context: str) -> HTTPException:
    """Journalise le détail côté serveur, ne renvoie qu'un message générique au client
    (le détail complet n'est inclus dans la réponse qu'en debug explicite)."""
    logger.exception("crawl4ai: échec de %s", context)
    detail = str(exc) if _debug_enabled() else _GENERIC_500
    return HTTPException(status_code=500, detail=detail)


@router.get("/crawl4ai/status")
def get_crawl4ai_status() -> dict:
    return crawl4ai_adapter.status()


@router.post("/crawl4ai/install")
def post_crawl4ai_install() -> dict:
    try:
        return crawl4ai_adapter.install()
    except Exception as exc:  # noqa: BLE001 — journalisé, message générique au front
        raise _as_http_500(exc, context="l'installation")


@router.post("/crawl4ai/uninstall")
def post_crawl4ai_uninstall() -> dict:
    try:
        return crawl4ai_adapter.uninstall()
    except Exception as exc:  # noqa: BLE001
        raise _as_http_500(exc, context="la désinstallation")


@router.post("/crawl4ai/update/check")
def post_crawl4ai_update_check() -> dict:
    try:
        return crawl4ai_adapter.update_check()
    except Exception as exc:  # noqa: BLE001
        raise _as_http_500(exc, context="la vérification de mise à jour")


@router.post("/crawl4ai/update/start")
def post_crawl4ai_update_start() -> dict:
    try:
        return crawl4ai_adapter.start_update()
    except Exception as exc:  # noqa: BLE001
        raise _as_http_500(exc, context="le démarrage de la mise à jour")


@router.get("/crawl4ai/update/status")
def get_crawl4ai_update_status() -> dict:
    return crawl4ai_adapter.update_status()
