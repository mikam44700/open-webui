"""Appels Google directs côté bridge (Chemin A) — sans la skill Hermes ni gws.

Couvre les services Google absents du script ``google_api.py`` de Hermes
(Meet, Slides, Analytics, Search Console). On réutilise le même jeton OAuth que la
skill (``~/.hermes/google_token.json``, format ``authorized_user`` écrit par
``oauth_engine``), on rafraîchit l'``access_token`` via httpx, puis on appelle les
API REST Google. Le moteur Hermes reste intact (« Hermes seul maître »).

Garde-fous : Google non connecté → ``GoogleNotConnected`` ; erreur réseau/API →
``HermesUnavailable`` (503). Aucun secret n'est journalisé.
"""

from __future__ import annotations

import datetime
import json
import uuid
from urllib.parse import quote

from . import calendar_common, fsutil, hermes_adapter
from .hermes_adapter import HermesUnavailable

try:  # httpx est une dépendance du bridge (moteur OAuth) ; garde défensive.
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

_TIMEOUT = 30
GOOGLE_TOKEN_FILE = hermes_adapter.HERMES_HOME / "google_token.json"

# Verrou exclusif sur ``google_token.json`` (fichier ``<path>.lock`` dédié, cf. ``fsutil``).
#
# Deux appels concurrents à ``_access_token()`` (ex. le briefing du matin + une action de
# chat qui crée un lien Meet, quasi simultanément) qui tombent tous les deux sur une
# rotation de ``refresh_token`` côté Google liraient potentiellement le MÊME jeton de
# départ et écriraient chacun un ``google_token.json`` différent sans coordination — le
# perdant écrase le gagnant (cf. audit phase 3, finding MOYENNE). Alias conservé (même nom)
# pour que les tests puissent continuer à monkeypatcher ``google_direct._token_file_lock``.
_token_file_lock = fsutil.file_lock


class GoogleNotConnected(Exception):
    """Le compte Google n'est pas connecté (OAuth à faire via l'onglet Intégrations)."""


