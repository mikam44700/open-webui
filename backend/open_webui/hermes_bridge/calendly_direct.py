"""Appels Calendly directs côté bridge (Chemin A) — RDV planifiés, lecture seule.

Alimente la page « Calendrier » d'Agent OS quand le client a connecté Calendly
(feature 016 : OAuth « 1 clic »). Calendly est un outil de PRISE DE RENDEZ-VOUS : on
affiche les RDV déjà planifiés (``scheduled_events``), on n'en crée pas depuis Agent OS
(lecture seule assumée — cf. honnêteté des libellés). Jeton OAuth réutilisé
(``~/.hermes/calendly_token.json``), rafraîchi via ``oauth_engine.refresh_token``.

Garde-fous : Calendly non connecté → ``CalendlyNotConnected`` ; erreur réseau/API →
``HermesUnavailable`` (503). Aucun secret n'est journalisé.
"""

from __future__ import annotations

import datetime
import json
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import calendar_common, hermes_adapter, oauth_engine
from .hermes_adapter import HermesUnavailable

logger = logging.getLogger(__name__)

try:  # httpx est une dépendance du bridge (moteur OAuth) ; garde défensive.
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

_TIMEOUT = 30
_PROVIDER_ID = "calendly"
_API = "https://api.calendly.com"
CALENDLY_TOKEN_FILE = hermes_adapter.HERMES_HOME / "calendly_token.json"


class CalendlyNotConnected(Exception):
    """Le compte Calendly n'est pas connecté (OAuth à faire via l'onglet Intégrations)."""


def status() -> bool:
    """Connecté ⇔ le fichier jeton existe (preuve réelle, cf. honnêteté des libellés)."""
    return CALENDLY_TOKEN_FILE.exists()


def _load_token() -> dict:
    if not CALENDLY_TOKEN_FILE.exists():
        raise CalendlyNotConnected()
    try:
        data = json.loads(CALENDLY_TOKEN_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HermesUnavailable(f"calendly_token.json illisible: {exc}") from exc
    if not isinstance(data, dict) or not data.get("access_token"):
        raise CalendlyNotConnected()
    return data


def _access_token() -> str:
    if not CALENDLY_TOKEN_FILE.exists():
        raise CalendlyNotConnected()
    try:
        oauth_engine.refresh_token(_PROVIDER_ID)
    except Exception:  # noqa: BLE001 — refresh best-effort, jamais bloquant
        # `oauth_engine.refresh_token` ne journalise déjà aucun secret (cf. sa docstring) ;
        # ce message ne contient donc que le type d'exception, jamais le token.
        logger.debug("rafraîchissement du token Calendly échoué (repli sur le token courant)", exc_info=True)
    access = _load_token().get("access_token")
    if not access:
        raise HermesUnavailable("access_token Calendly absent")
    return access


def _api(path: str, access_token: str, *, params: dict | None = None) -> dict:
    if httpx is None:  # pragma: no cover
        raise HermesUnavailable("httpx indisponible côté bridge")
    try:
        resp = httpx.get(
            f"{_API}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise HermesUnavailable(f"appel Calendly échoué: {exc}") from exc
    if resp.status_code >= 400:
        raise HermesUnavailable(f"Calendly API {resp.status_code}: {resp.text[:200]}")
    return resp.json() if resp.content else {}


def _to_local(iso_utc: str, tz: str) -> str:
    """Convertit un début ISO UTC Calendly (« …Z ») vers l'heure locale du client (naïve),
    pour que ``when_label`` affiche l'heure attendue. Retour au brut si parsing impossible."""
    if not iso_utc:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        local = dt.astimezone(ZoneInfo(tz))
        return local.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, ZoneInfoNotFoundError):
        return iso_utc


def _location_label(loc: object) -> str:
    """Rend une localisation Calendly lisible (adresse, lien visio, ou type)."""
    if not isinstance(loc, dict):
        return ""
    for key in ("location", "join_url"):
        val = loc.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    kind = loc.get("type")
    labels = {
        "physical": "En présentiel",
        "zoom": "Zoom",
        "google_conference": "Google Meet",
        "microsoft_teams_conference": "Microsoft Teams",
        "gotomeeting": "GoToMeeting",
        "webex": "Webex",
        "outbound_call": "Appel sortant",
        "inbound_call": "Appel entrant",
        "custom": "",
    }
    return labels.get(kind, "") if isinstance(kind, str) else ""


def _to_event(e: dict, tz: str) -> dict:
    uri = e.get("uri") or ""
    event_id = uri.rstrip("/").rsplit("/", 1)[-1] if uri else ""
    start = _to_local(e.get("start_time") or "", tz)
    end = _to_local(e.get("end_time") or "", tz)
    return calendar_common.event_dict(
        id=event_id,
        title=e.get("name"),
        start=start,
        end=end,
        location=_location_label(e.get("location")),
        link="",  # l'URI Calendly est une URL d'API, non destinée au client
        all_day=False,
        source="calendly",
    )


def _current_user_uri(access: str) -> str:
    data = _api("/users/me", access)
    resource = data.get("resource") if isinstance(data, dict) else None
    uri = (resource or {}).get("uri") if isinstance(resource, dict) else None
    if not uri:
        raise HermesUnavailable("URI utilisateur Calendly introuvable")
    return uri


def list_events(
    start: str | None = None,
    end: str | None = None,
    maximum: int = 25,
    tz: str = "UTC",
) -> list[dict]:
    """RDV Calendly planifiés (actifs), triés par date. Lecture seule."""
    access = _access_token()
    user_uri = _current_user_uri(access)
    params = {
        "user": user_uri,
        "status": "active",
        "sort": "start_time:asc",
        "count": str(min(maximum, 100)),
    }
    if start:
        params["min_start_time"] = start
    if end:
        params["max_start_time"] = end
    data = _api("/scheduled_events", access, params=params)
    collection = data.get("collection") if isinstance(data, dict) else None
    return [_to_event(e, tz) for e in (collection or [])]
