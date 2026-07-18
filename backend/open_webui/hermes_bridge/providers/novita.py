"""Novita — plateforme d'hébergement (143 modèles). Catalogue /models PUBLIC, riche.

Novita est PAYANT (pas cher, mais dépôt requis) : AUCUN vrai gratuit (les modèles « prix 0 »
renvoient eux aussi 403 « not enough balance » sans solde — vérifié clé client 2026-07-07).
La liste figée du moteur (6 modèles) est pauvre ; le vrai /models a 143 modèles MAIS mêle des
tests bidons (ai_infer_test_*), des versions dev (dev/*), des modèles inactifs (status=4) et
43 non tool-capable (qui planteraient le chat agentique). On expose donc uniquement les vrais
modèles UTILISABLES : status actif + type chat + function-calling, bidons/dev écartés, libellés
via `display_name` (déjà propres). Tout est marqué « 💳 crédit requis » (0 solde) → badge retiré
dès qu'un probe détecte du solde (politique asymétrique). Zéro modif moteur.
"""

from __future__ import annotations

import time

import httpx

from ..ttl_cache import TTLCache
from ._shared import _credit_cache_hit

_NOVITA_BASE_URL = "https://api.novita.ai/openai/v1"
_NOVITA_MODELS_URL = f"{_NOVITA_BASE_URL}/models"
_NOVITA_CATALOG_TTL = 6 * 3600  # 6 h
_NOVITA_CACHE = TTLCache(_NOVITA_CATALOG_TTL)
_novita_credit_cache: dict = {}  # api_key -> {"has": bool, "ts": float}
_NOVITA_PAID_TAG = " 💳 crédit requis"
_NOVITA_CREDIT_PROBE_MODEL = "deepseek/deepseek-v4-flash"  # payant bon marché
_NOVITA_RECOMMENDED = "deepseek/deepseek-v4-flash"


def _fetch_novita_catalog() -> list[dict] | None:
    """Catalogue Novita (GET /models public) : items bruts (id, display_name, status, features,
    model_type). Caché en mémoire (TTL 6h). Repli sur le dernier cache si le réseau échoue."""
    fresh = _NOVITA_CACHE.fresh()
    if fresh is not None:
        return fresh
    try:
        resp = httpx.get(_NOVITA_MODELS_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:  # noqa: BLE001 — réseau/JSON KO = on garde le dernier bon cache
        return _NOVITA_CACHE.last()
    _NOVITA_CACHE.store(data)
    return data


def _novita_has_credit(api_key: str | None) -> bool:
    """True si le compte Novita a du solde (un modèle payant répond 200 ; 403 = non). Politique
    asymétrique par clé (confirmé → jamais re-sondé ; sinon re-sonde /3 min, gratuite)."""
    if not api_key:
        return False
    now = time.time()
    cached = _credit_cache_hit(_novita_credit_cache.get(api_key), api_key, now)
    if cached is not None:
        return cached
    has = False
    try:
        resp = httpx.post(
            f"{_NOVITA_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": _NOVITA_CREDIT_PROBE_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            timeout=8,
        )
        has = resp.status_code == 200
    except httpx.HTTPError:
        has = False
    _novita_credit_cache[api_key] = {"has": has, "ts": now}
    return has


def _novita_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Novita pour le sélecteur : catalogue live filtré (actifs + chat + tool-capable,
    bidons/dev écartés), libellés `display_name`, tri alpha, recommandé (le moins cher) en tête.
    Tout marqué « 💳 crédit requis » sauf si du solde est détecté. Repli vide si indisponible."""
    # Appelle via le module hermes_adapter (pas les noms locaux) : les tests monkeypatchent
    # ``ha._fetch_novita_catalog`` / ``ha._novita_has_credit`` et attendent que cette fonction
    # (ré-exportée sous le même nom) obéisse au double. cf. providers/__init__.py.
    from providers_bridge import hermes_adapter as ha

    catalog = ha._fetch_novita_catalog()
    if not catalog:
        return []
    has_credit = ha._novita_has_credit(api_key)
    pairs: list[tuple[str, str]] = []
    for m in catalog:
        mid = m.get("id")
        if not mid:
            continue
        if m.get("status") != 1 or m.get("model_type") != "chat":
            continue  # actifs + conversation seulement
        if "function-calling" not in (m.get("features") or []):
            continue  # chat agentique : tool-capable requis
        if "test" in mid.lower() or mid.startswith("dev/"):
            continue  # écarte les modèles de test / versions dev internes
        # display_name Novita parfois « sale » (tabulations/espaces multiples) → on normalise.
        name = " ".join((m.get("display_name") or mid).split())
        pairs.append((mid, name if has_credit else name + _NOVITA_PAID_TAG))
    pairs.sort(key=lambda p: p[1].lower())
    head = [p for p in pairs if p[0] == _NOVITA_RECOMMENDED]
    rest = [p for p in pairs if p[0] != _NOVITA_RECOMMENDED]
    return head + rest
