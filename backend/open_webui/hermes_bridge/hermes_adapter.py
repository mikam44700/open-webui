"""Adapter Hermes — seul point qui parle à Hermes.

Stratégie (cf. specs/001-providers-page/research.md D2) :
- LISTER les providers/modèles : on interroge Hermes via SON propre interpréteur Python
  (subprocess JSON), pour éviter tout souci de version Python côté bridge.
- ÉTAT des clés : lecture de ``~/.hermes/.env`` (présence seulement, jamais la valeur).
- CERVEAU actif : lecture de ``~/.hermes/config.yaml`` (``model.provider`` / ``model.default``).
- ÉCRITURE (clé / provider / modèle) : ``hermes config set ...`` (non-interactif, atomique).

Tout est configurable par variables d'env (utile pour le déploiement) :
- ``HERMES_HOME``   (défaut ``~/.hermes``)
- ``HERMES_PYTHON`` (défaut ``<HERMES_HOME>/hermes-agent/venv/bin/python``)
- ``HERMES_BIN``    (défaut ``hermes`` dans le PATH)
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import httpx
import yaml

from . import fsutil
from .model_catalog import clean_model_label, load_model_metadata, provider_catalog_policy
from .models import ActiveSelection, AuthType, Category, Model, Provider, ProviderState
from .ttl_cache import TTLCache

logger = logging.getLogger(__name__)

# Ré-exports : le socle (ci-dessous) + les modules providers/<nom>.py (un par fournisseur de
# passerelle) formaient un seul fichier de ~2800 lignes. Découpé pour rester sous la limite
# projet (800 lignes/fichier) — cf. providers/__init__.py pour la règle anti-cycle. Les tests
# accèdent à ces symboles via ``hermes_adapter.<nom>`` (ex. ``ha._groq_served_ids``) : les
# imports ci-dessous PRÉSERVENT cet accès, comportement strictement identique.
from .providers._shared import (  # noqa: F401 — ré-export intentionnel (cf. commentaire ci-dessus)
    _beautify_model_label,
    _CURATED_MODELS,
    _COHERE_CURATED_MODELS,
    _credit_cache_hit,
    _CREDIT_RECHECK_TTL,
    _display_pairs,
    _NVIDIA_CURATED_MODELS,
)
from .providers.openrouter import (  # noqa: F401 — ré-export intentionnel
    _fetch_openrouter_catalog,
    _openrouter_model_list,
    _OPENROUTER_CACHE,
)
from .providers.kilocode import (  # noqa: F401 — ré-export intentionnel
    _fetch_kilocode_catalog,
    _kilocode_has_credit,
    _kilocode_model_pairs,
    _kilocode_credit_cache,
    _KILOCODE_CACHE,
    _KILOCODE_RECOMMENDED,
)
from .providers.opencode import (  # noqa: F401 — ré-export intentionnel
    _fetch_opencode_catalog,
    _opencode_has_payment,
    _opencode_model_pairs,
    _opencode_pay_cache,
    _OPENCODE_CACHE,
    _OPENCODE_BROKEN_FREE,
    _OPENCODE_RECOMMENDED,
)
from .providers.novita import (  # noqa: F401 — ré-export intentionnel
    _fetch_novita_catalog,
    _novita_has_credit,
    _novita_model_pairs,
    _novita_credit_cache,
    _NOVITA_CACHE,
    _NOVITA_RECOMMENDED,
)
from .providers.huggingface import (  # noqa: F401 — ré-export intentionnel
    _hf_label,
    _huggingface_model_pairs,
    _HF_CACHE,
)
from .providers.gmi import (  # noqa: F401 — ré-export intentionnel
    _gmi_served_ids,
    _gmi_has_credit,
    _gmi_model_pairs,
    _gmi_credit_cache,
    _GMI_CACHE,
)
from .providers.ollama_cloud import (  # noqa: F401 — ré-export intentionnel
    _OLLAMA_CLOUD_MODELS,
    _ollama_is_subscribed,
    _ollama_cloud_model_pairs,
    _ollama_sub_cache,
)
from .providers.zai import (  # noqa: F401 — ré-export intentionnel
    _ZAI_FREE_MODELS,
    _ZAI_PAID_MODELS,
    _zai_read_key,
    _zai_probe,
    _zai_mode,
    _zai_mode_cache,
    _zai_model_pairs,
)
from .providers.cerebras import (  # noqa: F401 — ré-export intentionnel
    _cerebras_served_ids,
    _cerebras_model_pairs,
    _CEREBRAS_CACHE,
)
from .providers.fireworks import (  # noqa: F401 — ré-export intentionnel
    _fireworks_served_ids,
    _fireworks_model_pairs,
    _FIREWORKS_CACHE,
    _FIREWORKS_BROKEN,
)
from .providers.groq import (  # noqa: F401 — ré-export intentionnel
    _groq_is_chat,
    _groq_served_ids,
    _groq_model_pairs,
    _GROQ_CACHE,
    _GROQ_NON_CHAT,
)
from .providers.xiaomi import (  # noqa: F401 — ré-export intentionnel
    _xiaomi_is_chat,
    _xiaomi_served_ids,
    _xiaomi_model_pairs,
    _XIAOMI_CACHE,
    _XIAOMI_NON_CHAT,
)
from .providers.stepfun import (  # noqa: F401 — ré-export intentionnel
    _stepfun_is_canonical,
    _stepfun_served_ids,
    _stepfun_model_pairs,
    _STEPFUN_CACHE,
)
from .providers.kimi import (  # noqa: F401 — ré-export intentionnel
    _kimi_read_key,
    _kimi_base_for_key,
    _kimi_served_ids,
    _kimi_model_pairs,
    _kimi_unavailable_reasons,
    _KIMI_CACHE,
    _KIMI_CODE_BASE,
)

HERMES_HOME = Path(os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes")))
HERMES_PYTHON = os.path.expanduser(
    os.environ.get("HERMES_PYTHON", str(HERMES_HOME / "hermes-agent" / "venv" / "bin" / "python"))
)
HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")

# « Modèle local (confidentiel) » via un serveur Ollama local. Injecté par le bridge
# (pas dans le catalogue Hermes : ollama local = provider « custom », URL propre à la
# machine). Configurable pour le déploiement (Ollama distant sur le réseau du client).
OLLAMA_LOCAL_ID = "ollama-local"
OLLAMA_LOCAL_BASE_URL = os.environ.get("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434")

# slug Hermes -> nom de fichier de logo (dans le fork : src/lib/assets/providers/<logo>.svg)
_LOGO_BY_SLUG: dict[str, str] = {
    "nous": "nous-research", "openrouter": "openrouter", "anthropic": "claude-color",
    "moa": "nousresearch",  # Mixture of Agents = technique interne du moteur -> logo Hermes Agent
    "openai-codex": "codex", "openai-api": "openai", "gemini": "gemini-color",
    "deepseek": "deepseek-color", "xai": "grok", "xai-oauth": "grok", "zai": "zai",
    "kimi-coding": "moonshot", "kimi-coding-cn": "moonshot", "minimax": "minimax-color",
    "minimax-cn": "minimax-color", "minimax-oauth": "minimax-color", "alibaba": "qwen",
    "alibaba-coding-plan": "qwen", "qwen-oauth": "qwen", "xiaomi": "mimo",
    "nvidia": "nvidia-color", "huggingface": "huggingface", "ollama-cloud": "ollama",
    "lmstudio": "lmstudio", "opencode-zen": "opencode", "opencode-go": "opencode",
    "novita": "novita", "tencent-tokenhub": "tencent", "copilot": "copilot",
    "stepfun": "stepfun", "arcee": "arcee-color", "gmi": "gmi", "kilocode": "kilocode",
    "azure-foundry": "azure", "custom": "custom", "bedrock": "bedrock-color",
    "copilot-acp": "copilot", "ollama-local": "ollama",
    # Google Vertex (n'avait pas de logo) + 8 fournisseurs LLM natifs ajoutés.
    "vertex": "vertex-color", "mistral": "mistral-color", "groq": "groq-color",
    "cerebras": "cerebras-color", "together": "together-color", "fireworks": "fireworks-color",
    "cohere": "cohere-color", "perplexity": "perplexity-color", "baidu-ernie": "baidu-color",
    "sakana": "sakana-color",
}

# introspection exécutée par l'interpréteur de Hermes (renvoie du JSON sur stdout)
_INTROSPECT_SCRIPT = """
import json
import hermes_cli.models as m
import hermes_cli.auth as a
# Les providers ajoutés par PLUGIN (model-provider : Mistral, Groq, Cerebras...) étendent
# CANONICAL_PROVIDERS mais PAS _PROVIDER_MODELS (réservé aux natifs). Leurs modèles vivent
# dans le champ `fallback_models` de leur profil. Sans ce repli, un provider-plugin branché
# afficherait « 0 modèle » (rien à choisir dans le chat). On lit donc les fallback_models du
# profil quand _PROVIDER_MODELS est vide — même comportement que le picker natif du moteur.
try:
    from providers import list_providers as _lp
    _plugin_models = {}
    for _pp in _lp():
        _fb = list(getattr(_pp, "fallback_models", ()) or ())
        if not _fb:
            continue
        _plugin_models[_pp.name] = _fb
        for _al in getattr(_pp, "aliases", ()) or ():
            _plugin_models.setdefault(_al, _fb)
except Exception:
    _plugin_models = {}
out = []
for e in m.CANONICAL_PROVIDERS:
    reg = a.PROVIDER_REGISTRY.get(e.slug)
    _models = list(m._PROVIDER_MODELS.get(e.slug, []) or [])
    if not _models:
        _models = _plugin_models.get(e.slug, [])
    # Les catalogues dont Hermes sait récupérer une version fraîche sont fusionnés avec le
    # repli embarqué. Cas clé : ChatGPT Codex publie ses nouveaux modèles par compte ; ils
    # apparaissent ainsi sans attendre une nouvelle image LunarIA. Toute panne conserve la
    # liste statique et ne peut donc jamais vider le sélecteur.
    if e.slug in {
        "nous", "openai-codex", "anthropic", "gemini", "deepseek",
        "mistral", "together", "cohere", "perplexity",
    }:
        try:
            _live = list(m.provider_model_ids(e.slug) or [])
        except Exception:
            _live = []
        _seen = {str(_mid).lower() for _mid in _live}
        _models = _live + [_mid for _mid in _models if str(_mid).lower() not in _seen]
    out.append({
        "slug": e.slug,
        "label": e.label,
        "auth_type": getattr(reg, "auth_type", "api_key") if reg else "api_key",
        "env_vars": list(getattr(reg, "api_key_env_vars", ()) or ()) if reg else [],
        "base_url": (getattr(reg, "inference_base_url", "") or None) if reg else None,
        "models": _models,
    })
print(json.dumps(out))
"""


class HermesUnavailable(RuntimeError):
    """Hermes n'est pas joignable (interpréteur/fichiers absents)."""


# Plateforme Hermes pilotée par défaut pour les toolsets/skills (configurable).
# Hermes gère ces capacités par plateforme (cli/telegram/...) ; on aligne sur la surface
# consommée par OpenWebUI. À ajuster via la variable d'env si nécessaire.
HERMES_PLATFORM = os.environ.get("HERMES_PLATFORM", "cli")


