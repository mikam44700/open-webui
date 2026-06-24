"""Router /api/capabilities — capacités natives de Hermes (Outils + Compétences).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité unique des toolsets et skills (cf. page Capacités).

- Outils (toolsets natifs Hermes : Web Search, Terminal, Browser, ...) : GET /tools, PATCH /tools/{name}
- Compétences (skills Hermes) : GET /skills, PATCH /skills/{name}

Les connecteurs MCP, troisième volet de la page Capacités, restent servis par /api/v1/connectors.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class EnabledBody(BaseModel):
    enabled: bool


@router.get("/tools")
async def list_tools(user=Depends(get_admin_user)):
    """Liste les toolsets natifs Hermes avec leur état (admin-only)."""
    return await _bridge("GET", "/tools")


@router.patch("/tools/{toolset_name}")
async def set_tool_enabled(toolset_name: str, body: EnabledBody, user=Depends(get_admin_user)):
    """Active/désactive un toolset natif Hermes."""
    return await _bridge("PATCH", f"/tools/{toolset_name}", json=body.model_dump())


@router.get("/skills")
async def list_skills(user=Depends(get_admin_user)):
    """Liste les compétences natives Hermes avec leur état (admin-only)."""
    return await _bridge("GET", "/skills")


@router.patch("/skills/{skill_name}")
async def set_skill_enabled(skill_name: str, body: EnabledBody, user=Depends(get_admin_user)):
    """Active/désactive une compétence native Hermes."""
    return await _bridge("PATCH", f"/skills/{skill_name}", json=body.model_dump())
