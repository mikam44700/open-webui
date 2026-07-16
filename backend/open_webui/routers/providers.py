"""Router /api/v1/providers — gestion des cerveaux Hermes (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI. Le bridge pilote Hermes (`hermes config set`).

Voir specs/001-providers-page/contracts/openwebui-providers-api.md
"""

from __future__ import annotations

import logging
import os
from urllib.parse import quote

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.auth import get_admin_user
from open_webui.utils.session_pool import get_session

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://host.docker.internal:8650").rstrip("/")
BRIDGE_KEY = os.getenv("BRIDGE_KEY", "")

# Timeout total appliqué à chaque appel au bridge (évite un gel indéfini si le
# service interne ne répond jamais — AIOHTTP_CLIENT_TIMEOUT vaut None par défaut).
_BRIDGE_TIMEOUT = aiohttp.ClientTimeout(total=15)

log = logging.getLogger(__name__)
router = APIRouter()


def _bridge_segment(value: str) -> str:
    """Encode un segment de chemin avant de l'interpoler dans l'URL du bridge.

    Anti path/query injection (finding audit #7) : un `/`, `?`, `#`, ou un espace dans
    l'identifiant ne doit jamais changer la route ou ajouter des paramètres à l'URL du
    bridge. On percent-encode (plutôt que rejeter par regex) pour ne pas casser les
    identifiants externes légitimes qui ne sont pas de simples slugs — ex. les event_id
    Google/Outlook peuvent contenir `=`, `+`, `/` (base64-like).
    """
    if not isinstance(value, str) or not value:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_identifier",
                    "message": "Identifiant invalide.",
                }
            },
        )
    return quote(value, safe="")


def _sanitize_bridge_error(detail):
    """Whiteliste le détail d'erreur du bridge avant de le renvoyer au front.

    Le corps brut du bridge peut contenir des informations internes (chemins, traces).
    On ne transmet que `code` + `message` ; le détail complet reste dans les logs serveur
    (finding audit #4).
    """
    if isinstance(detail, dict) and isinstance(detail.get("error"), dict):
        err = detail["error"]
        return {
            "error": {
                "code": err.get("code", "bridge_error"),
                "message": err.get("message", "Erreur du service Providers."),
            }
        }
    return {"error": {"code": "bridge_error", "message": "Erreur du service Providers."}}


class ActiveSelection(BaseModel):
    provider_id: str
    model_id: str


class KeyBody(BaseModel):
    value: str


class AwsBody(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str | None = None


class ReasoningBody(BaseModel):
    effort: str


async def _bridge(method: str, path: str, json: dict | None = None):
    """Appelle le Providers Bridge avec la clé partagée. 503 si injoignable/hors délai."""
    session = await get_session()
    headers = {"X-Bridge-Key": BRIDGE_KEY, "Content-Type": "application/json"}
    try:
        async with session.request(
            method,
            f"{BRIDGE_URL}{path}",
            headers=headers,
            json=json,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=_BRIDGE_TIMEOUT,
        ) as resp:
            body = await resp.json()
            if not resp.ok:
                # Le bridge enveloppe déjà en {"detail": {"error": {...}}} (HTTPException
                # FastAPI côté bridge) : ne PAS re-envelopper une 2e fois, sinon le front
                # reçoit {"detail": {"detail": {"error": ...}}} et isBridgeDown ne matche
                # plus jamais (finding audit #1).
                inner = body.get("detail", body) if isinstance(body, dict) else body
                log.warning("Providers bridge error %s %s -> %s: %s", method, path, resp.status, inner)
                raise HTTPException(status_code=resp.status, detail=_sanitize_bridge_error(inner))
            return body
    except (aiohttp.ClientError, TimeoutError) as exc:
        # TimeoutError couvre aussi asyncio.TimeoutError (alias natif depuis Python 3.11),
        # levé par aiohttp quand `_BRIDGE_TIMEOUT` expire (finding audit #3).
        log.warning("Providers bridge unreachable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "bridge_unreachable",
                    "message": "Le service Providers est injoignable.",
                }
            },
        )