def introspect(script: str, timeout: int = 30, hermes_home: Path | str | None = None):
    """Exécute un script Python via l'interpréteur de Hermes et parse le JSON renvoyé.

    Helper générique partagé par les adapters (tools/skills). Lève ``HermesUnavailable``
    si l'interpréteur est absent, échoue ou dépasse le délai.

    ``hermes_home`` cible un profil précis (``~/.hermes/profiles/<name>/``) : on le passe au
    sous-process via l'env ``HERMES_HOME`` pour qu'il lise le bon ``config.yaml``/``.env``.
    Par défaut, on passe le ``HERMES_HOME`` courant du bridge — cohérent et sûr (en test,
    il pointe sur un dossier temporaire, jamais sur les vrais profils de la machine).
    """
    if not Path(HERMES_PYTHON).exists():
        raise HermesUnavailable(f"interpréteur Hermes introuvable: {HERMES_PYTHON}")
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home or HERMES_HOME)
    try:
        res = subprocess.run(
            [HERMES_PYTHON, "-c", script], capture_output=True, text=True, timeout=timeout, env=env
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    if res.returncode != 0:
        raise HermesUnavailable(res.stderr.strip()[:300] or "introspection Hermes échouée")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        # code retour 0 mais stdout non-JSON (print de debug oublié, warning d'une dépendance
        # écrit sur stdout au lieu de stderr, sortie tronquée…) : ne JAMAIS laisser un
        # JSONDecodeError brut remonter (casserait l'enveloppe d'erreur uniforme {"error":...}
        # de tous les endpoints Providers qui n'attrapent que HermesUnavailable).
        raise HermesUnavailable(
            "sortie non-JSON de l'interpréteur Hermes: " + res.stdout.strip()[:300]
        ) from exc


def _map_auth(raw: str) -> AuthType:
    raw = (raw or "").lower()
    if "oauth" in raw:
        return AuthType.oauth
    if "aws" in raw or "bedrock" in raw:
        return AuthType.aws_sdk
    if raw in ("", "none", "external_process"):
        return AuthType.none
    return AuthType.api_key


# providers tournant sur un serveur local (base_url localhost, pas de clé requise)
_LOCAL_SLUGS = {"lmstudio", "ollama", "vllm", "llamacpp", "atomicchat"}


def _category(slug: str, raw_auth: str, base_url: str | None) -> Category:
    """Regroupement UX par mode de connexion. Source : auth_type Hermes + slug + base_url.

    - oauth : auth_type OAuth (device code, external, minimax) → bouton « Se connecter »
    - local : serveur local (slug connu ou base_url localhost) → champ URL
    - other : AWS Bedrock / GitHub Copilot / Microsoft Azure + Qwen/Alibaba Cloud (cas à part :
              cloud entreprise à auth externe — ressource + endpoint + déploiements/région requis)
    - api   : tout le reste (clé API à coller)
    """
    raw = (raw_auth or "").lower()
    if "oauth" in raw:
        return Category.oauth
    if slug in _LOCAL_SLUGS or (base_url and ("127.0.0.1" in base_url or "localhost" in base_url)):
        return Category.local
    # Rangés dans l'onglet « Autres » à côté d'AWS Bedrock / Azure (choix produit 2026-07-08 ;
    # l'onglet « Autres » est déjà réservé au mode Expert côté front) :
    #  - Qwen Cloud (`alibaba`) + Alibaba Cloud Coding Plan (`alibaba-coding-plan`) : cloud entreprise
    #  - Baidu ERNIE (`baidu-ernie`) : cloud entreprise chinois (Qianfan, région/endpoint)
    #  - Sur-mesure (`custom`) : endpoint personnalisé, cas technique avancé
    _OTHER_SLUGS = ("azure-foundry", "alibaba", "alibaba-coding-plan", "baidu-ernie", "custom")
    if slug in _OTHER_SLUGS or "aws" in raw or "bedrock" in raw or raw in ("external_process", "copilot"):
        return Category.other
    return Category.api


def _introspect() -> list[dict]:
    if not Path(HERMES_PYTHON).exists():
        raise HermesUnavailable(f"interpréteur Hermes introuvable: {HERMES_PYTHON}")
    try:
        res = subprocess.run(
            [HERMES_PYTHON, "-c", _INTROSPECT_SCRIPT],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    if res.returncode != 0:
        raise HermesUnavailable(res.stderr.strip()[:300] or "introspection échouée")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        # même garde-fou que introspect() ci-dessus (cf. commentaire là-bas).
        raise HermesUnavailable(
            "sortie non-JSON de l'interpréteur Hermes: " + res.stdout.strip()[:300]
        ) from exc


def _present_env_keys() -> set[str]:
    """Noms des variables définies (non commentées) dans ~/.hermes/.env. Jamais les valeurs."""
    env_path = HERMES_HOME / ".env"
    present: set[str] = set()
    if not env_path.exists():
        return present
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        present.add(line.split("=", 1)[0].strip())
    return present


def _oauth_connected_slugs() -> set[str]:
    """Slugs OAuth connectés = présents dans ``credential_pool`` de ~/.hermes/auth.json
    avec au moins une entrée. Ne lit jamais les tokens (juste la présence).
    """
    path = HERMES_HOME / "auth.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError):
        return set()
    pool = data.get("credential_pool") or {}
    return {
        slug
        for slug, entries in pool.items()
        if isinstance(entries, list) and len(entries) > 0
    }


def get_active() -> ActiveSelection | None:
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return None
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    model = cfg.get("model") or {}
    provider = model.get("provider")
    default = model.get("default")
    if not provider or not default:
        return None
    # base_url est porté ici (même s'il est souvent absent) pour que ``set_active`` puisse
    # réconcilier le TRIPLET complet en cas d'échec partiel, pas seulement provider/default
    # (cf. audit Haute — base_url échappait à la réconciliation).
    return ActiveSelection(provider_id=provider, model_id=default, base_url=model.get("base_url") or None)


def _detect_ollama_local() -> tuple[bool, list[str]]:
    """Détecte si un serveur Ollama tourne en local. Renvoie (running, noms de modèles).

    Honnêteté (cf. honnêteté des libellés) : on n'affiche « disponible » que si le
    serveur répond réellement. Timeout court pour ne pas ralentir la page Providers ;
    si Ollama est éteint, la connexion est refusée immédiatement.
    """
    try:
        resp = httpx.get(f"{OLLAMA_LOCAL_BASE_URL}/api/tags", timeout=1.5)
        if resp.status_code != 200:
            return False, []
        data = resp.json()
        models = [m["name"] for m in data.get("models", []) if isinstance(m, dict) and m.get("name")]
        return True, models
    except (httpx.HTTPError, ValueError, KeyError):
        return False, []


def _ollama_local_provider(active: ActiveSelection | None) -> Provider:
    """Carte synthétique « Modèle local (confidentiel) » avec état honnête.

    - actif si Hermes pointe dessus ; sinon « configured » (disponible) si Ollama tourne ;
      sinon « not_configured » (non démarré / non installé).
    """
    running, models = _detect_ollama_local()
    if active and active.provider_id == OLLAMA_LOCAL_ID:
        state = ProviderState.active
    elif running:
        state = ProviderState.configured
    else:
        state = ProviderState.not_configured
    policy = provider_catalog_policy(OLLAMA_LOCAL_ID, len(models))
    return Provider(
        id=OLLAMA_LOCAL_ID,
        label="Modèle local (confidentiel)",
        logo="ollama",
        auth_type=AuthType.none,
        category=Category.local,
        env_key=None,
        base_url=f"{OLLAMA_LOCAL_BASE_URL}/v1",
        state=state,
        models=[Model(id=m, label=clean_model_label(m, m), provider_id=OLLAMA_LOCAL_ID) for m in models],
        catalog_source=policy["source"],
        catalog_refresh=policy["refresh"],
        catalog_sort=policy["sort"],
    )


# Repli pour les agrégateurs que le registre Hermes n'expose PAS complètement.
# OpenRouter a un routage « bespoke » (cf. providers/README.md) : le registre ne peuple
# ni ``env_vars`` ni ``inference_base_url`` pour lui. Sans repli, la carte est inutilisable :
#   - ``env_key`` None → set_key refuse (« Impossible d'enregistrer la clé »)
#   - jamais détecté « configuré » (l'état resterait « non connecté » même clé posée)
#   - ``base_url`` None → validate_key avorte (« pas d'URL d'inférence connue »)
# Le moteur, lui, lit BIEN ``OPENROUTER_API_KEY`` depuis le .env (hermes_cli/auth.py:1495).
# env_vars/base_url = valeurs déclarées par le profil moteur du provider.
_PROVIDER_REGISTRY_FALLBACK: dict[str, dict] = {
    "openrouter": {
        "env_vars": ["OPENROUTER_API_KEY"],
        "base_url": "https://openrouter.ai/api/v1",
    },
}


def _provider_model_pairs(item: dict, state: "ProviderState", env_vars: list[str], fallback: dict) -> list[tuple[str, str]]:
    """Calcule les (id, label) des modèles d'UN provider. Isolé de la boucle pour pouvoir
    être exécuté EN PARALLÈLE (les branches passerelles font des appels réseau : catalogue +
    sonde de crédit). Robuste : toute erreur retombe sur la liste figée du moteur (jamais vide
    par surprise). Chaque provider n'écrit que SA propre clé de cache → sûr entre threads."""
    slug = item["slug"]
    connected = state != ProviderState.not_configured
    try:
        # OpenRouter / Kilo / OpenCode / Novita / HF / Ollama / Z.AI / Kimi : catalogue live
        # (fetch réseau) seulement si connecté — sinon on ne paie pas d'appel réseau inutile.
        if slug == "openrouter" and connected:
            return _openrouter_model_list(item.get("models", []))
        if slug == "kilocode" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _kilocode_model_pairs(key)
        if slug in ("opencode-zen", "opencode-go") and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            base = (item.get("base_url") or fallback.get("base_url") or "").rstrip("/")
            return _opencode_model_pairs(slug, base, key) if base else _display_pairs(slug, item.get("models", []))
        if slug == "novita" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _novita_model_pairs(key)
        if slug == "gmi" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _gmi_model_pairs(key, list(item.get("models", [])))
        if slug == "huggingface" and connected:
            return _huggingface_model_pairs()
        if slug == "nvidia" and connected:
            return list(_NVIDIA_CURATED_MODELS)
        if slug == "ollama-cloud" and connected:
            return _ollama_cloud_model_pairs()
        if slug == "zai" and connected:
            return _zai_model_pairs()
        if slug == "cohere" and connected:
            return list(_COHERE_CURATED_MODELS)
        if slug == "cerebras" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _cerebras_model_pairs(key)
        if slug == "fireworks" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _fireworks_model_pairs(key)
        if slug == "groq" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _groq_model_pairs(key)
        if slug == "xiaomi" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _xiaomi_model_pairs(key)
        if slug == "stepfun" and connected:
            key = next((read_env_value(k) for k in env_vars if read_env_value(k)), None)
            return _stepfun_model_pairs(key)
        if slug in ("kimi-coding", "kimi-coding-cn") and connected:
            return _kimi_model_pairs(slug, item.get("base_url") or "", list(item.get("models", [])))
    except Exception:  # noqa: BLE001 — un provider qui échoue ne doit pas casser toute la liste
        return _display_pairs(slug, item.get("models", []))
    # Providers natifs (Anthropic, Gemini, DeepSeek…) ou non connectés : libellés propres.
    return _display_pairs(slug, item.get("models", []))


# Cache TTL COURT sur ``list_providers()`` (cf. audit perf Haute #2/#3, Moyenne #1/#2) :
# c'est la fonction la plus chère du bridge (1 subprocess d'introspection Hermes + jusqu'à
# 12 sondes réseau parallèles, passe 2) et elle est rappelée par au moins 8 points d'entrée
# (``set_key``, ``remove_key``, ``set_active``/``activate_provider``, ``validate_key``,
# ``hermes_status``…) sans jamais être mémoïsée — jusqu'à 2 reconstructions complètes pour
# une seule requête HTTP (``remove_key``). Le TTL est volontairement COURT (quelques
# secondes, cf. ``LIST_PROVIDERS_CACHE_TTL_S``) : il sert UNIQUEMENT à dédupliquer les
# rafales d'appels internes à une même action et les requêtes rapprochées dans le temps
# (deux onglets ouverts, front qui re-fetch) — jamais à masquer un changement d'état réel.
#
# INVARIANT D'HONNÊTETÉ (prime sur la perf) : toute écriture qui change l'état d'un
# provider — clé posée (``set_key``), clé retirée (``remove_key``), cerveau activé
# (``set_active``/``activate_provider``), credentials AWS, déconnexion OAuth
# (``logout_oauth``) — DOIT invalider ce cache avant de rendre la main, via
# ``_invalidate_providers_cache()``. Sans ça, l'UI pourrait afficher un état périmé juste
# après une action utilisateur explicite — inacceptable même pour gagner en latence.
_LIST_PROVIDERS_CACHE_TTL_S = float(os.environ.get("LIST_PROVIDERS_CACHE_TTL_S", "4"))
_LIST_PROVIDERS_CACHE = TTLCache(_LIST_PROVIDERS_CACHE_TTL_S)


def _invalidate_providers_cache() -> None:
    """Vide le cache de ``list_providers()``.

    À appeler après TOUTE écriture qui change l'état d'un provider (cf. docstring du cache
    ci-dessus) — jamais après une simple LECTURE (``activate_provider``/``remove_key`` en
    font un usage interne en tête de fonction, avant toute écriture : ces lectures-là
    doivent au contraire profiter du cache, sinon on retombe dans le bug audité).
    """
    _LIST_PROVIDERS_CACHE.clear()


def list_providers() -> list[Provider]:
    """Catalogue des providers connus de Hermes (état + modèles). Caché (TTL court, cf.
    ``_LIST_PROVIDERS_CACHE`` ci-dessus) : les appelants rapprochés dans le temps (même
    requête HTTP qui la rappelle 2 fois, ou deux requêtes qui se suivent) partagent le
    même résultat au lieu de repayer le subprocess + les sondes réseau à chaque fois."""
    cached = _LIST_PROVIDERS_CACHE.fresh()
    if cached is not None:
        return cached
    providers = _list_providers_uncached()
    _LIST_PROVIDERS_CACHE.store(providers)
    return providers


def _list_providers_uncached() -> list[Provider]:
    raw = _introspect()
    present = _present_env_keys()
    oauth_connected = _oauth_connected_slugs()
    active = get_active()

    # Passe 1 (locale, sans réseau) : métadonnées + état de chaque provider.
    metas: list[dict] = []
    for item in raw:
        slug = item["slug"]
        _fallback = _PROVIDER_REGISTRY_FALLBACK.get(slug, {})
        env_vars = item.get("env_vars") or _fallback.get("env_vars") or []
        auth = _map_auth(item.get("auth_type"))
        category = _category(slug, item.get("auth_type"), item.get("base_url"))
        # OAuth : connecté = token dans auth.json ; AWS Bedrock : credentials AWS présents ;
        # sinon : clé présente dans .env.
        if category == Category.oauth:
            configured = slug in oauth_connected
        elif auth == AuthType.aws_sdk:
            configured = all(k in present for k in _AWS_ENV_REQUIRED)
        else:
            configured = any(k in present for k in env_vars)
        if active and active.provider_id == slug:
            state = ProviderState.active
        elif configured:
            state = ProviderState.configured
        else:
            state = ProviderState.not_configured
        metas.append({"item": item, "slug": slug, "fallback": _fallback,
                      "env_vars": env_vars, "auth": auth, "category": category, "state": state})

    # Passe 2 (PARALLÈLE) : les model_pairs des passerelles font des appels réseau (catalogue +
    # sonde de crédit) — les lancer en parallèle évite d'additionner les latences (16 providers
    # connectés : ~7 s en séquentiel → ~1-2 s). Cap à 12 threads (largement > nb de passerelles).
    with ThreadPoolExecutor(max_workers=12) as pool:
        pairs_by_index = list(pool.map(
            lambda m: _provider_model_pairs(m["item"], m["state"], m["env_vars"], m["fallback"]),
            metas,
        ))

    # Une seule lecture models.dev pour TOUS les modèles. Elle n'appelle aucun modèle et ne
    # consomme aucun crédit : dates/casse/raisonnement servent uniquement à l'UX et au tri.
    requested_metadata = {
        meta["slug"]: [mid for mid, _label in pairs]
        for meta, pairs in zip(metas, pairs_by_index)
        if pairs
    }
    model_metadata = load_model_metadata(HERMES_PYTHON, HERMES_HOME, requested_metadata)

    # Passe 3 (locale) : assemble les objets Provider.
    providers: list[Provider] = []
    for meta, model_pairs in zip(metas, pairs_by_index):
        item, slug = meta["item"], meta["slug"]
        env_vars = meta["env_vars"]
        policy = provider_catalog_policy(slug, len(model_pairs))
        provider_meta = model_metadata.get(slug, {})
        models: list[Model] = []
        for mid, label in model_pairs:
            details = provider_meta.get(mid, {})
            models.append(
                Model(
                    id=mid,
                    label=clean_model_label(label, mid),
                    provider_id=slug,
                    release_date=details.get("release_date") or None,
                    family=details.get("family") or None,
                    reasoning=details.get("reasoning"),
                    supported_efforts=details.get("supported_efforts"),
                    metadata_confidence=details.get("confidence") or "unknown",
                )
            )
        # Kimi Coding Plan : un modèle peut être au catalogue mais refusé par le FORFAIT
        # de la clé (HighSpeed = Allegretto et plus). On le grise avec la raison au lieu
        # de laisser le client récolter un 401 anglais en plein chat (vécu le 2026-07-22).
        # Lecture de cache uniquement : la sonde a été chauffée en passe 2 (parallèle).
        if slug in ("kimi-coding", "kimi-coding-cn"):
            plan_locks = _kimi_unavailable_reasons(slug)
            for model in models:
                reason = plan_locks.get(model.id)
                if reason:
                    model.available = False
                    model.unavailable_reason = reason
        providers.append(
            Provider(
                id=slug,
                label=item["label"],
                logo=_LOGO_BY_SLUG.get(slug, "api"),
                auth_type=meta["auth"],
                category=meta["category"],
                env_key=env_vars[0] if env_vars else None,
                base_url=item.get("base_url") or meta["fallback"].get("base_url"),
                state=meta["state"],
                models=models,
                catalog_source=policy["source"],
                catalog_refresh=policy["refresh"],
                catalog_sort=policy["sort"],
            )
        )
    # Injection bridge : « Modèle local (confidentiel) » (Ollama local), sans toucher Hermes.
    # On évite le doublon si Hermes exposait déjà un slug ollama/ollama-local.
    if not any(p.id in (OLLAMA_LOCAL_ID, "ollama") for p in providers):
        providers.append(_ollama_local_provider(active))
    return providers


def _hermes_config_set(key: str, value: str) -> None:
    """Écriture atomique via la CLI Hermes (non-interactif).

    ``--`` sépare explicitement les options de la valeur positionnelle (convention
    argparse standard) : sans ça, une ``value`` commençant par ``-`` (ex. un
    ``model_id``/``base_url`` fourni via une requête HTTP) pourrait être interprétée
    comme un flag de la CLI plutôt que comme une valeur littérale (cf. audit Basse #3,
    CWE-88 injection d'argument). Pas de ``shell=True`` ici (liste d'arguments) donc pas
    d'injection de commande — seulement un risque de flag détourné.
    """
    try:
        res = subprocess.run(
            [HERMES_BIN, "config", "set", key, "--", value],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    if res.returncode != 0:
        raise HermesUnavailable(res.stderr.strip()[:300] or "hermes config set échoué")


def set_active(provider_id: str, model_id: str, base_url: str | None = None) -> ActiveSelection:
    """Bascule le cerveau actif (``model.provider`` + ``model.default`` + ``base_url``).

    La CLI Hermes n'écrit qu'UNE clé à la fois (pas de transaction multi-champs) : si
    l'écriture de ``model.default`` échoue APRÈS que ``model.provider`` a déjà été écrit
    (process Hermes tué, disque plein le temps de l'appel…), on se retrouverait avec
    ``config.yaml`` pointant sur le NOUVEAU fournisseur mais l'ANCIEN modèle — un
    « cerveau fantôme » qui échouerait en silence au prochain message de chat (cf. audit
    Haute #2). On réconcilie donc explicitement en cas d'échec : restauration de la paire
    précédente (ou repli honnête sur ``auto`` si aucune paire cohérente n'existait avant).

    ``model.base_url`` fait partie du MÊME triplet et de la MÊME réconciliation : sans ça,
    un échec sur cette 3e écriture laisserait ``provider``/``default`` basculés sur le
    nouveau fournisseur alors que ``base_url`` resterait sur l'ancien — Hermes routerait
    alors les appels du nouveau fournisseur vers la mauvaise adresse, sans rollback ni
    alerte (cf. audit Haute — base_url échappait à la réconciliation).
    """
    previous = get_active()
    try:
        _hermes_config_set("model.provider", provider_id)
        # IMPORTANT : bien « model.default ». « hermes config set model <val> » traite « model »
        # comme une clé scalaire et ÉCRASE tout le dict model (perte de provider/default) →
        # l'activation ne prenait jamais effet (bug historique du bouton « Activer »).
        _hermes_config_set("model.default", model_id)
        # Aligne l'URL d'inférence sur le fournisseur activé. Sinon un base_url résiduel
        # (ex. le défaut d'usine « auto » → openrouter.ai) resterait et Hermes routerait les
        # appels du nouveau fournisseur vers la mauvaise adresse → « ça ne répond pas ».
        # Cette écriture reste DANS le même bloc try/except que les deux précédentes : un
        # échec ici doit lui aussi déclencher la réconciliation (cf. docstring ci-dessus).
        if base_url:
            _hermes_config_set("model.base_url", base_url)
    except HermesUnavailable:
        _reconcile_after_failed_set_active(previous)
        raise
    finally:
        # config.yaml a pu changer (succès COMME réconciliation partielle) : le cache de
        # list_providers() ne doit jamais rendre l'ancien état "active" après ce point
        # (cf. invariant d'honnêteté ci-dessus). Inconditionnel, dans les deux branches.
        _invalidate_providers_cache()
    return ActiveSelection(provider_id=provider_id, model_id=model_id)


def _reconcile_after_failed_set_active(previous: ActiveSelection | None) -> None:
    """Best-effort, appelé après un échec en cours de ``set_active`` : ne JAMAIS laisser
    ``model.provider``/``model.default``/``model.base_url`` dépareillés. Restaure le
    TRIPLET précédent s'il était cohérent (base_url inclus, quand il y en avait un) ;
    sinon retombe sur ``auto`` (état honnête « pas de cerveau actif », jamais un provider
    seul pointant vers le modèle — ou l'adresse — d'un autre fournisseur).

    Pas de boucle infinie possible : ces écritures ne rappellent jamais ``set_active``
    (donc jamais cette fonction elle-même), et un nouvel échec ici est simplement avalé
    (best-effort) — l'exception d'origine, déjà en cours de propagation, suffit à
    signaler l'incident à l'appelant.
    """
    try:
        if previous is not None:
            _hermes_config_set("model.provider", previous.provider_id)
            _hermes_config_set("model.default", previous.model_id)
            if previous.base_url:
                _hermes_config_set("model.base_url", previous.base_url)
        else:
            _hermes_config_set("model.provider", "auto")
    except HermesUnavailable as exc:
        # best-effort : l'exception d'origine (déjà en cours) sera de toute façon propagée à
        # l'appelant — on trace quand même celle-ci pour ne pas perdre la cause d'un "cerveau
        # actif" resté dans un état intermédiaire après un double échec.
        logger.debug("Restauration du provider précédent après échec : %s", exc)


class UnknownProvider(Exception):
    """Provider absent de ``list_providers()`` (id inconnu de Hermes)."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        super().__init__(f"provider inconnu: {provider_id}")


class ProviderNotConfigured(Exception):
    """Provider connu mais sans clé/OAuth valide (``ProviderState.not_configured``)."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        super().__init__(f"provider non configuré: {provider_id}")


def activate_provider(provider_id: str, model_id: str) -> tuple[ActiveSelection, str]:
    """Bascule le cerveau actif en repassant par les 3 garde-fous du chemin « officiel ».

    Chemin PARTAGÉ : ``routers/providers.py`` (``POST /active``, sélecteur de cerveau normal)
    et ``moa_adapter.deactivate`` (restauration du cerveau utilisé avant MoA) appellent tous
    les deux CETTE fonction — aucun des deux ne peut donc plus réactiver un provider inconnu
    ou devenu déconnecté entre-temps, oublier son ``base_url``, ou sauter la propagation aux
    agents nommés (cf. audit phase 3, finding HAUTE : ``moa_adapter.deactivate`` appelait
    ``set_active`` bas niveau directement, sans aucun de ces 3 garde-fous).

    Lève ``UnknownProvider`` si ``provider_id`` n'existe pas, ``ProviderNotConfigured`` s'il
    existe mais n'a ni clé ni OAuth valide, ``HermesUnavailable`` si Hermes est injoignable.
    Renvoie ``(ActiveSelection appliquée, "ok"|"failed")`` — le 2e élément (``team_brain_sync``)
    reflète la propagation best-effort aux agents nommés, jamais bloquante.
    """
    providers = list_providers()
    target = next((p for p in providers if p.id == provider_id), None)
    if target is None:
        raise UnknownProvider(provider_id)
    if target.state == ProviderState.not_configured:
        raise ProviderNotConfigured(provider_id)

    applied = set_active(provider_id, model_id, target.base_url)

    team_brain_sync = "ok"
    try:
        # Import différé : profiles_adapter importe déjà hermes_adapter au niveau module,
        # un import en tête de fichier créerait un cycle. Au moment de l'appel, ce module
        # est nécessairement déjà chargé (on est en train d'exécuter une de ses fonctions).
        from . import profiles_adapter

        profiles_adapter.propagate_brain_to_agents(applied.provider_id, applied.model_id, target.base_url)
    except Exception:  # noqa: BLE001 — effet de bord non bloquant
        team_brain_sync = "failed"
        logger.warning("propagation du cerveau aux agents impossible", exc_info=True)
    return applied, team_brain_sync


# Niveau de raisonnement (« intelligence ») global du moteur, lu/écrit dans
# ~/.hermes/config.yaml sous agent.reasoning_effort. Le moteur Hermes le transmet
# réellement aux appels API (OpenAI Responses/OpenRouter/Gemini/Anthropic…). Valeurs
# acceptées par le moteur : none | minimal | low | medium | high | xhigh.
VALID_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")


def ensure_performance_defaults() -> None:
    """Enable Hermes progressive tool disclosure on installs without a choice.

    With several MCP connectors, sending every JSON schema on every turn wastes
    context and lets the model pick a heavyweight crawler for trivial lookups.
    Hermes' native tool-search bridge keeps all capabilities available on
    demand. An explicit user value (``on``, ``off`` or ``auto``) always wins.
    """
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        configured = (((cfg.get("tools") or {}).get("tool_search") or {}).get("enabled"))
        if configured is None:
            _hermes_config_set("tools.tool_search.enabled", "on")
            logger.info("performance Hermes : découverte progressive des outils activée")
    except Exception:  # noqa: BLE001 — optimisation non bloquante au démarrage
        logger.warning("activation de la découverte progressive des outils impossible", exc_info=True)


def get_reasoning() -> str:
    """Effort de raisonnement actif (chaîne vide = défaut moteur = medium)."""
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return ""
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    agent = cfg.get("agent") or {}
    value = agent.get("reasoning_effort")
    return str(value).strip() if value else ""


def set_reasoning(effort: str) -> str:
    """Écrit agent.reasoning_effort via la CLI Hermes. Appelant valide la valeur."""
    _hermes_config_set("agent.reasoning_effort", effort)
    return effort


# Backend de recherche/lecture web actif, lu/écrit dans ~/.hermes/config.yaml sous
# web.search_backend / web.extract_backend. Le moteur relit config.yaml à chaud (cache
# invalidé sur le mtime), donc AUCUN redémarrage du gateway n'est nécessaire — même
# modèle que set_active pour le cerveau. Le changement s'applique aux nouveaux appels
# d'outils.
def get_web_backends() -> dict[str, str]:
    """Backends web actifs (search/extract) lus dans config.yaml (chaînes vides si absents)."""
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return {"search": "", "extract": ""}
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    web = cfg.get("web") or {}
    return {
        "search": str(web.get("search_backend") or "").strip(),
        "extract": str(web.get("extract_backend") or "").strip(),
    }


def set_web_backend(search: str, extract: str | None = None) -> None:
    """Écrit web.search_backend (et web.extract_backend si fourni) via la CLI Hermes.

    ``extract=None`` laisse ``web.extract_backend`` inchangé (cas d'un backend de recherche
    seule : la lecture de page reste assurée par le navigateur / l'ancien extracteur).
    """
    _hermes_config_set("web.search_backend", search)
    if extract is not None:
        _hermes_config_set("web.extract_backend", extract)


# Capacités d'un modèle (reasoning/vision/outils/contexte), lues à la demande dans le
# catalogue models.dev du moteur Hermes. Provider/modèle passés par ENV (pas d'injection).
# Repli gracieux : en cas d'échec/absence, on renvoie des None → l'UI affiche tout par défaut.
_CAPS_SCRIPT = """
import json, os
out = {"reasoning": None, "vision": None, "tools": None, "context_window": None}
try:
    from agent.models_dev import get_model_capabilities
    caps = get_model_capabilities(os.environ.get("CAP_PROVIDER", ""), os.environ.get("CAP_MODEL", ""))
    out = {
        "reasoning": bool(getattr(caps, "supports_reasoning", False)),
        "vision": bool(getattr(caps, "supports_vision", False)),
        "tools": bool(getattr(caps, "supports_tools", False)),
        "context_window": int(getattr(caps, "context_window", 0) or 0),
    }
except Exception as exc:  # noqa: BLE001 - repli gracieux volontaire
    out["error"] = str(exc)[:200]
print(json.dumps(out))
"""

_CAPS_UNKNOWN = {"reasoning": None, "vision": None, "tools": None, "context_window": None}


def _raw_model_capabilities(provider_id: str, model_id: str) -> dict:
    """Capacités brutes selon models.dev (via l'interpréteur Hermes). None si indisponible."""
    if not Path(HERMES_PYTHON).exists():
        return dict(_CAPS_UNKNOWN)
    env = os.environ.copy()
    env["HERMES_HOME"] = str(HERMES_HOME)
    env["CAP_PROVIDER"] = provider_id or ""
    env["CAP_MODEL"] = model_id or ""
    try:
        res = subprocess.run(
            [HERMES_PYTHON, "-c", _CAPS_SCRIPT],
            capture_output=True, text=True, timeout=8, env=env,
        )
        if res.returncode != 0:
            return dict(_CAPS_UNKNOWN)
        data = json.loads(res.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return dict(_CAPS_UNKNOWN)
    return {
        "reasoning": data.get("reasoning"),
        "vision": data.get("vision"),
        "tools": data.get("tools"),
        "context_window": data.get("context_window"),
    }


# Table de secours des capacités : quand models.dev ne connaît pas encore un modèle
# (trop récent → tout revient à null/False), on se rabat sur les capacités CONNUES des
# grandes familles (repérées par sous-chaîne du nom). Évite de mentir « ne gère rien »
# alors que le modèle raisonne/voit/utilise des outils (ex. gpt-5.5). Ordre = plus
# spécifique d'abord. Valeurs vérifiées via la doc des fournisseurs (juillet 2026).
_CAPS_FALLBACK: tuple[tuple[str, dict], ...] = (
    # gpt-oss (OpenAI open source, servi par Cerebras/Fireworks/Groq…) : raisonne (reasoning_effort
    # natif + reasoning_content, testé en réel 2026-07-08), outils, texte seul, 131k. Sans ce repli,
    # l'ID court « gpt-oss-120b » (Cerebras) est inconnu de models.dev → carte « ne gère rien ».
    ("gpt-oss", {"reasoning": True, "vision": False, "tools": True, "context_window": 131072}),
    ("gpt-5", {"reasoning": True, "vision": True, "tools": True, "context_window": 1000000}),
    ("gpt-4.1", {"reasoning": False, "vision": True, "tools": True, "context_window": 1000000}),
    ("gpt-4o", {"reasoning": False, "vision": True, "tools": True, "context_window": 128000}),
    ("o4", {"reasoning": True, "vision": True, "tools": True, "context_window": 200000}),
    ("o3", {"reasoning": True, "vision": True, "tools": True, "context_window": 200000}),
    ("o1", {"reasoning": True, "vision": True, "tools": True, "context_window": 200000}),
    ("claude", {"reasoning": True, "vision": True, "tools": True, "context_window": 200000}),
    ("gemini", {"reasoning": True, "vision": True, "tools": True, "context_window": 1000000}),
    ("grok", {"reasoning": True, "vision": True, "tools": True, "context_window": 256000}),
    ("deepseek", {"reasoning": True, "vision": False, "tools": True, "context_window": 128000}),
    ("mistral", {"reasoning": False, "vision": True, "tools": True, "context_window": 128000}),
    # Kimi K2.x : raisonne (reasoning_content + reasoning_effort honoré, testé), outils, 256k
    # contexte, pas de vision. models.dev ne connaît pas encore ces modèles récents.
    ("kimi", {"reasoning": True, "vision": False, "tools": True, "context_window": 262144}),
    # Arcee Trinity (mini + large-thinking) : reasoning + outils, texte seul, 131k contexte.
    # Vérifié via l'API Arcee (supported_features), HuggingFace (arcee-ai/Trinity-Mini :
    # reasoning-parser deepseek_r1 + tool-call-parser hermes) et OpenRouter. models.dev n'a
    # pas de provider « arcee » → sans ce repli, la card afficherait « ne gère rien ».
    ("trinity", {"reasoning": True, "vision": False, "tools": True, "context_window": 131072}),
    # Familles servies par les passerelles (GMI Cloud…) que models.dev ne rattache pas au
    # provider hôte → sans repli, la card afficherait « ne gère rien ». Capacités vérifiées via
    # models.dev (sous les providers d'origine : openrouter, vercel…) ou la doc constructeur.
    # Tous tool-capable, texte seul (pas de vision sauf Gemma 4). Contextes = valeurs models.dev.
    ("qwen", {"reasoning": True, "vision": False, "tools": True, "context_window": 131072}),
    ("glm", {"reasoning": True, "vision": False, "tools": True, "context_window": 202752}),
    ("minimax", {"reasoning": True, "vision": False, "tools": True, "context_window": 204800}),
    ("nemotron", {"reasoning": True, "vision": False, "tools": True, "context_window": 131072}),
    ("mimo", {"reasoning": True, "vision": False, "tools": True, "context_window": 131072}),
    ("kat-coder", {"reasoning": False, "vision": False, "tools": True, "context_window": 256000}),
    # Gemma 4 (Google, ex. servi par Cerebras) : RAISONNE (reasoning_content, testé en réel
    # 2026-07-08) — contrairement à Gemma 3. Doit précéder le repli « gemma » générique (hérité
    # de Gemma 3, reasoning=False) pour ne pas afficher à tort « ne raisonne pas ». Vision, outils.
    ("gemma-4", {"reasoning": True, "vision": True, "tools": True, "context_window": 262144}),
    ("gemma", {"reasoning": False, "vision": True, "tools": True, "context_window": 262144}),
    # --- Familles débusquées par l'audit intelligence 2026-07-08 (modèles servis par Kimi/NVIDIA/
    # Novita/HuggingFace/GMI qui s'affichaient « ne gère rien » : inconnus de models.dev + aucun
    # repli). Tous tool-capable (liste curée validée ou catalogue live filtré tool-capable) →
    # `tools: True`. `reasoning` : True UNIQUEMENT si prouvé en réel (reasoning_content), sinon
    # False prudent (jamais promettre un raisonnement non vérifié). Spécifique AVANT générique.
    ("command-a-reasoning", {"reasoning": True, "vision": False, "tools": True, "context_window": 256000}),  # testé: raisonne
    ("command", {"reasoning": False, "vision": False, "tools": True, "context_window": 256000}),  # command-r/a testés: non
    ("moonshot", {"reasoning": False, "vision": False, "tools": True, "context_window": 131072}),  # Moonshot V1 (pré-K2)
    ("solar", {"reasoning": False, "vision": False, "tools": True, "context_window": 4096}),  # NVIDIA SOLAR 10.7B
    ("dracarys", {"reasoning": False, "vision": False, "tools": True, "context_window": 131072}),  # avant « llama »
    ("llama-4", {"reasoning": False, "vision": True, "tools": True, "context_window": 1048576}),  # Scout/Maverick: vision
    ("llama", {"reasoning": False, "vision": False, "tools": True, "context_window": 131072}),  # Llama 3.x instruct
    ("olmo", {"reasoning": False, "vision": False, "tools": True, "context_window": 65536}),  # testé: non
    ("ling-2", {"reasoning": False, "vision": False, "tools": True, "context_window": 131072}),  # testé: non
    ("bielik", {"reasoning": False, "vision": False, "tools": True, "context_window": 32768}),  # Bielik 11B (PL)
    # Chinois récents non testables (Novita/GMI à 0 solde) → reasoning False prudent, À REVALIDER.
    ("hy3", {"reasoning": False, "vision": False, "tools": True, "context_window": 262144}),  # Tencent Hunyuan 3
    # StepFun Step-3.x — direct (`step-3.5-flash`) ET Novita (`stepfun-ai/step-3.x-flash`). Le needle
    # « step-3 » couvre les deux (l'ancien « stepfun » ne matchait PAS l'ID direct `step-3.5-flash`).
    # Step-3.5-Flash RAISONNE (99.8% AIME 2025, 98% HMMT — specs off.), text-only, 256K, agentic.
    # vision=False prudent : le multimodal n'arrive qu'en 3.7 et « step-3 » ne distingue pas 3.5/3.7.
    ("step-3", {"reasoning": True, "vision": False, "tools": True, "context_window": 262144}),
    ("stepfun", {"reasoning": True, "vision": False, "tools": True, "context_window": 262144}),  # filet Novita
    ("seed-2", {"reasoning": False, "vision": False, "tools": True, "context_window": 131072}),  # ByteDance Seed 2.0
    # Exotiques Novita sans famille claire (non testables, 0 solde) : repli minimal honnête
    # (tool-capable confirmé par le filtre, reste non promis). À revalider / arbitrer plus tard.
    ("bunny", {"reasoning": False, "vision": False, "tools": True, "context_window": 32768}),
    ("cobuddy", {"reasoning": False, "vision": False, "tools": True, "context_window": 32768}),
    ("gt-4p", {"reasoning": False, "vision": False, "tools": True, "context_window": 32768}),
)


def _caps_with_fallback(model_id: str, caps: dict) -> dict:
    """Complète les capacités avec la table de secours SEULEMENT si models.dev n'a rien
    renvoyé (tout null/False = modèle inconnu). Ne remplace jamais des données réelles."""
    if caps.get("reasoning") or caps.get("vision") or caps.get("tools") or caps.get("context_window"):
        return caps  # models.dev connaît le modèle → on lui fait confiance
    m = (model_id or "").lower()
    for needle, fallback in _CAPS_FALLBACK:
        if needle in m:
            return dict(fallback)
    return caps  # inconnu même de notre table → honnête : on ne prétend rien


# Niveaux d'intelligence (reasoning_effort) exposés dans le chat, du + léger au + poussé.
# Mappés aux libellés front Rapide/Équilibré/Approfondi/Maximum.
_CHAT_EFFORT_LEVELS = ("low", "medium", "high", "xhigh")
# Niveaux NON honorés par certains fournisseurs (on ne les propose donc pas), quel que soit le
# modèle. Prouvé en réel : Gemini rejette « xhigh » (message : "Valid values are: high, low, medium,
# minimal, none") ; Cerebras rejette « xhigh » sur TOUS ses modèles (gpt-oss + gemma-4 + zai-glm-4.7,
# HTTP 400, 2026-07-08). Défaut = aucune restriction ; on ne retire QUE sur preuve, jamais par
# supposition, pour ne pas amputer un modèle qui sait vraiment faire.
_EFFORTS_UNSUPPORTED: dict[str, frozenset[str]] = {
    "gemini": frozenset({"xhigh"}),
    "cerebras": frozenset({"xhigh"}),
    # Xiaomi MiMo (mimo-v2.5-pro/mimo-v2.5) : low/medium/high acceptés, « xhigh » → HTTP 400
    # (prouvé en réel 2026-07-08, clé client). Les 2 modèles raisonnent (reasoning_content).
    "xiaomi": frozenset({"xhigh"}),
}
# Restrictions PAR MODÈLE (propriété du modèle, indépendante de l'hébergeur — prouvé en réel) :
# gpt-oss (OpenAI open source, servi par Groq/Cerebras/Fireworks…) n'accepte que low/medium/high ;
# « xhigh » → HTTP 400 chez tous les hébergeurs testés. On ne propose donc jamais « Maximum » dessus.
_MODEL_EFFORTS_LOW_MED_HIGH = ("gpt-oss",)


def supported_efforts(
    provider_id: str,
    model_id: str = "",
    *,
    declared_efforts: list[str] | None = None,
    reasoning: bool | None = None,
) -> list[str] | None:
    """Niveaux d'intelligence réellement acceptés par ce (fournisseur, modèle), parmi ceux du chat.

    Sert au front à griser les crans qu'un modèle n'honore pas (honnêteté : ne jamais proposer un
    niveau qui planterait ou serait ignoré). La restriction est PAR MODÈLE, pas seulement par
    fournisseur : un même hébergeur peut servir un modèle à 3 niveaux et un autre à zéro (ex. Groq
    sert gpt-oss en low/medium/high mais qwen3/llama en none|default seulement). Défaut = tous les
    niveaux du chat, moins ceux que le fournisseur rejette en bloc."""
    m = (model_id or "").lower()
    if reasoning is False:
        return []
    # Une source exacte prime, puis on applique les restrictions de transport prouvées.
    if declared_efforts is not None:
        bad = _EFFORTS_UNSUPPORTED.get(provider_id, frozenset())
        return [e for e in declared_efforts if e in _CHAT_EFFORT_LEVELS and e not in bad]
    # gpt-oss : low/medium/high partout, jamais xhigh (400 chez Groq/Cerebras/Fireworks).
    if any(tok in m for tok in _MODEL_EFFORTS_LOW_MED_HIGH):
        return ["low", "medium", "high"]
    # Groq (hors gpt-oss) : aucun modèle n'accepte de reasoning_effort chiffré. qwen3 raisonne en
    # mode par défaut (reasoning=True conservé, honnête) mais l'API refuse un cran → 400 ; llama/scout
    # ne raisonnent pas. Dans les deux cas : aucun niveau proposé (tous grisés côté front).
    if provider_id == "groq":
        return []
    bad = _EFFORTS_UNSUPPORTED.get(provider_id)
    if bad is not None:
        return [e for e in _CHAT_EFFORT_LEVELS if e not in bad]
    # Inconnu n'est PAS synonyme de compatible : le front affiche « Automatique » au lieu
    # de quatre boutons susceptibles d'être ignorés ou refusés par l'API.
    return None


def get_model_capabilities(provider_id: str, model_id: str) -> dict:
    """Capacités du modèle actif, avec table de secours pour les modèles trop récents
    pour models.dev (sinon on afficherait à tort « ne gère rien »). Jamais bloquant.

    Inclut ``supported_efforts`` : les niveaux d'intelligence que ce (fournisseur, modèle) honore
    vraiment (le front grise le reste)."""
    caps = _caps_with_fallback(model_id, _raw_model_capabilities(provider_id, model_id))
    metadata = load_model_metadata(HERMES_PYTHON, HERMES_HOME, {provider_id: [model_id]})
    details = metadata.get(provider_id, {}).get(model_id, {})
    # L'alias de modèle peut être inconnu du helper capabilities tout en étant rattaché à une
    # famille exacte par notre enrichissement (ex. gpt-5.6-sol-pro -> gpt-5.6-sol).
    if details.get("reasoning") is not None:
        caps["reasoning"] = details["reasoning"]
    caps["supported_efforts"] = supported_efforts(
        provider_id,
        model_id,
        declared_efforts=details.get("supported_efforts"),
        reasoning=caps.get("reasoning"),
    )
    caps["effort_confidence"] = details.get("confidence") or (
        "verified_override" if caps["supported_efforts"] is not None else "unknown"
    )
    return caps


# Verrou exclusif sur le ``.env`` visé (fichier ``<path>.lock`` dédié, cf. ``fsutil``).
#
# Trois implémentations indépendantes (bridge + ``tool_connection_adapter``) lisaient et
# réécrivaient intégralement le même ``.env`` sans se voir : deux écritures concurrentes
# (deux onglets, double-clic) pouvaient se chevaucher et perdre silencieusement une clé
# déjà enregistrée (cf. audit Haute #3). Alias conservé (même nom) pour que les tests
# puissent continuer à monkeypatcher ``hermes_adapter._env_file_lock``.
_env_file_lock = fsutil.file_lock


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    """Écrit les lignes du ``.env`` de façon atomique (fichier temporaire + ``os.replace``).

    L'appelant doit déjà tenir ``_env_file_lock``. Jamais de fichier à moitié écrit visible
    par un lecteur concurrent (contrairement à un ``write_text`` direct).

    Ce fichier contient des secrets (clés API fournisseurs, copies ``env_key`` des tokens
    OAuth) : le mode ``0600`` est posé EXPLICITEMENT ici (cf. audit Moyenne #1) plutôt que
    de compter sur le comportement par défaut de ``tempfile.mkstemp`` — un futur
    changement de mécanisme de fichier temporaire ne doit pas pouvoir régresser cet
    invariant en silence. Délègue à ``fsutil.atomic_write_text`` (``mode=0o600``), qui pose
    la permission sur le temporaire AVANT écriture puis la reconfirme sur la cible après le
    ``replace`` — mêmes deux ``chmod`` que l'implémentation d'origine.
    """
    content = "\n".join(lines) + ("\n" if lines else "")
    fsutil.atomic_write_text(path, content, mode=0o600)


def _mutate_env_file(path: Path, mutate: Callable[[list[str]], list[str]]) -> None:
    """Point d'entrée UNIQUE pour muter un ``.env`` : lecture -> ``mutate(lignes)`` ->
    écriture, le tout sous verrou exclusif + écriture atomique. Toute mutation d'un ``.env``
    (bridge ET ``tool_connection_adapter``) doit passer par ici — DRY + sûr (cf. audit Haute #3)."""
    with _env_file_lock(path):
        lines = path.read_text().splitlines() if path.exists() else []
        _atomic_write_lines(path, mutate(lines))


def _write_env_kv(path: Path, key: str, value: str) -> None:
    """Écrit/MAJ ``KEY=value`` dans le fichier ``.env`` donné (préserve le reste).

    Reproduit ``save_env_value`` de Hermes. La valeur n'est jamais journalisée. Le paramètre
    ``path`` permet de cibler le ``.env`` d'un profil précis (chaque agent lit le sien).
    """

    def mutate(lines: list[str]) -> list[str]:
        out: list[str] = []
        found = False
        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and "=" in stripped
                and stripped.split("=", 1)[0].strip() == key
            ):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"{key}={value}")
        return out

    _mutate_env_file(path, mutate)


def _remove_env_kv(path: Path, key: str) -> None:
    """Supprime ``KEY`` du fichier ``.env`` donné (préserve le reste). No-op si absent."""
    if not path.exists():
        return

    def mutate(lines: list[str]) -> list[str]:
        return [
            line
            for line in lines
            if not (
                line.strip()
                and not line.strip().startswith("#")
                and "=" in line
                and line.strip().split("=", 1)[0].strip() == key
            )
        ]

    _mutate_env_file(path, mutate)


def _set_env_value(key: str, value: str) -> None:
    """Écrit/MAJ ``KEY=value`` dans le ``.env`` du profil courant du bridge (``~/.hermes/.env``)."""
    _write_env_kv(HERMES_HOME / ".env", key, value)


def _remove_env_value(key: str) -> None:
    """Supprime ``KEY`` du ``.env`` du profil courant (miroir de ``_set_env_value``)."""
    _remove_env_kv(HERMES_HOME / ".env", key)


def read_env_value(key: str) -> str | None:
    """Lit la valeur d'une variable dans ``~/.hermes/.env`` (jamais journalisée).

    Helper partagé : le coffre (``OBSIDIAN_VAULT_PATH``) et les intégrations le réutilisent.
    """
    path = HERMES_HOME / ".env"
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            name, value = stripped.split("=", 1)
            if name.strip() == key:
                return value.strip()
    return None


def set_key(provider_id: str, value: str, providers: list[Provider] | None = None) -> str:
    """Enregistre la clé API d'un provider dans ``~/.hermes/.env``.

    Retourne le nom de l'``env_key`` utilisé (jamais la valeur).
    Lève ``KeyError`` si provider inconnu, ``ValueError`` s'il n'attend pas de clé.

    ``providers`` : liste déjà calculée à réutiliser (évite de reconstruire ``list_providers()``
    — subprocess + jusqu'à 12 appels réseau parallèles — quand l'appelant l'a déjà sous la main,
    cf. ``set_key_and_maybe_activate``). ``None`` (défaut) = comportement inchangé.
    """
    items = providers if providers is not None else list_providers()
    provider = next((p for p in items if p.id == provider_id), None)
    if provider is None:
        raise KeyError(provider_id)
    if not provider.env_key:
        raise ValueError(f"provider {provider_id} n'attend pas de clé API")
    _set_env_value(provider.env_key, value)
    _invalidate_providers_cache()
    return provider.env_key


# --- Auto-activation au premier branchement ----------------------------------
# « Poser sa clé = ça marche tout de suite » : à l'enregistrement d'une clé, si aucun
# VRAI cerveau n'est encore actif, on active automatiquement ce fournisseur pour que le
# dirigeant n'ait pas à comprendre le bouton « Activer ». Le choix FIN du modèle se fait
# ensuite dans le chat. On ne vole jamais un cerveau déjà actif (2e clé ajoutée = simple
# mise en réserve). La liste des modèles d'un provider n'étant pas triée par pertinence
# (ex. Anthropic expose « fable » en premier), un défaut curé évite d'activer un modèle
# exotique ; repli sur le 1er modèle exposé si le provider n'est pas dans la table.
_RECOMMENDED_MODEL = {
    "anthropic": "claude-sonnet-4-6",
    "openai-api": "gpt-5.5",
    "gemini": "gemini-3.5-flash",
    "mistral": "mistral-large-latest",
    "deepseek": "deepseek-v4-pro",
    "perplexity": "sonar",
    "xai": "grok-4.3",
    # Ollama Cloud : impératif un modèle GRATUIT (les premium 403-eraient au 1er message
    # pour un client sur le palier gratuit). gpt-oss 120B = gratuit, solide, tool-capable.
    "ollama-cloud": "gpt-oss:120b",
    # Z.AI : impératif un modèle GRATUIT (les payants 429-eraient au 1er message sans crédit).
    # En mode Coding Plan glm-4.7-flash est absent de la liste → repli sur le 1er du forfait
    # (glm-5.2, inclus) via _default_model_for. glm-4.7-flash = gratuit, tool-capable, raisonne.
    "zai": "glm-4.7-flash",
    # Kimi : le plus récent/puissant en tête (K2.7-Code) = recommandé, cohérent avec l'ordre
    # récent → ancien du sélecteur (le front badge le 1er modèle exposé).
    "kimi-coding": "kimi-k2.7-code",
    # Cohere : le plus récent/puissant (Command-A-Plus, 05-2026) = recommandé.
    "cohere": "command-a-plus-05-2026",
    # Kilo Code : impératif un modèle GRATUIT (les payants 402-eraient à 0 crédit). kilo-auto/free
    # = routeur auto gratuit, tool-capable → un compte sans crédit a un cerveau qui répond.
    "kilocode": "kilo-auto/free",
    # OpenCode Zen : impératif un GRATUIT (les payants → 401 « No payment method » sans carte).
    # deepseek-v4-flash-free répond sans carte (testé). Go : mécanisme identique (défini au test).
    "opencode-zen": "deepseek-v4-flash-free",
    # Novita : aucun gratuit (payant). Le moins cher (Deepseek V4 Flash) = défaut d'activation ;
    # il faudra du solde pour qu'il réponde (badge « crédit requis » honnête en attendant).
    "novita": "deepseek/deepseek-v4-flash",
    # Hugging Face : le crédit mensuel gratuit fait tourner les modèles. DeepSeek-V3.2 = bon défaut.
    "huggingface": "deepseek-ai/DeepSeek-V3.2",
    # Cerebras : 3 modèles TOUS gratuits (1M tokens/j). gpt-oss-120b = seul « Production » (stable,
    # les 2 autres sont Preview volatils) + raisonne → défaut d'activation sûr et pérenne.
    "cerebras": "gpt-oss-120b",
    # Fireworks : deepseek-v4-pro = le plus capable (1M contexte, raisonne, tool-capable) → défaut.
    "fireworks": "accounts/fireworks/models/deepseek-v4-pro",
    # Groq : tier gratuit → tout gratuit. llama-3.3-70b-versatile = flagship stable tool-capable
    # (le plus éprouvé pour un usage général) → défaut d'activation sûr.
    "groq": "llama-3.3-70b-versatile",
    "xiaomi": "mimo-v2.5-pro",  # le plus puissant des 2 LLM MiMo (raisonne + outils, testé)
    "stepfun": "step-3.5-flash",  # seul LLM chat servi (raisonne, 256K — specs off. ; abonnement requis)
}


def _default_model_for(provider: Provider) -> str | None:
    """Modèle à activer par défaut : le recommandé curé s'il existe chez ce provider,
    sinon le premier modèle exposé (``None`` si le provider n'expose aucun modèle)."""
    rec = _RECOMMENDED_MODEL.get(provider.id)
    if rec and any(m.id == rec for m in provider.models):
        return rec
    return provider.models[0].id if provider.models else None


def _has_real_active_brain(providers: list[Provider] | None = None) -> bool:
    """True si un VRAI cerveau tourne déjà : provider ≠ défaut d'usine « auto » ET son
    fournisseur est configuré. Sert à auto-activer au 1er branchement sans jamais voler
    le cerveau actif quand on ajoute une clé supplémentaire.

    ``providers`` : cf. ``set_key`` — liste déjà calculée à réutiliser. ``None`` = inchangé."""
    active = get_active()
    if active is None or active.provider_id in ("", "auto", None):
        return False
    items = providers if providers is not None else list_providers()
    prov = next((p for p in items if p.id == active.provider_id), None)
    return prov is not None and prov.state != ProviderState.not_configured


def set_key_and_maybe_activate(provider_id: str, value: str) -> dict:
    """Enregistre la clé, puis auto-active ce fournisseur si aucun vrai cerveau n'est
    encore actif. Retourne ``{env_key, activated}`` où ``activated`` vaut ``None`` (rien
    changé) ou ``{provider_id, model_id}`` (fournisseur activé). Propage KeyError/ValueError.

    ``list_providers()`` n'est reconstruit qu'UNE fois ici (subprocess + jusqu'à 12 appels
    réseau parallèles à chaque appel) et réutilisé pour ``set_key``/``_has_real_active_brain``
    — au lieu de jusqu'à 3 reconstructions indépendantes pour un seul geste « enregistrer une
    clé » (cf. audit Moyenne #2, chemin le plus fréquenté : le tout premier onboarding)."""
    providers = list_providers()
    env_key = set_key(provider_id, value, providers=providers)
    activated = None
    if not _has_real_active_brain(providers=providers):
        provider = next((p for p in providers if p.id == provider_id), None)
        if provider is not None:
            model = _default_model_for(provider)
            if model:
                set_active(provider_id, model, provider.base_url)
                activated = {"provider_id": provider_id, "model_id": model}
    return {"env_key": env_key, "activated": activated}


def remove_key(provider_id: str) -> dict:
    """Retire la clé API d'un provider (efface ``env_key`` du ``.env``, miroir de set_key).

    Si ce fournisseur était le cerveau ACTIF, on bascule proprement : sur un autre
    fournisseur encore branché s'il y en a un, sinon retour au défaut « auto » (le
    bandeau affichera alors « Choisissez votre cerveau »). Jamais de cerveau fantôme.
    Retourne ``{switched}`` : ``None`` (cerveau inchangé) ou le nouveau cerveau actif.
    Lève ``KeyError`` (provider inconnu) / ``ValueError`` (pas de clé attendue).

    Les DEUX lectures de ``list_providers()`` ci-dessous (avant/après le retrait de la clé)
    partagent le cache TTL court (cf. ``_LIST_PROVIDERS_CACHE``) tant qu'aucune écriture ne
    l'a invalidé entre les deux — une seule reconstruction réelle pour les deux lookups
    (cf. audit perf Haute #3). Sûr : la 2e lecture EXCLUT explicitement ``provider_id``
    (``p.id != provider_id``), donc même si le cache renvoie encore ce provider comme
    "configuré" (retrait pas encore visible), il est de toute façon filtré. Le cache n'est
    invalidé qu'à la TOUTE fin de la fonction — jamais avant, pour ne pas provoquer une 3e
    reconstruction ici — afin que les appels EXTERNES suivants (front qui re-fetch) voient
    l'état à jour (invariant d'honnêteté)."""
    provider = next((p for p in list_providers() if p.id == provider_id), None)
    if provider is None:
        raise KeyError(provider_id)
    if not provider.env_key:
        raise ValueError(f"provider {provider_id} n'a pas de clé à retirer")
    _remove_env_value(provider.env_key)

    switched = None
    active = get_active()
    if active is not None and active.provider_id == provider_id:
        # Ce fournisseur était le cerveau actif → basculer (miroir de l'auto-activation).
        others = [
            p
            for p in list_providers()
            if p.id != provider_id and p.state != ProviderState.not_configured and p.models
        ]
        if others:
            target = others[0]
            model = _default_model_for(target)
            if model:
                # set_active() invalide déjà le cache (cf. son propre finally) — l'appel
                # explicite ci-dessous reste nécessaire pour couvrir aussi le chemin
                # "aucun autre provider" (repli "auto" via _hermes_config_set direct,
                # qui ne passe pas par set_active).
                set_active(target.id, model, target.base_url)
                switched = {"provider_id": target.id, "model_id": model}
        if switched is None:
            # Plus aucun cerveau branché → retour au défaut « auto » (assistant sans cerveau,
            # état honnête). On ne pose que le provider : en mode auto la clé manque de toute
            # façon, l'utilisateur doit rebrancher une clé (ce qui réactivera tout proprement).
            _hermes_config_set("model.provider", "auto")
            switched = {"provider_id": "auto", "model_id": None}
    # Invalidation de fin de fonction (cf. docstring) : la clé retirée ne doit plus jamais
    # apparaître "configurée" au prochain appel EXTERNE de list_providers().
    _invalidate_providers_cache()
    return {"switched": switched}


# Credentials AWS (Bedrock, auth_type=aws_sdk) — lus par le SDK AWS de Hermes.
_AWS_ENV_REQUIRED = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


def set_aws_credentials(access_key_id: str, secret_access_key: str, region: str | None) -> None:
    """Enregistre les credentials AWS (Bedrock) dans ``~/.hermes/.env``.

    Les valeurs ne sont jamais renvoyées ni journalisées.
    """
    _set_env_value("AWS_ACCESS_KEY_ID", access_key_id)
    _set_env_value("AWS_SECRET_ACCESS_KEY", secret_access_key)
    if region:
        _set_env_value("AWS_DEFAULT_REGION", region)
    # Change l'état "configuré" du provider Bedrock (aws_sdk) dans list_providers().
    _invalidate_providers_cache()


# --- Process en arrière-plan (OAuth, mise à jour Hermes) ----------------------
# On lance une commande Hermes en arrière-plan, on écrit sa sortie dans un fichier
# de log, et on suit l'avancement via le statut (running / success / log).

_OAUTH_RUNS: dict[str, dict] = {}  # clé -> {proc, log_path, log_file}
# Protège le triplet vérification-Popen-écriture de _start_bg_run : sans lui, deux appels
# concurrents pour la MÊME clé (double-clic « Connecter », retry réseau) liraient tous deux
# _OAUTH_RUNS AVANT qu'aucun n'écrive → deux process lancés, le handle de l'un des deux perdu
# (fuite + confusion PKCE/state côté flux OAuth qui suit). Même principe que _UPDATE_LOCK
# pour start_update, mais générique (couvre aussi start_oauth engine + tool_connection_adapter).
_BG_RUN_LOCK = threading.Lock()


def _oauth_log_path(key: str) -> Path:
    safe = "".join(c for c in key if c.isalnum() or c in "-_")
    return Path(tempfile.gettempdir()) / f"hermes_bg_{safe}.log"


def _start_bg_run(key: str, cmd: list[str]) -> None:
    """Lance ``cmd`` en arrière-plan sous ``key`` (idempotent tant qu'un run est actif)."""
    with _BG_RUN_LOCK:
        existing = _OAUTH_RUNS.get(key)
        if existing and existing["proc"].poll() is None:
            return  # déjà en cours
        if existing is not None:
            # Le run précédent (même clé) est terminé : on ferme explicitement son fd de log
            # plutôt que de compter sur le ramasse-miettes lors de l'écrasement de l'entrée
            # (sinon ResourceWarning, non portable vers un runtime sans GC déterministe).
            old_log_file = existing.get("log_file")
            if old_log_file is not None and not old_log_file.closed:
                old_log_file.close()
        log_path = _oauth_log_path(key)
        log_file = log_path.open("w")
        try:
            # PYTHONUNBUFFERED : la sortie est redirigée vers un FICHIER (pas un TTY), donc le CLI
            # Python la bufferise par blocs → le device code (URL + code d'appairage OAuth, ~200 o)
            # ne serait flushé qu'à la sortie du process (timeout). On force le flush immédiat pour
            # que l'UI puisse afficher l'URL/le code dès qu'ils sont générés.
            proc = subprocess.Popen(  # noqa: S603 (commande Hermes interne)
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,  # line-buffered côté parent
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except OSError as exc:
            log_file.close()
            raise HermesUnavailable(str(exc)) from exc
        _OAUTH_RUNS[key] = {"proc": proc, "log_path": log_path, "log_file": log_file}


def _bg_status(key: str) -> dict:
    """État d'un run en arrière-plan : {running, success?, returncode?, log}."""
    run = _OAUTH_RUNS.get(key)
    if not run:
        return {"running": False, "started": False, "log": ""}
    proc = run["proc"]
    log_path: Path = run["log_path"]
    log = log_path.read_text(errors="replace") if log_path.exists() else ""
    rc = proc.poll()
    if rc is None:
        return {"running": True, "started": True, "log": log}
    return {"running": False, "started": True, "success": rc == 0, "returncode": rc, "log": log}


def start_oauth(provider_id: str) -> None:
    """Démarre `hermes auth add <provider> --type oauth` (navigateur ouvert sur l'hôte)."""
    _start_bg_run(provider_id, [HERMES_BIN, "auth", "add", provider_id, "--type", "oauth"])


def oauth_status(provider_id: str) -> dict:
    return _bg_status(provider_id)


# Déconnexion OAuth exécutée par l'interpréteur de Hermes (le venv du bridge n'a pas
# ``hermes_cli`` ; seul ``HERMES_PYTHON`` l'a — même mécanisme que ``_INTROSPECT_SCRIPT``).
# On appelle directement la lib plutôt que le CLI ``hermes logout`` : ce dernier bride
# ``--provider`` à une liste figée (nous/openai-codex/xai-oauth/spotify) via ``argparse`` et
# rejette tout autre fournisseur — dont ``minimax-oauth`` — avant d'agir (code 2). Le
# ``provider_id`` est reçu en ``sys.argv[1]`` (jamais interpolé dans la source → aucune
# injection possible depuis l'URL). Code retour 3 = fournisseur inconnu.
_LOGOUT_SCRIPT = (
    "import sys\n"
    "from hermes_cli.auth import (clear_provider_auth, is_known_auth_provider,\n"
    "    _should_reset_config_provider_on_logout, _reset_config_provider)\n"
    "pid = sys.argv[1]\n"
    "if not is_known_auth_provider(pid):\n"
    "    sys.stderr.write('fournisseur inconnu: ' + pid); raise SystemExit(3)\n"
    "should_reset = _should_reset_config_provider_on_logout(pid)\n"
    "clear_provider_auth(pid)\n"  # idempotent côté moteur : rien à effacer = sans effet
    "if should_reset:\n"
    "    _reset_config_provider()\n"
)


def logout_oauth(provider_id: str) -> None:
    """Déconnecte un compte OAuth via l'interpréteur de Hermes (``HERMES_PYTHON``).

    Reproduit fidèlement ``hermes logout`` (la fonction ``logout_command`` du moteur) mais
    SANS passer par le CLI, qui bride ``--provider`` et rejette ``minimax-oauth``. Retire le
    fournisseur de ``providers`` et ``credential_pool`` de ``auth.json`` (verrou + écriture
    atomique côté moteur), remet ``active_provider`` à ``None`` s'il était actif, et
    réinitialise ``model.provider`` dans ``config.yaml`` si le fournisseur y était sélectionné
    (cas du fournisseur actif — MiniMax). Idempotent : déjà déconnecté = sans effet. Lève
    ``HermesUnavailable`` si le fournisseur est inconnu ou si le moteur échoue.
    """
    env = os.environ.copy()
    env["HERMES_HOME"] = str(HERMES_HOME)  # cible le bon auth.json/config.yaml (profil, ou tmp en test)
    try:
        proc = subprocess.run(  # noqa: S603 (interpréteur Hermes interne ; argv sûr)
            [HERMES_PYTHON, "-c", _LOGOUT_SCRIPT, provider_id],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    if proc.returncode == 3:
        raise HermesUnavailable(f"fournisseur OAuth inconnu : {provider_id}")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        raise HermesUnavailable(
            f"déconnexion Hermes échouée (code {proc.returncode})" + (f" : {detail}" if detail else "")
        )
    # auth.json (credential_pool) et éventuellement config.yaml (model.provider réinitialisé)
    # viennent de changer : ce fournisseur ne doit plus apparaître "connecté" au prochain
    # list_providers() (cf. invariant d'honnêteté du cache).
    _invalidate_providers_cache()


# --- Mise à jour du moteur avec filet de sécurité (readiness + rollback auto) ----
#
# `hermes update` peut « réussir » (code retour 0) sans que le moteur reparte, ou
# échouer à mi-chemin (réseau coupé, disque plein, dépendances cassées). Pour que la
# MAJ en 1 clic soit sans risque chez un client non-tech, on encadre la commande :
#   1. avant : on note le commit git courant (point de retour du code) ;
#   2. `--backup` crée déjà une sauvegarde ZIP de ~/.hermes ;
#   3. après : contrôle de santé (le CLI répond ET le chat répond) ;
#   4. si la MAJ a échoué OU si le moteur ne repart pas → rollback automatique
#      (git reset + réinstall des deps + restauration + redémarrage du gateway).

# Le clone réellement exécuté par HERMES_BIN. Dans la stack Docker il est monté sur un
# volume dédié à /opt/hermes-agent afin que `hermes update` survive aux recréations.
# HERMES_INSTALL_DIR explicite évite surtout l'ancien bug : le rollback visait une copie
# sous HERMES_HOME alors que le gateway exécutait /opt/hermes-agent.
_HERMES_CLONE = Path(
    os.path.expanduser(
        os.environ.get(
            "HERMES_INSTALL_DIR",
            str(HERMES_HOME / "hermes-agent"),
        )
    )
)

# État partagé enrichi par le thread de supervision. `phase` ∈
# idle | running | finalizing | success | rolling_back | rolled_back | rollback_failed
_UPDATE_STATE: dict = {"phase": "idle"}
# Protège le check-then-spawn de start_update : deux appels concurrents (double-clic, retry
# front) ne doivent JAMAIS lancer deux superviseurs sur le même process (double rollback).
_UPDATE_LOCK = threading.Lock()
_GATEWAY_PID_FILE = Path(
    os.environ.get("HERMES_GATEWAY_PID_FILE", "/tmp/lunaria-hermes-gateway.pid")
)
_RUNTIME_PID_FILE = Path(
    os.environ.get("HERMES_RUNTIME_PID_FILE", "/tmp/lunaria-hermes-runtime.pid")
)


def _git_head() -> str | None:
    """Commit courant du clone moteur — point de retour du code pour un rollback."""
    try:
        res = subprocess.run(
            ["git", "-C", str(_HERMES_CLONE), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("git rev-parse HEAD indisponible (%s) — aucun point de retour connu", exc)
        return None
    head = res.stdout.strip()
    if not (res.returncode == 0 and head):
        logger.debug("git rev-parse HEAD a échoué (code %s) — aucun point de retour connu", res.returncode)
        return None
    return head


def _prepare_git_branch_for_update(prev_hash: str | None) -> bool:
    """Place un ancien seed Docker détaché sur ``main`` avant la MAJ.

    Les premières images LunarIA épinglaient Hermes avec ``git checkout <sha>``.
    Dans ce cas, ``hermes update`` bascule vers la branche locale ``main`` déjà au
    dernier commit, conclut « Already up to date » et saute la réinstallation des
    dépendances. Le code change alors sans que le venv suive. Les nouvelles images
    sont seedées directement sur ``main`` ; cette garde répare aussi les volumes
    persistants créés par les anciennes images.
    """
    if not prev_hash:
        return False
    try:
        branch = subprocess.run(
            ["git", "-C", str(_HERMES_CLONE), "symbolic-ref", "--quiet", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if branch.returncode == 0:
            return True
        checkout = subprocess.run(
            ["git", "-C", str(_HERMES_CLONE), "checkout", "-B", "main", prev_hash],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Préparation de la branche Hermes impossible : %s", exc)
        return False
    if checkout.returncode != 0:
        logger.error("Préparation de la branche Hermes échouée : %s", checkout.stderr.strip()[:1000])
        return False
    return True


def _latest_pre_update_backup() -> Path | None:
    """La sauvegarde ZIP créée juste avant la MAJ (la plus récente)."""
    backups = HERMES_HOME / "backups"
    if not backups.is_dir():
        return None
    zips = sorted(backups.glob("pre-update-*.zip"))
    return zips[-1] if zips else None


def _engine_ready() -> bool:
    """Le moteur est-il vraiment reparti ? CLI répond ET API du chat joignable."""
    if _hermes_version() is None:
        return False
    return _api_server_reachable(_api_server_port())


def _log_step_result(
    step: str, result: subprocess.CompletedProcess | None, exc: Exception | None = None
) -> None:
    """Journalise le résultat d'une étape critique (rollback, redémarrage gateway).

    Capture le stdout/stderr du sous-process AU LIEU de les avaler (audit observabilité
    2026-07-16, Haute #1) — c'est ce qui permet de comprendre après coup, sans accès à la
    machine, quelle étape a cassé et pourquoi. Tronqué (4000 car.) pour éviter un log géant si
    la commande est très bavarde. Ne journalise jamais de secret : ces commandes (git/pip/
    hermes CLI) n'écrivent pas de clé/token sur leur sortie standard.
    """
    if exc is not None:
        logger.warning("Rollback moteur — étape %r : exception %s: %s", step, type(exc).__name__, exc)
        return
    if result is None:  # défensif — ne devrait pas arriver hors test avec un subprocess mocké
        return
    output = ((result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")).strip()
    output = output[:4000]
    if result.returncode == 0:
        logger.info(
            "Rollback moteur — étape %r : OK (code 0)%s",
            step,
            f" — sortie : {output}" if output else "",
        )
    else:
        logger.warning(
            "Rollback moteur — étape %r : ÉCHEC (code %s) — sortie : %s",
            step,
            result.returncode,
            output or "(vide)",
        )


def _restart_gateway() -> None:
    """Demande à la boucle de l'entrypoint de relancer le gateway Hermes.

    Dans Docker, ``hermes gateway restart`` tente de gérer lui-même un service et peut
    rester bloqué. L'entrypoint LunarIA est déjà le superviseur : on termine uniquement
    son processus enfant identifié par PID, puis sa boucle le relance avec le nouveau code.
    """
    logger.info("Redémarrage du gateway et du runtime Hermes via le superviseur LunarIA")
    # Le runtime résident a importé le code Hermes en mémoire : une mise à jour doit donc
    # le recycler lui aussi. Échec non bloquant, car le gateway reste le repli sûr.
    try:
        runtime_pid = int(_RUNTIME_PID_FILE.read_text(encoding="utf-8").strip())
        runtime_cmdline = (
            Path(f"/proc/{runtime_pid}/cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", errors="replace")
        )
        if "hermes_runtime_server.py" not in runtime_cmdline:
            raise RuntimeError(f"PID {runtime_pid} ne correspond pas au runtime LunarIA")
        os.kill(runtime_pid, signal.SIGTERM)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning("Recyclage du runtime conversationnel non confirmé : %s", exc)
    try:
        old_pid = int(_GATEWAY_PID_FILE.read_text(encoding="utf-8").strip())
        cmdline = (
            Path(f"/proc/{old_pid}/cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", errors="replace")
        )
        if "hermes" not in cmdline or "gateway run" not in cmdline:
            raise RuntimeError(f"PID {old_pid} ne correspond pas au gateway Hermes")
        os.kill(old_pid, signal.SIGTERM)
        for _ in range(15):  # boucle entrypoint : relance après 10 s
            time.sleep(2)
            try:
                new_pid = int(_GATEWAY_PID_FILE.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                continue
            if new_pid != old_pid and Path(f"/proc/{new_pid}").exists():
                logger.info(
                    "Gateway Hermes relancé par LunarIA (ancien PID=%s, nouveau PID=%s)",
                    old_pid,
                    new_pid,
                )
                return
        raise TimeoutError("le superviseur LunarIA n'a pas relancé le gateway sous 30 s")
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        _log_step_result("relance gateway supervisée", None, exc)


def _rollback(prev_hash: str | None, backup: Path | None) -> bool:
    """Restaure l'état d'avant la MAJ : code (git) + deps + données, puis relance.

    Best-effort : on tente chaque étape et on relance le gateway dans tous les cas.
    Renvoie True uniquement si le VRAI clone exécuté a le commit attendu ET si le moteur
    répond après redémarrage. On ne doit jamais annoncer « restauré » sur le seul code retour
    de `git reset` appliqué au mauvais dossier ou sur un gateway resté hors ligne.

    Chaque étape journalise début/fin/résultat (INFO succès, WARNING échec) — c'est le chemin
    le plus critique du bridge (audit observabilité 2026-07-16, Haute #1) : sans ça, un rollback
    raté à distance chez un client ne laissait aucune trace exploitable après un redémarrage.
    """
    logger.warning(
        "Rollback moteur DÉMARRÉ (prev_hash=%s, backup=%s)",
        prev_hash or "(aucun point de retour connu)",
        backup or "(aucune sauvegarde pré-MAJ trouvée)",
    )
    code_ok = False
    clone = str(_HERMES_CLONE)
    if prev_hash:
        try:
            r = subprocess.run(
                ["git", "-C", clone, "reset", "--hard", prev_hash],
                capture_output=True,
                text=True,
                timeout=180,
            )
            code_ok = r.returncode == 0
            _log_step_result("git reset --hard", r)
        except (OSError, subprocess.TimeoutExpired) as exc:
            code_ok = False
            _log_step_result("git reset --hard", None, exc)
        # Réinstalle les deps de l'ancienne version (best-effort ; install git = venv).
        try:
            r_pip = subprocess.run(
                [HERMES_PYTHON, "-m", "pip", "install", "-e", f"{clone}[all]"],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=1800,
            )
            _log_step_result("pip install -e [all]", r_pip)
        except (OSError, subprocess.TimeoutExpired) as exc:
            _log_step_result("pip install -e [all]", None, exc)
    # Restaure la config/les données depuis la sauvegarde pré-MAJ (best-effort).
    if backup and backup.exists():
        try:
            r_import = subprocess.run(
                [HERMES_BIN, "import", str(backup), "--force"],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=600,
            )
            _log_step_result("hermes import --force", r_import)
        except (OSError, subprocess.TimeoutExpired) as exc:
            _log_step_result("hermes import --force", None, exc)
    _restart_gateway()
    actual_hash = _git_head()
    commit_ok = bool(code_ok and prev_hash and actual_hash == prev_hash)
    ready = False
    if commit_ok:
        for _ in range(20):  # ~80 s max, comme la vérification post-MAJ
            if _engine_ready():
                ready = True
                break
            time.sleep(4)
    restored = bool(commit_ok and ready)
    logger.warning(
        "Rollback moteur TERMINÉ : reset_ok=%s commit_ok=%s moteur_prêt=%s restauré=%s",
        code_ok,
        commit_ok,
        ready,
        restored,
    )
    return restored


def _supervise_update(prev_hash: str | None) -> None:
    """Attend la fin de `hermes update`, contrôle la santé, rollback si besoin.

    Journalise chaque transition de phase (audit observabilité 2026-07-16, Haute #1) : c'est le
    seul moyen de reconstituer après coup le déroulé d'une MAJ si le bridge redémarre en cours
    de route (l'état ``_UPDATE_STATE`` en mémoire, lui, est perdu au redémarrage).
    """
    run = _OAUTH_RUNS.get("__update__")
    if not run:
        return
    logger.info("Supervision de la MAJ moteur démarrée (prev_hash=%s)", prev_hash or "(inconnu)")
    rc = run["proc"].wait()
    logger.info("Commande `hermes update --yes --backup` terminée (code retour %s)", rc)
    backup = _latest_pre_update_backup()
    if rc != 0:
        # La commande de MAJ a échoué → on restaure l'état précédent.
        logger.warning("MAJ moteur en ÉCHEC (code %s) → déclenchement du rollback automatique", rc)
        _UPDATE_STATE["phase"] = "rolling_back"
        ok = _rollback(prev_hash, backup)
        _UPDATE_STATE["phase"] = "rolled_back" if ok else "rollback_failed"
        logger.warning("Fin de supervision MAJ moteur : phase finale = %s", _UPDATE_STATE["phase"])
        return
    # MAJ « réussie » (rc==0) : on s'assure que le moteur repart vraiment.
    logger.info("MAJ moteur réussie côté commande (code 0) — vérification que le moteur repart")
    _UPDATE_STATE["phase"] = "finalizing"
    _restart_gateway()
    ready = False
    for _ in range(20):  # ~80 s max, le temps que le gateway remonte
        if _engine_ready():
            ready = True
            break
        time.sleep(4)
    if ready:
        _UPDATE_STATE["phase"] = "success"
        logger.info("MAJ moteur terminée avec succès : le moteur répond de nouveau")
    else:
        # Le code s'est installé mais le moteur ne repart pas → rollback.
        logger.warning("Le moteur ne répond pas après la MAJ → déclenchement du rollback automatique")
        _UPDATE_STATE["phase"] = "rolling_back"
        ok = _rollback(prev_hash, backup)
        _UPDATE_STATE["phase"] = "rolled_back" if ok else "rollback_failed"
        logger.warning("Fin de supervision MAJ moteur : phase finale = %s", _UPDATE_STATE["phase"])


def start_update() -> None:
    """Lance `hermes update --yes --backup` sous supervision (readiness + rollback).

    Idempotent : si une MAJ est déjà en cours (un superviseur tourne), on NE relance ni le
    process ni un second superviseur. Sinon un double appel (double-clic, retry front) ferait
    tourner deux _supervise_update sur le même process → deux _rollback concurrents (double
    git reset / pip install / hermes import) → corruption possible du moteur sur le VPS client.
    """
    with _UPDATE_LOCK:
        if _UPDATE_STATE.get("phase") in ("running", "finalizing", "rolling_back"):
            logger.info(
                "start_update() ignoré : une MAJ moteur est déjà en cours (phase=%s)",
                _UPDATE_STATE.get("phase"),
            )
            return
        prev_hash = _git_head()
        if not _prepare_git_branch_for_update(prev_hash):
            raise RuntimeError("Impossible de préparer le dépôt Hermes pour une mise à jour sûre")
        logger.info("Démarrage d'une MAJ moteur (hermes update --yes --backup, prev_hash=%s)", prev_hash or "(inconnu)")
        _start_bg_run("__update__", [HERMES_BIN, "update", "--yes", "--backup"])
        _UPDATE_STATE.clear()
        _UPDATE_STATE.update({"phase": "running", "prev_hash": prev_hash})
        threading.Thread(target=_supervise_update, args=(prev_hash,), daemon=True).start()


def update_status() -> dict:
    """État de la MAJ, enrichi par la phase de supervision (readiness / rollback)."""
    base = _bg_status("__update__")
    phase = _UPDATE_STATE.get("phase", "idle")
    base["phase"] = phase
    if phase in ("running", "finalizing", "rolling_back"):
        # Tant qu'on finalise / rollback : on garde le front en attente (polling).
        base["running"] = True
        base["started"] = True
        base.pop("success", None)
    elif phase == "success":
        base.update({"running": False, "started": True, "success": True})
    elif phase in ("rolled_back", "rollback_failed"):
        base.update(
            {
                "running": False,
                "started": True,
                "success": False,
                "rolled_back": phase == "rolled_back",
            }
        )
    return base


# --- Statut Hermes (onglet « Agent Hermes ») ----------------------------------


def _hermes_version() -> str | None:
    """Première ligne de `hermes --version` (ex: 'Hermes Agent v0.17.0 ...')."""
    try:
        res = subprocess.run([HERMES_BIN, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (res.stdout or res.stderr or "").strip()
    return text.splitlines()[0] if text else None


def _api_server_port() -> int:
    """Port de l'API server Hermes (chat) — lu dans ~/.hermes/.env, défaut 8642.

    8642 est le défaut du moteur (gateway/platforms/api_server.py DEFAULT_PORT) ;
    l'ancien repli 8645 venait de la v1 et ne correspondait à rien côté moteur.
    """
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_PORT") and "=" in line:
                try:
                    return int(line.split("=", 1)[1].strip())
                except ValueError:
                    logger.debug("API_SERVER_PORT invalide dans .env (%r) — repli sur 8642", line)
    return 8642


def _api_server_key() -> str | None:
    """Clé d'auth de l'API server Hermes — lue dans ``~/.hermes/.env`` (``API_SERVER_KEY``).

    Sert à autoriser les appels à l'API jobs (cron) d'Hermes. ``None`` si absente.
    """
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_KEY") and "=" in line:
                value = line.split("=", 1)[1].strip()
                return value or None
    return None


def _api_server_reachable(port: int) -> bool:
    """L'API server du chat répond-il ? (401/403 = joignable, connexion refusée = non)."""
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{port}/v1/models"
    try:
        urllib.request.urlopen(url, timeout=5)  # noqa: S310 (URL locale contrôlée)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


def _last_update_date() -> str | None:
    """Date ISO de la dernière mise à jour = horodatage de la dernière sauvegarde
    ``pre-update-*.zip`` (créée automatiquement à chaque MAJ). None si jamais mis à jour."""
    backups = HERMES_HOME / "backups"
    if not backups.is_dir():
        return None
    zips = sorted(backups.glob("pre-update-*.zip"))
    if not zips:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})", zips[-1].name)
    if not m:
        return None
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


def _brain_connected(providers: list | None = None) -> bool:
    """Un modèle IA est-il RÉELLEMENT utilisable ? = au moins un fournisseur connecté
    (compte OAuth, clé API ou local). Faux = aucun modèle, même si le moteur tourne :
    l'assistant ne pourrait pas répondre, l'UI doit le dire honnêtement.
    """
    try:
        items = providers if providers is not None else list_providers()
        return any(p.state != ProviderState.not_configured for p in items)
    except HermesUnavailable:
        return False


def _active_provider_label(active, providers: list) -> str | None:
    """Nom LISIBLE du fournisseur actif (son label, ex. « OpenAI Codex »), jamais le slug
    technique (« auto » / « openai-codex »). ``None`` si aucun modèle actif ; repli sur le
    slug si le fournisseur n'est pas dans la liste (ex. mode « auto »)."""
    if not active:
        return None
    match = next((p for p in providers if p.id == active.provider_id), None)
    return match.label if match else active.provider_id


def hermes_status() -> dict:
    """Vue d'ensemble : version, modèle IA actif, joignabilité (moteur + câble du chat)."""
    try:
        active = get_active()
    except HermesUnavailable:
        active = None
    try:
        providers = list_providers()
    except HermesUnavailable:
        providers = []
    port = _api_server_port()
    return {
        "version": _hermes_version(),
        "active": active.model_dump() if active else None,
        "active_provider_label": _active_provider_label(active, providers),
        "brain_connected": _brain_connected(providers),
        "hermes_available": Path(HERMES_PYTHON).exists(),
        "api_server": {"port": port, "reachable": _api_server_reachable(port)},
        "last_update": _last_update_date(),
    }


def _version_tuple(v: str | None) -> tuple[int, ...]:
    """Extrait les composants numériques d'une version pour comparaison.

    ``"v0.18.0"`` -> ``(0, 18, 0)``. ``()`` si vide/illisible.
    """
    if not v:
        return ()
    return tuple(int(n) for n in re.findall(r"\d+", v))


def _pyproject_version(text: str | None) -> str | None:
    """Lit ``version = "x.y.z"`` dans un contenu de ``pyproject.toml``."""
    if not text:
        return None
    m = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else None


def _local_pkg_version() -> str | None:
    """Version du paquet dans le ``pyproject.toml`` du clone local."""
    try:
        return _pyproject_version((_HERMES_CLONE / "pyproject.toml").read_text())
    except OSError:
        return None


def _remote_pkg_version() -> str | None:
    """Version du paquet sur ``origin/main`` (après un fetch léger). ``None`` si indéterminée.

    Déterministe et tolérant au hors-ligne : toute erreur git -> ``None`` (on ne crie
    JAMAIS « MAJ dispo » sans certitude).
    """
    if not (_HERMES_CLONE / ".git").exists():
        return None
    try:
        subprocess.run(
            ["git", "-C", str(_HERMES_CLONE), "fetch", "origin", "main", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        res = subprocess.run(
            ["git", "-C", str(_HERMES_CLONE), "show", "origin/main:pyproject.toml"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return _pyproject_version(res.stdout) if res.returncode == 0 else None


def update_check() -> dict:
    """Vérifie si une nouvelle **version** du moteur est disponible.

    Détection **déterministe par version** (choix produit, honnête pour un dirigeant) :
    on compare le numéro de version du paquet (``pyproject.toml``) local à celui
    d'``origin/main``. Un simple commit de correctif sur ``main`` qui ne change PAS le
    numéro de version ne déclenche donc pas de « mise à jour disponible » — cohérent avec
    le « v0.18.0 » affiché partout au client.

    ``hermes update --check`` est toujours lancé, mais seulement pour son journal
    technique (affiché replié dans l'UI). L'état ``available`` ne dépend PLUS d'un
    parsing de ce texte anglais (fragile), et ``hermes update --check`` renvoie de toute
    façon toujours ``0`` (à jour ou non), d'où l'inutilité du code de retour.
    """
    try:
        res = subprocess.run(
            [HERMES_BIN, "update", "--check"], capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HermesUnavailable(str(exc)) from exc
    output = ((res.stdout or "") + (res.stderr or "")).strip()

    current = _local_pkg_version()
    latest = _remote_pkg_version()
    # available = True UNIQUEMENT si on est certain qu'une version plus récente existe.
    available = bool(current and latest and _version_tuple(latest) > _version_tuple(current))
    return {
        "returncode": res.returncode,
        "output": output[:2000],
        "available": available,
        "current_version": current,
        "latest_version": latest,
    }


# --- Test de clé API (probe réseau avant enregistrement) ---------------------
# Le probe générique ``GET {base_url}/models`` en ``Authorization: Bearer`` convient
# à la majorité des API OpenAI-compatibles, mais échoue pour deux familles, d'où
# une table de stratégies par provider (constatée par audit réseau, cf. tests) :
#
#   "anthropic" : auth via ``x-api-key`` + ``anthropic-version`` (le Bearer est ignoré)
#                 et l'endpoint est ``{base}/v1/models`` (le base_url n'a pas de /v1).
#                 Sans ça → HTTP 404 même avec une clé VALIDE (faux négatif).
#   "chat"      : providers dont ``GET /models`` est PUBLIC (répond 200 sans clé →
#                 faux positif : une fausse clé passe pour valide) ou absent
#                 (Perplexity → 404). On teste ``POST /chat/completions`` qui, lui,
#                 exige l'auth (401/403 sur clé invalide, franchie sinon).
#
# Défaut ("models") : ``GET {base}/models`` en Bearer.
_ANTHROPIC_VERSION = "2023-06-01"
_PROBE_ANTHROPIC = frozenset({"anthropic", "minimax", "minimax-cn"})
# ``openrouter`` : son ``GET /models`` est un catalogue PUBLIC (répond 200 même avec
# une clé bidon → faux positif). ``POST /chat/completions`` exige l'auth (401 sur clé
# invalide, franchi sinon) → seule stratégie fiable.
_PROBE_CHAT = frozenset(
    {"perplexity", "nvidia", "huggingface", "ollama-cloud", "kilocode", "alibaba-coding-plan", "openrouter",
     # OpenCode Zen/Go : leur GET /models est PUBLIC (200 même avec une clé bidon → faux positif).
     # Seul POST /chat/completions exige l'auth (401 « Invalid API key »). Vérifié en réel 2026-07-07.
     "opencode-zen", "opencode-go",
     # Novita : GET /models PUBLIC (200 clé bidon). POST /chat/completions exige l'auth
     # (401 « FAILED_TO_AUTH »). Vérifié en réel 2026-07-07.
     "novita"}
)
# Google Gemini : la clé passe en query param (?key=), JAMAIS en Bearer (Google
# refuserait une clé valide → faux « clé refusée »). Une clé invalide renvoie 400
# (API_KEY_INVALID), pas 401. Source : Hermes _CREDENTIAL_PROBES (auth "query").
_PROBE_QUERY_KEY = frozenset({"gemini"})


def _http_status(url: str, headers: dict[str, str], *, method: str = "GET", body: str | None = None) -> tuple[int | None, str | None, str]:
    """Requête → ``(status_code, None, body)`` ou ``(None, raison, "")``.

    Un 4xx/5xx renvoie son code (pas une exception) : c'est un signal, pas une panne.
    ``body`` = corps de la réponse d'erreur (tronqué), pour distinguer une clé refusée
    d'un compte sans crédit. La valeur d'auth passée dans ``headers`` n'est jamais journalisée.
    """
    import urllib.error
    import urllib.request
    from urllib.parse import urlparse

    # Garde anti-SSRF/file-read (cf. audit Moyenne #2 semgrep) : ``urlopen`` accepte tout
    # schéma supporté par la stdlib (http, https, ftp, file...). Aujourd'hui aucune route
    # bridge ne laisse un appelant piloter ``url`` jusqu'ici (elle vient du registre
    # provider interne), mais le risque est latent — on restreint donc explicitement
    # au lieu de compter sur cette hypothèse pour rester vraie indéfiniment.
    if urlparse(url).scheme not in ("http", "https"):
        return (None, "schéma d'URL non autorisé", "")

    data = body.encode() if body is not None else None
    # User-Agent de navigateur : certains fournisseurs derrière Cloudflare (ex. opencode.ai)
    # bannissent la signature « Python-urllib » (HTTP 403 « error code: 1010 ») → faux « clé
    # refusée ». curl/httpx passent ; on aligne urllib. N'écrase pas un UA déjà fourni.
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
        **headers,
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:  # noqa: S310 (URL provider contrôlée)
            return (resp.status, None, "")
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", "replace")[:2000]
        except Exception:  # noqa: BLE001 — corps illisible = pas grave, on renvoie vide
            err_body = ""
        return (exc.code, None, err_body)
    except (urllib.error.URLError, OSError):
        return (None, "connexion impossible", "")


# Signatures (dans le corps d'erreur) d'un compte SANS CRÉDIT — la clé est valide, il
# manque juste de l'argent/quota. Constaté en réel : xAI « doesn't have any credits /
# credits or licenses » (403), OpenAI « account is not active … billing » (403/401),
# DeepSeek « Insufficient Balance » (402). On renvoie alors le code "no_credit" pour un
# message honnête (« clé valide, mais compte sans crédit ») au lieu de « clé refusée ».
_NO_CREDIT_MARKERS = (
    "insufficient balance",
    "insufficient_quota",
    "exceeded your current quota",
    "any credit",
    "credits or licenses",
    "no credit",
    "not active",
    "billing",
    "add funds",
    "payment required",
    # Kilo Code (402) : la clé est VALIDE, il manque juste des crédits (les modèles gratuits
    # marchent). Corps type : « Paid Model - Credits Required » / « Add credits to continue ».
    "credits required",
    "add credits",
    "paid model",
    # OpenCode Zen/Go (401 CreditsError) : clé VALIDE mais pas de moyen de paiement (les
    # modèles « -free » marchent). Corps : « No payment method. Add a payment method here… ».
    "payment method",
    # Novita (403 NOT_ENOUGH_BALANCE) : clé VALIDE, compte sans solde. Corps : « not enough
    # balance ». (Novita n'a pas de gratuit exploitable : dépôt requis même pour les prix 0.)
    "not enough balance",
)


def _looks_like_no_credit(body: str | None) -> bool:
    b = (body or "").lower()
    return any(m in b for m in _NO_CREDIT_MARKERS)


def _interpret_status(provider_id: str, status: int | None, err: str | None, body: str = "") -> tuple[bool, str | None]:
    """Traduit un code HTTP en ``(valid, raison)`` honnête pour l'UI.

    Règle commune : ``2xx``/``429`` = valide ; ``401/402/403`` = clé refusée — SAUF si le
    corps indique un compte sans crédit (raison ``"no_credit"``, la clé est bonne). En
    stratégie "chat", un ``400/404/422`` = auth franchie → clé valide.
    """
    if status is None:
        return (False, err or "connexion impossible")
    if 200 <= status < 300 or status == 429:
        # 429 = clé valide mais quota/débit atteint → l'auth est passée.
        return (True, None)
    if status in (401, 402, 403):
        if _looks_like_no_credit(body):
            return (False, "no_credit")
        return (False, "clé refusée par le fournisseur")
    if provider_id in _PROBE_CHAT and status in (400, 404, 422):
        return (True, None)
    if provider_id in _PROBE_QUERY_KEY and status == 400:
        # Google renvoie 400 (API_KEY_INVALID) pour une clé refusée, pas 401.
        return (False, "no_credit" if _looks_like_no_credit(body) else "clé refusée par le fournisseur")
    return (False, f"HTTP {status}")


def validate_key(provider_id: str, value: str) -> tuple[bool, str | None]:
    """Teste une clé par un probe réseau AVANT enregistrement.

    Choisit la stratégie de probe adaptée au provider (cf. ``_PROBE_*``).
    Retourne ``(valid, reason)``. La valeur n'est jamais journalisée.
    """
    provider = next((p for p in list_providers() if p.id == provider_id), None)
    if provider is None:
        raise KeyError(provider_id)
    base = provider.base_url or _PROVIDER_REGISTRY_FALLBACK.get(provider_id, {}).get("base_url")
    if not base:
        return (False, "pas d'URL d'inférence connue pour ce provider")
    base = base.rstrip("/")
    # Kimi : une clé Coding Plan (`sk-kimi-`) vit sur l'endpoint coding, pas Moonshot classique.
    # Sans ça, elle serait testée sur api.moonshot.ai et refusée à tort (bug miroir Z.AI/OpenRouter).
    if provider_id in ("kimi-coding", "kimi-coding-cn") and value.startswith("sk-kimi-"):
        base = _KIMI_CODE_BASE

    if provider_id in _PROBE_ANTHROPIC:
        status, err, resp_body = _http_status(
            f"{base}/v1/models",
            {"x-api-key": value, "anthropic-version": _ANTHROPIC_VERSION},
        )
    elif provider_id in _PROBE_CHAT:
        model = provider.models[0].id if provider.models else "test"
        body = json.dumps(
            {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
        )
        status, err, resp_body = _http_status(
            f"{base}/chat/completions",
            {"Authorization": f"Bearer {value}", "Content-Type": "application/json"},
            method="POST",
            body=body,
        )
    elif provider_id in _PROBE_QUERY_KEY:
        # Google Gemini : clé en query param (?key=), pas d'en-tête d'auth.
        from urllib.parse import quote

        status, err, resp_body = _http_status(
            f"{base}/models?key={quote(value, safe='')}",
            {"Accept": "application/json"},
        )
    else:
        status, err, resp_body = _http_status(f"{base}/models", {"Authorization": f"Bearer {value}"})

    return _interpret_status(provider_id, status, err, resp_body)
