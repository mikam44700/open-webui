"""Capacités natives : Outils (toolsets) + connexion des toolsets (003) + Compétences (skills)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from .. import hermes_adapter, skills_adapter, tool_connection_adapter, tools_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import (
    CustomSkillsResponse,
    SkillsResponse,
    ToolConnection,
    ToolOAuthStatus,
    ToolsetsResponse,
)
from ..schemas import (
    CapabilityEnabledBody,
    CustomSkillCreateBody,
    ToolDisconnectBody,
    ToolKeyBody,
    ToolProviderBody,
)

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/sources-publiques/status")
def get_sources_publiques_status() -> dict:
    """État réel du palier Agent Reach géré, sans exposer sa plomberie au client."""
    agent_reach_bin = Path("/opt/hermes-agent/venv/bin/agent-reach")
    ytdlp_bin = Path("/opt/hermes-agent/venv/bin/yt-dlp")
    try:
        result = subprocess.run(
            [str(agent_reach_bin), "--version"],
            capture_output=True,
            check=True,
            text=True,
            timeout=3,
        )
        match = re.search(r"\d+(?:\.\d+)+", result.stdout)
        version = match.group(0) if match else "installé"
    except (OSError, subprocess.SubprocessError):
        version = None
    try:
        connected = "sources-publiques" in __import__(
            "open_webui.hermes_bridge.mcp_adapter", fromlist=["_load_mcp_servers"]
        )._load_mcp_servers()
    except Exception:  # noqa: BLE001 — statut best effort, jamais bloquant
        connected = False
    channels = {
        "web": version is not None,
        "youtube": version is not None and ytdlp_bin.is_file(),
        "rss": version is not None,
        "github": version is not None,
    }
    return {
        "installed": version is not None,
        "active": version is not None and connected and all(channels.values()),
        "managed": True,
        "version": version,
        "channels": channels,
    }


def _toolset_unknown(name: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": f"toolset inconnu: {name}"}},
    )


@router.get("/tools")
def get_tools() -> ToolsetsResponse:
    """Liste les toolsets natifs Hermes avec leur état (page Capacités, onglet Outils)."""
    try:
        return ToolsetsResponse(toolsets=tools_adapter.list_toolsets())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.patch("/tools/{toolset_name}")
def patch_tool(toolset_name: str, body: CapabilityEnabledBody) -> dict:
    """Active/désactive un toolset natif. 404 si inconnu."""
    try:
        found = tools_adapter.set_toolset_enabled(toolset_name, body.enabled)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"toolset inconnu: {toolset_name}"}},
        )
    return {"toolset": toolset_name, "enabled": body.enabled}


@router.get("/tools/{toolset_name}/connection")
def get_tool_connection(toolset_name: str) -> ToolConnection:
    """Métadonnées de connexion d'un toolset (champs/fournisseurs, état connecté)."""
    try:
        return tool_connection_adapter.get_connection(toolset_name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.put("/tools/{toolset_name}/key")
def put_tool_key(toolset_name: str, body: ToolKeyBody) -> dict:
    """Enregistre un ou plusieurs champs (env_vars) d'un toolset. Valeurs jamais renvoyées."""
    try:
        saved = tool_connection_adapter.set_key(toolset_name, body.values)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_input", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    state = tool_connection_adapter.get_connection(toolset_name).connected
    return {
        "saved": saved,
        "connection_state": "connected" if state else "connection_required",
    }


@router.post("/tools/{toolset_name}/test")
def post_tool_test(toolset_name: str) -> dict:
    """Teste la connexion d'un toolset (présence des credentials)."""
    try:
        return tool_connection_adapter.test_connection(toolset_name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/tools/{toolset_name}/test-key")
def post_tool_test_key(toolset_name: str, body: ToolKeyBody) -> dict:
    """Teste RÉELLEMENT une clé/URL d'un fournisseur (appel HTTP). Valeurs jamais renvoyées."""
    return tool_connection_adapter.test_key(body.values)


@router.delete("/tools/{toolset_name}/connection")
def delete_tool_connection(toolset_name: str) -> dict:
    """Déconnecte un toolset : retrait des credentials + désactivation (FR-007)."""
    try:
        return tool_connection_adapter.disconnect(toolset_name)
    except KeyError:
        raise _toolset_unknown(toolset_name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/tools/{toolset_name}/disconnect-provider")
def post_tool_disconnect_provider(toolset_name: str, body: ToolDisconnectBody) -> dict:
    """Déconnecte UN fournisseur : efface seulement ses champs, sans désactiver l'outil."""
    try:
        return tool_connection_adapter.disconnect_keys(toolset_name, body.keys)
    except KeyError:
        raise _toolset_unknown(toolset_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_input", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/tools/{toolset_name}/activate-provider")
def post_tool_activate_provider(toolset_name: str, body: ToolProviderBody) -> dict:
    """Choisit explicitement le fournisseur utilisé par un toolset connecté."""
    if toolset_name != "web":
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_input", "message": "choix réservé à la recherche web"}},
        )
    try:
        backend = tool_connection_adapter.activate_web_provider(body.slug)
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_input", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"active": body.slug, "backend": backend}


@router.post("/tools/{toolset_name}/oauth/start")
def post_tool_oauth_start(toolset_name: str) -> dict:
    """Démarre un flux OAuth headless pour un toolset (Spotify, xAI)."""
    try:
        tool_connection_adapter.start_oauth(toolset_name)
    except tool_connection_adapter.OAuthUnsupported:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "invalid_input",
                    "message": f"aucun flux OAuth pour le toolset {toolset_name}",
                }
            },
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"started": True}


