"""Ollama Cloud : liste FIGÉE curée, validée par test réel (2026-07-06). Le catalogue
/v1/models est PUBLIC (34 modèles) mais ne fournit QUE des IDs bruts (« deepseek-v4-pro »)
et ne dit RIEN du tool calling ni du palier requis. Test réel (chat + tools, clé du palier
GRATUIT) : les 34 acceptent les outils (Ollama template les tools côté serveur), MAIS 14
renvoient HTTP 403 « this model requires a subscription » sur le palier gratuit. On expose
donc les 34 avec des noms LISIBLES, les 20 GRATUITS en tête (grands noms d'abord) puis les
14 PREMIUM marqués « 🔒 Abonnement » → le client voit tout de suite ce qui est inclus vs
payant (plus de 403 mystère). Un client Pro/Max accède aux 14 (on ne bride personne).
⚠️ Le modèle d'auto-activation (_RECOMMENDED_MODEL) DOIT rester un GRATUIT, sinon un client
gratuit s'auto-activerait sur un 403 (assistant cassé au 1er message). À revalider quand
Ollama fait évoluer sa flotte cloud.
"""

from __future__ import annotations

import json
import time

_OLLAMA_CLOUD_MODELS: list[tuple[str, str]] = [
    # --- Gratuits (palier free, tool calling confirmé) — grands noms d'abord ---
    ("gpt-oss:120b", "OpenAI : Gpt-Oss-120B"),
    ("gpt-oss:20b", "OpenAI : Gpt-Oss-20B"),
    ("qwen3-coder:480b", "Qwen : Qwen3-Coder-480B"),
    ("qwen3-coder-next", "Qwen : Qwen3-Coder-Next"),
    ("minimax-m3", "MiniMax : M3"),
    ("minimax-m2.5", "MiniMax : M2.5"),
    ("minimax-m2.1", "MiniMax : M2.1"),
    ("glm-4.7", "GLM : GLM-4.7"),
    ("nemotron-3-ultra", "NVIDIA : Nemotron-3-Ultra"),
    ("nemotron-3-super", "NVIDIA : Nemotron-3-Super"),
    ("nemotron-3-nano:30b", "NVIDIA : Nemotron-3-Nano-30B"),
    ("devstral-2:123b", "Mistral : Devstral-2-123B"),
    ("devstral-small-2:24b", "Mistral : Devstral-Small-2-24B"),
    ("ministral-3:14b", "Mistral : Ministral-3-14B"),
    ("ministral-3:8b", "Mistral : Ministral-3-8B"),
    ("ministral-3:3b", "Mistral : Ministral-3-3B"),
    ("gemma4:31b", "Google : Gemma-4-31B"),
    ("gemma3:27b", "Google : Gemma-3-27B"),
    ("gemma3:12b", "Google : Gemma-3-12B"),
    ("gemma3:4b", "Google : Gemma-3-4B"),
    # --- Premium (abonnement Ollama Cloud requis — 403 sur le palier gratuit) ---
    ("deepseek-v4-pro", "DeepSeek : V4-Pro 🔒 Abonnement"),
    ("deepseek-v4-flash", "DeepSeek : V4-Flash 🔒 Abonnement"),
    ("deepseek-v3.2", "DeepSeek : V3.2 🔒 Abonnement"),
    ("deepseek-v3.1:671b", "DeepSeek : V3.1-671B 🔒 Abonnement"),
    ("glm-5.2", "GLM : GLM-5.2 🔒 Abonnement"),
    ("glm-5.1", "GLM : GLM-5.1 🔒 Abonnement"),
    ("glm-5", "GLM : GLM-5 🔒 Abonnement"),
    ("kimi-k2.7-code", "Moonshot : Kimi-K2.7-Code 🔒 Abonnement"),
    ("kimi-k2.6", "Moonshot : Kimi-K2.6 🔒 Abonnement"),
    ("kimi-k2.5", "Moonshot : Kimi-K2.5 🔒 Abonnement"),
    ("minimax-m2.7", "MiniMax : M2.7 🔒 Abonnement"),
    ("mistral-large-3:675b", "Mistral : Large-3-675B 🔒 Abonnement"),
    ("qwen3.5:397b", "Qwen : Qwen3.5-397B 🔒 Abonnement"),
    ("gemini-3-flash-preview", "Google : Gemini-3-Flash-Preview 🔒 Abonnement"),
]

