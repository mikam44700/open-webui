"""Adapter Connexion des outils — métadonnées + connexion des toolsets natifs Hermes.

Feature 003. Source de vérité = Hermes :
- MÉTADONNÉES : introspection de ``TOOL_CATEGORIES`` (+ ``TOOLSET_ENV_REQUIREMENTS``).
- ÉTAT « connecté » : ``_toolset_has_keys`` (helper générique Hermes).
- ÉCRITURE clé/env : ``hermes_adapter._set_env_value`` (présence seule renvoyée, jamais la valeur).
- DÉCONNEXION : retrait des env_vars + token OAuth, puis désactivation du toolset.
- OAUTH : briques headless Hermes (Spotify/xAI) lancées en arrière-plan via ``_start_bg_run``.

On réutilise ``hermes_adapter.introspect`` / ``_set_env_value`` / ``_start_bg_run`` / ``_bg_status``
pour rester DRY et cohérent avec ``mcp_adapter`` (feature 002).
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import httpx

from . import hermes_adapter, net_guard, tools_adapter
from .models import (
    ToolConnection,
    ToolConnectionState,
    ToolField,
    ToolProvider,
    ToolProviderKind,
)

# Toolsets dont la connexion passe par OAuth (mapping vers l'identifiant de provider du store auth).
_OAUTH_PROVIDER_BY_TOOLSET: dict[str, str] = {
    "spotify": "spotify",
    "x_search": "xai-oauth",
}


# --- Introspection : métadonnées de connexion d'un toolset -------------------

_CONNECTION_SCRIPT = """
import json
import hermes_cli.tools_config as _tc
from hermes_cli.tools_config import TOOL_CATEGORIES
try:
    from hermes_cli.tools_config import _toolset_has_keys
except Exception:
    _toolset_has_keys = None
try:
    from hermes_cli.tools_config import TOOLSET_ENV_REQUIREMENTS
except Exception:
    TOOLSET_ENV_REQUIREMENTS = {{}}
try:
    from hermes_cli.config import get_env_value
except Exception:
    import os
    def get_env_value(k):
        return os.environ.get(k)

# Fournisseurs plugins (Exa, Tavily, Firecrawl, FAL, ...) chargés dynamiquement par Hermes.
_PLUGIN_FNS = {{
    "web": "_plugin_web_search_providers",
    "image_gen": "_plugin_image_gen_providers",
    "video_gen": "_plugin_video_gen_providers",
    "browser": "_plugin_browser_providers",
    "tts": "_plugin_tts_providers",
}}

name = {name}
_SECRET_HINTS = ("token", "key", "secret", "password")

def _is_secret(k):
    low = k.lower()
    return any(h in low for h in _SECRET_HINTS)

def _field(key, label=None, default=None, url=None):
    return {{
        "key": key,
        "label": label or key,
        "default": default,
        "url": url,
        "secret": _is_secret(key),
        "present": bool(get_env_value(key)),
    }}

# Seuls ces toolsets ont un vrai flux OAuth pilotable (cf. _OAUTH_SCRIPT_BY_TOOLSET).
_OAUTH_TOOLSETS = ("spotify", "x_search")

# Champs supplémentaires injectés pour certains fournisseurs (clé matchée sur le nom Hermes).
# xAI Web Search ne déclare pas d'env_var côté Hermes (il réutilise l'OAuth Grok ou la clé
# globale) : on expose XAI_API_KEY pour permettre une saisie directe — `present` reste calculé
# nativement par get_env_value, donc l'UI affiche « déjà renseigné » si la clé existe déjà.
_EXTRA_ENV_VARS = {{
    "xAI Web Search (Grok)": [
        {{"key": "XAI_API_KEY", "prompt": "xAI API key", "url": "https://console.x.ai"}},
    ],
}}

def _detect_connected(pname):
    # État réel détecté localement (sans réseau) pour les fournisseurs OAuth/compte.
    # Renvoie True/False si une détection existe, sinon None (non applicable).
    if pname == "OpenAI (Codex auth)":
        # Le runtime sélectionne les credentials depuis credential_pool.openai-codex,
        # pas depuis providers.openai-codex → on vérifie le pool en priorité.
        try:
            from hermes_cli.auth import read_credential_pool
            if read_credential_pool("openai-codex"):
                return True
        except Exception:
            pass
        try:
            from hermes_cli.auth import _load_auth_store, _load_provider_state
            if _load_provider_state(_load_auth_store(), "openai-codex"):
                return True
        except Exception:
            return None
        return False
    if pname in ("xAI Grok Imagine (image)", "xAI Grok Imagine", "xAI TTS"):
        try:
            from hermes_cli.auth import _read_xai_oauth_tokens
            _read_xai_oauth_tokens()
            return True
        except Exception:
            pass
        try:
            return bool(str(get_env_value("XAI_API_KEY") or "").strip())
        except Exception:
            return None
    return None

def _map_provider(p):
    env_vars = list(p.get("env_vars", []) or []) + _EXTRA_ENV_VARS.get(p.get("name"), [])
    if env_vars:
        kind = "key"
    elif p.get("post_setup") and name in _OAUTH_TOOLSETS:
        kind = "oauth"
    else:
        # Pas de champ à saisir ni de flux OAuth ici (ex. DuckDuckGo, abonnement Nous).
        kind = "managed"
    fields = [
        _field(ev["key"], ev.get("prompt"), ev.get("default"), ev.get("url"))
        for ev in env_vars if ev.get("key")
    ]
    return {{
        "name": p.get("name", name),
        "tag": p.get("tag"),
        "badge": p.get("badge"),
        "kind": kind,
        "fields": fields,
        "connected": _detect_connected(p.get("name", name)),
    }}

# 1. Fournisseurs statiques (TOOL_CATEGORIES) + 2. fournisseurs plugins, fusionnés et dédupliqués.
raw_providers = []
cat = TOOL_CATEGORIES.get(name)
if cat:
    raw_providers.extend(cat.get("providers", []) or [])
fn_name = _PLUGIN_FNS.get(name)
if fn_name and hasattr(_tc, fn_name):
    try:
        raw_providers.extend(getattr(_tc, fn_name)() or [])
    except Exception:
        pass

providers = []
seen = set()
required = False
for p in raw_providers:
    mp = _map_provider(p)
    if mp["name"] in seen:
        continue
    seen.add(mp["name"])
    if mp["fields"] or mp["kind"] in ("oauth", "managed"):
        required = True
    providers.append(mp)

# Fallback TOOLSET_ENV_REQUIREMENTS (ex. vision, moa) si aucune définition de fournisseur.
if not providers and name in TOOLSET_ENV_REQUIREMENTS:
    fields = []
    for entry in TOOLSET_ENV_REQUIREMENTS[name]:
        if isinstance(entry, (list, tuple)):
            key = entry[0]
            url = entry[1] if len(entry) > 1 else None
        else:
            key, url = entry, None
        fields.append(_field(key, None, None, url))
    if fields:
        required = True
        providers.append({{"name": name, "tag": None, "badge": None, "kind": "key", "fields": fields}})

connected = False
if _toolset_has_keys is not None:
    try:
        connected = bool(_toolset_has_keys(name))
    except Exception:
        connected = False

print(json.dumps({{"name": name, "required": required, "connected": connected, "providers": providers}}))
"""


# Carte name -> état de connexion, pour enrichir la liste des toolsets (US2).
_STATES_SCRIPT = """
import json
from hermes_cli.tools_config import _get_effective_configurable_toolsets, TOOL_CATEGORIES
try:
    from hermes_cli.tools_config import _toolset_has_keys
except Exception:
    _toolset_has_keys = None
try:
    from hermes_cli.tools_config import TOOLSET_ENV_REQUIREMENTS
except Exception:
    TOOLSET_ENV_REQUIREMENTS = {}

out = {}
for key, _label, _desc in _get_effective_configurable_toolsets():
    has_def = key in TOOL_CATEGORIES or key in TOOLSET_ENV_REQUIREMENTS
    if not has_def:
        out[key] = "not_required"
        continue
    connected = False
    if _toolset_has_keys is not None:
        try:
            connected = bool(_toolset_has_keys(key))
        except Exception:
            connected = False
    out[key] = "connected" if connected else "connection_required"
