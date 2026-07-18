"""Adapter Outils — pilotage des toolsets natifs de Hermes (page Capacités, onglet Outils).

Source de vérité = Hermes :
- LISTE : introspection via l'interpréteur de Hermes (``CONFIGURABLE_TOOLSETS`` + état par plateforme).
- TOGGLE : ``_get_platform_tools`` / ``_save_platform_tools`` (clé ``platform_toolsets.<platform>``
  de config.yaml), exactement comme l'API HTTP officielle de Hermes.

Les toolsets sont gérés PAR PLATEFORME côté Hermes ; on pilote ``hermes_adapter.HERMES_PLATFORM``
(défaut ``cli``, configurable). On réutilise ``hermes_adapter.introspect`` pour rester DRY.
"""

from __future__ import annotations

import json
import time

from . import hermes_adapter
from .default_toolsets import DEFAULT_ENABLED_TOOLSETS
from .models import Toolset, ToolConnectionState

# Cache mémoire court de list_toolsets() : l'introspection Hermes coûte ~2 s, dominée à 93 %
# par la sonde réseau NON cachée du toolset « vision » (resolve_vision_provider_client, ~2 s
# à CHAQUE appel côté moteur). Sans ce cache, l'onglet Outils refait la sonde à chaque ouverture.
# TTL court = l'état de connexion reste frais ; invalidé explicitement au toggle d'un outil.
_TOOLSETS_CACHE: tuple[float, list[Toolset]] | None = None
_TOOLSETS_TTL_S = 45.0

# Liste des toolsets configurables + état activé/désactivé + état de connexion (feature 003).
_LIST_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.tools_config import _get_effective_configurable_toolsets, _get_platform_tools, TOOL_CATEGORIES
from toolsets import resolve_toolset
try:
    from hermes_cli.tools_config import _toolset_has_keys
except Exception:
    _toolset_has_keys = None
try:
    from hermes_cli.tools_config import TOOLSET_ENV_REQUIREMENTS
except Exception:
    TOOLSET_ENV_REQUIREMENTS = {{}}

import hermes_cli.tools_config as _tc
_PLUGIN_FNS = {{
    "web": "_plugin_web_search_providers",
    "image_gen": "_plugin_image_gen_providers",
    "video_gen": "_plugin_video_gen_providers",
    "browser": "_plugin_browser_providers",
    "tts": "_plugin_tts_providers",
}}

platform = {platform}
config = load_config()
enabled = set(_get_platform_tools(config, platform))

def _provider_names(key):
    names = []
    cat = TOOL_CATEGORIES.get(key)
    if cat:
        names += [p.get("name") for p in cat.get("providers", []) or []]
    fn = _PLUGIN_FNS.get(key)
    if fn and hasattr(_tc, fn):
        try:
            names += [p.get("name") for p in getattr(_tc, fn)() or []]
        except Exception:
            pass
    seen = set(); out = []
    for n in names:
        if n and n not in seen:
            seen.add(n); out.append(n)
    return out

def _connection_state(key):
    if key not in TOOL_CATEGORIES and key not in TOOLSET_ENV_REQUIREMENTS:
        return "not_required"
    connected = False
    if _toolset_has_keys is not None:
        try:
            connected = bool(_toolset_has_keys(key))
        except Exception:
            connected = False
    return "connected" if connected else "connection_required"

out = []
for key, label, desc in _get_effective_configurable_toolsets():
    try:
        tools = sorted(set(resolve_toolset(key)))
    except Exception:
        tools = []
    out.append({{
        "name": key,
        "label": label,
        "description": desc or "",
        "tools": tools,
        "enabled": key in enabled,
        "connection_state": _connection_state(key),
        "providers": _provider_names(key),
    }})
print(json.dumps(out))
"""

# Active/désactive un toolset (membership dans la liste persistée), pattern de l'API Hermes.
_TOGGLE_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.tools_config import (
    _get_effective_configurable_toolsets,
    _get_platform_tools,
    _save_platform_tools,
)

platform = {platform}
name = {name}
enabled = {enabled}
valid = {{k for k, _, _ in _get_effective_configurable_toolsets()}}
if name not in valid:
    print(json.dumps({{"found": False}}))
else:
    config = load_config()
    current = set(_get_platform_tools(config, platform))
    if enabled:
        current.add(name)
    else:
        current.discard(name)
    _save_platform_tools(config, platform, current)
    print(json.dumps({{"found": True, "ok": True}}))
"""


def invalidate_toolsets_cache() -> None:
    """Purge le cache de list_toolsets() (après un changement d'état d'outil)."""
    global _TOOLSETS_CACHE
    _TOOLSETS_CACHE = None


