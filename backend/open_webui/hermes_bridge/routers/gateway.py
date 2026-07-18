"""Gateway : supervision + plateformes de messagerie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import gateway_adapter, hermes_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import (
    DiscordApplyResult,
    DiscordBotInfo,
    EmailApplyResult,
    GatewayStatus,
    MessagingActionResult,
    MessagingPlatformsResponse,
    MessagingUsersResponse,
    SlackApplyResult,
    SlackBotInfo,
    TelegramBotInfo,
    TelegramPairingApplyResult,
    TelegramPairingStart,
    TelegramPairingStatus,
)
from ..schemas import (
    DiscordApplyBody,
    EmailApplyBody,
    MessagingApproveBody,
    MessagingUpdateBody,
    SlackApplyBody,
)

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _not_found(platform_id: str) -> HTTPException:
    """404 homogène pour une plateforme/pairing inconnu."""
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": f"introuvable: {platform_id}"}},
    )


@router.get("/gateway/status")
def gateway_status() -> GatewayStatus:
    """État du gateway : tourne ou non, port de l'API server, présence de la clé API."""
    try:
        return gateway_adapter.gateway_status()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/gateway/platforms")
def gateway_platforms() -> MessagingPlatformsResponse:
    """Liste les plateformes de messagerie avec leur état (configuré/activé/connecté)."""
    try:
        return gateway_adapter.list_platforms()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/gateway/platforms/{platform_id}")
def gateway_update_platform(platform_id: str, body: MessagingUpdateBody) -> dict:
    """Met à jour une plateforme : tokens (.env) et/ou activation (config.yaml)."""
    try:
        res = gateway_adapter.update_platform(
            platform_id, env=body.env, clear_env=body.clear_env, enabled=body.enabled
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"plateforme inconnue: {platform_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return res


@router.post("/gateway/platforms/{platform_id}/test")
def gateway_test_platform(platform_id: str) -> dict:
    """Test « soft » d'une plateforme (présence des clés requises + état)."""
    try:
        return gateway_adapter.test_platform(platform_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"plateforme inconnue: {platform_id}"}},
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/gateway/api-key/generate")
def gateway_generate_api_key() -> dict:
    """(Re)génère la clé API du serveur (``API_SERVER_KEY`` dans ~/.hermes/.env)."""
    try:
        return gateway_adapter.generate_api_key()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/gateway/restart")
def gateway_restart() -> dict:
    """Redémarre le gateway (``hermes gateway restart``). Start/stop = supervision."""
    try:
        return gateway_adapter.restart_gateway()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Onboarding Telegram « managed bot » (parcours QR 1-clic) -----------------


@router.post("/gateway/platforms/telegram/pairing/start")
def telegram_pairing_start() -> TelegramPairingStart:
    """Démarre un pairing Telegram : renvoie le QR/lien à scanner (aucun token exposé)."""
    try:
        return gateway_adapter.telegram_pairing_start()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/gateway/platforms/telegram/pairing/{pairing_id}")