@router.get("/")
async def list_providers(user=Depends(get_admin_user)):
    """Liste les providers Hermes avec leur état (admin-only)."""
    return await _bridge("GET", "/providers")


@router.get("/active")
async def get_active(user=Depends(get_admin_user)):
    """Renvoie le cerveau actif (provider + modèle)."""
    return await _bridge("GET", "/active")


@router.post("/active")
async def set_active(body: ActiveSelection, user=Depends(get_admin_user)):
    """Change le cerveau actif. S'applique aux nouvelles conversations."""
    return await _bridge("POST", "/active", json=body.model_dump())


@router.post("/model-capabilities")
async def model_capabilities(body: ActiveSelection, user=Depends(get_admin_user)):
    """Capacités du modèle (reasoning/vision/outils/contexte) — adapte l'UI par modèle."""
    return await _bridge("POST", "/model-capabilities", json=body.model_dump())


@router.get("/reasoning")
async def get_reasoning(user=Depends(get_admin_user)):
    """Niveau d'intelligence actif (effort de raisonnement global du moteur)."""
    return await _bridge("GET", "/reasoning")


@router.post("/reasoning")
async def set_reasoning(body: ReasoningBody, user=Depends(get_admin_user)):
    """Change le niveau d'intelligence global. S'applique aux nouvelles conversations."""
    return await _bridge("POST", "/reasoning", json=body.model_dump())


@router.put("/{provider_id}/key")
async def set_key(provider_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Enregistre/remplace la clé API d'un provider (valeur jamais renvoyée — FR-006)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("PUT", f"/credentials/{provider_id}", json=body.model_dump())


@router.delete("/{provider_id}/key")
async def delete_key(provider_id: str, user=Depends(get_admin_user)):
    """Retire la clé API d'un provider (bascule le cerveau actif si besoin)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("DELETE", f"/credentials/{provider_id}")


@router.post("/{provider_id}/aws")
async def set_aws(provider_id: str, body: AwsBody, user=Depends(get_admin_user)):
    """Enregistre les credentials AWS (Bedrock) — valeurs jamais renvoyées (FR-006)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("POST", f"/credentials/{provider_id}/aws", json=body.model_dump())


@router.post("/{provider_id}/validate")
async def validate_key(provider_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Teste une clé avant enregistrement (probe réseau)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("POST", f"/credentials/{provider_id}/validate", json=body.model_dump())


@router.post("/{provider_id}/oauth/start")
async def oauth_start(provider_id: str, user=Depends(get_admin_user)):
    """Démarre le flow OAuth d'un provider (le navigateur s'ouvre sur l'hôte)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("POST", f"/oauth/{provider_id}/start")


@router.get("/{provider_id}/oauth/status")
async def oauth_status(provider_id: str, user=Depends(get_admin_user)):
    """État du flow OAuth en cours (running / success / log)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("GET", f"/oauth/{provider_id}/status")


@router.delete("/{provider_id}/oauth")
async def oauth_logout(provider_id: str, user=Depends(get_admin_user)):
    """Déconnecte un compte OAuth (retire les identifiants côté moteur Hermes)."""
    provider_id = _bridge_segment(provider_id)
    return await _bridge("DELETE", f"/oauth/{provider_id}")


# --- Agent Hermes : statut + mise à jour --------------------------------------


@router.get("/hermes/status")
async def hermes_status(user=Depends(get_admin_user)):
    """Vue d'ensemble Hermes (version, cerveau actif, joignabilité)."""
    return await _bridge("GET", "/hermes/status")


@router.post("/hermes/update/check")
async def hermes_update_check(user=Depends(get_admin_user)):
    """Vérifie si une mise à jour Hermes est disponible (sans rien installer)."""
    return await _bridge("POST", "/hermes/update/check")


@router.post("/hermes/update/start")
async def hermes_update_start(user=Depends(get_admin_user)):
    """Lance la mise à jour Hermes (avec backup)."""
    return await _bridge("POST", "/hermes/update/start")


@router.get("/hermes/update/status")
async def hermes_update_status(user=Depends(get_admin_user)):
    """État de la mise à jour en cours."""
    return await _bridge("GET", "/hermes/update/status")
