"""Appels Microsoft directs côté bridge (Chemin A) — Outlook Calendar via Graph.

Alimente la page « Calendrier » d'Agent OS quand le client a connecté Microsoft 365
(feature 016 : OAuth « 1 clic », scope ``Calendars.ReadWrite`` déjà accordé). On réutilise
le jeton OAuth stocké (``~/.hermes/microsoft_token.json``, écrit par ``oauth_engine``),
on le rafraîchit via ``oauth_engine.refresh_token`` puis on appelle Microsoft Graph.
Le moteur Hermes reste intact (« Hermes seul maître »).

Garde-fous : Microsoft non connecté → ``MicrosoftNotConnected`` ; erreur réseau/API →
``HermesUnavailable`` (503). Aucun secret n'est journalisé.
"""

from __future__ import annotations

import datetime
import json
import logging

from . import calendar_common, hermes_adapter, oauth_engine
from .hermes_adapter import HermesUnavailable

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_PROVIDER_ID = "microsoft-365"
_GRAPH = "https://graph.microsoft.com/v1.0"
MS_TOKEN_FILE = hermes_adapter.HERMES_HOME / "microsoft_token.json"


class MicrosoftNotConnected(Exception):
    """Le compte Microsoft 365 n'est pas connecté (OAuth à faire via l'onglet Intégrations)."""


def status() -> bool:
    """Connecté ⇔ le fichier jeton existe (preuve réelle, cf. honnêteté des libellés)."""
    return MS_TOKEN_FILE.exists()


def _load_token() -> dict:
    if not MS_TOKEN_FILE.exists():
        raise MicrosoftNotConnected()
    try:
        data = json.loads(MS_TOKEN_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HermesUnavailable(f"microsoft_token.json illisible: {exc}") from exc
    if not isinstance(data, dict) or not data.get("access_token"):
        raise MicrosoftNotConnected()
    return data


def _access_token() -> str:
    """Access token frais : rafraîchit d'abord (best-effort), puis relit le fichier."""
    if not MS_TOKEN_FILE.exists():
        raise MicrosoftNotConnected()
    # Le token Graph expire ~1 h : on tente un renouvellement via le refresh_token stocké.
    # Best-effort : en cas d'échec réseau on retombe sur l'access_token courant (peut être
    # encore valide) ; l'appel API tranchera.
    try:
        oauth_engine.refresh_token(_PROVIDER_ID)
    except Exception:  # noqa: BLE001 — refresh best-effort, jamais bloquant
        # `oauth_engine.refresh_token` ne journalise déjà aucun secret (cf. sa docstring) ;
        # ce message ne contient donc que le type d'exception, jamais le token.
        logger.debug("rafraîchissement du token Microsoft 365 échoué (repli sur le token courant)", exc_info=True)
    access = _load_token().get("access_token")
    if not access:
        raise HermesUnavailable("access_token Microsoft absent")
    return access


def _graph(
    method: str,
    path: str,
    access_token: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    extra_headers: dict | None = None,
) -> dict:
    """Appel REST Microsoft Graph authentifié (Bearer). Lève HermesUnavailable si HTTP>=400."""
    return calendar_common.authenticated_request(
        method,
        f"{_GRAPH}{path}",
        access_token,
        params=params,
        json_body=json_body,
        extra_headers=extra_headers,
        service_name="Microsoft",
        error_prefix="Microsoft Graph",
        timeout=_TIMEOUT,
    )


def _to_event(e: dict) -> dict:
    start = (e.get("start") or {}).get("dateTime") or ""
    end = (e.get("end") or {}).get("dateTime") or ""
    location = (e.get("location") or {}).get("displayName") or ""
    return calendar_common.event_dict(
        id=e.get("id"),
        title=e.get("subject"),
        start=start,
        end=end,
        location=location,
        link=e.get("webLink") or "",
        all_day=e.get("isAllDay"),
        source="outlook",
    )


def _default_window() -> tuple[str, str]:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.isoformat(), (now + datetime.timedelta(days=60)).isoformat()


def list_events(
    start: str | None = None,
    end: str | None = None,
    maximum: int = 25,
    tz: str = "UTC",
) -> list[dict]:
    """Événements Outlook via ``/me/calendarView``. Les heures sont renvoyées dans ``tz``
    (fuseau du client) grâce à l'en-tête ``Prefer`` → ``when_label`` juste."""
    access = _access_token()
    win_start, win_end = _default_window()
    params = {
        "startDateTime": start or win_start,
        "endDateTime": end or win_end,
        "$orderby": "start/dateTime",
        "$top": str(maximum),
        "$select": "id,subject,start,end,location,isAllDay,webLink",
    }
    data = _graph(
        "GET",
        "/me/calendarView",
        access,
        params=params,
        extra_headers={"Prefer": f'outlook.timezone="{tz}"'},
    )
    items = data.get("value") if isinstance(data, dict) else None
    return [_to_event(e) for e in (items or [])]


def create_event(
    title: str,
    start: str,
    end: str,
    location: str = "",
    description: str = "",
    tz: str = "UTC",
) -> dict:
    """Crée un événement Outlook (``/me/events``). ``start``/``end`` = heure locale du client
    exprimée dans ``tz``."""
    if not title.strip() or not start.strip() or not end.strip():
        raise ValueError("titre, début et fin sont requis")
    access = _access_token()
    body: dict = {
        "subject": title,
        "start": {"dateTime": start, "timeZone": tz},
        "end": {"dateTime": end, "timeZone": tz},
    }
    if location:
        body["location"] = {"displayName": location}
    if description:
        body["body"] = {"contentType": "text", "content": description}
    created = _graph("POST", "/me/events", access, json_body=body)
    return {
        "status": "created",
        "id": created.get("id"),
        "summary": created.get("subject"),
        "htmlLink": created.get("webLink"),
    }


def delete_event(event_id: str) -> dict:
    access = _access_token()
    _graph("DELETE", f"/me/events/{event_id}", access)
    return {"ok": True}
