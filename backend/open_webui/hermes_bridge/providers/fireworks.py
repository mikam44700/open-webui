"""Fireworks AI — catalogue LIVE filtré (gros hébergeur, catalogue mouvant)

`GET /inference/v1/models` (authed) renvoie des métadonnées fiables par modèle
(`supports_chat`, `supports_tools`, `context_length`). On n'expose que les modèles chat
tool-capable : ça écarte d'office flux-1-schnell (génération d'image, supports_chat=False).
`_FIREWORKS_BROKEN` retire en plus les modèles qui PLANTENT en réel malgré des métadonnées OK
(kimi-k2p5 : HTTP 500 constant le 2026-07-08 — à revalider, possible incident temporaire). Les
fallback_models du plugin (llama-v3p3-70b, deepseek-v3) sont périmés (404) → live indispensable.
Ordre + libellés via `_CURATED_MODELS["fireworks"]` (alphabétique). Repli figé si offline.
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
_FIREWORKS_MODELS_TTL = 6 * 60 * 60  # 6 h
_FIREWORKS_CACHE = TTLCache(_FIREWORKS_MODELS_TTL)  # keyed par clé API
_FIREWORKS_BROKEN = frozenset({"accounts/fireworks/models/kimi-k2p5"})


def _fireworks_served_ids(api_key: str | None) -> list[str]:
    """IDs chat tool-capable réellement servis (`GET /models` authed, filtrés sur les métadonnées
    `supports_chat`+`supports_tools`, hors `_FIREWORKS_BROKEN`). Caché par clé (TTL 6h). ``[]`` si
    l'appel échoue → repli figé."""
    if not api_key:
        return []
    fresh = _FIREWORKS_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{_FIREWORKS_BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
        if resp.status_code == 200:
            ids = [
                m["id"]
                for m in resp.json().get("data", [])
                if m.get("supports_chat") and m.get("supports_tools") and m.get("id") not in _FIREWORKS_BROKEN
            ]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _FIREWORKS_CACHE.store(ids, api_key)
    return ids


def _fireworks_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Fireworks pour le sélecteur : catalogue LIVE filtré, ordonné + labellisé par la
    table curée (alphabétique). Repli sur la table figée si l'appel échoue (offline)."""
    served = _fireworks_served_ids(api_key)
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get("fireworks", [])]
    return _display_pairs("fireworks", served)
