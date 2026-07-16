"""Router /api/v1/calendar — Calendrier piloté par Hermes (feature 014, multi-source).

Admin-only. Proxifie vers le Providers Bridge (``/calendar/*``), qui pilote la source
choisie par le client : Google Agenda (skill google-workspace), Outlook (Microsoft Graph)
ou Calendly (RDV, lecture seule). La page s'adapte à ce que le client a connecté.

Le router natif ``calendar.py`` (base locale, monté sous /api/v1/calendars) reste intact ;
la page front utilise ce proxy.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge, _bridge_segment
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def calendar_status(user=Depends(get_admin_user)):
    """Statut honnête agrégé : sources connectées + source par défaut."""
    return await _bridge("GET", "/calendar/status")


@router.get("/sources")
async def calendar_sources(user=Depends(get_admin_user)):
    """Détail des sources de calendrier (id, libellé, écriture possible, connecté)."""
    return await _bridge("GET", "/calendar/sources")


@router.get("/events")
async def list_events(
    source: str | None = None,
    start: str | None = None,
    end: str | None = None,
    tz: str = "UTC",
    user=Depends(get_admin_user),
):
    """Liste les événements réels de la source demandée (ou la 1re connectée)."""
    params = {k: v for k, v in {"source": source, "start": start, "end": end, "tz": tz}.items() if v}
    query = f"?{urlencode(params)}" if params else ""
    return await _bridge("GET", f"/calendar/events{query}")


@router.post("/events")
async def create_event(body: dict, user=Depends(get_admin_user)):
    """Crée un événement (Google ou Outlook ; Calendly est en lecture seule)."""
    return await _bridge("POST", "/calendar/events", json=body)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, source: str | None = None, user=Depends(get_admin_user)):
    """Supprime un événement (confirmation côté UI)."""
    event_id = _bridge_segment(event_id)
    query = f"?{urlencode({'source': source})}" if source else ""
    return await _bridge("DELETE", f"/calendar/events/{event_id}{query}")
