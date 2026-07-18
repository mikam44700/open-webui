"""Connecteurs MCP (feature 002)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import hermes_adapter, mcp_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import CatalogResponse, ConnectorsResponse
from ..schemas import McpConnectorCreate, McpEnabledBody, McpKeyBody

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/mcp/connectors")
def get_mcp_connectors() -> ConnectorsResponse:
    """Liste les connecteurs MCP installés avec leur état (contrat bridge-mcp-api §GET /mcp/connectors)."""
    try:
        return ConnectorsResponse(connectors=mcp_adapter.list_connectors())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/mcp/catalog")
def get_mcp_catalog() -> CatalogResponse:
    """Liste le catalogue MCP de Hermes (connecteurs prêts à installer)."""
    try:
        return CatalogResponse(entries=mcp_adapter.list_catalog())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/mcp/connectors")
def create_mcp_connector(body: McpConnectorCreate) -> dict:
    """Installe un connecteur depuis le catalogue (asynchrone) ou en custom (US5)."""
    if body.from_catalog:
        try:
            mcp_adapter.install_from_catalog(body.from_catalog)
        except hermes_adapter.HermesUnavailable as exc:
            raise hermes_unavailable(exc)
        return {"started": True, "connector_id": body.from_catalog}
    # Installation depuis le registre distant (remote OAuth, ou stdio avec clés/args)
    if body.from_registry:
        try:
            connector = mcp_adapter.install_from_registry(body.from_registry, body.fields)
        except mcp_adapter.NameConflict as exc:
            raise HTTPException(
                status_code=409, detail={"error": {"code": "name_conflict", "message": str(exc)}}
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "invalid_connector", "message": str(exc)}},
            )
        except hermes_adapter.HermesUnavailable as exc:
            raise hermes_unavailable(exc)
        return {"connector": connector.model_dump()}
    # Connecteur custom (US5)
    if body.name and body.transport:
        try:
            connector = mcp_adapter.add_custom(
                body.name,
                body.transport,
                url=body.url,
                command=body.command,
                args=body.args,
                env=body.env,
                auth_type=body.auth_type or "none",
            )
        except mcp_adapter.NameConflict as exc:
            raise HTTPException(
                status_code=409, detail={"error": {"code": "name_conflict", "message": str(exc)}}
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "invalid_connector", "message": str(exc)}},
            )
        except hermes_adapter.HermesUnavailable as exc:
            raise hermes_unavailable(exc)
        return {"connector": connector.model_dump()}
    raise HTTPException(
        status_code=422,
        detail={"error": {"code": "invalid_connector", "message": "from_catalog ou (name + transport) requis"}},
    )


@router.get("/mcp/connectors/{connector_id}/install/status")
def mcp_install_status(connector_id: str) -> dict:
    """État de l'installation en cours (running / success / log)."""
    return mcp_adapter.install_status(connector_id)


@router.put("/mcp/connectors/{connector_id}/key")
def put_mcp_key(connector_id: str, body: McpKeyBody) -> dict[str, str]:
    """Enregistre/remplace la clé API d'un connecteur. Valeur jamais renvoyée (FR-011)."""
    try:
        mcp_adapter.set_key(connector_id, body.value)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"connector_id": connector_id, "secret_state": "present"}


@router.post("/mcp/connectors/{connector_id}/oauth/start")
def start_mcp_oauth(connector_id: str) -> dict[str, bool]:
    """Démarre le flux OAuth d'un connecteur (navigateur ouvert sur l'hôte)."""
    try:
        mcp_adapter.start_oauth(connector_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"started": True}


@router.get("/mcp/connectors/{connector_id}/oauth/status")
def mcp_oauth_status(connector_id: str) -> dict:
    """État du flux OAuth (running / success / auth_url / log)."""
    return mcp_adapter.oauth_status(connector_id)


@router.patch("/mcp/connectors/{connector_id}")
def patch_mcp_connector(connector_id: str, body: McpEnabledBody) -> dict:
    """Active/désactive un connecteur. 404 si inconnu."""
    try:
        found = mcp_adapter.set_enabled(connector_id, body.enabled)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"connecteur inconnu: {connector_id}"}},
        )
    return {"connector_id": connector_id, "enabled": body.enabled}


@router.post("/mcp/connectors/{connector_id}/test")
def test_mcp_connector(connector_id: str) -> dict:
    """Teste la connexion d'un connecteur (probe réelle, timeout borné)."""
    try:
        return mcp_adapter.test_connection(connector_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/mcp/connectors/{connector_id}")
def delete_mcp_connector(connector_id: str) -> dict:
    """Supprime un connecteur (entrée config + tokens). 404 si introuvable."""
    try:
        removed = mcp_adapter.remove_connector(connector_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"connecteur inconnu: {connector_id}"}},
        )
    return {"deleted": connector_id}
