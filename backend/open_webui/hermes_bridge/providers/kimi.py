"""Kimi / Moonshot — catalogue des modèles utilisables (2 plans auto-routés)

Kimi a deux offres, distinguées par le PRÉFIXE de la clé (comme le moteur, cf.
_resolve_kimi_base_url) : clé `sk-kimi-` = Coding Plan → api.kimi.com/coding ; sinon =
API classique Moonshot → api.moonshot.ai/v1 (ou .cn pour kimi-coding-cn). La liste FIGÉE du
moteur `_PROVIDER_MODELS["kimi-coding"]` est trompeuse. On interroge le vrai endpoint
`/models` (authed), puis, pour une clé Coding Plan, on normalise sa réponse vers les trois IDs
officiellement appelables : `k3`, `kimi-for-coding` et `kimi-for-coding-highspeed`. Le endpoint
peut aussi annoncer des noms de version comme `kimi-k2.7-code`, mais Kimi les refuse au chat
avec HTTP 401 : ils ne doivent donc jamais être proposés au client.
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

# HighSpeed est au catalogue de TOUTES les clés Coding Plan, mais Kimi le refuse au chat
# si le forfait est trop bas (vérifié en réel le 2026-07-22, plan Moderato : HTTP 401
# « Your current subscription does not have access to kimi-for-coding-highspeed »).
_KIMI_HIGHSPEED_ID = "kimi-for-coding-highspeed"
_KIMI_HIGHSPEED_PLAN_REASON = "Forfait Allegretto et plus"
_KIMI_LOCK_CACHE = TTLCache(_KIMI_MODELS_TTL)  # keyed par clé API


def _kimi_code_callable_ids(raw_ids: list[str]) -> list[str]:
    """Réduit le catalogue Coding Plan aux IDs de requête documentés par Kimi.

    Le `/models` peut renvoyer des noms de version non appelables. On conserve l'alias K3
    réellement renvoyé par le compte (`kimi-k3` fonctionne avec la clé testée), mais K2.7 est
    toujours exposé avec son ID de requête officiel `kimi-for-coding`.
    """
    available = set(raw_ids)
    callable_ids: list[str] = []

    if "k3" in available:
        callable_ids.append("k3")
    elif "kimi-k3" in available:
        callable_ids.append("kimi-k3")

    if {"kimi-for-coding-highspeed", "kimi-k2.7-code-highspeed"} & available:
        callable_ids.append("kimi-for-coding-highspeed")
    if {"kimi-for-coding", "kimi-k2.7-code"} & available:
        callable_ids.append("kimi-for-coding")

    return callable_ids


def _kimi_read_key(slug: str) -> str | None:
    """Clé Kimi présente dans .env (variables acceptées par le moteur selon le provider)."""
    # Import différé pour éviter le cycle au chargement de hermes_adapter. Le paquet a été
    # intégré à Open WebUI sous `open_webui.hermes_bridge` : l'ancien nom `providers_bridge`
    # faisait échouer silencieusement le catalogue live et activait le repli non filtré.
    from .. import hermes_adapter as ha

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


def _kimi_highspeed_locked(api_key: str) -> bool:
    """La clé a-t-elle accès à HighSpeed ? Sondé par un appel chat minimal (1 token max),
    caché 6 h par clé. En cas de doute (panne réseau, statut inattendu) : NON verrouillé
    et rien en cache — on ne grise jamais un modèle sur un incident passager."""
    cached = _KIMI_LOCK_CACHE.fresh(api_key)
    if cached is not None:
        return cached
    try:
        resp = httpx.post(
            f"{_KIMI_CODE_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _KIMI_HIGHSPEED_ID,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
            timeout=8,
        )
    except httpx.HTTPError:
        return False
    if resp.status_code == 200:
        locked = False
    elif resp.status_code in (401, 403) and "subscription" in resp.text.lower():
        locked = True
    else:
        return False  # verdict ambigu : pas de verrou, pas de cache
    _KIMI_LOCK_CACHE.store(locked, api_key)
    return locked


def _kimi_unavailable_reasons(slug: str) -> dict[str, str]:
    """Modèles listés au catalogue mais refusés par le FORFAIT de la clé → raison courte
    affichable au client (le front les grise). ``{}`` hors Coding Plan ou si tout passe."""
    api_key = _kimi_read_key(slug)
    if not api_key or not api_key.startswith("sk-kimi-"):
        return {}
    if _kimi_highspeed_locked(api_key):
        return {_KIMI_HIGHSPEED_ID: _KIMI_HIGHSPEED_PLAN_REASON}
    return {}


def _kimi_model_pairs(slug: str, default_base: str, fallback_ids: list[str]) -> list[tuple[str, str]]:
    """Modèles Kimi pour le sélecteur, filtrés et ordonnés pour l'offre de la clé."""
    api_key = _kimi_read_key(slug)
    base = _kimi_base_for_key(api_key, default_base) if api_key else default_base
    served = _kimi_served_ids(api_key, base) if api_key else []
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get(slug, [])] or fallback_ids
    if api_key and api_key.startswith("sk-kimi-"):
        served = _kimi_code_callable_ids(served)
        if _KIMI_HIGHSPEED_ID in served:
            # Chauffe le cache du verrou forfait pendant la passe parallèle du bridge :
            # l'assemblage des providers (passe locale) le relira sans appel réseau.
            _kimi_highspeed_locked(api_key)
    return _display_pairs(slug, served)