print(json.dumps(out))
"""


# --- Localisation FR + ordre des fournisseurs de recherche web (toolset « web ») ------
#
# Hermes renvoie les libellés en anglais et dans un ordre interne. Cette surcouche les
# traduit, les ré-explique pour le client final (sans jargon) et impose l'ordre voulu,
# sans toucher à ``_refs/``. La clé de chaque entrée = nom Hermes d'origine (cf. dump
# d'introspection). Les noms propres (marques) sont conservés ; ``tag`` = description
# affichée sous le titre ; ``fields`` = libellés FR des champs, mappés par clé d'env_var.

_WEB_PROVIDER_FR: dict[str, dict] = {
    "DuckDuckGo (ddgs)": {
        "slug": "duckduckgo",
        "name": "DuckDuckGo",
        "badge": "Gratuit · sans clé",
        "tag": (
            "Recherche web gratuite, sans inscription ni clé : idéal pour démarrer tout de "
            "suite. Il trouve les pages mais n'en lit pas le contenu en détail — à associer "
            "à un fournisseur de lecture (Firecrawl, Exa…) si tu veux extraire le texte."
        ),
    },
    "Exa": {
        "slug": "exa",
        "advanced": True,
        "category": "paid",
        "name": "Exa",
        "badge": "Payant",
        "tag": (
            "Recherche intelligente qui comprend le sens de ta demande (pas seulement les "
            "mots-clés) et récupère directement le contenu des pages. Très bon pour la veille "
            "et la recherche documentaire. Nécessite une clé API."
        ),
        "fields": {"EXA_API_KEY": "Clé API Exa"},
    },
    "Firecrawl": {
        "slug": "firecrawl",
        "advanced": True,
        "category": "paid",
        "name": "Firecrawl",
        "badge": "Payant",
        "tag": (
            "Recherche et lit des pages web entières, et en ressort un texte propre prêt pour "
            "l'IA. Parfait pour extraire le contenu d'un site. Laisse la clé vide si tu héberges "
            "ta propre instance (voir « Firecrawl auto-hébergé »)."
        ),
        "fields": {
            "FIRECRAWL_API_KEY": {
                "label": "Clé API Firecrawl (laisse vide si auto-hébergé)",
                "url": "https://www.firecrawl.dev/",
            }
        },
    },
    "Brave Search (Free)": {
        "slug": "brave",
        "advanced": True,
        "category": "free",
        "name": "Brave Search",
        "badge": "Gratuit",
        "tag": (
            "Moteur de recherche indépendant et respectueux de la vie privée. Offre gratuite : "
            "2 000 recherches par mois. Recherche seule (ne lit pas le contenu des pages). "
            "Nécessite une clé gratuite."
        ),
        "fields": {"BRAVE_SEARCH_API_KEY": "Clé API Brave Search (offre gratuite)"},
    },
    "Tavily": {
        "slug": "tavily",
        "advanced": True,
        "category": "paid",
        "name": "Tavily",
        "badge": "Payant",
        "tag": (
            "Recherche et lecture de pages réunies dans un seul service, pensé pour l'IA. "
            "Simple et efficace. Nécessite une clé API."
        ),
        "fields": {"TAVILY_API_KEY": "Clé API Tavily"},
    },
    "Parallel": {
        "slug": "parallel",
        "advanced": True,
        "category": "paid",
        "name": "Parallel",
        "badge": "Payant",
        "tag": (
            "Recherche optimisée par objectif qui lit plusieurs pages en parallèle pour des "
            "réponses plus complètes. Utile pour des recherches approfondies. Nécessite une clé API."
        ),
        "fields": {"PARALLEL_API_KEY": "Clé API Parallel"},
    },
    "Linkup": {
        "slug": "linkup",
        "advanced": True,
        "category": "free",
        "name": "Linkup",
        "badge": "Gratuit · clé requise",
        "tag": (
            "Recherche web souveraine (société française) réputée pour la fiabilité de ses "
            "réponses : elle lit les pages et renvoie un contenu prêt pour l'IA. Offre gratuite "
            "généreuse. Nécessite une clé gratuite."
        ),
        "fields": {"LINKUP_API_KEY": {"label": "Clé API Linkup", "url": "https://app.linkup.so"}},
    },
    "Serper": {
        "slug": "serper",
        "advanced": True,
        "category": "free",
        "name": "Serper",
        "badge": "Gratuit · crédits offerts",
        "tag": (
            "Accès direct aux résultats de Google, rapide et très bon marché. Idéal quand tu veux "
            "exactement ce que renvoie Google. Crédits gratuits à l'inscription, puis paiement à "
            "l'usage. Recherche seule (ne lit pas les pages)."
        ),
        "fields": {"SERPER_API_KEY": {"label": "Clé API Serper", "url": "https://serper.dev"}},
    },
    "Jina Reader": {
        "slug": "jina",
        "advanced": True,
        "category": "free",
        "name": "Jina Reader",
        "badge": "Gratuit · clé optionnelle",
        "tag": (
            "Recherche web ET lecture de pages en texte propre, pensé pour l'IA. Fonctionne "
            "gratuitement sans clé ; une clé gratuite augmente les quotas. Bon couteau suisse "
            "pour la veille."
        ),
        "fields": {
            "JINA_API_KEY": {
                "label": "Clé API Jina (optionnelle)",
                "url": "https://jina.ai/api-dashboard",
            }
        },
    },
    "SerpAPI": {
        "slug": "serpapi",
        "advanced": True,
        "category": "paid",
        "name": "SerpAPI",
        "badge": "Payant · 100 gratuits/mois",
        "tag": (
            "Résultats structurés de plus de 40 moteurs (Google par défaut), fiable et complet. "
            "Bon choix pour de la recherche exigeante. 100 recherches gratuites par mois, puis "
            "payant. Recherche seule."
        ),
        "fields": {
            "SERPAPI_API_KEY": {
                "label": "Clé API SerpAPI",
                "url": "https://serpapi.com/manage-api-key",
            }
        },
    },
    "Perplexity Sonar": {
        "slug": "perplexity",
        "advanced": True,
        "category": "paid",
        "name": "Perplexity Sonar",
        "badge": "Payant",
        "tag": (
            "Moteur de réponse en temps réel : il cherche sur le web et cite ses sources. Pratique "
            "pour des questions d'actualité avec les liens à l'appui. Nécessite une clé API."
        ),
        "fields": {
            "PERPLEXITY_API_KEY": {
                "label": "Clé API Perplexity",
                "url": "https://www.perplexity.ai/settings/api",
            }
        },
    },
    "SearXNG": {
        "slug": "searxng",
        "advanced": True,
        "category": "self_hosted",
        "name": "SearXNG",
        "badge": "Gratuit · auto-hébergé",
        "tag": (
            "Méta-moteur gratuit et privé que tu héberges toi-même : il interroge plusieurs "
            "moteurs à la fois sans te pister. Indique l'adresse de ton instance SearXNG."
        ),
        "fields": {"SEARXNG_URL": "Adresse de ton instance SearXNG (ex. http://localhost:8080)"},
    },
    "Firecrawl Self-Hosted": {
        "slug": "firecrawl",
        "advanced": True,
        "category": "self_hosted",
        "name": "Firecrawl auto-hébergé",
        "badge": "Gratuit · auto-hébergé",
        "tag": (
            "Ta propre installation de Firecrawl (via Docker), sans frais d'abonnement : mêmes "
            "capacités d'extraction que Firecrawl, mais sur ton serveur. Indique l'adresse de "
            "ton instance."
        ),
        "fields": {"FIRECRAWL_API_URL": "Adresse de ton instance Firecrawl (ex. http://localhost:3002)"},
    },
    "xAI Web Search (Grok)": {
        "slug": "xai",
        "advanced": True,
        "category": "paid",
        "name": "xAI Web Search (Grok)",
        "badge": "Payant",
        "tag": (
            "Recherche web en temps réel propulsée par Grok (xAI). La clé xAI est la même que "
            "celle de Grok : si tu utilises déjà Grok, elle est sans doute déjà active (le champ "
            "indiquera « renseigné »). Sinon, colle ta clé xAI ci-dessous."
        ),
        "fields": {"XAI_API_KEY": "Clé API xAI (optionnelle si tu es déjà connecté à Grok)"},
    },
    "Nous Subscription": {
        "slug": "nous",
        "name": "Abonnement Nous",
        "badge": "Abonnement",
        "tag": (
            "Firecrawl géré, inclus dans ton abonnement Nous : aucune clé à saisir, rien à "
            "configurer. Activé automatiquement si ton abonnement est actif."
        ),
    },
}

# Ordre d'affichage voulu (par nom Hermes d'origine). Les fournisseurs inconnus de cette
# liste (si Hermes en ajoute) sont conservés et rejetés en fin de liste, jamais masqués.
_WEB_PROVIDER_ORDER: list[str] = [
    "DuckDuckGo (ddgs)",
    "Exa",
    "Firecrawl",
    "Brave Search (Free)",
    "Tavily",
    "Parallel",
    "Linkup",
    "Serper",
    "Jina Reader",
    "SerpAPI",
    "Perplexity Sonar",
    "SearXNG",
    "Firecrawl Self-Hosted",
    "xAI Web Search (Grok)",
    "Nous Subscription",
]


# --- Backend de recherche web actif (web.search_backend) : bascule automatique -------
#
# Modèle : DuckDuckGo (ddgs, gratuit sans clé) est le FILET par défaut ; connecter un
# fournisseur natif le fait devenir l'actif ; le déconnecter rebascule sur le meilleur
# restant, ddgs en dernier ressort (jamais de valeur vide → la recherche ne casse jamais).
# Le moteur relit config.yaml à chaud → aucun redémarrage requis.

# Le filet gratuit, toujours disponible sans clé.
_DEFAULT_WEB_BACKEND = "ddgs"

# slug (UI) → identifiant de backend NATIF du moteur Hermes.
#   • None = fournisseur géré par PLUGIN (linkup/serper/jina/serpapi/perplexity) : pas de
#     backend natif → on ne bascule jamais web.search_backend dessus.
#   • Seul écart slug ≠ backend : brave → « brave-free ».
#   • firecrawl couvre la clé ET l'auto-hébergé (même backend, env_var différente).
_WEB_SLUG_TO_BACKEND: dict[str, str | None] = {
    "duckduckgo": "ddgs",
    "exa": "exa",
    "firecrawl": "firecrawl",
    "brave": "brave-free",
    "tavily": "tavily",
    "parallel": "parallel",
    "searxng": "searxng",
    "xai": "xai",
    "linkup": None,
    "serper": None,
    "jina": None,
    "serpapi": None,
    "perplexity": None,
}

# Backends qui savent LIRE le contenu des pages (extract), pas seulement chercher. Les
# autres (ddgs, brave-free, searxng, xai) sont « recherche seule » : la lecture reste au
# navigateur automatisé.
_EXTRACT_CAPABLE_BACKENDS: frozenset[str] = frozenset({"exa", "firecrawl", "tavily", "parallel"})


def _web_env_to_slug() -> dict[str, str]:
    """env_var (ex. « EXA_API_KEY ») → slug du fournisseur, dérivé de _WEB_PROVIDER_FR."""
    out: dict[str, str] = {}
    for meta in _WEB_PROVIDER_FR.values():
        slug = meta.get("slug")
        if not slug:
            continue
        for env_var in (meta.get("fields") or {}):
            out[env_var] = slug
    return out


def _backend_for_slug(slug: str | None) -> str | None:
    """Backend natif d'un slug (None si plugin / inconnu / sans backend)."""
    if not slug:
        return None
    return _WEB_SLUG_TO_BACKEND.get(slug)


