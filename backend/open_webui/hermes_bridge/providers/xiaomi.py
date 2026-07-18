"""Xiaomi MiMo — catalogue LIVE filtré (petit catalogue : 2 LLM + modèles audio à écarter)

`GET /v1/models` (authed — 200 avec clé valide, donc test de clé fiable sans _PROBE_CHAT) renvoie
6 IDs sans flag `supports_tools`/`supports_chat` : les 2 vrais LLM (`mimo-v2.5-pro`, `mimo-v2.5`,
tool-capable + raisonnants prouvés en réel 2026-07-08) ET 4 modèles NON-chat — `-asr`
(reconnaissance vocale) + `-tts`/`-tts-voiceclone`/`-tts-voicedesign` (synthèse) → « Param
Incorrect » (400) sur /chat/completions. Faute de flag, on FILTRE le bruit audio par sous-chaîne
(`_XIAOMI_NON_CHAT`). La liste FIGÉE du moteur ajoutait `mimo-v2-pro/omni/flash` (v2 PÉRIMÉE →
« Unsupported model » 400) : le live les retire tout seuls. Libellés/ordre via `_CURATED_MODELS`.
"""

from __future__ import annotations

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_XIAOMI_BASE = "https://api.xiaomimimo.com/v1"
_XIAOMI_MODELS_TTL = 6 * 60 * 60  # 6 h
_XIAOMI_CACHE = TTLCache(_XIAOMI_MODELS_TTL)  # keyed par clé API
# Sous-chaînes des modèles audio (STT/TTS) à écarter — Xiaomi n'expose pas de flag chat/tools.
_XIAOMI_NON_CHAT = ("asr", "tts")


def _xiaomi_is_chat(model_id: str) -> bool:
    """True si l'ID n'est pas un modèle audio connu (asr = voix→texte, tts = texte→voix)."""
    low = model_id.lower()
    return not any(tok in low for tok in _XIAOMI_NON_CHAT)


def _xiaomi_served_ids(api_key: str | None) -> list[str]:
    """IDs chat réellement servis (`GET /models` authed, bruit audio filtré par `_XIAOMI_NON_CHAT`).
    Caché par clé (TTL 6h). ``[]`` si l'appel échoue → repli figé."""
    if not api_key:
        return []
    fresh = _XIAOMI_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{_XIAOMI_BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id") and _xiaomi_is_chat(m["id"])]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _XIAOMI_CACHE.store(ids, api_key)
    return ids


def _xiaomi_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles Xiaomi MiMo pour le sélecteur : catalogue LIVE filtré (audio écarté, v2 périmée
    retirée), ordonné + labellisé par la table curée. Repli sur la table figée si offline."""
    served = _xiaomi_served_ids(api_key)
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get("xiaomi", [])]
    return _display_pairs("xiaomi", served)
