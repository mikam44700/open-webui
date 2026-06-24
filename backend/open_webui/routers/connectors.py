"""Router /api/connectors — gestion des connecteurs MCP de Hermes (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité unique des MCP (cf. specs/002-connecteurs-mcp).

Voir specs/002-connecteurs-mcp/contracts/openwebui-connectors-api.md
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_connectors(user=Depends(get_admin_user)):
    """Liste les connecteurs MCP avec leur état (admin-only)."""
    return await _bridge("GET", "/mcp/connectors")
