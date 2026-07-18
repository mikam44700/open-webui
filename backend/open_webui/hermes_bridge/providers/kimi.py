"""Kimi / Moonshot — liste LIVE des modèles réellement servis (2 plans auto-routés)

Kimi a deux offres, distinguées par le PRÉFIXE de la clé (comme le moteur, cf.
_resolve_kimi_base_url) : clé `sk-kimi-` = Coding Plan → api.kimi.com/coding ; sinon =
API classique Moonshot → api.moonshot.ai/v1 (ou .cn pour kimi-coding-cn). La liste FIGÉE du
moteur `_PROVIDER_MODELS["kimi-coding"]` est trompeuse : test réel (2026-07-07) → 5 de ses 8
modèles sont des FANTÔMES (`kimi-for-coding`, `kimi-k2-thinking`… → HTTP 404 « Not found the
model ») et elle OUBLIE tous les `moonshot-v1-*` réellement servis. On interroge donc le vrai
endpoint `/models` (authed) et on n'affiche que ce qui existe. Cache par clé (TTL 6h). Repli
sur la table curée `_CURATED_MODELS` si l'appel échoue (offline). Zéro modif moteur.
Endpoint Coding Plan : le chemin OpenAI-compat inclut « /v1 » (vérifié en réel : /coding/models
= 404, /coding/v1/models = 401 = existe). Le KIMI_CODE_BASE_URL du moteur (« …/coding » sans /v1)
est un préfixe ; les appels REST du bridge (/models, /chat/completions) exigent « /coding/v1 ».
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_KIMI_CODE_BASE = "https://api.kimi.com/coding/v1"
_KIMI_MODELS_TTL = 6 * 60 * 60  # 6 h
_KIMI_CACHE = TTLCache(_KIMI_MODELS_TTL)  # keyed par clé API


def _kimi_read_key(slug: str) -> str | None:
    """Clé Kimi présente dans .env (variables acceptées par le moteur selon le provider)."""
    from providers_bridge import hermes_adapter as ha

    names = ("KIMI_CN_API_KEY",) if slug == "kimi-coding-cn" else ("KIMI_API_KEY", "KIMI_CODING_API_KEY")
    for name in names:
        val = ha.read_env_value(name)
        if val:
            return val
    return None


def _kimi_base_for_key(api_key: str, default_base: str) -> str:
    """Endpoint selon le préfixe de la clé : `sk-kimi-` → Coding Plan, sinon le défaut du
    provider (Moonshot classique). Miroir de `_resolve_kimi_base_url` du moteur."""
    return _KIMI_CODE_BASE if api_key.startswith("sk-kimi-") else default_base


def _kimi_served_ids(api_key: str, base: str) -> list[str]:
    """IDs réellement servis par la clé via `GET {base}/models` (authed). Caché par clé
    (TTL 6h). ``[]`` si l'appel échoue (l'appelant retombe alors sur la table figée)."""
    fresh = _KIMI_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _KIMI_CACHE.store(ids, api_key)
    return ids


def _kimi_model_pairs(slug: str, default_base: str, fallback_ids: list[str]) -> list[tuple[str, str]]:
    """Modèles Kimi pour le sélecteur : les IDs réellement servis (`/models` du bon endpoint),
    ordonnés/labellisés via `_display_pairs`. Repli sur la table curée (ou la liste moteur) si
    l'appel échoue. Exclut de fait les fantômes (absents de `/models`)."""
    api_key = _kimi_read_key(slug)
    served = _kimi_served_ids(api_key, _kimi_base_for_key(api_key, default_base)) if api_key else []
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get(slug, [])] or fallback_ids
    return _display_pairs(slug, served)
