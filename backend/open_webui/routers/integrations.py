"""Router /api/integrations — intégrations connectables de Hermes (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité unique (skills connectables : Gmail, Notion, GitHub…). Cf. specs/004-integrations.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class GoogleClientSecretBody(BaseModel):
    client_secret_json: dict


class GoogleAuthCodeBody(BaseModel):
    code: str


class KeyBody(BaseModel):
    value: str


class EmailGuessBody(BaseModel):
    email: str


class EmailCredentialsBody(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int


@router.get("/")
async def list_integrations(user=Depends(get_admin_user)):
    """Liste les intégrations connectables avec leur état réel (admin-only)."""
    return await _bridge("GET", "/integrations")


# --- Connexion par clé / chemin + test (Notion, GitHub, Airtable, Obsidian) ---


@router.put("/{integration_id}/key")
async def set_key(integration_id: str, body: KeyBody, user=Depends(get_admin_user)):
    """Enregistre la clé/chemin d'une intégration (valeur jamais renvoyée)."""
    return await _bridge("PUT", f"/integrations/{integration_id}/key", json=body.model_dump())


@router.post("/{integration_id}/test")
async def test_integration(integration_id: str, user=Depends(get_admin_user)):
    """Teste l'accès réel d'une intégration."""
    return await _bridge("POST", f"/integrations/{integration_id}/test")


# --- Connexion Email (IMAP/SMTP) ---


@router.post("/email/guess")
async def email_guess(body: EmailGuessBody, user=Depends(get_admin_user)):
    """Devine les serveurs IMAP/SMTP d'après l'email."""
    return await _bridge("POST", "/integrations/email/guess", json=body.model_dump())


@router.post("/email/credentials")
async def email_credentials(body: EmailCredentialsBody, user=Depends(get_admin_user)):
    """Enregistre la config Email (mot de passe jamais renvoyé)."""
    return await _bridge("POST", "/integrations/email/credentials", json=body.model_dump())


# --- Connexion Google Workspace (US3) ---


@router.post("/google-workspace/google/client-secret")
async def google_client_secret(body: GoogleClientSecretBody, user=Depends(get_admin_user)):
    """Enregistre l'app Google du client (contenu jamais renvoyé)."""
    return await _bridge(
        "POST", "/integrations/google-workspace/google/client-secret", json=body.model_dump()
    )


@router.post("/google-workspace/google/auth-url")
async def google_auth_url(user=Depends(get_admin_user)):
    """Récupère l'URL d'autorisation Google."""
    return await _bridge("POST", "/integrations/google-workspace/google/auth-url")


@router.post("/google-workspace/google/auth-code")
async def google_auth_code(body: GoogleAuthCodeBody, user=Depends(get_admin_user)):
    """Échange le code de redirection contre une connexion."""
    return await _bridge(
        "POST", "/integrations/google-workspace/google/auth-code", json=body.model_dump()
    )


@router.get("/google-workspace/google/status")
async def google_status(user=Depends(get_admin_user)):
    """État réel de la connexion Google."""
    return await _bridge("GET", "/integrations/google-workspace/google/status")


@router.delete("/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str, user=Depends(get_admin_user)):
    """Déconnecte une intégration (après confirmation côté UI)."""
    return await _bridge("DELETE", f"/integrations/{integration_id}/disconnect")


# --- OAuth centralisé 1 clic (Microsoft 365 et futurs providers OAuth) ---


class OAuthExchangeBody(BaseModel):
    code: str
    state: str


@router.get("/oauth/{provider_id}/auth-url")
async def oauth_auth_url(provider_id: str, user=Depends(get_admin_user)):
    """Récupère l'URL d'autorisation OAuth du fournisseur (redirige l'utilisateur)."""
    return await _bridge("GET", f"/integrations/oauth/{provider_id}/auth-url")


@router.post("/oauth/{provider_id}/exchange")
async def oauth_exchange(
    provider_id: str, body: OAuthExchangeBody, user=Depends(get_admin_user)
):
    """Échange le code OAuth de retour contre un token stocké par le bridge."""
    return await _bridge(
        "POST", f"/integrations/oauth/{provider_id}/exchange", json=body.model_dump()
    )


@router.get("/oauth/{provider_id}/status")
async def oauth_status(provider_id: str, user=Depends(get_admin_user)):
    """Retourne l'état de connexion OAuth d'un fournisseur (connected | not_connected)."""
    return await _bridge("GET", f"/integrations/oauth/{provider_id}/status")


@router.delete("/oauth/{provider_id}")
async def oauth_disconnect(provider_id: str, user=Depends(get_admin_user)):
    """Révoque et supprime les tokens OAuth d'un fournisseur."""
    return await _bridge("DELETE", f"/integrations/oauth/{provider_id}")
