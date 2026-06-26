"""Router /api/v1/gateway — supervision du gateway Hermes + plateformes de messagerie.

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité (tokens ~/.hermes/.env, activation config.yaml, état du gateway).

Page « Gateway » d'Agent OS — portage de la page Gateway de Hermes Desktop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class MessagingUpdate(BaseModel):
    env: dict[str, str] | None = None
    clear_env: list[str] | None = None
    enabled: bool | None = None


@router.get("/status")
async def gateway_status(user=Depends(get_admin_user)):
    """État du gateway : tourne ou non, port de l'API server, présence de la clé API."""
    return await _bridge("GET", "/gateway/status")


@router.get("/platforms")
async def list_platforms(user=Depends(get_admin_user)):
    """Liste les plateformes de messagerie avec leur état."""
    return await _bridge("GET", "/gateway/platforms")


@router.post("/platforms/{platform_id}")
async def update_platform(platform_id: str, body: MessagingUpdate, user=Depends(get_admin_user)):
    """Met à jour une plateforme : tokens (.env) et/ou activation (config.yaml)."""
    return await _bridge("POST", f"/gateway/platforms/{platform_id}", json=body.model_dump(exclude_none=True))


@router.post("/platforms/{platform_id}/test")
async def test_platform(platform_id: str, user=Depends(get_admin_user)):
    """Test « soft » d'une plateforme (présence des clés requises + état)."""
    return await _bridge("POST", f"/gateway/platforms/{platform_id}/test")


@router.post("/api-key/generate")
async def generate_api_key(user=Depends(get_admin_user)):
    """(Re)génère la clé API du serveur Hermes (API_SERVER_KEY)."""
    return await _bridge("POST", "/gateway/api-key/generate")


@router.post("/restart")
async def restart_gateway(user=Depends(get_admin_user)):
    """Redémarre le gateway (start/stop = supervision launchd/systemd)."""
    return await _bridge("POST", "/gateway/restart")
