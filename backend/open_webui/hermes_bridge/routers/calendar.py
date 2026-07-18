"""Calendrier (feature 014, étendu multi-source) — Google Agenda / Outlook / Calendly.

Page « Calendrier » d'Agent OS : le dirigeant voit (et crée/supprime pour Google & Outlook)
ses événements. La page s'adapte à la ou les source(s) que le client a connectée(s) dans
Intégrations ; Calendly est en lecture seule (outil de prise de RDV).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import calendar_adapter
from ..calendar_adapter import CalendarNotConnected, ReadOnlySource
from ..deps import hermes_unavailable, require_bridge_key
from ..hermes_adapter import HermesUnavailable
from ..schemas import EventCreate

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _not_connected(source: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error": {
                "code": f"{source}_not_connected",
                "message": "Connectez ce calendrier dans l'onglet Intégrations.",
                "source": source,
            }
        },
    )


def _read_only(source: str) -> HTTPException:
    label = calendar_adapter.source_label(source)
    return HTTPException(
        status_code=405,
        detail={
            "error": {
                "code": "read_only_source",
                "message": f"{label} est en lecture seule : consultation uniquement, pas de création/suppression.",
                "source": source,
            }
        },
    )


@router.get("/calendar/status")
def calendar_status() -> dict:
    """Statut honnête agrégé : sources connectées + source par défaut."""
    try:
        return calendar_adapter.calendar_status()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/calendar/sources")
def calendar_sources() -> dict:
    """Détail des sources (id, libellé, écriture possible, connecté)."""
    try:
        return {
            "sources": calendar_adapter.calendar_sources(),
            "default": calendar_adapter.default_source(),
        }
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/calendar/events")
def list_events(
    source: str | None = None,
    start: str | None = None,
    end: str | None = None,
    tz: str = "UTC",
) -> dict:
    try:
        return {"events": calendar_adapter.list_events(start, end, source=source, tz=tz)}
    except CalendarNotConnected as exc:
        raise _not_connected(exc.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid", "message": str(exc)}})
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/calendar/events")
def create_event(body: EventCreate) -> dict:
    try:
        result = calendar_adapter.create_event(
            body.title,
            body.start,
            body.end,
            body.location or "",
            body.description or "",
            with_meet=body.with_meet,
            source=body.source,
            tz=body.tz,
        )
        return {"event": result}
    except CalendarNotConnected as exc:
        raise _not_connected(exc.source)
    except ReadOnlySource as exc:
        raise _read_only(exc.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid", "message": str(exc)}})
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/calendar/events/{event_id}")
def delete_event(event_id: str, source: str | None = None) -> dict:
    try:
        return calendar_adapter.delete_event(event_id, source=source)
    except CalendarNotConnected as exc:
        raise _not_connected(exc.source)
    except ReadOnlySource as exc:
        raise _read_only(exc.source)
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)
