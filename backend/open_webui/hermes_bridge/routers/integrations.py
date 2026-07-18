"""Intégrations (feature 004, onglet Intégrations)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import hermes_adapter, integrations_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import IntegrationsResponse
from ..schemas import (
    CredentialBody,
    EmailCredentialsBody,
    EmailGuessBody,
    GoogleAuthCodeBody,
    GoogleClientSecretBody,
)

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/integrations")
def get_integrations() -> IntegrationsResponse:
    """Liste les intégrations connectables avec leur état réel (jamais de valeur de secret)."""
    try:
        return IntegrationsResponse(integrations=integrations_adapter.list_integrations())
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# Connexion Google Workspace (US3) — flow OAuth piloté côté Hermes (le client fournit son app).


@router.post("/integrations/google-workspace/google/client-secret")
def google_client_secret(body: GoogleClientSecretBody) -> dict:
    """Enregistre l'app Google du client (client_secret.json). Le contenu n'est jamais renvoyé."""
    try:
        integrations_adapter.google_set_client_secret(body.client_secret_json)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"ok": True}


@router.post("/integrations/google-workspace/google/auth-url")
def google_auth_url() -> dict:
    """Retourne l'URL d'autorisation Google à présenter au client."""
    try:
        return {"auth_url": integrations_adapter.google_auth_url()}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/integrations/google-workspace/google/auth-code")
def google_auth_code(body: GoogleAuthCodeBody) -> dict:
    """Échange le code de redirection ; renvoie l'état réel confirmé."""
    try:
        ok = integrations_adapter.google_submit_code(body.code)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"state": "connected" if ok else "not_connected"}


@router.get("/integrations/google-workspace/google/status")
def google_status() -> dict:
    """État réel de la connexion Google (via --check)."""
    try:
        return {"state": integrations_adapter.google_status()}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.put("/integrations/{integration_id}/key")
def set_integration_secret(integration_id: str, body: CredentialBody) -> dict:
    """Enregistre la clé (mode key) ou le chemin (mode path). La valeur n'est jamais renvoyée."""
    try:
        secret_state = integrations_adapter.set_secret(integration_id, body.value)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"intégration inconnue: {integration_id}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_mode", "message": str(exc)}}
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"secret_state": secret_state.value}


@router.post("/integrations/{integration_id}/test")
def test_integration(integration_id: str) -> dict:
    """Teste l'accès réel d'une intégration ; renvoie l'état confirmé (honnête)."""
    try:
        state, reason = integrations_adapter.test_access(integration_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"intégration inconnue: {integration_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"ok": state == "connected", "state": state, "reason": reason}


@router.post("/integrations/email/guess")
def email_guess(body: EmailGuessBody) -> dict:
    """Devine les serveurs IMAP/SMTP d'après le domaine de l'email (None si inconnu)."""
    return {"servers": integrations_adapter.email_guess_servers(body.email)}


@router.post("/integrations/email/credentials")
def email_credentials(body: EmailCredentialsBody) -> dict:
    """Enregistre la config Email (Himalaya). Le mot de passe n'est jamais renvoyé."""
    try:
        integrations_adapter.set_email_credentials(
            body.email, body.password, body.imap_host, body.imap_port, body.smtp_host, body.smtp_port
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"state": "connected"}


@router.delete("/integrations/{integration_id}/disconnect")
def disconnect_integration(integration_id: str) -> dict:
    """Déconnecte une intégration (révocation Google / effacement de clé/chemin selon le mode)."""
    try:
        integrations_adapter.disconnect(integration_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"intégration inconnue: {integration_id}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "not_supported", "message": str(exc)}}
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"state": "not_connected"}
