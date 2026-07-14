"""Router /api/v1/agent-channel — canal « Agent OS » où Hermes publie (feature 015).

Admin-only. Garantit l'existence d'un canal dédié « agent-os » + un webhook « Agent OS »,
et y publie le briefing du jour (assemblé par le bridge). C'est le sens « Hermes → canal »
du flux Channels : l'agent dépose ses briefings / résultats dans un canal de l'app.

Réutilise les fonctions natives Channels (création canal/webhook, insertion de message) ;
rien n'est dupliqué ni supprimé du natif.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.channels import Channels, ChannelWebhookForm, CreateChannelForm
from open_webui.models.messages import MessageForm, Messages
from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()

CHANNEL_NAME = "agent-os"


async def _ensure_channel_and_webhook(user, db: AsyncSession):
    """Récupère (ou crée) le canal Agent OS et son webhook de publication."""
    channels = await Channels.get_channels(db=db)
    channel = next((c for c in channels if c.name == CHANNEL_NAME), None)
    if not channel:
        channel = await Channels.insert_new_channel(
            CreateChannelForm(name=CHANNEL_NAME, description="Messages de LunarIA"),
            user.id,
            db=db,
        )
    webhooks = await Channels.get_webhooks_by_channel_id(channel.id, db=db)
    webhook = (
        webhooks[0]
        if webhooks
        else await Channels.insert_webhook(channel.id, user.id, ChannelWebhookForm(name="LunarIA"), db=db)
    )
    return channel, webhook


@router.post("/publish-briefing")
async def publish_briefing(
    user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    """Publie le briefing du jour (assemblé par Hermes) dans le canal Agent OS."""
    channel, webhook = await _ensure_channel_and_webhook(user, db)

    data = await _bridge("GET", "/briefing")
    text = (data or {}).get("text") or "Briefing momentanément indisponible."

    message = await Messages.insert_new_message(
        MessageForm(content=text, meta={"webhook": {"id": webhook.id}}),
        channel.id,
        webhook.user_id,
        db=db,
    )

    # Emit temps-réel best-effort (le message est de toute façon persisté en base).
    try:
        from open_webui.socket.main import sio

        full = await Messages.get_message_by_id(message.id, db=db)
        identity = {"id": webhook.id, "name": webhook.name, "role": "webhook"}
        await sio.emit(
            "events:channel",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {"type": "message", "data": {**full.model_dump(), "user": identity}},
                "user": identity,
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("agent-channel emit failed: %s", exc)

    return {"ok": True, "channel_id": channel.id, "message_id": message.id}
