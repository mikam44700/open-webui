"""Adapter Calendrier — multi-source (Google Agenda, Outlook, Calendly).

La page « Calendrier » d'Agent OS s'adapte au(x) calendrier(s) que le CLIENT a connecté(s)
dans l'onglet Intégrations. Le client ne voit qu'une source à la fois ; s'il en a connecté
plusieurs, le front propose un sélecteur (aucun mélange). Chaque source est branchée sans
toucher au moteur Hermes (« Hermes seul maître ») :

- ``google``   : script déterministe de la skill google-workspace (``google_api.py``),
                 source historique (feature 014).
- ``outlook``  : Microsoft Graph via ``microsoft_direct`` (Chemin A, scope Calendars.ReadWrite).
- ``calendly`` : RDV planifiés via ``calendly_direct`` (Chemin A, LECTURE SEULE).

Garde-fous : statut réel vérifié avant tout appel (jamais de faux événement) ; source non
connectée → ``CalendarNotConnected`` ; source en lecture seule sollicitée en écriture →
``ReadOnlySource`` ; erreur/injoignable → ``HermesUnavailable`` (503).
"""

from __future__ import annotations

import json
import subprocess

from . import (
    calendar_common,
    calendly_direct,
    google_direct,
    hermes_adapter,
    integrations_adapter,
    microsoft_direct,
)
from .hermes_adapter import HermesUnavailable

GOOGLE_API_SCRIPT = (
    hermes_adapter.HERMES_HOME / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py"
)
_TIMEOUT = 30


# ─── Sources ─────────────────────────────────────────────────────────────────

# L'ordre fixe la source par défaut (première connectée) et l'ordre du sélecteur front.
_SOURCE_META: tuple[dict, ...] = (
    {"id": "google", "label": "Google Agenda", "can_write": True},
    {"id": "outlook", "label": "Outlook Calendar", "can_write": True},
    {"id": "calendly", "label": "Calendly", "can_write": False},
)
_SOURCE_IDS = {m["id"] for m in _SOURCE_META}


class CalendarNotConnected(Exception):
    """La source de calendrier demandée n'est pas connectée."""

    def __init__(self, source: str = "google"):
        self.source = source
        super().__init__(f"calendrier {source} non connecté")


class GoogleNotConnected(CalendarNotConnected):
    """Rétrocompat : Google non connecté (sous-classe de CalendarNotConnected)."""

    def __init__(self):
        super().__init__("google")


class ReadOnlySource(Exception):
    """La source (ex. Calendly) est en lecture seule : pas de création/suppression."""

    def __init__(self, source: str):
        self.source = source
        super().__init__(f"la source {source} est en lecture seule")


def _connected(source: str) -> bool:
    if source == "google":
        return integrations_adapter.google_status() == "connected"
    if source == "outlook":
        return microsoft_direct.status()
    if source == "calendly":
        return calendly_direct.status()
    return False


def calendar_sources() -> list[dict]:
    """Liste des sources avec leur état de connexion réel (ordre = priorité par défaut)."""
    return [{**meta, "connected": _connected(meta["id"])} for meta in _SOURCE_META]


def _can_write(source: str) -> bool:
    """Dérive le blocage écriture directement de ``_SOURCE_META`` (source unique de vérité).

    Une future source en lecture seule n'a qu'à poser ``can_write: False`` dans la table :
    ``create_event``/``delete_event`` la respectent automatiquement, sans comparaison de
    chaîne à dupliquer (finding audit — les deux mécanismes pouvaient diverger).
    """
    meta = next((m for m in _SOURCE_META if m["id"] == source), None)
    return bool(meta and meta["can_write"])


def source_label(source: str) -> str:
    """Libellé humain d'une source (ex. ``"calendly"`` -> ``"Calendly"``), depuis
    ``_SOURCE_META`` (source unique de vérité — cf. ``_can_write``).

    Utilisé par le routeur pour les messages d'erreur (ex. lecture seule) : sans ça, le
    message restait câblé en dur sur « Calendly » alors que le mécanisme est générique et
    qu'une future source en lecture seule (ex. un futur agenda partagé) n'aurait pas eu un
    message cohérent. Repli sur l'identifiant brut si la source est inconnue.
    """
    meta = next((m for m in _SOURCE_META if m["id"] == source), None)
    return meta["label"] if meta else source


def default_source() -> str | None:
    """Première source connectée (ou None si aucune). Point d'entrée public (cf. ``_default_source``,
    conservé en interne pour ``calendar_status()``)."""
    return _default_source()


def _default_source() -> str | None:
    """Première source connectée (ou None si aucune)."""
    for meta in _SOURCE_META:
        if _connected(meta["id"]):
            return meta["id"]
    return None


