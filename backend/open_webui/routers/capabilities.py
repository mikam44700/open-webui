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


# --- Connexion des toolsets (feature 003) ------------------------------------


class ToolKeyBody(BaseModel):
    values: dict[str, str]


@router.get("/tools/{toolset_name}/connection")
async def get_tool_connection(toolset_name: str, user=Depends(get_admin_user)):
    """Métadonnées de connexion d'un toolset (champs/fournisseurs, état)."""
    return await _bridge("GET", f"/tools/{toolset_name}/connection")


@router.put("/tools/{toolset_name}/key")
async def set_tool_key(toolset_name: str, body: ToolKeyBody, user=Depends(get_admin_user)):
    """Enregistre les identifiants d'un toolset (valeurs jamais renvoyées)."""
    return await _bridge("PUT", f"/tools/{toolset_name}/key", json=body.model_dump())


@router.post("/tools/{toolset_name}/test")
async def test_tool_connection(toolset_name: str, user=Depends(get_admin_user)):
    """Teste la connexion d'un toolset."""
    return await _bridge("POST", f"/tools/{toolset_name}/test")


@router.delete("/tools/{toolset_name}/connection")
async def disconnect_tool(toolset_name: str, user=Depends(get_admin_user)):
    """Déconnecte un toolset (retrait des identifiants + désactivation)."""
    return await _bridge("DELETE", f"/tools/{toolset_name}/connection")


@router.post("/tools/{toolset_name}/oauth/start")
async def start_tool_oauth(toolset_name: str, user=Depends(get_admin_user)):
    """Démarre le flux OAuth d'un toolset (Spotify, xAI)."""
    return await _bridge("POST", f"/tools/{toolset_name}/oauth/start")


@router.get("/tools/{toolset_name}/oauth/status")
async def get_tool_oauth_status(toolset_name: str, user=Depends(get_admin_user)):
    """État du flux OAuth d'un toolset."""
    return await _bridge("GET", f"/tools/{toolset_name}/oauth/status")


@router.get("/skills")
async def list_skills(user=Depends(get_admin_user)):
    """Liste les compétences natives Hermes avec leur état (admin-only)."""
    return await _bridge("GET", "/skills")


@router.patch("/skills/{skill_name}")
async def set_skill_enabled(skill_name: str, body: EnabledBody, user=Depends(get_admin_user)):
    """Active/désactive une compétence native Hermes."""
    return await _bridge("PATCH", f"/skills/{skill_name}", json=body.model_dump())