def telegram_pairing_poll(pairing_id: str) -> TelegramPairingStatus:
    """Interroge un pairing : ``waiting`` puis ``ready`` (avec bot_username/owner)."""
    try:
        return gateway_adapter.telegram_pairing_poll(pairing_id)
    except KeyError:
        raise _not_found(pairing_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/gateway/platforms/telegram/pairing/{pairing_id}/apply")
def telegram_pairing_apply(pairing_id: str) -> TelegramPairingApplyResult:
    """Applique un pairing prêt : branche + active + auto-approuve le propriétaire +
    home channel + redémarre le gateway."""
    try:
        return gateway_adapter.telegram_pairing_apply(pairing_id)
    except KeyError:
        raise _not_found(pairing_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/gateway/platforms/telegram/pairing/{pairing_id}")
def telegram_pairing_cancel(pairing_id: str) -> dict:
    """Annule/oublie un pairing en cours (modale fermée, expiration)."""
    return gateway_adapter.telegram_pairing_cancel(pairing_id)


@router.get("/gateway/platforms/telegram/bot-info")
def telegram_bot_info() -> TelegramBotInfo:
    """Nom + lien du bot Telegram connecté (à afficher/partager)."""
    try:
        return gateway_adapter.telegram_bot_info()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Onboarding Discord (parcours guidé : token → branché + invite 1-clic) ----


@router.post("/gateway/platforms/discord/apply")
def discord_apply(body: DiscordApplyBody) -> DiscordApplyResult:
    """Branche Discord depuis un token collé : valide le token, active + redémarre,
    renvoie l'URL d'invitation « Ajouter à mon serveur »."""
    try:
        return gateway_adapter.discord_apply(body.token)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/gateway/platforms/discord/bot-info")
def discord_bot_info() -> DiscordBotInfo:
    """Nom du bot Discord connecté + URL d'invitation (à afficher/partager)."""
    try:
        return gateway_adapter.discord_bot_info()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Onboarding Slack (parcours guidé : 2 tokens → branché) -------------------


@router.post("/gateway/platforms/slack/apply")
def slack_apply(body: SlackApplyBody) -> SlackApplyResult:
    """Branche Slack depuis les 2 tokens collés (xoxb-… + xapp-…) : valide les deux,
    active + redémarre, renvoie le nom du workspace + du bot."""
    try:
        return gateway_adapter.slack_apply(body.bot_token, body.app_token)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/gateway/platforms/slack/bot-info")
def slack_bot_info() -> SlackBotInfo:
    """Nom du bot Slack connecté + workspace (à afficher)."""
    try:
        return gateway_adapter.slack_bot_info()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Onboarding Email (validation réelle IMAP/SMTP → auto-activation) ----------


@router.post("/gateway/platforms/email/apply")
def email_apply(body: EmailApplyBody) -> EmailApplyResult:
    """Branche Email en testant réellement la connexion (login IMAP + SMTP) : si OK,
    active le canal tout seul et redémarre. Sinon message clair, rien n'est activé."""
    try:
        return gateway_adapter.email_apply(
            body.address, body.password, body.imap_host, body.smtp_host
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Partage : allowlist des utilisateurs -------------------------------------


@router.get("/gateway/platforms/{platform_id}/users")
def gateway_list_users(platform_id: str) -> MessagingUsersResponse:
    """Liste les utilisateurs autorisés + les demandes en attente d'une plateforme."""
    try:
        return gateway_adapter.list_platform_users(platform_id)
    except KeyError:
        raise _not_found(platform_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/gateway/platforms/{platform_id}/users")
def gateway_approve_user(platform_id: str, body: MessagingApproveBody) -> MessagingActionResult:
    """Autorise un utilisateur : via un code en attente (``code``) ou par ``user_id``."""
    try:
        return gateway_adapter.approve_platform_user(
            platform_id, code=body.code, user_id=body.user_id, user_name=body.user_name
        )
    except KeyError:
        raise _not_found(platform_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/gateway/platforms/{platform_id}/users/{user_id}")
def gateway_revoke_user(platform_id: str, user_id: str) -> MessagingActionResult:
    """Retire l'accès d'un utilisateur (le sort de l'allowlist)."""
    try:
        return gateway_adapter.revoke_platform_user(platform_id, user_id)
    except KeyError:
        raise _not_found(platform_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


# --- Déconnexion --------------------------------------------------------------


@router.post("/gateway/platforms/{platform_id}/disconnect")
def gateway_disconnect(platform_id: str) -> MessagingActionResult:
    """Déconnecte totalement une plateforme : efface les clés, désactive, purge
    l'allowlist, redémarre."""
    try:
        return gateway_adapter.disconnect_platform(platform_id)
    except KeyError:
        raise _not_found(platform_id)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