def _extract_for(backend: str) -> str | None:
    """Backend d'extraction à écrire pour ce backend de recherche.

    Un backend qui sait lire les pages sert aussi d'extracteur ; sinon None (on laisse
    l'extraction au navigateur / au réglage précédent).
    """
    return backend if backend in _EXTRACT_CAPABLE_BACKENDS else None


def _web_provider_active(slug: str | None, active_search_backend: str) -> bool | None:
    """Ce fournisseur web est-il le ``search_backend`` courant ? (badge « Actif » honnête).

    None = notion non applicable (fournisseur sans backend natif, ex. plugin), pour ne pas
    afficher « inactif » sur quelque chose qui ne passe pas par ce mécanisme.
    """
    backend = _backend_for_slug(slug)
    if not backend:
        return None
    return backend == active_search_backend


def _apply_web_backend_for_env_vars(env_vars: list[str]) -> None:
    """À la connexion : bascule web.search_backend sur le fournisseur natif qu'on vient de

    connecter (première env_var reconnue). No-op si aucune ne correspond à un backend natif
    (ex. plugin linkup/serper/jina…) : ceux-là s'activent par ``hermes plugins``, pas ici.
    L'extract n'est touché que si le fournisseur sait lire les pages (sinon on préserve un
    éventuel extracteur déjà en place → on autorise « recherche X + lecture Y »).
    """
    env_to_slug = _web_env_to_slug()
    for env_var in env_vars:
        backend = _backend_for_slug(env_to_slug.get(env_var))
        if backend:
            hermes_adapter.set_web_backend(backend, _extract_for(backend))
            return


def _resolve_active_web_backend() -> tuple[str, str]:
    """(search, extract) à appliquer d'après les fournisseurs web encore connectés.

    Préférence : un backend qui sait LIRE les pages d'abord (meilleure qualité), puis
    recherche seule, puis ``ddgs`` en dernier ressort. Ne renvoie JAMAIS de search vide
    (ddgs = filet). ``extract`` vaut le backend si extract-capable, sinon '' (chaîne vide)
    pour PURGER un extracteur payant résiduel devenu invalide.
    """
    present = hermes_adapter._present_env_keys()
    env_to_slug = _web_env_to_slug()
    backends = [
        b for ev in present if (b := _backend_for_slug(env_to_slug.get(ev))) is not None
    ]
    for backend in backends:
        if backend in _EXTRACT_CAPABLE_BACKENDS:
            return backend, backend
    if backends:
        return backends[0], ""
    return _DEFAULT_WEB_BACKEND, ""


def _reapply_web_backend_after_disconnect() -> None:
    """À la déconnexion : réécrit le backend actif (meilleur restant, ddgs sinon).

    On écrit toujours ``extract`` explicitement (backend ou '') pour ne jamais laisser un
    extracteur d'un fournisseur déconnecté pointer dans le vide.
    """
    search, extract = _resolve_active_web_backend()
    hermes_adapter.set_web_backend(search, extract)


# --- Localisation FR des fournisseurs du toolset « browser » (Navigateur automatisé) --
# Même principe que pour « web ». L'ordre Hermes convient déjà → pas de réordonnancement.

