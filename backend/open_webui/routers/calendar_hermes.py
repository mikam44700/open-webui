"""Router /api/v1/calendar — Calendrier piloté par Hermes (feature 014).

Admin-only. Proxifie vers le Providers Bridge (``/calendar/*``), qui pilote Google Agenda
via le script déterministe de la skill google-workspace de Hermes. Source de vérité = Google.

Le router natif ``calendar.py`` (base locale, monté sous /api/v1/calendars) reste intact ;
la page front utilise désormais ce proxy.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def calendar_status(user=Depends(get_admin_user)):
    """Statut honnête : Google Agenda connecté ou non."""
    return await _bridge("GET", "/calendar/status")


@router.get("/events")
async def list_events(start: str | None = None, end: str | None = None, user=Depends(get_admin_user)):
    """Liste les événements réels de Google Agenda."""
    params = {k: v for k, v in {"start": start, "end": end}.items() if v}
    query = f"?{urlencode(params)}" if params else ""
    return await _bridge("GET", f"/calendar/events{query}")


@router.post("/events")
async def create_event(body: dict, user=Depends(get_admin_user)):
    """Crée un événement dans Google Agenda."""
    return await _bridge("POST", "/calendar/events", json=body)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, user=Depends(get_admin_user)):
    """Supprime un événement (confirmation côté UI)."""
    return await _bridge("DELETE", f"/calendar/events/{event_id}")
