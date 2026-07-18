"""Router Providers — gestion des cerveaux Hermes depuis le fork, sans bridge.

Adapté de la v1 (agent-os) : le bridge tournait dans un service séparé parce
qu'OpenWebUI était dans Docker. Ici le backend tourne sur l'hôte, donc le router
appelle directement ``open_webui.hermes_bridge.hermes_adapter`` (paquet porté
tel quel depuis la v1). Les chemins collent au client front v1
(``src/lib/apis/providers``). Admin-only. Les valeurs de clés et tokens ne sont
jamais lus ni renvoyés.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from open_webui.hermes_bridge import hermes_adapter
from open_webui.hermes_bridge.models import ActiveSelection, ProvidersResponse
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel

router = APIRouter()


class CredentialBody(BaseModel):
    value: str


class AwsCredentialBody(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str | None = None


class ReasoningBody(BaseModel):
    effort: str


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": {"code": "hermes_unavailable", "message": str(exc)}},
    )


def _unknown_provider(provider_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "unknown_provider", "message": f"provider inconnu: {provider_id}"}},
    )


@router.get("/", response_model=ProvidersResponse)
def get_providers(user=Depends(get_admin_user)):
    try:
        return ProvidersResponse(providers=hermes_adapter.list_providers())
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)


@router.get("/active")
def get_active(user=Depends(get_admin_user)):
    try:
        return hermes_adapter.get_active()
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)


@router.post("/active")
def set_active(selection: ActiveSelection, user=Depends(get_admin_user)) -> dict:
    try:
        applied, team_brain_sync = hermes_adapter.activate_provider(
            selection.provider_id, selection.model_id
        )
    except hermes_adapter.UnknownProvider as exc:
        raise _unknown_provider(exc.provider_id)
    except hermes_adapter.ProviderNotConfigured as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "not_configured", "message": f"provider non configuré: {exc.provider_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {
        "provider_id": applied.provider_id,
        "model_id": applied.model_id,
        "applies_to": "new_conversations",
        "team_brain_sync": team_brain_sync,
    }


@router.post("/model-capabilities")
def model_capabilities(selection: ActiveSelection, user=Depends(get_admin_user)) -> dict:
    return hermes_adapter.get_model_capabilities(selection.provider_id, selection.model_id)


@router.get("/reasoning")
def get_reasoning(user=Depends(get_admin_user)) -> dict:
    try:
        return {"effort": hermes_adapter.get_reasoning() or "medium"}
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)


@router.post("/reasoning")
def set_reasoning(body: ReasoningBody, user=Depends(get_admin_user)) -> dict:
    effort = (body.effort or "").strip().lower()
    if effort not in hermes_adapter.VALID_REASONING_EFFORTS:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_effort", "message": f"niveau inconnu: {body.effort}"}},
        )
    try:
        hermes_adapter.set_reasoning(effort)
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {"effort": effort, "applies_to": "new_conversations"}


@router.put("/{provider_id}/key")
def put_key(provider_id: str, body: CredentialBody, user=Depends(get_admin_user)) -> dict:
    """Enregistre/remplace une clé (écrite dans ~/.hermes/.env, jamais renvoyée)."""
    try:
        result = hermes_adapter.set_key_and_maybe_activate(provider_id, body.value)
    except KeyError:
        raise _unknown_provider(provider_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "no_api_key", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    response: dict = {"provider_id": provider_id, "state": "present"}
    if result.get("activated"):
        response["activated"] = result["activated"]
    return response


@router.delete("/{provider_id}/key")
def delete_key(provider_id: str, user=Depends(get_admin_user)) -> dict:
    try:
        result = hermes_adapter.remove_key(provider_id)
    except KeyError:
        raise _unknown_provider(provider_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "no_api_key", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    response: dict = {"provider_id": provider_id, "state": "removed"}
    if result.get("switched"):
        response["switched"] = result["switched"]
    return response


@router.post("/{provider_id}/aws")
def put_aws(provider_id: str, body: AwsCredentialBody, user=Depends(get_admin_user)) -> dict:
    try:
        hermes_adapter.set_aws_credentials(
            body.access_key_id, body.secret_access_key, body.region
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {"provider_id": provider_id, "state": "present"}


@router.post("/{provider_id}/validate")
def validate_key(provider_id: str, body: CredentialBody, user=Depends(get_admin_user)) -> dict:
    try:
        valid, reason = hermes_adapter.validate_key(provider_id, body.value)
    except KeyError:
        raise _unknown_provider(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {"valid": True} if valid else {"valid": False, "reason": reason}


@router.post("/{provider_id}/oauth/start")
def oauth_start(provider_id: str, user=Depends(get_admin_user)) -> dict:
    """Lance `hermes auth add <provider> --type oauth` (navigateur ouvert sur l'hôte)."""
    try:
        hermes_adapter.start_oauth(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {"started": True}


@router.get("/{provider_id}/oauth/status")
def oauth_status(provider_id: str, user=Depends(get_admin_user)) -> dict:
    return hermes_adapter.oauth_status(provider_id)


@router.delete("/{provider_id}/oauth")
def oauth_logout(provider_id: str, user=Depends(get_admin_user)) -> dict:
    try:
        hermes_adapter.logout_oauth(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise _unavailable(exc)
    return {"disconnected": True}
