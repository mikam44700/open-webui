"""Hugging Face — Inference Providers (router.huggingface.co). Catalogue /models PUBLIC.

HF route vers Together/Novita/Fireworks… Chaque modèle du /models liste ses `providers`
(status/pricing/is_free/supports_tools). La liste figée du moteur (9) est pauvre ; le vrai
catalogue a 121 modèles, dont ~85 tool-capable (au moins un provider live `supports_tools`).
Les 36 autres n'ont pas d'outils → planteraient le chat agentique. On expose donc les 85
tool-capable, libellés lisibles (nom après « / », casse HF déjà propre), tri alpha, recommandé
en tête. HF marche via un CRÉDIT MENSUEL GRATUIT (les modèles répondent, prouvé E2E clé client
2026-07-07) → pas de badge « crédit » par défaut. Catalogue public (pas besoin de clé pour le
fetch). Zéro modif moteur.
"""

from __future__ import annotations

import re

import httpx

from ..ttl_cache import TTLCache
from ._shared import _beautify_model_label

_HF_MODELS_URL = "https://router.huggingface.co/v1/models"
_HF_CATALOG_TTL = 6 * 3600  # 6 h
_HF_CACHE = TTLCache(_HF_CATALOG_TTL)
_HF_RECOMMENDED = "deepseek-ai/DeepSeek-V3.2"
# Dates en suffixe des noms HF, à SUPPRIMER (le _beautify générique ne gère que -\d{6,8}) :
# « -03-2025 » (MM-YYYY), « -05.2026 » (MM.YYYY, avec point), « -2507 »/« -0905 »/« -0324 »
# (MMYY/YYMM, 4 chiffres purs — jamais une taille, qui porte une lettre : 70B/80k). Les
# versions (V3.2, 3.6) ont un point mais 1 chiffre avant → « \d{2}\.\d{4} » ne les touche pas.
_HF_DATE_SUFFIX = re.compile(r"(?:-\d{2}-\d{4}|-\d{2}\.\d{4}|-\d{4}|-\d{6,8})$")
# Même date MM-YYYY / MM.YYYY mais en MILIEU de nom, suivie d'un suffixe de quantization
# (ex : « command-a-plus-05-2026-bf16 » → -bf16/-fp8/-w4a4 la suit ; sinon _beautify la
# transformerait en « 05.2026 » et la date resterait affichée au dirigeant).
_HF_DATE_INLINE = re.compile(r"-\d{2}[-.]\d{4}(?=-)")


def _hf_label(model_id: str) -> str:
    """Libellé HF : nom après « / », date retirée (suffixe ET milieu), puis _beautify (Majuscules,
    tailles en B, versions avec « . »). Ex : c4ai-command-a-03-2025 → « C4ai-Command-A »."""
    name = _HF_DATE_INLINE.sub("", model_id.split("/")[-1])
    name = _HF_DATE_SUFFIX.sub("", name)
    return _beautify_model_label(name)


def _huggingface_model_pairs() -> list[tuple[str, str]]:
    """Modèles HF pour le sélecteur : catalogue live filtré tool-capable (>=1 provider live
    `supports_tools`), libellés = nom après « / », tri alpha, recommandé en tête. Caché 6h.
    Repli sur le dernier cache si le réseau échoue."""
    fresh = _HF_CACHE.fresh()
    if fresh is not None:
        return fresh
    try:
        resp = httpx.get(_HF_MODELS_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:  # noqa: BLE001 — réseau/JSON KO = on garde le dernier bon cache
        return _HF_CACHE.last() or []
    pairs: list[tuple[str, str]] = []
    for m in data:
        mid = m.get("id")
        if not mid:
            continue
        live = [p for p in (m.get("providers") or []) if p.get("status") == "live"]
        if not any(p.get("supports_tools") for p in live):
            continue  # chat agentique : au moins un backend live gérant les outils
        pairs.append((mid, _hf_label(mid)))  # nom lisible : Majuscules, sans date
    pairs.sort(key=lambda p: p[1].lower())
    head = [p for p in pairs if p[0] == _HF_RECOMMENDED]
    rest = [p for p in pairs if p[0] != _HF_RECOMMENDED]
    result = head + rest
    _HF_CACHE.store(result)
    return result
