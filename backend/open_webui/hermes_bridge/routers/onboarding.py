"""Endpoints du parcours d'onboarding (première connexion).

  POST /onboarding/crawl  → crawle le site d'une entreprise et renvoie son contenu
                            markdown propre + un statut honnête (reussi/partiel/echec).

La SYNTHÈSE (markdown → offre/ton/clientèle/services) se fait côté front avec le modèle
actif ; ici on ne fait que la LECTURE du site (déterministe, via Crawl4AI). La persistance
du contexte validé réutilise les endpoints Mémoire existants (USER.md + coffre).
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from open_webui.retrieval.web.brave import search_brave
from open_webui.retrieval.web.exa import search_exa
from open_webui.retrieval.web.tavily import search_tavily

from .. import (
    crawl4ai_adapter,
    direct_response,
    hermes_adapter,
    tool_connection_adapter,
)
from ..deps import require_bridge_key

router = APIRouter(dependencies=[Depends(require_bridge_key)])

ONBOARDING_STRUCTURED_TIMEOUT_SECONDS = 240


class CrawlRequest(BaseModel):
    url: str
    mode: Literal['baseline', 'quality'] = 'baseline'


class StructuredRequest(BaseModel):
    provider_id: str
    model_id: str
    system: str = Field(min_length=1, max_length=10_000)
    user: str = Field(min_length=1, max_length=60_000)
    max_tokens: int = Field(default=4_000, ge=256, le=8_000)
    timeout_seconds: int = Field(default=90, ge=10, le=240)


class WebSearchRequest(BaseModel):
    provider: Literal['exa', 'brave', 'tavily']
    queries: list[str] = Field(min_length=1, max_length=8)


@router.post('/onboarding/crawl')
def post_onboarding_crawl(body: CrawlRequest) -> dict:
    """Lit le site d'une entreprise via Crawl4AI — la home PLUS quelques pages clés (à propos,
    tarifs, services, contact…) pour un contexte riche. Dégradé gracieux : renvoie toujours 200
    avec un ``status`` honnête (echec inclus) plutôt qu'une 5xx, pour ne jamais casser le
    parcours d'onboarding. Seule l'URL invalide renvoie une 400."""
    url = (body.url or '').strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        raise HTTPException(status_code=400, detail='URL invalide')
    if body.mode == 'quality':
        return crawl4ai_adapter.crawl_site_quality(url)
    return crawl4ai_adapter.crawl_site(url)


@router.post('/onboarding/structured')
async def post_onboarding_structured(body: StructuredRequest) -> dict:
    """Synthèse sans outil avec le provider et le modèle explicitement confirmés."""
    active = hermes_adapter.get_active()
    if (
        active is None
        or active.provider_id in {'', 'auto'}
        or active.provider_id != body.provider_id
        or active.model_id != body.model_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                'error': {
                    'code': 'brain_changed',
                    'message': (
                        "Le cerveau IA confirmé n'est plus actif. "
                        'Revenez à la configuration et choisissez explicitement votre modèle.'
                    ),
                }
            },
        )
    try:
        answer, actual_model = await direct_response.complete_without_tools(
            [
                {'role': 'system', 'content': body.system},
                {'role': 'user', 'content': body.user},
            ],
            max_tokens=body.max_tokens,
            timeout_seconds=min(
                body.timeout_seconds,
                ONBOARDING_STRUCTURED_TIMEOUT_SECONDS,
            ),
        )
    except Exception as exc:  # runtime local : erreurs aiohttp, modèle et délais normalisées ici
        raise HTTPException(
            status_code=502,
            detail={
                'error': {
                    'code': 'brain_failed',
                    'message': f"Le cerveau IA n'a pas terminé l'analyse : {str(exc)[:240]}",
                }
            },
        ) from exc
    return {'content': answer, 'model': actual_model or active.model_id}


def _active_web_provider() -> str | None:
    connection = tool_connection_adapter.get_connection('web')
    return next(
        (
            provider.slug
            for provider in connection.providers
            if provider.active is True and provider.slug in {'exa', 'brave', 'tavily'}
        ),
        None,
    )


def _web_key(provider: str) -> str:
    env_key = {
        'exa': 'EXA_API_KEY',
        'brave': 'BRAVE_SEARCH_API_KEY',
        'tavily': 'TAVILY_API_KEY',
    }[provider]
    value = (hermes_adapter.read_env_value(env_key) or '').strip().strip('"').strip("'")
    if not value:
        raise HTTPException(
            status_code=409,
            detail={
                'error': {
                    'code': 'web_key_missing',
                    'message': f"La connexion {provider.title()} n'est plus disponible.",
                }
            },
        )
    return value


async def _search_one(provider: str, key: str, query: str):
    if provider == 'brave':
        return await search_brave(key, query, 6)
    if provider == 'exa':
        return await asyncio.to_thread(search_exa, key, query, 6)
    return await asyncio.to_thread(search_tavily, key, query, 6)


@router.post('/onboarding/web-search')
async def post_onboarding_web_search(body: WebSearchRequest) -> dict:
    """Recherche avec le même fournisseur que celui testé et activé à l'étape 1."""
    active = _active_web_provider()
    if active != body.provider:
        raise HTTPException(
            status_code=409,
            detail={
                'error': {
                    'code': 'web_provider_changed',
                    'message': ("Le moteur Web confirmé n'est plus actif. Revenez à la configuration et réactivez-le."),
                }
            },
        )
    key = _web_key(body.provider)
    queries = [query.strip()[:300] for query in body.queries if query.strip()]
    try:
        if body.provider == 'brave':
            batches = []
            for query in queries:
                batches.append(await _search_one(body.provider, key, query))
        else:
            batches = await asyncio.gather(*(_search_one(body.provider, key, query) for query in queries))
    except Exception as exc:  # les bibliothèques fournisseurs lèvent des erreurs hétérogènes
        raise HTTPException(
            status_code=502,
            detail={
                'error': {
                    'code': 'web_search_failed',
                    'message': f'La recherche {body.provider.title()} a échoué : {str(exc)[:220]}',
                }
            },
        ) from exc

    seen: set[str] = set()
    items = []
    for results in batches:
        for result in results or []:
            link = str(result.link or '').strip()
            if not link or link in seen:
                continue
            seen.add(link)
            items.append(
                {
                    'title': str(result.title or link)[:500],
                    'link': link,
                    'snippet': str(result.snippet or '')[:4_000],
                }
            )
    if not items:
        raise HTTPException(
            status_code=502,
            detail={
                'error': {
                    'code': 'web_search_empty',
                    'message': (
                        f"{body.provider.title()} n'a renvoyé aucun résultat exploitable. "
                        "L'analyse est arrêtée pour éviter une Carte incomplète."
                    ),
                }
            },
        )
    return {'provider': body.provider, 'items': items}
