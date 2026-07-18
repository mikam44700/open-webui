"""Cerebras — catalogue LIVE (petit catalogue volatil : 2 des 3 modèles sont « Preview »)

Cerebras expose un catalogue OFFICIEL de 3 modèles (`GET /v1/models`, authed — 403 sans clé,
donc test de clé fiable sans _PROBE_CHAT). On lit le live plutôt qu'une liste figée car la doc
Cerebras marque gemma-4-31b et zai-glm-4.7 comme « Preview, peuvent être discontinués vite » :
le live les retire automatiquement le jour où ils sautent (pas de 404 chez le client). Ordre et
libellés viennent de `_CURATED_MODELS["cerebras"]` (Production d'abord). Repli figé si offline.
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_CEREBRAS_BASE = "https://api.cerebras.ai/v1"
_CEREBRAS_MODELS_TTL = 6 * 60 * 60  # 6 h
_CEREBRAS_CACHE = TTLCache(_CEREBRAS_MODELS_TTL)  # keyed par clé API


def _cerebras_served_ids(api_key: str | None) -> list[str]:
    """IDs réellement servis par la clé via `GET /v1/models` (authed). Caché par clé (TTL 6h).
    ``[]`` si l'appel échoue → l'appelant retombe sur la table figée `_CURATED_MODELS`."""
    if not api_key:
        return []
    fresh = _CEREBRAS_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{_CEREBRAS_BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _CEREBRAS_CACHE.store(ids, api_key)
    return ids


def _cerebras_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Cerebras pour le sélecteur : catalogue LIVE (`/models`), ordonné + labellisé par
    la table curée (Production d'abord). Repli sur la table figée si l'appel échoue (offline)."""
    served = _cerebras_served_ids(api_key)
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get("cerebras", [])]
    return _display_pairs("cerebras", served)
