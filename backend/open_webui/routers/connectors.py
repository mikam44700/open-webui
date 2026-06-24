"""Router /api/connectors — gestion des connecteurs MCP de Hermes (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité unique des MCP (cf. specs/002-connecteurs-mcp).

Voir specs/002-connecteurs-mcp/contracts/openwebui-connectors-api.md
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class ConnectorCreate(BaseModel):
    from_catalog: str | None = None
    name: str | None = None
    transport: str | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    auth_type: str | None = None


class KeyBody(BaseModel):
    value: str


@router.get("/")
async def list_connectors(user=Depends(get_admin_user)):
    """Liste les connecteurs MCP avec leur état (admin-only)."""
    return await _bridge("GET", "/mcp/connectors")


@router.get("/catalog")
async def get_catalog(user=Depends(get_admin_user)):
    """Catalogue des connecteurs MCP prêts à installer."""
    return await _bridge("GET", "/mcp/catalog")


@router.post("/")
async def create_connector(body: ConnectorCreate, user=Depends(get_admin_user)):
    """Installe un connecteur (catalogue, asynchrone) ou en custom (US5)."""
    return await _bridge("POST", "/mcp/connectors", json=body.model_dump(exclude_none=True))


@router.get("/{connector_id}/install/status")
async def install_status(connector_id: str, user=Depends(get_admin_user)):
    """État de l'installation en cours."""
    return await _bridge("GET", f"/mcp/connectors/{connector_id}/install/status")


@router.put("/{connector_id}/key")
async def set_key(connector_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Enregistre la clé API d'un connecteur (valeur jamais renvoyée — FR-011)."""
    return await _bridge("PUT", f"/mcp/connectors/{connector_id}/key", json=body.model_dump())


@router.post("/{connector_id}/oauth/start")
async def oauth_start(connector_id: str, user=Depends(get_admin_user)):
    """Démarre le flux OAuth d'un connecteur (le navigateur s'ouvre sur l'hôte)."""
    return await _bridge("POST", f"/mcp/connectors/{connector_id}/oauth/start")


@router.get("/{connector_id}/oauth/status")
async def oauth_status(connector_id: str, user=Depends(get_admin_user)):
    """État du flux OAuth en cours (running / success / auth_url / log)."""
    return await _bridge("GET", f"/mcp/connectors/{connector_id}/oauth/status")