def list_toolsets() -> list[Toolset]:
    """Liste les toolsets natifs Hermes avec leur état (activé/désactivé) pour la plateforme.

    Résultat caché ~45 s (voir _TOOLSETS_CACHE) : évite de refaire la sonde « vision » de ~2 s
    à chaque ouverture de l'onglet Outils. Invalidé au toggle via invalidate_toolsets_cache().
    """
    global _TOOLSETS_CACHE
    if _TOOLSETS_CACHE is not None and (time.monotonic() - _TOOLSETS_CACHE[0]) < _TOOLSETS_TTL_S:
        return _TOOLSETS_CACHE[1]

    script = _LIST_SCRIPT.format(platform=json.dumps(hermes_adapter.HERMES_PLATFORM))
    raw = hermes_adapter.introspect(script)
    result = [
        Toolset(
            name=it["name"],
            label=it.get("label", it["name"]),
            description=it.get("description", ""),
            tools=it.get("tools", []),
            enabled=bool(it.get("enabled", True)),
            connection_state=ToolConnectionState(it.get("connection_state", "not_required")),
            providers=it.get("providers", []),
        )
        for it in raw
    ]
    _TOOLSETS_CACHE = (time.monotonic(), result)
    return result


def set_toolset_enabled(name: str, enabled: bool) -> bool:
    """Active/désactive un toolset. Renvoie False si le toolset est inconnu (404)."""
    script = _TOGGLE_SCRIPT.format(
        platform=json.dumps(hermes_adapter.HERMES_PLATFORM),
        name=json.dumps(name),
        enabled=("True" if enabled else "False"),  # littéral Python (json.dumps → 'false' = NameError)
    )
    result = hermes_adapter.introspect(script)
    invalidate_toolsets_cache()  # l'état a changé → la prochaine liste sera recalculée
    return bool(result.get("found"))


# Applique le set d'outils cochés par défaut (install client). NON DESTRUCTIF : n'écrit
# `platform_toolsets.<platform>` QUE si le client n'a pas encore de config d'outils (install
# neuve), sauf `force`. Écrit la liste blanche DEFAULT_ENABLED_TOOLSETS → tout le reste décoché.
_APPLY_DEFAULTS_SCRIPT = """
import json
from hermes_cli.config import load_config
from hermes_cli.tools_config import (
    _get_effective_configurable_toolsets,
    _get_platform_tools,
    _save_platform_tools,
)

platform = {platform}
desired = {desired}
force = {force}

config = load_config()
valid = {{k for k, _, _ in _get_effective_configurable_toolsets()}}
existing = config.get("platform_toolsets") or {{}}
current_list = existing.get(platform) if isinstance(existing, dict) else None
current_list = [str(t) for t in current_list] if isinstance(current_list, list) else []

# "Déjà configuré par le client" = au moins un toolset INDIVIDUEL configurable présent
# (même logique que `has_explicit_config` de Hermes). Le composite par défaut `hermes-cli`
# seul N'EST PAS une perso — on applique alors nos défauts. Ainsi on écrit bien sur une
# install neuve, mais jamais par-dessus les choix d'un client qui a déjà coché/décoché.
already = any(t in valid for t in current_list)

if already and not force:
    print(json.dumps({{
        "applied": False,
        "reason": "already_configured",
        "enabled": sorted(_get_platform_tools(config, platform)),
    }}))
else:
    keep = [k for k in desired if k in valid]
    _save_platform_tools(config, platform, set(keep))
    print(json.dumps({{
        "applied": True,
        "enabled": sorted(keep),
        "skipped_unknown": sorted(set(desired) - valid),
    }}))
"""


def apply_default_toolsets(*, force: bool = False) -> dict:
    """Applique le set d'outils cochés par défaut à la config Hermes (install client).

    Non destructif : n'écrit `platform_toolsets.<platform>` QUE si aucune config d'outils
    n'existe encore (install neuve). Si le client a déjà personnalisé ses outils, on ne touche
    à RIEN — sauf `force=True`. Les serveurs MCP éventuels sont préservés par `_save_platform_tools`.

    Renvoie le dict du script : `{"applied": bool, "reason"?: str, "enabled": [...], ...}`.
    """
    script = _APPLY_DEFAULTS_SCRIPT.format(
        platform=json.dumps(hermes_adapter.HERMES_PLATFORM),
        desired=json.dumps(list(DEFAULT_ENABLED_TOOLSETS)),
        force=("True" if force else "False"),  # littéral Python (pas json.dumps → 'false' invalide)
    )
    result = hermes_adapter.introspect(script)
    return result if isinstance(result, dict) else {"applied": False, "reason": "unexpected_result"}


# Backend de recherche web par défaut à l'install : DuckDuckGo (gratuit, sans clé, souverain).
# Rend la recherche web fonctionnelle dès le 1er démarrage, sans aucune action du client. Le
# moteur relit config.yaml à chaud → aucun redémarrage. Recherche seule (la lecture des pages
# reste au navigateur automatisé) ; un fournisseur payant connecté prendra le relais ensuite.
_DEFAULT_WEB_SEARCH_BACKEND = "ddgs"


def apply_default_web_backend(*, force: bool = False) -> dict:
    """Écrit `web.search_backend: ddgs` à l'install si aucun backend n'est encore choisi.

    Non destructif : n'écrit QUE si `web.search_backend` est vide (install neuve). Ne touche
    jamais un choix client existant — sauf `force=True`. `extract_backend` est laissé tel quel.
    """
    current = hermes_adapter.get_web_backends().get("search", "")
    if current and not force:
        return {"applied": False, "reason": "already_configured", "search_backend": current}
    hermes_adapter.set_web_backend(_DEFAULT_WEB_SEARCH_BACKEND, None)
    return {"applied": True, "search_backend": _DEFAULT_WEB_SEARCH_BACKEND}
