"""Endpoints du parcours d'onboarding (première connexion).

  POST /onboarding/crawl  → crawle le site d'une entreprise et renvoie son contenu
                            markdown propre + un statut honnête (reussi/partiel/echec).

La SYNTHÈSE (markdown → offre/ton/clientèle/services) se fait côté front avec le modèle
actif ; ici on ne fait que la LECTURE du site (déterministe, via Crawl4AI). La persistance
du contexte validé réutilise les endpoints Mémoire existants (USER.md + coffre).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import crawl4ai_adapter
from ..deps import require_bridge_key

router = APIRouter(dependencies=[Depends(require_bridge_key)])


class CrawlRequest(BaseModel):
    url: str
    mode: Literal["baseline", "quality"] = "baseline"


@router.post("/onboarding/crawl")
def post_onboarding_crawl(body: CrawlRequest) -> dict:
    """Lit le site d'une entreprise via Crawl4AI — la home PLUS quelques pages clés (à propos,
    tarifs, services, contact…) pour un contexte riche. Dégradé gracieux : renvoie toujours 200
    avec un ``status`` honnête (echec inclus) plutôt qu'une 5xx, pour ne jamais casser le
    parcours d'onboarding. Seule l'URL invalide renvoie une 400."""
    url = (body.url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL invalide")
    if body.mode == "quality":
        return crawl4ai_adapter.crawl_site_quality(url)
    return crawl4ai_adapter.crawl_site(url)
