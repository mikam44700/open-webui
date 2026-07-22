"""Métadonnées et politique UX du catalogue de modèles LunarIA.

La disponibilité d'un modèle reste décidée par Hermes / l'API du fournisseur. Ce module
n'ajoute jamais un modèle de lui-même : il enrichit uniquement les modèles déjà exposés avec
les métadonnées publiques de models.dev (date, raisonnement, efforts) et applique une politique
totale, valable aussi pour un fournisseur futur inconnu du code.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .ttl_cache import TTLCache

SMALL_CATALOG_MAX = 12

# Corrections vérifiées sur les sources officielles Kimi. models.dev reste la source
# générale du catalogue, mais ses fiches peuvent avoir quelques jours de retard lors
# d'une sortie (cas K3) ou contenir une date sentinelle (K2.5 = 1970-01-01). Les valeurs
# d'effort sont celles comprises par l'UI Hermes : xhigh est appliqué comme max par K3.
# Ces overrides n'ajoutent JAMAIS un modèle : ils enrichissent uniquement un ID que
# l'API du client a réellement renvoyé.
_KIMI_VERIFIED_METADATA: dict[str, dict[str, object]] = {
    "kimi-k3": {
        "release_date": "2026-07-16",
        "reasoning": True,
        "supported_efforts": ["low", "high", "xhigh"],
        "confidence": "official_kimi",
    },
    # Identifiant canonique documenté par Kimi Code ; conservé pour les futures réponses
    # live même si la clé testée aujourd'hui renvoie encore l'alias `kimi-k3`.
    "k3": {
        "release_date": "2026-07-16",
        "reasoning": True,
        "supported_efforts": ["low", "high", "xhigh"],
        "confidence": "official_kimi",
    },
    "kimi-for-coding-highspeed": {
        "release_date": "2026-06-12",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2.7-code-highspeed": {
        "release_date": "2026-06-12",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2.7-code": {
        "release_date": "2026-06-12",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-for-coding": {
        "release_date": "2026-06-12",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2.6": {
        "release_date": "2026-04-20",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2.5": {
        "release_date": "2026-01-27",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2-thinking-turbo": {
        "release_date": "2025-11-06",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2-thinking": {
        "release_date": "2025-11-06",
        "reasoning": True,
        "supported_efforts": None,
        "confidence": "official_kimi",
    },
    "kimi-k2-0905-preview": {
        "release_date": "2025-09-05",
        "reasoning": False,
        "supported_efforts": [],
        "confidence": "official_kimi",
    },
    "kimi-k2-turbo-preview": {
        "release_date": "2025-08-01",
        "reasoning": False,
        "supported_efforts": [],
        "confidence": "official_kimi",
    },
}


def verified_model_metadata(provider_id: str, model_id: str) -> dict[str, object]:
    """Métadonnées officielles locales pour les sorties trop récentes du registre général."""
    if provider_id not in {"kimi-coding", "kimi-coding-cn"}:
        return {}
    return dict(_KIMI_VERIFIED_METADATA.get((model_id or "").lower(), {}))


def _apply_verified_metadata(
    metadata: dict[str, dict[str, dict]], requested: dict[str, list[str]]
) -> dict[str, dict[str, dict]]:
    """Superpose les preuves officielles sans jamais créer un modèle non demandé."""
    for provider_id, model_ids in requested.items():
        for model_id in model_ids:
            override = verified_model_metadata(provider_id, model_id)
            if not override:
                continue
            current = metadata.setdefault(provider_id, {}).setdefault(model_id, {})
            current.update(override)
    return metadata

# Sources réellement utilisées par hermes_adapter._provider_model_pairs. Les fournisseurs
# absents de ces ensembles retombent automatiquement sur le catalogue Hermes : cette règle
# par défaut garantit qu'un nouveau provider reçoit une politique et apparaît dans l'audit.
LIVE_CATALOG_PROVIDERS = frozenset(
    {
        "nous",
        "openai-codex",
        "openrouter",
        "kilocode",
        "opencode-zen",
        "opencode-go",
        "novita",
        "gmi",
        "huggingface",
        "cerebras",
        "fireworks",
        "groq",
        "xiaomi",
        "stepfun",
        "kimi-coding",
        "kimi-coding-cn",
    }
)
CURATED_CATALOG_PROVIDERS = frozenset({"nvidia", "cohere", "ollama-cloud", "zai"})
LOCAL_CATALOG_PROVIDERS = frozenset({"ollama-local", "lmstudio", "custom"})


def provider_catalog_policy(provider_id: str, model_count: int) -> dict[str, str]:
    """Politique exhaustive par construction : aucun provider ne peut rester sans réponse."""
    if provider_id in LIVE_CATALOG_PROVIDERS:
        source = "live_api"
        refresh = "automatic"
    elif provider_id in CURATED_CATALOG_PROVIDERS:
        source = "verified_curation"
        refresh = "engine_update"
    elif provider_id in LOCAL_CATALOG_PROVIDERS:
        source = "local_runtime"
        refresh = "automatic"
    else:
        source = "hermes_catalog"
        refresh = "engine_update"
    return {
        "source": source,
        "refresh": refresh,
        "sort": "alphabetical_search" if model_count > SMALL_CATALOG_MAX else "recent_first",
    }


_TOKEN_CASE = {
    "ai": "AI",
    "api": "API",
    "asr": "ASR",
    "gpt": "GPT",
    "glm": "GLM",
    "llm": "LLM",
    "oss": "OSS",
    "pdf": "PDF",
    "r1": "R1",
    "tts": "TTS",
    "vl": "VL",
}
_BRAND_CASE = {
    "anthropic": "Anthropic",
    "cohere": "Cohere",
    "deepseek": "DeepSeek",
    "fireworks": "Fireworks",
    "gemini": "Gemini",
    "grok": "Grok",
    "llama": "Llama",
    "minimax": "MiniMax",
    "mimo": "MiMo",
    "mistral": "Mistral",
    "nvidia": "NVIDIA",
    "openai": "OpenAI",
    "qwen": "Qwen",
}


def _clean_token(token: str) -> str:
    if "/" in token:
        return "/".join(_clean_token(part) for part in token.split("/"))
    lower = token.lower()
    if lower in _TOKEN_CASE:
        return _TOKEN_CASE[lower]
    if lower in _BRAND_CASE:
        return _BRAND_CASE[lower]
    # Certains identifiants collent la marque et la version avec un point
    # (ex. Bedrock ``deepseek.v3.2``). On corrige la marque sans toucher au reste.
    brand_prefix = re.match(r"^([a-z]+)([._].+)$", token, re.IGNORECASE)
    if brand_prefix and brand_prefix.group(1).lower() in _BRAND_CASE:
        return f"{_BRAND_CASE[brand_prefix.group(1).lower()]}{brand_prefix.group(2)}"
    # Tailles de modèles : 120b -> 120B, 8k -> 8K. Les versions restent inchangées.
    size = re.fullmatch(r"(\d+(?:\.\d+)?)([bkm])", lower)
    if size:
        return f"{size.group(1)}{size.group(2).upper()}"
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return token
    return token[:1].upper() + token[1:] if token else token


def clean_model_label(label: str, model_id: str = "") -> str:
    """Normalise uniquement le libellé visible ; l'identifiant API n'est jamais modifié."""
    raw = (label or model_id).strip().replace(":", "-")
    # Préserve les séparateurs de chemin des passerelles dans l'ID technique, mais montre un
    # libellé compact. Un label officiel contenant « Provider: Model » est déjà lisible.
    if ": " in (label or ""):
        provider, name = (label or "").split(": ", 1)
        return f"{_clean_token(provider)}: {clean_model_label(name, model_id)}"
    parts = [p for p in raw.split("-") if p]
    return "-".join(_clean_token(part) for part in parts)


_METADATA_CACHE = TTLCache(3600)  # models.dev se rafraîchit lui-même toutes les heures.

_METADATA_SCRIPT = r"""
import json, sys
from agent.models_dev import PROVIDER_TO_MODELS_DEV, fetch_models_dev

