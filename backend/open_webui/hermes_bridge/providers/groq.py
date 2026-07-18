"""Groq — catalogue LIVE filtré (hébergeur ultra-rapide, tier gratuit généreux)

`GET /openai/v1/models` (authed — 401 sans clé, donc test de clé fiable sans _PROBE_CHAT) renvoie
17 modèles MAIS sans flag `supports_tools` (juste id/context_window/owned_by). Le catalogue mêle
du chat tool-capable (llama, gpt-oss, qwen) et du NON-chat : STT (whisper), TTS (orpheus), modèles
de garde/modération (prompt-guard, safeguard) et les systèmes agentiques `groq/compound*` qui
REFUSENT le tool calling externe (HTTP 400 « tool calling is not supported » — incompatibles avec
l'agent Hermes, comme Perplexity, testé en réel 2026-07-08). Faute de flag tools, on FILTRE le
bruit non-chat par sous-chaîne (`_GROQ_NON_CHAT`) ; les 7 restants sont tous tool-capable (prouvé
en réel : llama-3.3-70b/llama-3.1-8b/llama-4-scout/gpt-oss-120b/gpt-oss-20b/qwen3-32b/qwen3.6-27b).
Le fallback_models du plugin (`moonshotai/kimi-k2-instruct`) est PÉRIMÉ (absent du live). Ordre +
libellés via `_CURATED_MODELS["groq"]`. Repli figé si offline.
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_GROQ_BASE = "https://api.groq.com/openai/v1"
_GROQ_MODELS_TTL = 6 * 60 * 60  # 6 h
_GROQ_CACHE = TTLCache(_GROQ_MODELS_TTL)  # keyed par clé API
# Sous-chaînes des modèles NON conversationnels ou tool-incapables à écarter (Groq n'expose pas de
# flag tools). compound* = agentiques à outils intégrés qui refusent le tool calling externe (400).
_GROQ_NON_CHAT = ("whisper", "orpheus", "prompt-guard", "safeguard", "allam", "compound")


def _groq_is_chat(model_id: str) -> bool:
    """True si l'ID n'est pas un modèle non-chat/tool-incapable connu (STT/TTS/garde/compound)."""
    low = model_id.lower()
    return not any(tok in low for tok in _GROQ_NON_CHAT)


def _groq_served_ids(api_key: str | None) -> list[str]:
    """IDs chat tool-capable réellement servis (`GET /models` authed, bruit non-chat filtré par
    `_GROQ_NON_CHAT`). Caché par clé (TTL 6h). ``[]`` si l'appel échoue → repli figé."""
    if not api_key:
        return []
    fresh = _GROQ_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{_GROQ_BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id") and _groq_is_chat(m["id"])]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _GROQ_CACHE.store(ids, api_key)
    return ids


def _groq_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Groq pour le sélecteur : catalogue LIVE filtré (bruit non-chat écarté), ordonné +
    labellisé par la table curée. Repli sur la table figée si l'appel échoue (offline)."""
    served = _groq_served_ids(api_key)
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get("groq", [])]
    return _display_pairs("groq", served)
