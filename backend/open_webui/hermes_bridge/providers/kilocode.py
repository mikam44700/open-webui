"""Kilo Code — passerelle multi-modèles (~340 modèles). Catalogue /models PUBLIC.

Kilo route vers Claude/GPT/Gemini/NVIDIA… Une clé = accès selon le SOLDE de crédits : les
modèles gratuits (champ `isFree`) répondent sans crédit ; les payants renvoient 402 « Paid
Model - Credits Required » tant que balance=0 (constaté en réel, clé client 2026-07-07 :
les 5 modèles figés du moteur étaient TOUS payants → un compte à 0 crédit ne pouvait rien
faire, et le test de clé mentait « refusée » sur un simple 402). On expose donc TOUT le
catalogue tool-capable (le chat est agentique), GRATUITS EN TÊTE (utilisables tout de suite),
et on marque les payants « 💳 crédit requis » — badge RETIRÉ dès qu'un probe détecte des
crédits (détection auto par clé, comme Ollama Cloud). Recommandé/auto-activation =
kilo-auto/free → un compte à 0 crédit a quand même un cerveau qui répond. Zéro modif moteur.
"""

from __future__ import annotations

import time

import httpx

from ..ttl_cache import TTLCache
from ._shared import _credit_cache_hit

_KILOCODE_BASE_URL = "https://api.kilo.ai/api/gateway"
_KILOCODE_MODELS_URL = f"{_KILOCODE_BASE_URL}/models"
_KILOCODE_CATALOG_TTL = 6 * 3600  # 6 h
_KILOCODE_CACHE = TTLCache(_KILOCODE_CATALOG_TTL)
# Sonde de crédit : un modèle PAYANT courant. 402 = pas de crédit, 200 = crédit. Caché par clé
# (politique asymétrique _credit_cache_hit : True définitif, False re-sondé toutes les 3 min).
_KILOCODE_CREDIT_PROBE_MODEL = "openai/gpt-5.4"
_kilocode_credit_cache: dict = {}  # api_key -> {"has": bool, "ts": float}
_KILOCODE_PAID_TAG = " 💳 crédit requis"
_KILOCODE_RECOMMENDED = "kilo-auto/free"


def _fetch_kilocode_catalog() -> list[dict] | None:
    """Catalogue Kilo (public) : items bruts {id, name, isFree, supported_parameters}.
    Caché en mémoire (TTL 6h). Repli sur le dernier cache si le réseau échoue. Ne lève jamais."""
    fresh = _KILOCODE_CACHE.fresh()
    if fresh is not None:
        return fresh
    try:
        resp = httpx.get(_KILOCODE_MODELS_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:  # noqa: BLE001 — réseau/JSON KO = on garde le dernier bon cache
        return _KILOCODE_CACHE.last()
    _KILOCODE_CACHE.store(data)
    return data


def _kilocode_has_credit(api_key: str | None) -> bool:
    """True si le compte Kilo a des crédits (un modèle payant répond 200 ; 402 = non).
    Politique asymétrique par clé : crédit confirmé → jamais re-sondé ; sinon re-sonde /3 min
    (sonde gratuite car rejetée). Sans clé → False (payants marqués « crédit requis »)."""
    if not api_key:
        return False
    now = time.time()
    cached = _credit_cache_hit(_kilocode_credit_cache.get(api_key), api_key, now)
    if cached is not None:
        return cached
    has = False
    try:
        resp = httpx.post(
            f"{_KILOCODE_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _KILOCODE_CREDIT_PROBE_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
            timeout=8,
        )
        has = resp.status_code == 200
    except httpx.HTTPError:
        has = False
    _kilocode_credit_cache[api_key] = {"has": has, "ts": now}
    return has


def _kilocode_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Kilo pour le sélecteur : catalogue live tool-capable, GRATUITS en tête
    (kilo-auto/free en 1er = recommandé), payants marqués « 💳 crédit requis » sauf si le
    compte a des crédits. Repli minimal si le catalogue est indisponible (offline)."""
    # Appelle via le module hermes_adapter (pas les noms locaux) : les tests monkeypatchent
    # ``ha._fetch_kilocode_catalog`` / ``ha._kilocode_has_credit`` et s'attendent à ce que cette
    # fonction (ré-exportée sous le même nom) obéisse au double. cf. providers/__init__.py.
    from providers_bridge import hermes_adapter as ha

    catalog = ha._fetch_kilocode_catalog()
    if not catalog:
        return [(_KILOCODE_RECOMMENDED, "Auto Free")]
    has_credit = ha._kilocode_has_credit(api_key)
    free_pairs: list[tuple[str, str]] = []
    paid_pairs: list[tuple[str, str]] = []
    for m in catalog:
        sp = m.get("supported_parameters")
        if not (isinstance(sp, list) and "tools" in sp):
            continue  # chat agentique : on n'expose que les modèles tool-capable
        mid = m.get("id")
        if not mid:
            continue
        name = m.get("name") or mid
        if m.get("isFree"):
            free_pairs.append((mid, name))
        else:
            paid_pairs.append((mid, name if has_credit else name + _KILOCODE_PAID_TAG))
    free_pairs.sort(key=lambda p: p[1].lower())
    paid_pairs.sort(key=lambda p: p[1].lower())
    # kilo-auto/free en tout premier (recommandé), puis les autres gratuits, puis les payants.
    auto = [p for p in free_pairs if p[0] == _KILOCODE_RECOMMENDED]
    free_rest = [p for p in free_pairs if p[0] != _KILOCODE_RECOMMENDED]
    return auto + free_rest + paid_pairs
