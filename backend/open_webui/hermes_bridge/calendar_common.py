"""Utilitaires partagés entre les sources de calendrier (Google, Outlook, Calendly).

Format d'événement normalisé (vue dirigeant, identique quelle que soit la source) ::

    {id, title, start, end, location, when_label, all_day, link, source}

``when_label`` est un libellé FR calculé à partir d'un début ISO déjà exprimé dans
l'heure locale du client (chaque source convertit avant d'appeler ``event_dict``).

``authenticated_request`` mutualise la couche HTTP « Bearer + gestion d'erreur »
utilisée par ``google_direct._api`` et ``microsoft_direct._graph`` (finding d'audit :
les deux étaient des wrappers REST quasi identiques). Les libellés d'erreur restent
paramétrables : Google et Microsoft ne préfixent pas leurs messages de la même façon.
"""

from __future__ import annotations

from .hermes_adapter import HermesUnavailable

try:  # httpx est une dépendance du bridge (moteur OAuth) ; garde défensive.
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

_TIMEOUT = 30


def authenticated_request(
    method: str,
    url: str,
    access_token: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    extra_headers: dict | None = None,
    service_name: str,
    error_prefix: str,
    timeout: int = _TIMEOUT,
) -> dict:
    """Appel REST authentifié (Bearer), partagé entre les sources de calendrier.

    Lève ``HermesUnavailable`` sur erreur réseau (``"appel {service_name} échoué: ..."``)
    ou sur HTTP>=400 (``"{error_prefix} {status}: {texte tronqué à 200 car.}"``).
    ``service_name``/``error_prefix`` préservent les messages historiques de chaque
    appelant (ex. Google : ``"appel Google échoué"`` / ``"Google API {status}"`` ;
    Microsoft : ``"appel Microsoft échoué"`` / ``"Microsoft Graph {status}"``).
    """
    if httpx is None:  # pragma: no cover
        raise HermesUnavailable("httpx indisponible côté bridge")
    headers = {"Authorization": f"Bearer {access_token}"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        resp = httpx.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise HermesUnavailable(f"appel {service_name} échoué: {exc}") from exc
    if resp.status_code >= 400:
        raise HermesUnavailable(f"{error_prefix} {resp.status_code}: {resp.text[:200]}")
    return resp.json() if resp.content else {}


def when_label(start: str) -> str:
    """Libellé FR « le JJ/MM à HH:MM » (ou « journée ») depuis un début ISO local."""
    if not start:
        return ""
    try:
        date_part, sep, time_part = start.partition("T")
        _y, mo, d = date_part.split("-")[:3]
        if sep and time_part:
            hm = ":".join(time_part.replace("Z", "").split(":")[:2])
            return f"le {d}/{mo} à {hm}"
        return f"le {d}/{mo} (journée)"
    except Exception:
        return start[:16]


def event_dict(
    *,
    id: str | None,
    title: str | None,
    start: str,
    source: str,
    end: str = "",
    location: str = "",
    link: str = "",
    all_day: bool | None = None,
) -> dict:
    """Construit un événement normalisé. ``all_day`` déduit de l'absence d'heure si non fourni."""
    start = start or ""
    return {
        "id": id,
        "title": title or "(sans titre)",
        "start": start,
        "end": end or "",
        "location": location or "",
        "when_label": when_label(start),
        "all_day": (bool(start) and "T" not in start) if all_day is None else bool(all_day),
        "link": link or "",
        "source": source,
    }
