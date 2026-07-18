"""Providers (cerveaux) : liste, cerveau actif, credentials, OAuth."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import hermes_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import ActiveSelection, ProvidersResponse
from ..schemas import AwsCredentialBody, CredentialBody

router = APIRouter(dependencies=[Depends(require_bridge_key)])


class ReasoningBody(BaseModel):
    """Niveau d'intelligence (effort de raisonnement) global du moteur."""

    effort: str


@router.get("/providers")
def get_providers() -> ProvidersResponse:
    """Liste tous les providers Hermes avec leur état et leurs modèles (contrat bridge-api §GET /providers)."""
    try:
        return ProvidersResponse(providers=hermes_adapter.list_providers())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/active")
def get_active() -> ActiveSelection | None:
    """Cerveau actif (provider + modèle), ou ``null`` si aucun n'est défini."""
    try:
        return hermes_adapter.get_active()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/active")
def set_active(selection: ActiveSelection) -> dict[str, str]:
    """Définit le cerveau actif. 404 si provider inconnu, 409 s'il n'est pas configuré.

    Passe par ``hermes_adapter.activate_provider`` — chemin PARTAGÉ avec
    ``moa_adapter.deactivate`` (restauration du cerveau utilisé avant MoA) : les mêmes 3
    garde-fous (404/409, ``base_url``, propagation aux agents nommés) s'appliquent aux deux
    appelants, un seul endroit les implémente (cf. audit phase 3, finding HAUTE).
    """
    try:
        applied, team_brain_sync = hermes_adapter.activate_provider(selection.provider_id, selection.model_id)
    except hermes_adapter.UnknownProvider as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "unknown_provider", "message": f"provider inconnu: {exc.provider_id}"}},
        )
    except hermes_adapter.ProviderNotConfigured as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "not_configured", "message": f"provider non configuré: {exc.provider_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)

    # « Un dirigeant = un assistant » : le cerveau choisi vaut pour toute l'équipe. Le
    # ``team_brain_sync`` (« ok »/« failed ») reflète la propagation best-effort aux agents
    # nommés (aucun impact sur ce 200 — l'opération principale n'est jamais bloquée par elle).
    return {
        "provider_id": applied.provider_id,
        "model_id": applied.model_id,
        "applies_to": "new_conversations",
        "team_brain_sync": team_brain_sync,
    }


@router.post("/model-capabilities")
def model_capabilities(selection: ActiveSelection) -> dict:
    """Capacités du modèle (reasoning/vision/outils/contexte) via models.dev. Repli = None."""
    return hermes_adapter.get_model_capabilities(selection.provider_id, selection.model_id)


@router.get("/reasoning")
def get_reasoning() -> dict[str, str]:
    """Niveau d'intelligence actif (effort de raisonnement). Défaut moteur = medium."""
    try:
        return {"effort": hermes_adapter.get_reasoning() or "medium"}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/reasoning")
def set_reasoning(body: ReasoningBody) -> dict[str, str]:
    """Définit le niveau d'intelligence global (agent.reasoning_effort)."""
    effort = (body.effort or "").strip().lower()
    if effort not in hermes_adapter.VALID_REASONING_EFFORTS:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_effort", "message": f"niveau inconnu: {body.effort}"}},
        )
    try:
        hermes_adapter.set_reasoning(effort)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"effort": effort, "applies_to": "new_conversations"}


@router.put("/credentials/{provider_id}")
def put_credential(provider_id: str, body: CredentialBody) -> dict:
    """Enregistre/remplace la clé API d'un provider (écrite dans ~/.hermes/.env).

    Auto-active ce fournisseur si aucun vrai cerveau n'est encore actif (« poser sa clé =
    ça marche tout de suite ») ; ``activated`` reflète ce qui a été activé, ou est absent.
    La valeur n'est jamais renvoyée ni journalisée (FR-006).
    """
    try:
        result = hermes_adapter.set_key_and_maybe_activate(provider_id, body.value)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "unknown_provider", "message": f"provider inconnu: {provider_id}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "no_api_key", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    response: dict = {"provider_id": provider_id, "state": "present"}
    if result.get("activated"):
        response["activated"] = result["activated"]
    return response


@router.delete("/credentials/{provider_id}")
def delete_credential(provider_id: str) -> dict:
    """Retire la clé API d'un provider (efface la variable du ~/.hermes/.env).

    Si c'était le cerveau actif, bascule proprement (``switched`` reflète le nouveau
    cerveau, ou est absent). Symétrique de PUT.
    """
    try:
        result = hermes_adapter.remove_key(provider_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "unknown_provider", "message": f"provider inconnu: {provider_id}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "no_api_key", "message": str(exc)}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    response: dict = {"provider_id": provider_id, "state": "removed"}
    if result.get("switched"):
        response["switched"] = result["switched"]
    return response


@router.post("/credentials/{provider_id}/aws")
def put_aws_credential(provider_id: str, body: AwsCredentialBody) -> dict[str, str]:
    """Enregistre les credentials AWS (Bedrock) dans ~/.hermes/.env. Jamais renvoyés (FR-006)."""
    try:
        hermes_adapter.set_aws_credentials(body.access_key_id, body.secret_access_key, body.region)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"provider_id": provider_id, "state": "present"}


@router.post("/credentials/{provider_id}/validate")
def validate_credential(provider_id: str, body: CredentialBody) -> dict:
    """Teste une clé (probe réseau) AVANT enregistrement. La valeur n'est jamais journalisée."""
    try:
        valid, reason = hermes_adapter.validate_key(provider_id, body.value)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "unknown_provider", "message": f"provider inconnu: {provider_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"valid": True} if valid else {"valid": False, "reason": reason}


@router.post("/oauth/{provider_id}/start")
def start_oauth(provider_id: str) -> dict[str, bool]:
    """Démarre le flow OAuth d'un provider (`hermes auth add … --type oauth`).

    Le navigateur s'ouvre sur l'hôte. Suivre l'avancement via GET /oauth/{id}/status.
    """
    try:
        hermes_adapter.start_oauth(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"started": True}


@router.get("/oauth/{provider_id}/status")
def oauth_status(provider_id: str) -> dict:
    """État du flow OAuth (running / success / log)."""
    return hermes_adapter.oauth_status(provider_id)


@router.delete("/oauth/{provider_id}")
def logout_oauth(provider_id: str) -> dict[str, bool]:
    """Déconnecte un compte OAuth (`hermes logout --provider <provider>`).

    Retire le fournisseur du credential_pool de Hermes. Action volontaire du client
    (confirmée côté UI) : aucune donnée détruite, il pourra se reconnecter ensuite.
    """
    try:
        hermes_adapter.logout_oauth(provider_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"disconnected": True}