_BROWSER_PROVIDER_FR: dict[str, dict] = {
    "Local Browser": {
        "slug": "chromium",
        "name": "Navigateur local (Chromium)",
        "badge": "★ Recommandé · gratuit",
        "tag": (
            "Un navigateur Chromium intégré qui tourne directement sur ta machine, sans rien "
            "installer ni aucune clé. C'est l'option recommandée pour démarrer : gratuite, "
            "privée et immédiate."
        ),
    },
    "Nous Subscription (Browser Use cloud)": {
        "slug": "nous",
        "name": "Abonnement Nous (navigateur cloud)",
        "badge": "Abonnement",
        "tag": (
            "Navigateur dans le cloud, géré et inclus dans ton abonnement Nous : aucune clé à "
            "saisir, rien à installer. Activé automatiquement si ton abonnement est actif."
        ),
    },
    "Camofox": {
        "slug": "camofox",
        "advanced": True,
        "category": "self_hosted",
        "name": "Camofox",
        "badge": "Gratuit · local",
        "tag": (
            "Navigateur anti-détection (basé sur Firefox/Camoufox) que tu héberges toi-même : "
            "utile pour visiter des sites qui bloquent les robots. Indique l'adresse de ton "
            "instance Camofox."
        ),
        "fields": {"CAMOFOX_URL": "Adresse de ton instance Camofox"},
    },
    "Browser Use": {
        "slug": "browser-use",
        "advanced": True,
        "category": "paid",
        "name": "Browser Use",
        "badge": "Payant",
        "tag": (
            "Navigateur dans le cloud, exécuté à distance (rien à installer sur ta machine). "
            "Pratique pour automatiser la navigation à grande échelle. Nécessite une clé API."
        ),
        "fields": {"BROWSER_USE_API_KEY": "Clé API Browser Use"},
    },
    "Browserbase": {
        "slug": "browserbase",
        "advanced": True,
        "category": "paid",
        "name": "Browserbase",
        "badge": "Payant",
        "tag": (
            "Navigateur cloud avec mode furtif et proxies intégrés, pour contourner les blocages "
            "et naviguer de façon anonyme. Nécessite une clé API et un identifiant de projet."
        ),
        "fields": {
            "BROWSERBASE_API_KEY": "Clé API Browserbase",
            "BROWSERBASE_PROJECT_ID": "Identifiant de projet Browserbase",
        },
    },
    "Firecrawl": {
        "slug": "firecrawl",
        "advanced": True,
        "category": "paid",
        "name": "Firecrawl",
        "badge": "Payant",
        "tag": (
            "Navigateur cloud de Firecrawl, exécuté à distance. Idéal si tu utilises déjà "
            "Firecrawl pour la recherche web. Nécessite une clé API."
        ),
        "fields": {
            "FIRECRAWL_API_KEY": {
                "label": "Clé API Firecrawl",
                "url": "https://www.firecrawl.dev/",
            }
        },
    },
}

# --- Localisation FR : toolset « x_search » (Recherche X / Twitter via xAI Grok) ------
# 1er fournisseur = connexion par compte (OAuth, bouton Autoriser) ; 2e = clé API directe.

_XSEARCH_PROVIDER_FR: dict[str, dict] = {
    "xAI Grok OAuth (SuperGrok / Premium+)": {
        "slug": "xai",
        "name": "xAI Grok — connexion par compte (SuperGrok / Premium+)",
        "badge": "Abonnement",
        "tag": (
            "Connexion via ton compte X/xAI (abonnement SuperGrok ou Premium+), directement "
            "dans le navigateur sur accounts.x.ai. Aucune clé API à saisir : clique sur "
            "« Autoriser » et connecte-toi."
        ),
    },
    "xAI API key": {
        "slug": "xai",
        "name": "xAI — clé API",
        "badge": "Payant",
        "tag": (
            "Facturation directe via l'API xAI avec ta propre clé. À utiliser si tu n'as pas "
            "d'abonnement SuperGrok / Premium+. Colle ta clé xAI ci-dessous."
        ),
        "fields": {"XAI_API_KEY": "Clé API xAI"},
    },
}

# --- Localisation FR : toolset « computer_use » (Contrôle de l'ordinateur, macOS) ------

_COMPUTER_USE_PROVIDER_FR: dict[str, dict] = {
    "cua-driver (background)": {
        "slug": "cua",
        "name": "cua-driver (arrière-plan)",
        "badge": "★ Recommandé · gratuit · local",
        "tag": (
            "Contrôle de l'ordinateur en arrière-plan sur macOS (via les SkyLight SPIs) : il "
            "n'accapare PAS ta souris ni le focus, tu peux continuer à travailler pendant qu'il "
            "agit. Gratuit, local, compatible avec n'importe quel modèle. Rien à configurer."
        ),
    },
}

# --- Localisation FR : toolset « vision » (analyse d'image) ----------------------------
# Hermes n'a pas de fournisseurs structurés pour vision : c'est un fallback générique
# (TOOLSET_ENV_REQUIREMENTS → un seul « provider » nommé « vision » avec OPENROUTER_API_KEY).
# On le francise et on l'explique. Clé d'entrée = nom du provider générique = « vision ».

_VISION_PROVIDER_FR: dict[str, dict] = {
    "vision": {
        "slug": "openrouter",
        "name": "OpenRouter",
        "badge": "Secours · optionnel",
        "tag": (
            "Utile uniquement si le modèle de ton agent ne sait pas lire les images. OpenRouter "
            "donne alors accès à un modèle de vision (Gemini) avec une seule clé. Payant à "
            "l'usage (crédits). Autres secours possibles côté Hermes : un modèle de vision local "
            "(LM Studio / Ollama, gratuit) ou ta clé OpenAI / Anthropic."
        ),
        "fields": {"OPENROUTER_API_KEY": "Clé API OpenRouter"},
    },
}

# Encart d'information affiché en haut de la fenêtre « Connecter » (par toolset).
_TOOLSET_NOTE_FR: dict[str, str] = {
    "moa": (
        "🧠 Le « Mélange d'agents » interroge plusieurs modèles d'IA en parallèle sur ta question, "
        "puis fusionne leurs réponses pour en produire une seule, meilleure et plus fiable (idéal "
        "pour les questions complexes). Il a besoin d'une clé OpenRouter, la passerelle qui lui "
        "donne accès à tous ces modèles."
    ),
    "tts": (
        "💡 Pour commencer, « Microsoft Edge TTS » est gratuit et fonctionne sans rien configurer. "
        "Les autres fournisseurs offrent des voix plus naturelles (souvent payantes, clé API requise) "
        "ou tournent en local sur ta machine."
    ),
    "vision": (
        "✅ Si le modèle de ton agent gère déjà les images (GPT-4o, Claude, Gemini…), la vision "
        "fonctionne directement avec lui : rien à configurer ici, et c'est inclus dans ton "
        "abonnement. Le fournisseur ci-dessous n'est qu'un secours, utile seulement si ton "
        "modèle ne sait pas lire les images."
    ),
}

# --- Localisation FR : toolset « image_gen » (Génération d'images) ---------------------

_IMAGE_GEN_PROVIDER_FR: dict[str, dict] = {
    "Nous Subscription": {
        "slug": "nous",
        "name": "Abonnement Nous",
        "badge": "Abonnement",
        "tag": (
            "Génération d'images gérée (via FAL), incluse dans ton abonnement Nous : aucune clé "
            "à saisir, rien à installer. Activée automatiquement si ton abonnement est actif."
        ),
    },
    "FAL.ai": {
        "slug": "fal",
        "name": "FAL.ai",
        "badge": "Payant",
        "tag": (
            "Plateforme qui regroupe de nombreux modèles d'image (Flux, GPT-Image, Nano-Banana…) "
            "pour créer et retoucher des images. Nécessite une clé API."
        ),
        "fields": {"FAL_KEY": "Clé API FAL.ai"},
    },
    "Krea": {
        "slug": "krea",
        "name": "Krea",
        "badge": "Payant",
        "tag": (
            "Modèle Krea 2 (qualité Medium ~0,03 $ / Large ~0,06 $ l'image) : transfert de style, "
            "moodboards, génération guidée par une image de référence. Nécessite une clé API."
        ),
        "fields": {"KREA_API_KEY": "Clé API Krea"},
    },
    "OpenAI": {
        "slug": "openai",
        "name": "OpenAI",
        "badge": "Payant",
        "tag": (
            "Le modèle gpt-image d'OpenAI (qualité réglable) pour créer et retoucher des images. "
            "Nécessite une clé API OpenAI."
        ),
        "fields": {"OPENAI_API_KEY": "Clé API OpenAI"},
    },
    "OpenAI (Codex auth)": {
        "slug": "codex",
        "name": "OpenAI via ChatGPT (Codex)",
        "badge": "Gratuit · via ton compte ChatGPT",
        "tag": (
            "Génère des images avec gpt-image en réutilisant ta connexion ChatGPT/Codex — aucune "
            "clé API à saisir. Disponible uniquement si tu es connecté à ChatGPT/Codex (connexion "
            "gérée dans la page Modèles)."
        ),
    },
    "xAI Grok Imagine (image)": {
        "slug": "grok",
        "name": "xAI Grok Imagine",
        "badge": "Payant",
        "tag": (
            "Génère et retouche des images avec Grok (xAI). Nécessite ta connexion xAI : soit une "
            "clé XAI_API_KEY, soit la connexion Grok OAuth (configurable dans l'onglet Recherche X)."
        ),
    },
}

