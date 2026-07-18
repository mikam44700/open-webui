"""OpenCode Zen / Go — passerelles opencode.ai. Catalogue /models PUBLIC (id seuls).

Zen = pay-as-you-go : sans moyen de paiement, seuls les modèles « *-free » répondent (les
payants → 401 « No payment method »). La liste FIGÉE du moteur a des FANTÔMES (ex.
minimax-m3-free « not supported ») et n'identifie pas les gratuits. On lit donc le vrai
/models (public), on met les « -free » VALIDES en tête (recommandé), on marque les payants
« 💳 carte requise » — retiré si un probe détecte un moyen de paiement (comme Ollama/Kilo).
Vérifié en réel (clé client 2026-07-07 : 4 gratuits répondent, north-mini-code-free 500).
Zéro modif moteur. Même mécanisme pour Go (endpoint différent).
"""

from __future__ import annotations

import time

import httpx

from ..ttl_cache import TTLCache
from ._shared import _beautify_model_label, _credit_cache_hit

_OPENCODE_MODELS_TTL = 6 * 3600  # 6 h
_OPENCODE_CACHE = TTLCache(_OPENCODE_MODELS_TTL)  # keyed par base_url
_opencode_pay_cache: dict = {}  # api_key -> {"has": bool, "ts": float} (politique asymétrique)
_OPENCODE_PAID_TAG = " 💳 carte requise"
# Modèles « -free » listés mais cassés (500 en réel) → écartés. À revalider périodiquement.
_OPENCODE_BROKEN_FREE = frozenset({"north-mini-code-free"})
_OPENCODE_RECOMMENDED = {
    "opencode-zen": "deepseek-v4-flash-free",  # gratuit, répond sans carte (testé)
    "opencode-go": None,  # renseigné après test de la clé Go (mécanisme identique)
}


def _fetch_opencode_catalog(base_url: str) -> list[str] | None:
    """IDs du catalogue OpenCode (GET /models public). Caché par base_url (TTL 6h). Repli sur
    le dernier cache si le réseau échoue. Ne lève jamais."""
    fresh = _OPENCODE_CACHE.fresh(base_url)
    if fresh is not None:
        return fresh
    try:
        resp = httpx.get(f"{base_url}/models", timeout=6)
        resp.raise_for_status()
        ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
    except Exception:  # noqa: BLE001 — réseau/JSON KO = on garde le dernier bon cache
        return _OPENCODE_CACHE.last(base_url)
    _OPENCODE_CACHE.store(ids, base_url)
    return ids


def _opencode_has_payment(base_url: str, api_key: str | None, probe_model: str | None) -> bool:
    """True si le compte a un moyen de paiement (un modèle PAYANT répond 200 ; 401 CreditsError
    = non). Politique asymétrique par clé : paiement confirmé → jamais re-sondé ; sinon re-sonde
    /3 min (sonde gratuite car rejetée). Sans clé/modèle → False."""
    if not api_key or not probe_model:
        return False
    now = time.time()
    cached = _credit_cache_hit(_opencode_pay_cache.get(api_key), api_key, now)
    if cached is not None:
        return cached
    has = False
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": probe_model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            timeout=8,
        )
        has = resp.status_code == 200
    except httpx.HTTPError:
        has = False
    _opencode_pay_cache[api_key] = {"has": has, "ts": now}
    return has


def _opencode_model_pairs(slug: str, base_url: str, api_key: str | None) -> list[tuple[str, str]]:
    """Modèles OpenCode pour le sélecteur : catalogue live, gratuits « -free » VALIDES en tête
    (recommandé en 1er), payants marqués « 💳 carte requise » sauf si un moyen de paiement est
    détecté. Libellé « -free » → « … (Gratuit) ». Repli vide si catalogue indisponible."""
    # Appelle via le module hermes_adapter (pas les noms locaux) : les tests monkeypatchent
    # ``ha._fetch_opencode_catalog`` / ``ha._opencode_has_payment`` et attendent que cette
    # fonction (ré-exportée sous le même nom) obéisse au double. cf. providers/__init__.py.
    from providers_bridge import hermes_adapter as ha

    ids = ha._fetch_opencode_catalog(base_url)
    if not ids:
        return []
    free = [m for m in ids if m.endswith("-free") and m not in _OPENCODE_BROKEN_FREE]
    paid = [m for m in ids if not m.endswith("-free")]
    has_pay = ha._opencode_has_payment(base_url, api_key, paid[0] if paid else None)
    free_pairs = [
        (m, _beautify_model_label(m[: -len("-free")]) + " (Gratuit)") for m in sorted(free)
    ]
    paid_pairs = []
    for m in sorted(paid):
        lbl = _beautify_model_label(m)
        paid_pairs.append((m, lbl if has_pay else lbl + _OPENCODE_PAID_TAG))
    # Recommandé (gratuit qui répond) en tout premier.
    rec = _OPENCODE_RECOMMENDED.get(slug)
    head = [p for p in free_pairs if p[0] == rec]
    free_rest = [p for p in free_pairs if p[0] != rec]
    return head + free_rest + paid_pairs
