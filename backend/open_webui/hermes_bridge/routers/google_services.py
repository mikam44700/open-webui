"""Services Google additionnels (Chemin A) — Slides, Analytics, Search Console.

Ces services ne sont pas couverts par le script ``google_api.py`` de Hermes ; le bridge
les pilote directement via ``google_direct`` (jeton OAuth Google partagé, Hermes intact).
Garde-fou : Google non connecté → 409 ``google_not_connected``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import google_direct
from ..deps import hermes_unavailable, require_bridge_key
from ..hermes_adapter import HermesUnavailable
from ..schemas import SlidesCreate

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _not_connected() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error": {
                "code": "google_not_connected",
                "message": "Connectez Google dans Intégrations.",
            }
        },
    )


@router.post("/google/slides")
def create_presentation(body: SlidesCreate) -> dict:
    """Crée une présentation Google Slides (titre + plan optionnel). Renvoie l'URL d'édition."""
    try:
        result = google_direct.create_presentation(body.title, body.slides or [])
        return {"presentation": result}
    except google_direct.GoogleNotConnected:
        raise _not_connected()
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid", "message": str(exc)}}
        )
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/google/analytics")
def analytics_summary() -> dict:
    """Résumé Google Analytics (GA4) en lecture seule : métriques clés sur 7 jours."""
    try:
        return {"analytics": google_direct.analytics_summary()}
    except google_direct.GoogleNotConnected:
        raise _not_connected()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/google/search-console")
def search_console_summary() -> dict:
    """Top requêtes Google Search Console (lecture seule, 28 jours)."""
    try:
        return {"search_console": google_direct.search_console_summary()}
    except google_direct.GoogleNotConnected:
        raise _not_connected()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)
