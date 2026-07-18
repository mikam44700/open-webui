"""Agents : profils Hermes (page Agents)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from .. import hermes_adapter, mcp_adapter, profiles_adapter, skills_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import AgentsResponse, AgentToolsResponse
from ..schemas import (
    AgentActiveBody,
    AgentCreateBody,
    AvatarBody,
    DescriptionBody,
    SoulBody,
    ToggleToolBody,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _resync_roster_safe() -> None:
    """Resynchronise le bloc « équipe » des orchestrateurs après un changement d'agents.

    Best-effort : une erreur ici ne doit jamais faire échouer l'opération principale
    (création/suppression d'agent). On se contente de la journaliser.
    """
    try:
        profiles_adapter.sync_orchestrator_roster()
    except Exception:  # noqa: BLE001 — effet de bord non bloquant
        logger.warning("resync du roster orchestrateur impossible", exc_info=True)


def _agent_home_or_404(name: str):
    """Dossier du profil de l'agent, ou 404 s'il n'existe pas."""
    home = profiles_adapter.profile_home(name)
    if not home.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    return home


@router.get("/agents")
def get_agents() -> AgentsResponse:
    """Liste les agents (profils Hermes) avec leur état (page Agents)."""
    try:
        return AgentsResponse(agents=profiles_adapter.list_agents())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/agents")
def create_agent(body: AgentCreateBody) -> dict:
    """Crée un agent (profil Hermes, clone la config du profil actif). 409 si le nom existe."""
    try:
        res = profiles_adapter.create_agent(body.name, body.description, body.soul, body.avatar)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not res.get("ok"):
        if res.get("error") == "exists":
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "exists", "message": "un agent porte déjà ce nom"}},
            )
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "create_failed", "message": res.get("error", "création impossible")}},
        )
    _resync_roster_safe()  # l'orchestrateur découvre le nouvel agent
    return {"name": res.get("name")}


@router.post("/agents/sync-roster")
def sync_roster() -> dict:
    """Réinjecte la liste des agents dans le SOUL des orchestrateurs (resync manuel/au boot)."""
    try:
        return profiles_adapter.sync_orchestrator_roster()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/agents/active")
def activate_agent(body: AgentActiveBody) -> dict:
    """Bascule l'agent « de garde ». 404 si l'agent est inconnu."""
    try:
        found = profiles_adapter.set_active_agent(body.name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {body.name}"}},
        )
    return {"active": body.name}


@router.delete("/agents/{name}")
def delete_agent(name: str) -> dict:
    """Supprime un agent. 404 si inconnu, 400 si c'est l'agent par défaut (protégé)."""
    try:
        res = profiles_adapter.delete_agent(name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not res.get("found"):
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    if not res.get("ok") and res.get("error") == "default":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "default", "message": "l'agent par défaut ne peut pas être supprimé"}},
        )
    if not res.get("ok") and res.get("error") == "active":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "active",
                    "message": "impossible de supprimer l'agent de garde actuel : changez d'agent actif avant",
                }
            },
        )
    _resync_roster_safe()  # l'orchestrateur oublie l'agent supprimé
    return {"deleted": name}


@router.get("/agents/{name}/soul")
def get_agent_soul(name: str) -> dict:
    """Lit la mission (SOUL.md) d'un agent. 404 si inconnu."""
    try:
        content = profiles_adapter.get_agent_soul(name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    return {"name": name, "content": content}


@router.put("/agents/{name}/soul")
def set_agent_soul(name: str, body: SoulBody) -> dict:
    """Écrit la mission (SOUL.md) d'un agent. 404 si inconnu."""
    try:
        found = profiles_adapter.set_agent_soul(name, body.content)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    _resync_roster_safe()  # le rôle a changé : l'orchestrateur le reflète
    return {"name": name, "ok": True}


@router.get("/agents/{name}/tools")
def get_agent_tools(name: str) -> AgentToolsResponse:
    """Périmètre d'outils d'un agent : compétences + MCP avec leur état PAR AGENT. 404 si inconnu."""
    home = _agent_home_or_404(name)
    try:
        return AgentToolsResponse(
            skills=skills_adapter.list_skills(hermes_home=home),
            mcps=mcp_adapter.list_connectors(hermes_home=home),
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/agents/{name}/tools/skill")
def set_agent_skill(name: str, body: ToggleToolBody) -> dict:
    """Active/désactive une compétence POUR CET AGENT (skills.disabled de son config.yaml)."""
    home = _agent_home_or_404(name)
    try:
        found = skills_adapter.set_skill_enabled(body.name, body.enabled, hermes_home=home)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"compétence inconnue: {body.name}"}},
        )
    return {"ok": True}


@router.post("/agents/{name}/tools/mcp")
def set_agent_mcp(name: str, body: ToggleToolBody) -> dict:
    """Active/désactive un connecteur MCP POUR CET AGENT (enabled de son config.yaml)."""
    home = _agent_home_or_404(name)
    try:
        found = mcp_adapter.set_enabled(body.name, body.enabled, hermes_home=home)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"connecteur inconnu: {body.name}"}},
        )
    return {"ok": True}


@router.put("/agents/{name}/description")
def set_agent_description(name: str, body: DescriptionBody) -> dict:
    """Met à jour la description (profile.yaml) d'un agent. 404 si inconnu."""
    try:
        found = profiles_adapter.set_agent_description(name, body.description)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    _resync_roster_safe()  # le rôle affiché dans le roster a changé
    return {"name": name, "ok": True}


@router.put("/agents/{name}/avatar")
def set_agent_avatar(name: str, body: AvatarBody) -> dict:
    """Met à jour l'avatar (profile.yaml) d'un agent. 404 si inconnu. ``avatar: null`` désélectionne."""
    try:
        found = profiles_adapter.set_agent_avatar(name, body.avatar)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"agent inconnu: {name}"}},
        )
    return {"name": name, "avatar": body.avatar, "ok": True}