def _resolve_source(source: str | None) -> str:
    """Normalise la source : None/vide/'auto' → première connectée (sinon 'google' pour un
    message d'erreur cohérent). Source inconnue → ValueError."""
    if source in (None, "", "auto"):
        return _default_source() or "google"
    if source not in _SOURCE_IDS:
        raise ValueError(f"source de calendrier inconnue: {source}")
    return source


def calendar_status() -> dict:
    """Statut honnête agrégé : au moins une source connectée + détail par source."""
    sources = calendar_sources()
    return {
        "connected": any(s["connected"] for s in sources),
        "sources": sources,
        "default": _default_source(),
    }


# ─── Google (skill google-workspace, source historique) ──────────────────────


def _run_gapi(args: list[str]) -> object:
    """Exécute ``google_api.py <args>`` via le Python du venv Hermes. Renvoie le JSON parsé."""
    try:
        res = subprocess.run(
            [hermes_adapter.HERMES_PYTHON, str(GOOGLE_API_SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    if res.returncode != 0:
        raise HermesUnavailable((res.stderr or res.stdout).strip()[:300] or "google_api a échoué")
    out = res.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except (ValueError, json.JSONDecodeError) as exc:
        # Sortie non-JSON (script mis à jour, avertissement imprévu sur stdout...) : traité
        # comme une indisponibilité honnête (503), jamais comme un 500 brut.
        raise HermesUnavailable(f"réponse Google illisible: {out[:200]}") from exc


def event_to_dict(e: dict) -> dict:
    """Mappe un événement Google Agenda vers la vue dirigeant normalisée."""
    return calendar_common.event_dict(
        id=e.get("id"),
        title=e.get("summary"),
        start=e.get("start") or "",
        end=e.get("end") or "",
        location=e.get("location") or "",
        link=e.get("htmlLink") or "",
        source="google",
    )


def _google_list(start: str | None, end: str | None, maximum: int) -> list[dict]:
    args = ["calendar", "list", "--max", str(maximum)]
    if start:
        args += ["--start", start]
    if end:
        args += ["--end", end]
    data = _run_gapi(args)
    events = data if isinstance(data, list) else []
    return [event_to_dict(e) for e in events]


def _google_create(
    title: str, start: str, end: str, location: str, description: str, with_meet: bool
) -> dict:
    if not title.strip() or not start.strip() or not end.strip():
        raise ValueError("titre, début et fin sont requis")
    # Meet : passe par google_direct (conferenceData non géré par google_api.py). Hermes intact.
    if with_meet:
        try:
            return google_direct.create_meet_event(title, start, end, location, description)
        except google_direct.GoogleNotConnected as exc:
            raise GoogleNotConnected() from exc
    args = ["calendar", "create", "--summary", title, "--start", start, "--end", end]
    if location:
        args += ["--location", location]
    if description:
        args += ["--description", description]
    return _run_gapi(args)


# ─── API multi-source ────────────────────────────────────────────────────────


def list_events(
    start: str | None = None,
    end: str | None = None,
    maximum: int = 25,
    *,
    source: str | None = None,
    tz: str = "UTC",
) -> list[dict]:
    src = _resolve_source(source)
    if not _connected(src):
        raise CalendarNotConnected(src)
    if src == "google":
        return _google_list(start, end, maximum)
    if src == "outlook":
        try:
            return microsoft_direct.list_events(start, end, maximum, tz)
        except microsoft_direct.MicrosoftNotConnected as exc:
            raise CalendarNotConnected("outlook") from exc
    try:
        return calendly_direct.list_events(start, end, maximum, tz)
    except calendly_direct.CalendlyNotConnected as exc:
        raise CalendarNotConnected("calendly") from exc


def create_event(
    title: str,
    start: str,
    end: str,
    location: str = "",
    description: str = "",
    with_meet: bool = False,
    *,
    source: str | None = None,
    tz: str = "UTC",
) -> dict:
    src = _resolve_source(source)
    if not _connected(src):
        raise CalendarNotConnected(src)
    if not _can_write(src):
        raise ReadOnlySource(src)
    if src == "outlook":
        if not title.strip() or not start.strip() or not end.strip():
            raise ValueError("titre, début et fin sont requis")
        try:
            return microsoft_direct.create_event(title, start, end, location, description, tz)
        except microsoft_direct.MicrosoftNotConnected as exc:
            raise CalendarNotConnected("outlook") from exc
    return _google_create(title, start, end, location, description, with_meet)


def delete_event(event_id: str, *, source: str | None = None) -> dict:
    src = _resolve_source(source)
    if not _connected(src):
        raise CalendarNotConnected(src)
    if not _can_write(src):
        raise ReadOnlySource(src)
    if src == "outlook":
        try:
            return microsoft_direct.delete_event(event_id)
        except microsoft_direct.MicrosoftNotConnected as exc:
            raise CalendarNotConnected("outlook") from exc
    _run_gapi(["calendar", "delete", event_id])
    return {"ok": True}
