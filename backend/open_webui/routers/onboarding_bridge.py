"""Router /api/v1/onboarding — Onboarding de contexte entreprise (spec 019).

Admin-only. Proxifie vers le Providers Bridge, qui lit le site du client via Crawl4AI et
renvoie un markdown propre + un statut honnête (reussi/partiel/echec). La SYNTHÈSE (markdown →
offre/ton/clientèle/services) se fait côté front avec le modèle actif ; la PERSISTANCE du contexte
validé réutilise le router /api/v1/memory (profil USER.md + coffre). Cf. specs/019.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()

# Défense en profondeur anti-SSRF (finding audit #5) : le bridge a son propre net_guard,
# mais on ne délègue pas tout — on rejette ici le plus évident (schéma non http/https,
# hôte qui résout vers du loopback/privé/lien-local/metadata cloud).
_METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal"}


async def _reject_unsafe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_url",
                    "message": "L'URL doit être en http:// ou https://.",
                }
            },
        )
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_url", "message": "URL sans hôte valide."}},
        )
    if hostname.lower() in _METADATA_HOSTS:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "unsafe_url", "message": "Hôte non autorisé."}},
        )
    try:
        # Résolution DNS hors event loop (socket.getaddrinfo est bloquant).
        addr_infos = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except OSError:
        # Résolution DNS impossible ici : on laisse passer, le bridge (net_guard) tranchera.
        return
    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "unsafe_url",
                        "message": "Cette adresse n'est pas autorisée (réseau privé/local).",
                    }
                },
            )


class CrawlBody(BaseModel):
    url: str


@router.post("/crawl")
async def onboarding_crawl(body: CrawlBody, user=Depends(get_admin_user)):
    """Lit le site du client (Crawl4AI) et renvoie son markdown + un statut honnête."""
    await _reject_unsafe_url(body.url)
    return await _bridge("POST", "/onboarding/crawl", json=body.model_dump())
