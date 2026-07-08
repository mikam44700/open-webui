"""Router /api/v1/gateway — supervision du gateway Hermes + plateformes de messagerie.

Admin-only. Proxifie vers le Providers Bridge (service interne sur l'hôte) en réutilisant
l'auth admin d'OpenWebUI et le helper ``_bridge`` du router providers. Hermes reste la source
de vérité (tokens ~/.hermes/.env, activation config.yaml, état du gateway).

Page « Gateway » d'Agent OS — portage de la page Gateway de Hermes Desktop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class MessagingUpdate(BaseModel):
    env: dict[str, str] | None = None
    clear_env: list[str] | None = None
    enabled: bool | None = None


class MessagingApprove(BaseModel):
    code: str | None = None
    user_id: str | None = None
    user_name: str = ""


@router.get("/status")
async def gateway_status(user=Depends(get_admin_user)):
    """État du gateway : tourne ou non, port de l'API server, présence de la clé API."""
    return await _bridge("GET", "/gateway/status")


@router.get("/platforms")
async def list_platforms(user=Depends(get_admin_user)):
    """Liste les plateformes de messagerie avec leur état."""
    return await _bridge("GET", "/gateway/platforms")


@router.post("/platforms/{platform_id}")
async def update_platform(platform_id: str, body: MessagingUpdate, user=Depends(get_admin_user)):
    """Met à jour une plateforme : tokens (.env) et/ou activation (config.yaml)."""
    return await _bridge("POST", f"/gateway/platforms/{platform_id}", json=body.model_dump(exclude_none=True))


@router.post("/platforms/{platform_id}/test")
async def test_platform(platform_id: str, user=Depends(get_admin_user)):
    """Test « soft » d'une plateforme (présence des clés requises + état)."""
    return await _bridge("POST", f"/gateway/platforms/{platform_id}/test")


@router.post("/api-key/generate")
async def generate_api_key(user=Depends(get_admin_user)):
    """(Re)génère la clé API du serveur Hermes (API_SERVER_KEY)."""
    return await _bridge("POST", "/gateway/api-key/generate")


@router.post("/restart")
async def restart_gateway(user=Depends(get_admin_user)):
    """Redémarre le gateway (start/stop = supervision launchd/systemd)."""
    return await _bridge("POST", "/gateway/restart")


# --- Onboarding Telegram « managed bot » (parcours QR 1-clic) -----------------


@router.post("/platforms/telegram/pairing/start")
async def telegram_pairing_start(user=Depends(get_admin_user)):
    """Démarre un pairing Telegram : renvoie le QR/lien à scanner."""
    return await _bridge("POST", "/gateway/platforms/telegram/pairing/start")


@router.get("/platforms/telegram/pairing/{pairing_id}")
async def telegram_pairing_poll(pairing_id: str, user=Depends(get_admin_user)):
    """Interroge un pairing : waiting puis ready."""
    return await _bridge("GET", f"/gateway/platforms/telegram/pairing/{pairing_id}")


@router.post("/platforms/telegram/pairing/{pairing_id}/apply")
async def telegram_pairing_apply(pairing_id: str, user=Depends(get_admin_user)):
    """Applique un pairing prêt : branche + active + auto-approuve + home channel + restart."""
    return await _bridge("POST", f"/gateway/platforms/telegram/pairing/{pairing_id}/apply")


@router.delete("/platforms/telegram/pairing/{pairing_id}")
async def telegram_pairing_cancel(pairing_id: str, user=Depends(get_admin_user)):
    """Annule/oublie un pairing en cours."""
    return await _bridge("DELETE", f"/gateway/platforms/telegram/pairing/{pairing_id}")


# --- Partage : allowlist des utilisateurs -------------------------------------


@router.get("/platforms/{platform_id}/users")
async def list_platform_users(platform_id: str, user=Depends(get_admin_user)):
    """Liste les utilisateurs autorisés + les demandes en attente."""
    return await _bridge("GET", f"/gateway/platforms/{platform_id}/users")


@router.post("/platforms/{platform_id}/users")
async def approve_platform_user(platform_id: str, body: MessagingApprove, user=Depends(get_admin_user)):
    """Autorise un utilisateur (via un code en attente ou par user_id)."""
    return await _bridge(
        "POST", f"/gateway/platforms/{platform_id}/users", json=body.model_dump(exclude_none=True)
    )


@router.delete("/platforms/{platform_id}/users/{user_id}")
async def revoke_platform_user(platform_id: str, user_id: str, user=Depends(get_admin_user)):
    """Retire l'accès d'un utilisateur (le sort de l'allowlist)."""
    return await _bridge("DELETE", f"/gateway/platforms/{platform_id}/users/{user_id}")


# --- Déconnexion --------------------------------------------------------------


@router.post("/platforms/{platform_id}/disconnect")
async def disconnect_platform(platform_id: str, user=Depends(get_admin_user)):
    """Déconnecte totalement une plateforme (efface, désactive, purge, redémarre)."""
    return await _bridge("POST", f"/gateway/platforms/{platform_id}/disconnect")
