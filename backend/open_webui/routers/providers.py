"""Router /api/v1/providers — gestion des cerveaux Hermes (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI. Le bridge pilote Hermes (`hermes config set`).

Voir specs/001-providers-page/contracts/openwebui-providers-api.md
"""

from __future__ import annotations

import logging
import os

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.auth import get_admin_user
from open_webui.utils.session_pool import get_session

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://host.docker.internal:8650").rstrip("/")
BRIDGE_KEY = os.getenv("BRIDGE_KEY", "")

log = logging.getLogger(__name__)
router = APIRouter()


class ActiveSelection(BaseModel):
    provider_id: str
    model_id: str


class KeyBody(BaseModel):
    value: str


async def _bridge(method: str, path: str, json: dict | None = None):
    """Appelle le Providers Bridge avec la clé partagée. 503 si injoignable."""
    session = await get_session()
    headers = {"X-Bridge-Key": BRIDGE_KEY, "Content-Type": "application/json"}
    try:
        async with session.request(
            method,
            f"{BRIDGE_URL}{path}",
            headers=headers,
            json=json,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as resp:
            body = await resp.json()
            if not resp.ok:
                raise HTTPException(status_code=resp.status, detail=body)
            return body
    except aiohttp.ClientError as exc:
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


@router.put("/{provider_id}/key")
async def set_key(provider_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Enregistre/remplace la clé API d'un provider (valeur jamais renvoyée — FR-006)."""
    return await _bridge("PUT", f"/credentials/{provider_id}", json=body.model_dump())


@router.post("/{provider_id}/validate")
async def validate_key(provider_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Teste une clé avant enregistrement (probe réseau)."""
    return await _bridge("POST", f"/credentials/{provider_id}/validate", json=body.model_dump())
