"""Router /api/v1/onboarding — Onboarding de contexte entreprise (spec 019).

Admin-only. Proxifie vers le Providers Bridge, qui lit le site du client via Crawl4AI et
renvoie un markdown propre + un statut honnête (reussi/partiel/echec). La SYNTHÈSE (markdown →
offre/ton/clientèle/services) se fait côté front avec le modèle actif ; la PERSISTANCE du contexte
validé réutilise le router /api/v1/memory (profil USER.md + coffre). Cf. specs/019.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class CrawlBody(BaseModel):
    url: str


@router.post("/crawl")
async def onboarding_crawl(body: CrawlBody, user=Depends(get_admin_user)):
    """Lit le site du client (Crawl4AI) et renvoie son markdown + un statut honnête."""
    return await _bridge("POST", "/onboarding/crawl", json=body.model_dump())
