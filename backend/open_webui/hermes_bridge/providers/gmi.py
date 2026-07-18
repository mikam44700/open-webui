"""GMI Cloud — passerelle GPU (api.gmi-serving.com), API OpenAI-compatible.

Le profil moteur ne remonte que ~6 modèles figés ; le vrai /models (authed) en expose 69
(Claude, GPT-5.x, Gemini 3, DeepSeek V3/V4, Qwen3, Kimi K2, GLM-5, MiniMax, Nemotron, MiMo…).
Tous sont des LLM texte (pricing tokens) — vérifié : Tencent Hy3 et Seed-2.0 aussi (pas de
modèle image/vidéo dans la liste). Croisement models.dev : 0 modèle non tool-capable détecté
→ on expose le catalogue live, labels lisibles (nom après « / », Majuscules), tri alpha.
Le /models GMI ne porte AUCUN drapeau outils/type → filtrage tool-capable fin impossible sans
test réel (bloqué tant que le solde est à 0). Solde 0 → « 💳 crédit requis » (asymétrique,
retiré dès qu'un probe voit du solde, comme Novita). Cache par clé (TTL 6h). Zéro modif moteur.
"""

from __future__ import annotations

import time

import httpx

from ..ttl_cache import TTLCache
from ._shared import _credit_cache_hit
from .huggingface import _hf_label

_GMI_BASE_URL = "https://api.gmi-serving.com/v1"
_GMI_MODELS_URL = f"{_GMI_BASE_URL}/models"
_GMI_CATALOG_TTL = 6 * 3600  # 6 h
_GMI_CACHE = TTLCache(_GMI_CATALOG_TTL)  # keyed par clé API
_gmi_credit_cache: dict = {}  # api_key -> {"has": bool, "ts": float}
_GMI_PAID_TAG = " 💳 crédit requis"
_GMI_CREDIT_PROBE_MODEL = "Qwen/Qwen3.5-27B"  # open-source bon marché (402 = pas de solde)


def _gmi_served_ids(api_key: str) -> list[str]:
    """IDs réellement servis par GMI via `GET /models` (authed). Caché par clé (TTL 6h).
    ``[]`` si l'appel échoue → l'appelant retombe sur la liste figée du moteur."""
    fresh = _GMI_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(_GMI_MODELS_URL, headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _GMI_CACHE.store(ids, api_key)
    return ids


def _gmi_has_credit(api_key: str | None) -> bool:
    """True si le compte GMI a du solde (un modèle bon marché répond 200 ; 402 « Insufficient
    balance » = non). Politique asymétrique par clé (confirmé → jamais re-sondé ; sinon /3 min)."""
    if not api_key:
        return False
    now = time.time()
    cached = _credit_cache_hit(_gmi_credit_cache.get(api_key), api_key, now)
    if cached is not None:
        return cached
    has = False
    try:
        resp = httpx.post(
            f"{_GMI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": _GMI_CREDIT_PROBE_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            timeout=8,
        )
        has = resp.status_code == 200
    except httpx.HTTPError:
        has = False
    _gmi_credit_cache[api_key] = {"has": has, "ts": now}
    return has


def _gmi_model_pairs(api_key: str | None, fallback_ids: list[str]) -> list[tuple[str, str]]:
    """Modèles GMI pour le sélecteur : catalogue live (69 modèles), libellés = nom après « / »
    beautifié, tri alpha, badge « 💳 crédit requis » sauf si du solde est détecté. Repli sur la
    liste figée du moteur si l'appel échoue (offline). Pas de « recommandé » (gros catalogue)."""
    served = _gmi_served_ids(api_key) if api_key else []
    if not served:
        served = fallback_ids
    has_credit = _gmi_has_credit(api_key) if api_key else False
    pairs = [
        (mid, _hf_label(mid) if has_credit else _hf_label(mid) + _GMI_PAID_TAG)
        for mid in served
    ]
    pairs.sort(key=lambda p: p[1].lower())
    return pairs