# --- Localisation FR : toolset « video_gen » (Génération de vidéos) --------------------

_VIDEO_GEN_PROVIDER_FR: dict[str, dict] = {
    "FAL": {
        "slug": "fal",
        "name": "FAL.ai",
        "badge": "Payant",
        "tag": (
            "Plateforme qui regroupe les meilleurs modèles de génération vidéo (LTX, Pixverse, "
            "Veo 3.1, Seedance 2.0, Kling 4K, Happy Horse…) pour créer une vidéo à partir d'un "
            "texte ou d'une image. Nécessite une clé API."
        ),
        "fields": {"FAL_KEY": "Clé API FAL.ai"},
    },
    "xAI Grok Imagine": {
        "slug": "grok",
        "name": "xAI Grok Imagine",
        "badge": "Payant",
        "tag": (
            "Génère des vidéos avec Grok (xAI) : à partir d'un texte (modèle grok-imagine-video) "
            "ou d'une image (grok-imagine-video-1.5). Nécessite ta connexion xAI : soit une clé "
            "XAI_API_KEY, soit la connexion Grok OAuth (configurable dans l'onglet Recherche X)."
        ),
    },
    "Nous Subscription": {
        "slug": "nous",
        "name": "Abonnement Nous",
        "badge": "Abonnement",
        "tag": (
            "Génération de vidéos gérée (via FAL), incluse dans ton abonnement Nous : aucune clé "
            "à saisir, rien à installer. Disponible uniquement si ton abonnement Nous est actif."
        ),
    },
}

# Ordre client : les fournisseurs à clé d'abord, l'abonnement Nous en dernier.
_VIDEO_GEN_PROVIDER_ORDER = ["FAL", "xAI Grok Imagine", "Nous Subscription"]

# --- Localisation FR : toolset « tts » (Synthèse vocale) -------------------------------
# Organisation : 2 fournisseurs simples en clair (Edge gratuit recommandé + abonnement Nous),
# les autres repliés en mode Expert, groupés par catégorie (gratuit local → payant à clé).

_TTS_PROVIDER_FR: dict[str, dict] = {
    # — Standard (visibles directement) —
    "Microsoft Edge TTS": {
        "slug": "edge",
        "name": "Microsoft Edge TTS",
        "badge": "★ Recommandé · gratuit",
        "tag": (
            "Les voix de synthèse de Microsoft (celles du navigateur Edge) : bonne qualité, "
            "gratuites et sans clé à saisir. Le choix le plus simple pour faire parler ton agent."
        ),
    },
    "Nous Subscription": {
        "slug": "nous",
        "name": "Abonnement Nous",
        "badge": "Abonnement",
        "tag": (
            "Synthèse vocale gérée (voix OpenAI), incluse dans ton abonnement Nous : aucune clé "
            "à saisir. Disponible uniquement si ton abonnement Nous est actif."
        ),
    },
    # — Expert · gratuit (tourne en local sur ta machine) —
    "KittenTTS": {
        "slug": "kitten",
        "name": "KittenTTS",
        "badge": "Local · gratuit",
        "advanced": True,
        "category": "free",
        "tag": (
            "Petit modèle de synthèse vocale qui tourne en local sur ta machine (~25 Mo, "
            "technologie ONNX) : gratuit, sans clé, et fonctionne même sans connexion internet."
        ),
    },
    "Piper": {
        "slug": "piper",
        "name": "Piper",
        "badge": "Local · gratuit",
        "advanced": True,
        "category": "free",
        "tag": (
            "Synthèse vocale neuronale en local, 44 langues (voix de 20 à 90 Mo à télécharger) : "
            "gratuite, sans clé, et fonctionne hors ligne."
        ),
    },
    # — Expert · payant (clé API à coller) —
    "OpenAI TTS": {
        "slug": "openai",
        "name": "OpenAI TTS",
        "badge": "Payant",
        "advanced": True,
        "category": "paid",
        "tag": "Les voix de synthèse haute qualité d'OpenAI. Nécessite une clé API OpenAI.",
        "fields": {"VOICE_TOOLS_OPENAI_KEY": "Clé API OpenAI"},
    },
    "ElevenLabs": {
        "slug": "elevenlabs",
        "name": "ElevenLabs",
        "badge": "Payant",
        "advanced": True,
        "category": "paid",
        "tag": (
            "Les voix les plus naturelles du marché (expressivité et clonage de voix poussés). "
            "Nécessite une clé API ElevenLabs."
        ),
        "fields": {"ELEVENLABS_API_KEY": "Clé API ElevenLabs"},
    },
    "Mistral (Voxtral TTS)": {
        "slug": "mistral",
        "name": "Mistral (Voxtral TTS)",
        "badge": "Payant",
        "advanced": True,
        "category": "paid",
        "tag": (
            "Synthèse vocale multilingue de Mistral (modèle Voxtral, audio Opus natif). "
            "Nécessite une clé API Mistral."
        ),
        "fields": {"MISTRAL_API_KEY": "Clé API Mistral"},
    },
    "Google Gemini TTS": {
        "slug": "gemini",
        "name": "Google Gemini TTS",
        "badge": "Aperçu",
        "advanced": True,
        "category": "paid",
        "tag": (
            "30 voix prédéfinies de Google Gemini, pilotables par instructions (ton, style). "
            "Encore en version d'essai (preview). Nécessite une clé API Google AI Studio."
        ),
        "fields": {"GEMINI_API_KEY": "Clé API Gemini"},
    },
    "xAI TTS": {
        "slug": "grok",
        "name": "xAI TTS",
        "badge": "Payant",
        "advanced": True,
        "category": "paid",
        "tag": (
            "Les voix de Grok (xAI). Nécessite ta connexion xAI : soit une clé XAI_API_KEY, soit "
            "la connexion Grok OAuth (configurable dans l'onglet Recherche X)."
        ),
    },
}

# Ordre client : Edge (gratuit recommandé) → Nous, puis gratuit local, puis payant à clé.
_TTS_PROVIDER_ORDER = [
    "Microsoft Edge TTS", "Nous Subscription",
    "KittenTTS", "Piper",
    "OpenAI TTS", "ElevenLabs", "Mistral (Voxtral TTS)", "Google Gemini TTS", "xAI TTS",
]

# --- Localisation FR : toolset « moa » (Mélange d'agents / Mixture of Agents) ----------

_MOA_PROVIDER_FR: dict[str, dict] = {
    "moa": {
        "slug": "openrouter",
        "name": "OpenRouter",
        "badge": "Payant",
        "tag": (
            "Passerelle qui donne accès à des centaines de modèles d'IA (OpenAI, Claude, Gemini, "
            "Llama…) avec une seule clé. C'est elle qui permet au Mélange d'agents d'interroger "
            "plusieurs modèles à la fois. Nécessite une clé API OpenRouter."
        ),
        "fields": {"OPENROUTER_API_KEY": "Clé API OpenRouter"},
    },
}

# --- Localisation FR : toolset « homeassistant » (Domotique) ---------------------------

_HOMEASSISTANT_PROVIDER_FR: dict[str, dict] = {
    "Home Assistant": {
        "slug": "homeassistant",
        "name": "Home Assistant",
        "badge": "Domotique · auto-hébergé",
        "tag": (
            "Connecte ton serveur domotique Home Assistant pour piloter tes appareils (lumières, "
            "volets, thermostats, capteurs…) directement depuis ton agent. Renseigne l'adresse de "
            "ton Home Assistant et un jeton d'accès longue durée (créé dans ton profil Home Assistant)."
        ),
        "fields": {
            "HASS_TOKEN": "Jeton d'accès longue durée",
            "HASS_URL": "Adresse de ton Home Assistant (ex. http://localhost:8123)",
        },
    },
}

# --- Localisation FR : toolset « spotify » (Musique, connexion par compte) --------------

_SPOTIFY_PROVIDER_FR: dict[str, dict] = {
    "Spotify Web API": {
        "slug": "spotify",
        "name": "Spotify",
        "badge": "Connexion par compte",
        "tag": (
            "Connecte ton compte Spotify pour que l'agent contrôle ta musique (lecture, recherche, "
            "playlists…). La connexion se fait par autorisation sécurisée (OAuth) : un assistant "
            "s'ouvre pour lier ton compte, aucune clé à coller."
        ),
    },
}