@router.get("/tools/{toolset_name}/oauth/status")
def get_tool_oauth_status(toolset_name: str) -> ToolOAuthStatus:
    """État du flux OAuth d'un toolset (+ URL d'autorisation extraite du log)."""
    raw = tool_connection_adapter.oauth_status(toolset_name)
    return ToolOAuthStatus(**raw)


@router.get("/skills")
def get_skills() -> SkillsResponse:
    """Liste les compétences natives Hermes avec leur état (page Capacités, onglet Compétences)."""
    try:
        return SkillsResponse(skills=skills_adapter.list_skills())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.patch("/skills/{skill_name}")
def patch_skill(skill_name: str, body: CapabilityEnabledBody) -> dict:
    """Active/désactive une compétence native. 404 si inconnue."""
    try:
        found = skills_adapter.set_skill_enabled(skill_name, body.enabled)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"compétence inconnue: {skill_name}"}},
        )
    return {"skill": skill_name, "enabled": body.enabled}


# --- Compétences « maison » (sur mesure, créées par le client) ----------------


@router.get("/custom-skills")
def get_custom_skills() -> CustomSkillsResponse:
    """Liste les compétences maison du client (page Compétences de l'Espace de travail)."""
    return CustomSkillsResponse(skills=skills_adapter.list_custom_skills())


# IMPORTANT : ces 2 routes de corbeille doivent être déclarées AVANT ``/custom-skills/{name}``
# (plus bas) — FastAPI/Starlette essaie les routes dans l'ordre de déclaration, donc un
# ``GET /custom-skills/trash`` matcherait sinon d'abord ``/custom-skills/{name}`` avec
# ``name="trash"`` (jamais atteint la vraie route de corbeille).


@router.get("/custom-skills/trash")
def get_custom_skills_trash() -> list[dict]:
    """Corbeille des compétences maison supprimées (récupérables) — miroir de la corbeille du coffre."""
    return skills_adapter.list_custom_skills_trash()


@router.post("/custom-skills/trash/{ref}/restore")
def restore_custom_skill(ref: str) -> dict:
    """Restaure une compétence maison depuis la corbeille (fait suite à ``DELETE /custom-skills/{name}``).

    404 si la réf. de corbeille est inconnue, 409 si une compétence porte déjà ce nom (jamais
    d'écrasement silencieux — même règle de non-destruction que la corbeille du coffre).
    """
    try:
        return skills_adapter.restore_custom_skill(ref)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"réf. de corbeille inconnue: {ref}"}},
        )
    except skills_adapter.RestoreConflict:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "exists", "message": "une compétence porte déjà ce nom"}},
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_ref", "message": "réf. de corbeille invalide"}},
        )


@router.get("/custom-skills/{name}")
def get_custom_skill_detail(name: str) -> dict:
    """Contenu complet d'une compétence maison (libellé, description, catégorie, procédure). 404 si inconnue."""
    res = skills_adapter.get_custom_skill(name)
    if res is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"compétence inconnue: {name}"}},
        )
    return res


@router.post("/custom-skills")
def create_custom_skill(body: CustomSkillCreateBody) -> dict:
    """Crée une compétence maison. 409 si le nom existe déjà, 422 si le nom est vide."""
    if not body.label.strip():
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_input", "message": "le nom de la compétence est requis"}},
        )
    res = skills_adapter.create_custom_skill(
        body.label, body.description, body.instructions, body.category
    )
    if not res.get("ok"):
        if res.get("error") == "exists":
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "exists", "message": "une compétence porte déjà ce nom"}},
            )
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "create_failed", "message": res.get("error", "création impossible")}},
        )
    return {"name": res.get("name")}


@router.delete("/custom-skills/{name}")
def delete_custom_skill(name: str) -> dict:
    """Supprime une compétence maison. 404 si inconnue."""
    res = skills_adapter.delete_custom_skill(name)
    if not res.get("found"):
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"compétence inconnue: {name}"}},
        )
    return {"deleted": name}
