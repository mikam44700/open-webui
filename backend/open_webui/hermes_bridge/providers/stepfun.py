"""StepFun Step Plan — catalogue LIVE filtré (endpoint direct `api.stepfun.ai/step_plan`)

`GET /step_plan/v1/models` (authed) renvoie 200 avec 2 IDs — MÊME sans abonnement actif : la clé
est valide, mais le CHAT exige un forfait « Step Plan » payant (`POST /chat/completions` → 400
« you have no active step plan subscription »). Non testé E2E faute d'abonnement (choix client
2026-07-08). Les 2 IDs servis : `step-3.5-flash` (alias stable) + `step-3.5-flash-2603` (snapshot
daté = même modèle → écarté par `_stepfun_is_canonical`, on n'expose que l'alias). Step-3.5-Flash :
MoE 196.8B total / 11B actifs, RAISONNE (99.8% AIME 2025, 98% HMMT 2025 — specs officielles),
text-only (le multimodal n'arrive qu'en Step-3.7), 256K de contexte, agentic (74.4% SWE-bench).
"""

from __future__ import annotations

import re

import httpx

from ..ttl_cache import TTLCache
from ._shared import _CURATED_MODELS, _display_pairs

_STEPFUN_BASE = "https://api.stepfun.ai/step_plan/v1"
_STEPFUN_MODELS_TTL = 6 * 60 * 60  # 6 h
_STEPFUN_CACHE = TTLCache(_STEPFUN_MODELS_TTL)  # keyed par clé API


def _stepfun_is_canonical(model_id: str) -> bool:
    """True si l'ID n'est pas un snapshot daté (`-2603`, `-YYMM`), doublon de l'alias stable."""
    return not re.search(r"-\d{4}$", model_id or "")


def _stepfun_served_ids(api_key: str | None) -> list[str]:
    """IDs chat réellement servis (`GET /models` authed, snapshots datés écartés). Caché par clé
    (TTL 6h). ``[]`` si l'appel échoue → repli figé. Le 200 ne garantit PAS l'abonnement Step Plan."""
    if not api_key:
        return []
    fresh = _STEPFUN_CACHE.fresh(api_key)
    if fresh is not None:
        return fresh
    ids: list[str] = []
    try:
        resp = httpx.get(f"{_STEPFUN_BASE}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id") and _stepfun_is_canonical(m["id"])]
    except (httpx.HTTPError, ValueError, KeyError):
        ids = []
    if ids:
        _STEPFUN_CACHE.store(ids, api_key)
    return ids


def _stepfun_model_pairs(api_key: str | None) -> list[tuple[str, str]]:
    """Modèles StepFun pour le sélecteur : catalogue LIVE filtré (snapshots datés écartés),
    ordonné + labellisé par la table curée. Repli sur la table figée si offline."""
    served = _stepfun_served_ids(api_key)
    if not served:
        served = [mid for mid, _lbl in _CURATED_MODELS.get("stepfun", [])]
    return _display_pairs("stepfun", served)