# Tables FR + ordres par toolset. Un toolset absent de _PROVIDER_ORDER_BY_TOOLSET garde
# l'ordre d'origine renvoyé par Hermes (cas de « browser »).
_PROVIDER_FR_BY_TOOLSET: dict[str, dict[str, dict]] = {
    "web": _WEB_PROVIDER_FR,
    "browser": _BROWSER_PROVIDER_FR,
    "x_search": _XSEARCH_PROVIDER_FR,
    "computer_use": _COMPUTER_USE_PROVIDER_FR,
    "vision": _VISION_PROVIDER_FR,
    "image_gen": _IMAGE_GEN_PROVIDER_FR,
    "video_gen": _VIDEO_GEN_PROVIDER_FR,
    "tts": _TTS_PROVIDER_FR,
    "moa": _MOA_PROVIDER_FR,
    "homeassistant": _HOMEASSISTANT_PROVIDER_FR,
    "spotify": _SPOTIFY_PROVIDER_FR,
}
_PROVIDER_ORDER_BY_TOOLSET: dict[str, list[str]] = {
    "web": _WEB_PROVIDER_ORDER,
    "video_gen": _VIDEO_GEN_PROVIDER_ORDER,
    "tts": _TTS_PROVIDER_ORDER,
}


def _localize_providers(toolset: str, raw_providers: list[dict]) -> list[dict]:
    """Traduit en FR (+ réordonne si un ordre est défini) les fournisseurs d'un toolset."""
    fr_table = _PROVIDER_FR_BY_TOOLSET.get(toolset)
    if not fr_table:
        return raw_providers

    def translate(p: dict) -> dict:
        fr = fr_table.get(p.get("name"))
        if not fr:
            return p
        out = dict(p)
        for attr in ("name", "badge", "tag", "slug", "advanced", "category"):
            if fr.get(attr):
                out[attr] = fr[attr]
        # Surcharge des champs : valeur = libellé (str) OU {"label", "url"} pour aussi
        # corriger le lien « Obtenir cette valeur » fourni par Hermes.
        overrides = fr.get("fields") or {}
        if overrides and out.get("fields"):
            new_fields = []
            for f in out["fields"]:
                ov = overrides.get(f.get("key"))
                if isinstance(ov, dict):
                    new_fields.append(
                        {**f, "label": ov.get("label", f.get("label")), "url": ov.get("url", f.get("url"))}
                    )
                elif ov:
                    new_fields.append({**f, "label": ov})
                else:
                    new_fields.append(f)
            out["fields"] = new_fields
        return out

    order = _PROVIDER_ORDER_BY_TOOLSET.get(toolset)
    if order:
        rank = {name: i for i, name in enumerate(order)}
        # Tri d'abord sur le nom d'origine (clé de l'ordre), puis traduction.
        raw_providers = sorted(raw_providers, key=lambda p: rank.get(p.get("name"), len(rank)))
    return [translate(p) for p in raw_providers]


def connection_states() -> dict[str, ToolConnectionState]:
    """Carte ``name -> ToolConnectionState`` pour tous les toolsets configurables (US2)."""
    raw = hermes_adapter.introspect(_STATES_SCRIPT)
    return {name: ToolConnectionState(value) for name, value in raw.items()}


def get_connection(name: str) -> ToolConnection:
    """Métadonnées de connexion détaillées d'un toolset (écran « Connecter », US3/US4)."""
    raw = hermes_adapter.introspect(_CONNECTION_SCRIPT.format(name=json.dumps(name)))
    raw_providers = raw.get("providers", [])
    # Surcouche FR (+ ordre client) pour les toolsets pris en charge (web, browser).
    raw_providers = _localize_providers(raw.get("name", ""), raw_providers)
    # Badge « Actif » du toolset web : seul le fournisseur pointé par web.search_backend est
    # réellement l'actif (les autres sont juste « disponibles »). Repli silencieux : un badge
    # ne doit jamais casser l'écran de connexion.
    active_search = ""
    if raw.get("name") == "web":
        try:
            active_search = hermes_adapter.get_web_backends().get("search", "")
        except Exception:  # noqa: BLE001 — cosmétique
            active_search = ""
    providers = [
        ToolProvider(
            name=p["name"],
            tag=p.get("tag"),
            badge=p.get("badge"),
            kind=ToolProviderKind(p.get("kind", "key")),
            fields=[ToolField(**f) for f in p.get("fields", [])],
            slug=p.get("slug"),
            advanced=bool(p.get("advanced", False)),
            category=p.get("category"),
            connected=p.get("connected"),
            active=_web_provider_active(p.get("slug"), active_search) if active_search else None,
        )
        for p in raw_providers
    ]
    return ToolConnection(
        name=raw["name"],
        required=bool(raw.get("required")),
        connected=bool(raw.get("connected")),
        providers=providers,
        note=_TOOLSET_NOTE_FR.get(raw.get("name", "")),
    )


# --- US3 : écrire une clé / des champs ---------------------------------------


def set_key(name: str, values: dict[str, str]) -> list[str]:
    """Enregistre un ou plusieurs champs (env_vars) d'un toolset.

    Les valeurs ne sont jamais renvoyées ni journalisées (FR-004). Retourne les noms de clés
    écrites. Lève ``ValueError`` si une clé est vide ou une valeur manquante (→ 422).
    """
    if not values:
        raise ValueError("aucun champ fourni")
    saved: list[str] = []
    for key, value in values.items():
        key = (key or "").strip()
        if not key or not re.fullmatch(r"[A-Z0-9_]+", key):
            raise ValueError(f"nom de variable invalide: {key!r}")
        if value is None or str(value) == "":
            raise ValueError(f"valeur manquante pour {key}")
        str_value = str(value)
        if "\n" in str_value or "\r" in str_value:
            # Un retour à la ligne dans la VALEUR casserait le format ligne-par-ligne du
            # .env (écrivain naïf `f"{key}={value}"` par ligne) — corruption silencieuse
            # potentielle de toutes les autres variables. Cf. audit Moyenne — Issue #7.
            raise ValueError(f"valeur invalide pour {key} : retour à la ligne interdit")
        hermes_adapter._set_env_value(key, str_value)
        saved.append(key)
    # Recherche web : connecter un fournisseur natif le rend actif tout de suite
    # (bascule web.search_backend). Les plugins (linkup/serper/…) sont ignorés ici.
    if name == "web":
        _apply_web_backend_for_env_vars(saved)
    return saved


def disconnect_keys(name: str, keys: list[str]) -> dict:
    """Déconnecte UN fournisseur : efface seulement les ``env_vars`` ciblées (FR-007).

    Ne touche ni au toggle de l'outil ni aux autres fournisseurs. Les clés sont validées
    contre les champs réellement déclarés par le toolset : on n'efface jamais une variable
    arbitraire. Lève ``KeyError`` si le toolset est inconnu, ``ValueError`` si une clé
    n'appartient pas au toolset (→ 422).
    """
    conn = get_connection(name)
    known = {field.key for provider in conn.providers for field in provider.fields}
    if not known:
        raise KeyError(name)
    targets = [(k or "").strip() for k in keys if (k or "").strip()]
    if not targets:
        raise ValueError("aucun champ à déconnecter")
    for key in targets:
        if key not in known:
            raise ValueError(f"champ inconnu pour ce toolset: {key!r}")
    for key in targets:
        _unset_env_value(key)
    # Recherche web : après avoir retiré une clé, rebascule sur le meilleur fournisseur
    # restant — ddgs (gratuit) en dernier ressort. Jamais de backend vide.
    if name == "web":
        _reapply_web_backend_after_disconnect()
    return {
        "disconnected": targets,
        "connection_state": (
            ToolConnectionState.connected.value
            if _toolset_connected(name)
            else ToolConnectionState.connection_required.value
        ),
    }


def _toolset_connected(name: str) -> bool:
    """Recalcule l'état « connecté » d'un toolset via l'introspection ciblée."""
    return get_connection(name).connected