requested = json.load(sys.stdin)
data = fetch_models_dev()
extra = {
    "openai-api": "openai",
    "together": "togetherai",
    "baidu-ernie": "baidu",
}

global_index = {}
for pid, pdata in data.items():
    models = pdata.get("models", {}) if isinstance(pdata, dict) else {}
    if not isinstance(models, dict):
        continue
    for mid, raw in models.items():
        if isinstance(raw, dict):
            global_index.setdefault(str(mid).lower(), (pid, mid, raw))

out = {}
for provider_id, model_ids in requested.items():
    mdev_id = PROVIDER_TO_MODELS_DEV.get(provider_id, extra.get(provider_id, provider_id))
    pdata = data.get(mdev_id, {})
    pmodels = pdata.get("models", {}) if isinstance(pdata, dict) else {}
    if not isinstance(pmodels, dict):
        pmodels = {}
    lower_provider = {str(k).lower(): (k, v) for k, v in pmodels.items() if isinstance(v, dict)}
    provider_out = {}
    for model_id in model_ids:
        key = str(model_id).lower()
        found = lower_provider.get(key)
        confidence = "models_dev"
        # Les alias Hermes « -pro » utilisent le mode pro du même modèle de base.
        if found is None and key.endswith("-pro"):
            found = lower_provider.get(key[:-4])
            confidence = "family"
        if found is None:
            global_found = global_index.get(key)
            if global_found:
                _pid, canonical, raw = global_found
                found = (canonical, raw)
                confidence = "models_dev_global"
        if found is None:
            continue
        canonical, raw = found
        reasoning = bool(raw.get("reasoning", False))
        effort_values = None
        options = raw.get("reasoning_options")
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict) and option.get("type") == "effort" and isinstance(option.get("values"), list):
                    effort_values = [e for e in ("low", "medium", "high", "xhigh") if e in option["values"]]
                    break
        provider_out[model_id] = {
            "canonical_id": canonical,
            "name": raw.get("name") or "",
            "release_date": raw.get("release_date") or "",
            "family": raw.get("family") or "",
            "reasoning": reasoning,
            "supported_efforts": effort_values,
            "confidence": confidence,
        }
    out[provider_id] = provider_out
print(json.dumps(out))
"""


def load_model_metadata(
    hermes_python: str, hermes_home: Path, requested: dict[str, list[str]]
) -> dict[str, dict[str, dict]]:
    """Charge toutes les métadonnées en un seul sous-processus, sans clé ni requête LLM."""
    cached = _METADATA_CACHE.fresh()
    if cached is not None and all(
        all(mid in cached.get(provider_id, {}) for mid in model_ids)
        for provider_id, model_ids in requested.items()
    ):
        return _apply_verified_metadata(cached, requested)
    if not Path(hermes_python).exists():
        return {}
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    try:
        result = subprocess.run(
            [hermes_python, "-c", _METADATA_SCRIPT],
            input=json.dumps(requested),
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        if result.returncode != 0:
            return _apply_verified_metadata(_METADATA_CACHE.last() or {}, requested)
        metadata = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return _apply_verified_metadata(_METADATA_CACHE.last() or {}, requested)
    if cached:
        merged = {provider_id: dict(items) for provider_id, items in cached.items()}
        for provider_id, items in metadata.items():
            merged.setdefault(provider_id, {}).update(items)
        metadata = merged
    metadata = _apply_verified_metadata(metadata, requested)
    _METADATA_CACHE.store(metadata)
    return metadata