# Détection d'abonnement Ollama Cloud : il n'existe AUCUN endpoint compte/abonnement
# exploitable (/api/user, /api/subscription… → 404) et /v1/models est public (34 modèles
# quel que soit le palier). Le SEUL signal fiable = tenter un modèle premium : 403
# « requires a subscription » = palier gratuit, 200 = abonné (Pro/Max). Un probe premium ne
# consomme rien en gratuit (403 immédiat, zéro GPU) et max_tokens=1 en abonné est trivial.
# Résultat caché PAR CLÉ (TTL 30 min) car list_providers est appelé souvent : on ne re-probe
# pas à chaque affichage, et on re-vérifie régulièrement (un client peut s'abonner en cours).
_OLLAMA_PREMIUM_PROBE_MODEL = "deepseek-v4-pro"
_OLLAMA_SUB_TTL = 30 * 60  # 30 min
_ollama_sub_cache: dict = {"key": None, "subscribed": None, "ts": 0.0}


def _ollama_is_subscribed(api_key: str) -> bool | None:
    """``True`` si la clé Ollama Cloud a un abonnement (un modèle premium répond 200),
    ``False`` si palier gratuit (403), ``None`` si indéterminé (réseau/429 → on n'affirme
    rien, on garde les cadenas côté appelant). Ne lève jamais. Caché par clé (TTL 30 min)."""
    # Passe par le module hermes_adapter pour _http_status ET pour le cache : les tests
    # monkeypatchent ``ha._http_status`` et remplacent ``ha._ollama_sub_cache`` par un dict
    # neuf — cette fonction (ré-exportée sous le même nom) doit observer les deux. cf.
    # providers/__init__.py.
    from providers_bridge import hermes_adapter as ha

    now = time.time()
    c = ha._ollama_sub_cache
    if c["key"] == api_key and c["subscribed"] is not None and (now - c["ts"]) < _OLLAMA_SUB_TTL:
        return c["subscribed"]
    body = json.dumps({
        "model": _OLLAMA_PREMIUM_PROBE_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    })
    status, _reason, _err = ha._http_status(
        "https://ollama.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST", body=body,
    )
    if status == 200:
        result: bool = True
    elif status == 403:
        result = False
    else:
        return None  # indéterminé : on ne cache pas, prochain appel ré-essaiera
    ha._ollama_sub_cache.update({"key": api_key, "subscribed": result, "ts": now})
    return result


def _ollama_cloud_model_pairs() -> list[tuple[str, str]]:
    """Modèles Ollama Cloud pour le sélecteur, TOUS triés par ordre alphabétique (gratuits et
    premium mélangés), selon l'abonnement de la clé configurée :
    - ABONNÉ (probe premium → 200) : les 34 DÉBLOQUÉS (sans « 🔒 »).
    - GRATUIT / indéterminé : les 34, premium marqués « 🔒 Abonnement »."""
    # cf. commentaire de _ollama_is_subscribed : lookup via ha (read_env_value + le probe
    # sibling monkeypatchés dans les tests).
    from providers_bridge import hermes_adapter as ha

    api_key = ha.read_env_value("OLLAMA_API_KEY")
    if api_key and ha._ollama_is_subscribed(api_key) is True:
        pairs = [(mid, lbl.replace(" 🔒 Abonnement", "")) for mid, lbl in _OLLAMA_CLOUD_MODELS]
    else:
        pairs = list(_OLLAMA_CLOUD_MODELS)
    return sorted(pairs, key=lambda m: m[1].lower())