def test_connection(name: str) -> dict:
    """Teste la connexion (v1 = présence des credentials via ``_toolset_has_keys``)."""
    conn = get_connection(name)
    if conn.connected:
        return {"ok": True, "connection_state": ToolConnectionState.connected.value}
    return {
        "ok": False,
        "reason": "connexion incomplète : identifiants manquants",
        "connection_state": ToolConnectionState.connection_required.value,
    }


# --- Test RÉEL d'une clé/URL par un appel HTTP léger (par champ env_var) -------
#
# Clé de la table = nom de l'env_var. Un fournisseur sans entrée → « test indisponible »
# (on l'affiche honnêtement plutôt que de mentir). Heuristique d'auth :
#   401/403 → clé refusée ; <400 → valide ; autre 4xx → clé acceptée (requête incomplète).
# Les valeurs ne sont jamais journalisées ni renvoyées.

_FIELD_TEST: dict[str, dict] = {
    # Endpoints compatibles OpenAI (GET léger, gratuit) — Bearer
    "OPENAI_API_KEY": {"kind": "bearer", "url": "https://api.openai.com/v1/models"},
    "OPENROUTER_API_KEY": {"kind": "bearer", "url": "https://openrouter.ai/api/v1/key"},
    "XAI_API_KEY": {"kind": "bearer", "url": "https://api.x.ai/v1/api-key"},
    # Exa ne propose pas d'endpoint GET gratuit de validation : une recherche minimale
    # confirme simultanément l'authentification et l'accès réel au service.
    "EXA_API_KEY": {
        "kind": "header",
        "header": "x-api-key",
        "url": "https://api.exa.ai/search",
        "method": "POST",
        "json": {
            "query": "LunarIA connection test",
            "type": "instant",
            "numResults": 1,
        },
    },
    # Brave : header dédié (consomme 1 requête du quota gratuit)
    "BRAVE_SEARCH_API_KEY": {
        "kind": "header",
        "header": "X-Subscription-Token",
        "url": "https://api.search.brave.com/res/v1/web/search?q=ping&count=1",
    },
    # Instances auto-hébergées : la « clé » est l'URL → on vérifie qu'elle répond.
    "SEARXNG_URL": {"kind": "url_ping"},
    "CAMOFOX_URL": {"kind": "url_ping"},
    "FIRECRAWL_API_URL": {"kind": "url_ping"},
}


def _read_env_value(key: str) -> str | None:
    """Relit la valeur enregistrée d'une env_var dans ``~/.hermes/.env`` (pour tester une clé déjà saisie).

    Délègue à ``hermes_adapter.read_env_value`` : c'était la 3e réimplémentation indépendante
    de lecture/écriture de ``.env`` du bridge (aucune verrouillée) — cf. audit Haute #3. Un seul
    point de vérité maintenant, verrouillé + atomique côté écriture. On garde ici le
    déquotage (``"..."``/``'...'``) propre à cet appelant (comportement inchangé).
    """
    value = hermes_adapter.read_env_value(key)
    return value.strip('"').strip("'") if value is not None else None


# Nombre max de sauts de redirection suivis manuellement (au-delà : cible refusée par
# principe — une chaîne de redirections aussi longue n'a aucun usage self-hosted légitime).
_MAX_SELF_HOSTED_REDIRECTS = 5


class _RedirectionRefusee(Exception):
    """Levée quand une redirection HTTP pointe vers une cible interdite par net_guard."""


def _get_self_hosted_revalide(url: str, *, timeout: float) -> httpx.Response:
    """GET avec suivi manuel des redirections, en revalidant CHAQUE saut via net_guard.

    Cf. audit Haute #2 (SSRF par redirection) : ``httpx.get(..., follow_redirects=True)``
    ne revalide JAMAIS l'URL de destination d'une redirection — seule l'URL de départ
    passait par ``net_guard.is_safe_self_hosted_url``. Un serveur public quelconque
    (accepté par cette 1re validation) peut renvoyer un ``302 Location:
    http://169.254.169.254/...`` : httpx suivait ce saut en interne, sans jamais rappeler
    le garde-fou, et le process bridge (tourne sur l'hôte, pas isolé) allait chercher la
    cible interdite. On désactive donc ``follow_redirects`` et on revalide nous-mêmes
    CHAQUE URL (départ + chaque ``Location``) avant de la requêter, avec une limite de
    sauts pour éviter une boucle infinie ou une chaîne interminable.
    """
    current = url
    for _ in range(_MAX_SELF_HOSTED_REDIRECTS + 1):
        if not net_guard.is_safe_self_hosted_url(current):
            raise _RedirectionRefusee(current)
        response = httpx.get(current, timeout=timeout, follow_redirects=False)
        if response.status_code in (301, 302, 303, 307, 308) and "location" in response.headers:
            # Location peut être relative : la résoudre par rapport à l'URL courante.
            current = urljoin(current, response.headers["location"])
            continue
        return response
    raise _RedirectionRefusee(current)  # trop de sauts : on refuse par principe


def test_key(values: dict[str, str]) -> dict:
    """Teste réellement une clé/URL via un appel HTTP. ``values`` = ``{ENV_VAR: valeur}``.

    Une valeur vide → on relit celle enregistrée. Renvoie ``{tested, ok, reason}`` :
    ``tested=False`` quand aucun test réel n'existe pour ce fournisseur (affiché honnêtement).
    """
    target = next((k for k in values if k in _FIELD_TEST), None)
    if target is None:
        return {
            "tested": False,
            "ok": False,
            "reason": "Test réel indisponible pour ce fournisseur — la clé est enregistrée, "
            "mais ce service ne permet pas de la vérifier sans coût.",
        }
    cfg = _FIELD_TEST[target]
    value = (values.get(target) or "").strip() or (_read_env_value(target) or "")
    if not value:
        return {"tested": False, "ok": False, "reason": "Renseigne d'abord la valeur, puis teste."}

    try:
        if cfg["kind"] == "url_ping":
            url = value if value.startswith(("http://", "https://")) else f"http://{value}"
            # Garde anti-SSRF (cf. audit Haute #2) : ces URL sont fournies par l'appelant
            # (SearXNG/Camofox/Firecrawl auto-hébergés). Un refus total type
            # ``net_guard.is_public_http_url`` casserait la fonctionnalité pour la quasi
            # totalité des déploiements réels (ces services tournent en ``localhost`` ou
            # sur le LAN du VPS/client — voir les placeholders "ex. http://localhost:8080").
            # On accepte donc privé/loopback, mais on bloque toujours les cibles qui ne
            # sont JAMAIS une instance self-hosted légitime : métadonnées cloud
            # (169.254.169.254), multicast, réservé — cf. net_guard.is_safe_self_hosted_url.
            try:
                r = _get_self_hosted_revalide(url, timeout=8.0)
            except _RedirectionRefusee:
                # Refus dès l'URL de départ OU une redirection vers une cible interdite
                # (cf. audit Haute #2) — même message dans les deux cas, on ne fait pas
                # fuiter à l'appelant lequel des deux sauts a été bloqué.
                return {
                    "tested": True,
                    "ok": False,
                    "reason": "Adresse refusée (cible réseau non autorisée pour ce test).",
                }
            ok = r.status_code < 500
            return {
                "tested": True,
                "ok": ok,
                "reason": f"L'instance répond (HTTP {r.status_code})."
                if ok
                else f"L'instance renvoie une erreur (HTTP {r.status_code}).",
            }

        headers = {}
        if cfg["kind"] == "bearer":
            headers["Authorization"] = f"Bearer {value}"
        elif cfg["kind"] == "header":
            headers[cfg["header"]] = value
        r = httpx.request(
            cfg.get("method", "GET"),
            cfg["url"],
            headers=headers,
            json=cfg.get("json"),
            timeout=12.0,
        )
        if r.status_code in (401, 403):
            return {"tested": True, "ok": False, "reason": f"Clé refusée (HTTP {r.status_code})."}
        if r.status_code < 400:
            return {"tested": True, "ok": True, "reason": "Clé valide ✅"}
        # Autre 4xx : la clé est acceptée mais la requête de test est incomplète → clé OK.
        return {"tested": True, "ok": True, "reason": f"Clé acceptée (HTTP {r.status_code})."}
    except httpx.RequestError:
        return {
            "tested": True,
            "ok": False,
            "reason": "Service injoignable (réseau ou instance indisponible).",
        }