def _load_token() -> dict:
    """Lit ``google_token.json`` (format authorized_user). Lève GoogleNotConnected si absent."""
    if not GOOGLE_TOKEN_FILE.exists():
        raise GoogleNotConnected()
    try:
        data = json.loads(GOOGLE_TOKEN_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HermesUnavailable(f"google_token.json illisible: {exc}") from exc
    if not isinstance(data, dict) or not data.get("refresh_token"):
        raise GoogleNotConnected()
    return data


def _persist_rotated_refresh_token(tok: dict, new_refresh_token: str, access_token: str) -> None:
    """Réécrit ``google_token.json`` quand Google renvoie un ``refresh_token`` renouvelé.

    Google fait parfois tourner le ``refresh_token`` (changement de mot de passe côté
    compte Google, dépassement du nombre de grants actifs, ré-authentification de
    sécurité) — un cas documenté par Google lui-même. Ignorer ce nouveau
    ``refresh_token`` invaliderait silencieusement l'ancien côté Google : Meet/Slides/
    Analytics/Search Console casseraient au prochain appel, sans que ``token_status``/
    ``google_status`` (basés sur la seule présence du fichier) ne le signale (cf.
    finding audit 05 #3). Symétrique à ce que fait déjà ``oauth_engine.refresh_token``
    pour les autres fournisseurs. Écrit en 0600, même format ``authorized_user``.

    Verrouillée (``_token_file_lock``) : deux appels concurrents à ``_access_token()`` qui
    tombent tous les deux sur une rotation ne doivent jamais s'écraser silencieusement
    (cf. audit phase 3, finding MOYENNE — écriture jusqu'ici sans coordination).
    """
    updated = {**tok, "refresh_token": new_refresh_token, "token": access_token}
    payload = json.dumps(updated, ensure_ascii=False)
    with _token_file_lock(GOOGLE_TOKEN_FILE):
        fsutil.atomic_write_text(GOOGLE_TOKEN_FILE, payload, mode=0o600)


def _access_token() -> str:
    """Échange le refresh_token contre un access_token frais (jamais journalisé).

    Si Google renvoie un nouveau ``refresh_token`` (rotation), il est persisté dans
    ``google_token.json`` (cf. ``_persist_rotated_refresh_token``) — sinon l'ancien
    refresh_token stocké deviendrait invalide côté Google sans que rien ne le détecte.
    """
    if httpx is None:  # pragma: no cover
        raise HermesUnavailable("httpx indisponible côté bridge")
    tok = _load_token()
    try:
        resp = httpx.post(
            tok.get("token_uri") or "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": tok["refresh_token"],
                "client_id": tok.get("client_id", ""),
                "client_secret": tok.get("client_secret", ""),
            },
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise HermesUnavailable(f"rafraîchissement du jeton Google échoué: {exc}") from exc
    if resp.status_code != 200:
        raise HermesUnavailable(f"jeton Google refusé ({resp.status_code})")
    payload = resp.json() or {}
    access = payload.get("access_token")
    if not access:
        raise HermesUnavailable("access_token Google absent de la réponse")

    new_refresh_token = payload.get("refresh_token")
    if new_refresh_token and new_refresh_token != tok.get("refresh_token"):
        _persist_rotated_refresh_token(tok, new_refresh_token, access)

    return access


def _api(
    method: str,
    url: str,
    access_token: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """Appel REST Google authentifié (Bearer). Lève HermesUnavailable sur erreur/HTTP>=400."""
    return calendar_common.authenticated_request(
        method,
        url,
        access_token,
        params=params,
        json_body=json_body,
        service_name="Google",
        error_prefix="Google API",
        timeout=_TIMEOUT,
    )


# ─── Google Meet (via Agenda + conferenceData) ───────────────────────────────


def create_meet_event(
    title: str,
    start: str,
    end: str,
    location: str = "",
    description: str = "",
    attendees: list[str] | None = None,
) -> dict:
    """Crée un événement Agenda **avec lien Google Meet** et renvoie le lien.

    Le scope ``calendar`` (déjà demandé à la connexion Google) suffit : Meet se crée
    via l'API Agenda (``conferenceData.createRequest``), sans permission supplémentaire.
    """
    access = _access_token()
    event: dict = {
        "summary": title,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    if location:
        event["location"] = location
    if description:
        event["description"] = description
    if attendees:
        event["attendees"] = [{"email": e.strip()} for e in attendees if e.strip()]

    data = _api(
        "POST",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        access,
        params={"conferenceDataVersion": 1},
        json_body=event,
    )
    return {
        "status": "created",
        "id": data.get("id", ""),
        "summary": data.get("summary", ""),
        "htmlLink": data.get("htmlLink", ""),
        "meet_link": _extract_meet_link(data),
    }


def _extract_meet_link(event: dict) -> str:
    """Récupère le lien Meet de la réponse Agenda (hangoutLink ou entryPoints vidéo)."""
    if event.get("hangoutLink"):
        return event["hangoutLink"]
    for ep in (event.get("conferenceData", {}) or {}).get("entryPoints", []) or []:
        if ep.get("entryPointType") == "video" and ep.get("uri"):
            return ep["uri"]
    return ""


# ─── Google Search Console (lecture seule) ───────────────────────────────────


def search_console_summary(days: int = 28, limit: int = 5) -> dict:
    """Top requêtes Search Console (1er site vérifié, N jours). Lecture seule.

    Nécessite le scope ``webmasters.readonly``. État honnête : ``note=no_site`` si aucun
    site vérifié n'est rattaché au compte Google.
    """
    access = _access_token()
    sites = _api("GET", "https://www.googleapis.com/webmasters/v3/sites", access)
    site_url = _first_verified_site(sites)
    if not site_url:
        return {"connected": True, "site": "", "queries": [], "note": "no_site"}
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    report = _api(
        "POST",
        f"https://www.googleapis.com/webmasters/v3/sites/{quote(site_url, safe='')}/searchAnalytics/query",
        access,
        json_body={
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query"],
            "rowLimit": limit,
        },
    )
    queries = [
        {
            "query": (r.get("keys") or [""])[0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
        }
        for r in (report.get("rows") or [])
    ]
    return {"connected": True, "site": site_url, "days": days, "queries": queries}


def _first_verified_site(sites: dict) -> str:
    """1er site Search Console (priorité propriétaire/complet), '' si aucun."""
    entries = sites.get("siteEntry", []) or []
    for e in entries:
        if e.get("permissionLevel") in ("siteOwner", "siteFullUser") and e.get("siteUrl"):
            return e["siteUrl"]
    for e in entries:
        if e.get("siteUrl"):
            return e["siteUrl"]
    return ""


# ─── Google Slides ───────────────────────────────────────────────────────────


def create_presentation(title: str, slides: list[str] | None = None) -> dict:
    """Crée une présentation Google Slides (titre) + une diapo par ligne du plan (optionnel).

    Nécessite le scope ``presentations`` (ajouté à la connexion Google). Renvoie l'URL
    d'édition. Déterministe : pas de génération de contenu par LLM (chaque ligne du plan
    devient le titre d'une diapo).
    """
    if not (title or "").strip():
        raise ValueError("titre requis")
    access = _access_token()
    pres = _api(
        "POST",
        "https://slides.googleapis.com/v1/presentations",
        access,
        json_body={"title": title.strip()},
    )
    pres_id = pres.get("presentationId", "")
    requests = _build_outline_requests(slides or [])
    if pres_id and requests:
        _api(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{pres_id}:batchUpdate",
            access,
            json_body={"requests": requests},
        )
    return {
        "status": "created",
        "id": pres_id,
        "title": pres.get("title", title.strip()),
        "url": f"https://docs.google.com/presentation/d/{pres_id}/edit" if pres_id else "",
        "slides": len([r for r in requests if "createSlide" in r]),
    }


# ─── Google Analytics (GA4, lecture seule) ───────────────────────────────────


def analytics_summary(days: int = 7) -> dict:
    """Résumé GA4 (1re propriété trouvée, métriques clés sur N jours). Lecture seule.

    Nécessite le scope ``analytics.readonly``. État honnête : ``note=no_property`` si le
    compte Google n'a aucune propriété GA4 (jamais de faux chiffres).
    """
    access = _access_token()
    summaries = _api(
        "GET", "https://analyticsadmin.googleapis.com/v1beta/accountSummaries", access
    )
    prop_id, prop_name = _first_ga4_property(summaries)
    if not prop_id:
        return {"connected": True, "property": "", "metrics": [], "note": "no_property"}
    report = _api(
        "POST",
        f"https://analyticsdata.googleapis.com/v1beta/properties/{prop_id}:runReport",
        access,
        json_body={
            "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
            ],
        },
    )
    v = _first_metric_row(report)
    metrics = [
        {"label": "Visiteurs actifs", "value": v[0] if len(v) > 0 else "0"},
        {"label": "Sessions", "value": v[1] if len(v) > 1 else "0"},
        {"label": "Pages vues", "value": v[2] if len(v) > 2 else "0"},
    ]
    return {"connected": True, "property": prop_name, "days": days, "metrics": metrics}


def _first_ga4_property(summaries: dict) -> tuple[str, str]:
    """Renvoie (id, nom) de la 1re propriété GA4 trouvée, ('', '') si aucune."""
    for acc in summaries.get("accountSummaries", []) or []:
        for prop in acc.get("propertySummaries", []) or []:
            res = prop.get("property", "")  # ex. "properties/123456"
            if res:
                return res.split("/")[-1], prop.get("displayName", res)
    return "", ""


def _first_metric_row(report: dict) -> list[str]:
    """Valeurs de la 1re ligne de métriques d'un rapport GA4 (vide si aucune)."""
    rows = report.get("rows", []) or []
    if not rows:
        return []
    return [m.get("value", "0") for m in rows[0].get("metricValues", []) or []]


def _build_outline_requests(lines: list[str]) -> list[dict]:
    """Transforme un plan (lignes) en requêtes batchUpdate : 1 diapo + zone de texte / ligne."""
    reqs: list[dict] = []
    for i, raw in enumerate(lines):
        text = (raw or "").strip()
        if not text:
            continue
        slide_id, box_id = f"slide_{i}", f"box_{i}"
        reqs.append(
            {"createSlide": {"objectId": slide_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}
        )
        reqs.append(
            {
                "createShape": {
                    "objectId": box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 6000000, "unit": "EMU"},
                            "height": {"magnitude": 1000000, "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 500000,
                            "translateY": 500000,
                            "unit": "EMU",
                        },
                    },
                }
            }
        )
        reqs.append({"insertText": {"objectId": box_id, "text": text}})
    return reqs
