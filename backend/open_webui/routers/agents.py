"""Router /api/agents — agents (profils Hermes), page Agents (ex-onglet Modèles).

Admin-only. Proxifie vers le Providers Bridge en réutilisant le helper ``_bridge`` du router
providers. Hermes reste la source de vérité : un agent = un profil Hermes.

- Liste / création : GET /, POST /
- Activation (agent « de garde ») : POST /active
- Suppression : DELETE /{name}
- Mission (SOUL.md) : GET/PUT /{name}/soul
- Description : PUT /{name}/description
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    soul: str = ""
    avatar: str | None = None  # visage de l'agent (profile.yaml) — sinon repli sur l'initiale


class ActiveBody(BaseModel):
    name: str


class SoulBody(BaseModel):
    content: str


class DescriptionBody(BaseModel):
    description: str


class ToggleToolBody(BaseModel):
    name: str
    enabled: bool


@router.get("/")
async def list_agents(user=Depends(get_admin_user)):
    """Liste les agents (profils Hermes) avec leur état (admin-only)."""
    return await _bridge("GET", "/agents")


@router.post("/")
async def create_agent(body: AgentCreate, user=Depends(get_admin_user)):
    """Crée un agent (profil Hermes, clone la config du profil actif)."""
    return await _bridge("POST", "/agents", json=body.model_dump())


@router.post("/active")
async def activate_agent(body: ActiveBody, user=Depends(get_admin_user)):
    """Bascule l'agent « de garde »."""
    return await _bridge("POST", "/agents/active", json=body.model_dump())


@router.delete("/{name}")
async def delete_agent(name: str, user=Depends(get_admin_user)):
    """Supprime un agent (l'agent par défaut est protégé)."""
    return await _bridge("DELETE", f"/agents/{name}")


@router.get("/{name}/soul")
async def get_agent_soul(name: str, user=Depends(get_admin_user)):
    """Lit la mission (SOUL.md) d'un agent."""
    return await _bridge("GET", f"/agents/{name}/soul")


@router.put("/{name}/soul")
async def set_agent_soul(name: str, body: SoulBody, user=Depends(get_admin_user)):
    """Écrit la mission (SOUL.md) d'un agent."""
    return await _bridge("PUT", f"/agents/{name}/soul", json=body.model_dump())


@router.put("/{name}/description")
async def set_agent_description(name: str, body: DescriptionBody, user=Depends(get_admin_user)):
    """Met à jour la description d'un agent."""
    return await _bridge("PUT", f"/agents/{name}/description", json=body.model_dump())


@router.get("/{name}/tools")
async def get_agent_tools(name: str, user=Depends(get_admin_user)):
    """Périmètre d'outils d'un agent : compétences + MCP avec leur état pour cet agent."""
    return await _bridge("GET", f"/agents/{name}/tools")


@router.post("/{name}/tools/skill")
async def set_agent_skill(name: str, body: ToggleToolBody, user=Depends(get_admin_user)):
    """Active/désactive une compétence pour cet agent."""
    return await _bridge("POST", f"/agents/{name}/tools/skill", json=body.model_dump())


@router.post("/{name}/tools/mcp")
async def set_agent_mcp(name: str, body: ToggleToolBody, user=Depends(get_admin_user)):
    """Active/désactive un connecteur MCP pour cet agent."""
    return await _bridge("POST", f"/agents/{name}/tools/mcp", json=body.model_dump())
