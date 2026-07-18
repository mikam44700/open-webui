"""OpenRouter — passerelle multi-modèles (256+ modèles). Catalogue /models PUBLIC.

OpenRouter est une passerelle : son profil moteur ne curate que 5 fallback_models,
mais le client paie pour l'accès à TOUT le catalogue. On récupère donc le catalogue
PUBLIC (sans clé) et on le filtre sur le tool calling (indispensable au chat agentique :
un modèle sans « tools » planterait en HTTP 400). Les 5 recommandés sont épinglés en
tête ; le reste (trié par nom lisible) alimente la barre de recherche du sélecteur.
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache

_OPENROUTER_CATALOG_URL = "https://openrouter.ai/api/v1/models"
_OPENROUTER_CATALOG_TTL = 6 * 3600  # 6 h : le catalogue bouge lentement
_OPENROUTER_CACHE = TTLCache(_OPENROUTER_CATALOG_TTL)


def _fetch_openrouter_catalog() -> list[tuple[str, str]] | None:
    """Catalogue OpenRouter (public) filtré tool-capable → ``[(id, nom_lisible), ...]``.

    Caché en mémoire (TTL 6 h) pour éviter un appel réseau à chaque ``list_providers``.
    Repli gracieux : en cas d'échec réseau on renvoie le dernier cache (ou ``None`` au
    tout premier échec → l'appelant garde les 5 fallback). Ne lève jamais.
    """
    fresh = _OPENROUTER_CACHE.fresh()
    if fresh is not None:
        return fresh
    try:
        resp = httpx.get(_OPENROUTER_CATALOG_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:  # noqa: BLE001 — réseau/JSON KO = on garde le dernier bon cache
        return _OPENROUTER_CACHE.last()
    models: list[tuple[str, str]] = []
    for item in data:
        params = item.get("supported_parameters")
        # Garde-fou : seuls les modèles annonçant explicitement « tools » (le chat est
        # agentique). On écarte les image-only / completion-only qui 400-eraient.
        if not isinstance(params, list) or "tools" not in params:
            continue
        mid = item.get("id")
        if not mid:
            continue
        models.append((mid, item.get("name") or mid))
    _OPENROUTER_CACHE.store(models)
    return models


def _openrouter_model_list(fallback: list[str]) -> list[tuple[str, str]]:
    """Modèles OpenRouter pour le sélecteur : catalogue live TOUT trié par ordre
    alphabétique (le client choisit ; pas de « recommandé » vu le nombre de modèles).
    Repli sur les seuls fallback si le catalogue est indisponible (offline)."""
    catalog = _fetch_openrouter_catalog()
    if not catalog:
        return [(mid, mid) for mid in fallback]
    return sorted(catalog, key=lambda pair: pair[1].lower())
