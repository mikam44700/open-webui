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


@router.post("/tools/{toolset_name}/test-key")
async def test_tool_key(toolset_name: str, body: ToolKeyBody, user=Depends(get_admin_user)):
    """Teste RÉELLEMENT une clé/URL d'un fournisseur (appel HTTP côté bridge)."""
    return await _bridge("POST", f"/tools/{toolset_name}/test-key", json=body.model_dump())


@router.delete("/tools/{toolset_name}/connection")
async def disconnect_tool(toolset_name: str, user=Depends(get_admin_user)):
    """Déconnecte un toolset (retrait des identifiants + désactivation)."""
    return await _bridge("DELETE", f"/tools/{toolset_name}/connection")


class ToolDisconnectBody(BaseModel):
    keys: list[str]


@router.post("/tools/{toolset_name}/disconnect-provider")
async def disconnect_tool_provider(
    toolset_name: str, body: ToolDisconnectBody, user=Depends(get_admin_user)
):
    """Déconnecte UN seul fournisseur (efface ses champs, sans désactiver l'outil entier)."""
    return await _bridge(
        "POST", f"/tools/{toolset_name}/disconnect-provider", json=body.model_dump()
    )


@router.post("/tools/{toolset_name}/oauth/start")
async def start_tool_oauth(toolset_name: str, user=Depends(get_admin_user)):
    """Démarre le flux OAuth d'un toolset (Spotify, xAI)."""
    return await _bridge("POST", f"/tools/{toolset_name}/oauth/start")


@router.get("/tools/{toolset_name}/oauth/status")
async def get_tool_oauth_status(toolset_name: str, user=Depends(get_admin_user)):
    """État du flux OAuth d'un toolset."""
    return await _bridge("GET", f"/tools/{toolset_name}/oauth/status")


# --- Crawl4AI : installation à la demande (lecture web approfondie) ----------


@router.get("/crawl4ai/status")
async def crawl4ai_status(user=Depends(get_admin_user)):
    """État de Crawl4AI (conteneur Docker + connecteur MCP enregistré dans Hermes)."""
    return await _bridge("GET", "/crawl4ai/status")


@router.post("/crawl4ai/install")
async def crawl4ai_install(user=Depends(get_admin_user)):
    """Installe Crawl4AI : démarre le conteneur + enregistre le connecteur MCP."""
    return await _bridge("POST", "/crawl4ai/install")


@router.post("/crawl4ai/uninstall")
async def crawl4ai_uninstall(user=Depends(get_admin_user)):
    """Désinstalle Crawl4AI : retire le connecteur MCP + arrête le conteneur et l'image."""
    return await _bridge("POST", "/crawl4ai/uninstall")


@router.post("/crawl4ai/update/check")
async def crawl4ai_update_check(user=Depends(get_admin_user)):
    """Une mise à jour Crawl4AI est-elle disponible ? (comparaison de version, sans réseau)."""
    return await _bridge("POST", "/crawl4ai/update/check")


@router.post("/crawl4ai/update/start")
async def crawl4ai_update_start(user=Depends(get_admin_user)):
    """Lance la mise à jour Crawl4AI en arrière-plan (suivie via update/status)."""
    return await _bridge("POST", "/crawl4ai/update/start")


@router.get("/crawl4ai/update/status")
async def crawl4ai_update_status(user=Depends(get_admin_user)):
    """Progression de la mise à jour Crawl4AI."""
    return await _bridge("GET", "/crawl4ai/update/status")


@router.get("/skills")
async def list_skills(user=Depends(get_admin_user)):
    """Liste les compétences natives Hermes avec leur état (admin-only)."""
    return await _bridge("GET", "/skills")


@router.patch("/skills/{skill_name}")
async def set_skill_enabled(skill_name: str, body: EnabledBody, user=Depends(get_admin_user)):
    """Active/désactive une compétence native Hermes."""
    return await _bridge("PATCH", f"/skills/{skill_name}", json=body.model_dump())


# --- Compétences « maison » (sur mesure, créées par le client) ----------------


class CustomSkillBody(BaseModel):
    label: str
    description: str = ""
    instructions: str = ""
    category: str = "Autres"


@router.get("/custom-skills")
async def list_custom_skills(user=Depends(get_admin_user)):
    """Liste les compétences maison du client (admin-only)."""
    return await _bridge("GET", "/custom-skills")


@router.post("/custom-skills")
async def create_custom_skill(body: CustomSkillBody, user=Depends(get_admin_user)):
    """Crée une compétence maison."""
    return await _bridge("POST", "/custom-skills", json=body.model_dump())


@router.get("/custom-skills/{skill_name}")
async def get_custom_skill(skill_name: str, user=Depends(get_admin_user)):
    """Contenu complet d'une compétence maison (procédure incluse)."""
    return await _bridge("GET", f"/custom-skills/{skill_name}")


@router.delete("/custom-skills/{skill_name}")
async def delete_custom_skill(skill_name: str, user=Depends(get_admin_user)):
    """Supprime une compétence maison."""
    return await _bridge("DELETE", f"/custom-skills/{skill_name}")