# --- US3 : déconnexion (retrait credentials + désactivation) ------------------

_REMOVE_OAUTH_SCRIPT = """
import json
provider_id = {provider_id}
removed = False
try:
    from hermes_cli.auth import _auth_store_lock, _load_auth_store, _save_auth_store
    with _auth_store_lock():
        store = _load_auth_store()
        providers = store.get("providers")
        if isinstance(providers, dict) and provider_id in providers:
            del providers[provider_id]
            _save_auth_store(store)
            removed = True
except Exception as exc:
    print(json.dumps({{"removed": False, "error": str(exc)[:200]}}))
else:
    print(json.dumps({{"removed": removed}}))
"""


def _unset_env_value(key: str) -> None:
    """Retire ``KEY=...`` de ``~/.hermes/.env`` (préserve le reste du fichier).

    Délègue à ``hermes_adapter._remove_env_value`` (verrouillé + écriture atomique) : c'était
    une 2e réimplémentation indépendante, non verrouillée, du même fichier — cf. audit Haute #3.
    """
    hermes_adapter._remove_env_value(key)


def disconnect(name: str) -> dict:
    """Déconnecte un toolset : retrait des credentials + désactivation (FR-007).

    Lève ``KeyError`` si le toolset est inconnu de Hermes (→ 404).

    Ordre important : on valide/désactive le toolset EN PREMIER (``set_toolset_enabled``
    lève un 404 propre si Hermes ne le connaît pas), AVANT de toucher aux identifiants.
    L'ancien ordre effaçait déjà les env_vars puis découvrait le 404 en dernier : un
    toolset connu de nos métadonnées mais absent des toolsets réellement pilotables côté
    Hermes perdait silencieusement ses identifiants derrière un 404 « rien ne s'est passé »
    (cf. audit Moyenne — Issue #6).
    """
    conn = get_connection(name)
    # 1. valider + désactiver le toolset (404 si inconnu) — AVANT tout effet de bord.
    found = tools_adapter.set_toolset_enabled(name, False)
    if not found:
        raise KeyError(name)
    # 2. retirer les env_vars de chaque provider à champs
    for provider in conn.providers:
        for field in provider.fields:
            _unset_env_value(field.key)
    # 3. retirer le token OAuth éventuel
    provider_id = _OAUTH_PROVIDER_BY_TOOLSET.get(name)
    if provider_id:
        hermes_adapter.introspect(_REMOVE_OAUTH_SCRIPT.format(provider_id=json.dumps(provider_id)))
    return {
        "disconnected": True,
        "connection_state": ToolConnectionState.connection_required.value,
        "enabled": False,
    }


# --- US4 : OAuth headless (Spotify, xAI) en arrière-plan ----------------------

_AUTH_URL_RE = re.compile(r"https?://[^\s\"']+")

# Script Spotify : appelle les briques headless (pas le wizard interactif). Imprime l'URL
# d'autorisation tôt (extraite par oauth_status), attend le callback loopback, échange, persiste.
_SPOTIFY_OAUTH_SCRIPT = r"""
import sys, uuid
from hermes_cli.config import get_env_value
from hermes_cli.auth import (
    _spotify_code_verifier, _spotify_code_challenge, _spotify_build_authorize_url,
    _spotify_wait_for_callback, _spotify_exchange_code_for_tokens,
    _spotify_token_payload_to_state, _auth_store_lock, _load_auth_store,
    _store_provider_state, _save_auth_store,
    DEFAULT_SPOTIFY_REDIRECT_URI, DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL,
    DEFAULT_SPOTIFY_API_BASE_URL, DEFAULT_SPOTIFY_SCOPE,
)

client_id = get_env_value("HERMES_SPOTIFY_CLIENT_ID")
if not client_id:
    print("ERROR: HERMES_SPOTIFY_CLIENT_ID manquant — renseigne-le d'abord", flush=True)
    sys.exit(2)

redirect_uri = DEFAULT_SPOTIFY_REDIRECT_URI
scope = DEFAULT_SPOTIFY_SCOPE
verifier = _spotify_code_verifier()
challenge = _spotify_code_challenge(verifier)
state = uuid.uuid4().hex
url = _spotify_build_authorize_url(
    client_id=client_id, redirect_uri=redirect_uri, scope=scope,
    state=state, code_challenge=challenge,
    accounts_base_url=DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL,
)
print("AUTH_URL " + url, flush=True)
cb = _spotify_wait_for_callback(redirect_uri, timeout_seconds=180.0)
tokens = _spotify_exchange_code_for_tokens(
    client_id=client_id, code=cb["code"], redirect_uri=redirect_uri,
    code_verifier=verifier, accounts_base_url=DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL,
)
st = _spotify_token_payload_to_state(
    tokens, client_id=client_id, redirect_uri=redirect_uri, requested_scope=scope,
    accounts_base_url=DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL, api_base_url=DEFAULT_SPOTIFY_API_BASE_URL,
)
with _auth_store_lock():
    store = _load_auth_store()
    _store_provider_state(store, "spotify", st, set_active=False)
    _save_auth_store(store)
print("SUCCESS", flush=True)
"""

# Script xAI : discovery + listener loopback + URL + callback + échange + persistance.
_XAI_OAUTH_SCRIPT = r"""
import sys, uuid
from hermes_cli.auth import (
    _xai_oauth_discovery, _oauth_pkce_code_verifier, _oauth_pkce_code_challenge,
    _xai_oauth_build_authorize_url, _xai_start_callback_server, _xai_wait_for_callback,
    _xai_oauth_exchange_code_for_tokens, _save_xai_oauth_tokens,
)

discovery = _xai_oauth_discovery()
server, thread, result, redirect_uri = _xai_start_callback_server()
verifier = _oauth_pkce_code_verifier()
challenge = _oauth_pkce_code_challenge(verifier)
state = uuid.uuid4().hex
nonce = uuid.uuid4().hex
url = _xai_oauth_build_authorize_url(
    authorization_endpoint=discovery["authorization_endpoint"],
    redirect_uri=redirect_uri, code_challenge=challenge, state=state, nonce=nonce,
)
print("AUTH_URL " + url, flush=True)
cb = _xai_wait_for_callback(server, thread, result, timeout_seconds=180.0, manual_paste_redirect_uri=None)
tokens = _xai_oauth_exchange_code_for_tokens(
    token_endpoint=discovery["token_endpoint"], code=cb["code"],
    redirect_uri=redirect_uri, code_verifier=verifier, code_challenge=challenge,
)
payload = tokens.get("tokens", tokens) if isinstance(tokens, dict) else tokens
_save_xai_oauth_tokens(payload, discovery=discovery, redirect_uri=redirect_uri)
print("SUCCESS", flush=True)
"""

_OAUTH_SCRIPT_BY_TOOLSET: dict[str, str] = {
    "spotify": _SPOTIFY_OAUTH_SCRIPT,
    "x_search": _XAI_OAUTH_SCRIPT,
}


class OAuthUnsupported(ValueError):
    """Le toolset n'a pas de flux OAuth pilotable."""


def start_oauth(name: str) -> None:
    """Démarre le flux OAuth headless d'un toolset en arrière-plan (Spotify, xAI)."""
    script = _OAUTH_SCRIPT_BY_TOOLSET.get(name)
    if script is None:
        raise OAuthUnsupported(name)
    hermes_adapter._start_bg_run(
        f"tool_oauth_{name}", [hermes_adapter.HERMES_PYTHON, "-u", "-c", script]
    )


def oauth_status(name: str) -> dict:
    """État du flux OAuth + URL d'autorisation extraite du log (fallback copier-coller)."""
    raw = hermes_adapter._bg_status(f"tool_oauth_{name}")
    log = raw.get("log", "")
    match = _AUTH_URL_RE.search(log)
    if not raw.get("started"):
        status = "error"
    elif raw.get("running"):
        status = "running"
    elif raw.get("success") and "SUCCESS" in log:
        status = "success"
    else:
        status = "error"
    return {"status": status, "auth_url": match.group(0) if match else None, "log": log[-2000:]}
