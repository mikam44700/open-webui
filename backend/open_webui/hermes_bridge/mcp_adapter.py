"""Adapter MCP — pilotage des connecteurs MCP de Hermes (feature 002).

Source de vérité = Hermes :
- LISTE / CONFIG : lecture de ``~/.hermes/config.yaml`` (clé ``mcp_servers``).
- SECRETS : présence seulement (``MCP_<NAME>_API_KEY`` dans ``.env`` ; token OAuth dans
  ``~/.hermes/mcp-tokens/<name>.json``). Jamais les valeurs (FR-011).
- ÉTAT : dérivé à la volée (cf. specs/002-connecteurs-mcp/research.md D3). L'état « connecté »
  réel n'est connu qu'après une probe explicite (US4) ; par défaut on renvoie ``disconnected``.

On réutilise l'infrastructure de ``hermes_adapter`` (HERMES_HOME, ``_set_env_value``,
``_start_bg_run``/``_bg_status``, ``HermesUnavailable``) pour rester DRY et cohérent.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

import yaml

from . import hermes_adapter, mcp_curation, mcp_registry
from .models import (
    CatalogEntry,
    ConfigField,
    Connector,
    ConnectorState,
    McpAuthType,
    McpTransport,
    SecretState,
)

_logger = logging.getLogger(__name__)

# Un nom de connecteur devient une clé de config.yaml ET le composant central d'un chemin de
# fichier utilisé par ``_purge_oauth_tokens`` — charset sûr uniquement (défense en profondeur,
# finding HAUTE #1 : le vecteur DELETE HTTP direct est déjà bloqué par le routage Starlette,
# mais un nom hostile ne doit jamais pouvoir entrer par un autre chemin, ex. registre distant).
_SAFE_CONNECTOR_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _config_path(hermes_home=None) -> Path:
    return (hermes_home or hermes_adapter.HERMES_HOME) / "config.yaml"


def _load_mcp_servers(hermes_home=None) -> dict[str, dict]:
    """Renvoie le dict ``mcp_servers`` de config.yaml, ou ``{}`` si absent/illisible.

    ``hermes_home`` cible un profil précis (MCP PAR AGENT) ; None = profil courant du bridge.
    """
    path = _config_path(hermes_home)
    if not path.exists():
        return {}
    try:
        cfg = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError):
        return {}
    servers = cfg.get("mcp_servers")
    return servers if isinstance(servers, dict) else {}


_BOOLISH_TRUE = ("true", "1", "yes", "on")
_BOOLISH_FALSE = ("false", "0", "no", "off")


def _parse_boolish(value: object, default: bool = True) -> bool:
    """Interprète ``enabled`` (bool, ``"true"/"false"``, ``"1"/"0"``, ``"yes"/"no"``).

    Fail-safe inchangé (une valeur non reconnue désactive le connecteur), mais on avertit
    désormais (finding BASSE #7) au lieu de désactiver en silence — une coquille dans
    ``config.yaml`` édité à la main (ex. ``enabled: tru``) reste diagnosticable.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in _BOOLISH_TRUE:
        return True
    if text in _BOOLISH_FALSE:
        return False
    _logger.warning(
        "valeur 'enabled' non reconnue (%r) — connecteur traité comme désactivé (fail-safe)",
        value,
    )
    return False


def _detect_transport(entry: dict) -> McpTransport:
    if entry.get("command"):
        return McpTransport.stdio
    if str(entry.get("transport", "")).lower() == "sse":
        return McpTransport.sse
    return McpTransport.http


def _detect_auth_type(entry: dict) -> McpAuthType:
    if str(entry.get("auth", "")).lower() == "oauth":
        return McpAuthType.oauth
    # un secret externe est référencé via un placeholder ``${VAR}`` — uniquement dans les
    # champs structurellement pertinents (headers/env), jamais dans tout le JSON sérialisé
    # (finding BASSE #5 : une url/arg contenant "${" par coïncidence ne doit pas être classée
    # "key" à tort, ce qui afficherait "clé requise" pour un connecteur qui n'en a pas besoin).
    relevant = json.dumps([entry.get("headers"), entry.get("env")], default=str)
    if "${" in relevant:
        return McpAuthType.key
    return McpAuthType.none


def _env_key_for(name: str) -> str:
    """Convention de nommage de la variable de clé d'un connecteur MCP."""
    safe = "".join(c if c.isalnum() else "_" for c in name).upper()
    return f"MCP_{safe}_API_KEY"


def _token_present(name: str) -> bool:
    """Présence d'un token OAuth MCP (jamais son contenu)."""
    return (hermes_adapter.HERMES_HOME / "mcp-tokens" / f"{name}.json").exists()


def _secret_state(name: str, auth: McpAuthType, present_keys: set[str]) -> SecretState:
    if auth is McpAuthType.oauth:
        return SecretState.present if _token_present(name) else SecretState.absent
    if auth is McpAuthType.key:
        return SecretState.present if _env_key_for(name) in present_keys else SecretState.absent
    return SecretState.absent


def _derive_state(enabled: bool, auth: McpAuthType, secret: SecretState) -> ConnectorState:
    if not enabled:
        return ConnectorState.disabled
    if auth is McpAuthType.oauth and secret is SecretState.absent:
        return ConnectorState.auth_required
    if auth is McpAuthType.key and secret is SecretState.absent:
        return ConnectorState.incomplete
    return ConnectorState.disconnected  # configuré, connexion non encore testée (probe = US4)


def _endpoint_summary(entry: dict) -> str:
    """Résumé du raccordement (URL ou commande), sans secret."""
    if entry.get("url"):
        return str(entry["url"])
    command = entry.get("command")
    if command:
        args = entry.get("args") or []
        return " ".join([str(command), *(str(a) for a in args)])[:160]
    return ""


def _to_connector(name: str, entry: dict, present_keys: set[str]) -> Connector:
    entry = entry if isinstance(entry, dict) else {}
    enabled = _parse_boolish(entry.get("enabled", True))
    auth = _detect_auth_type(entry)
    secret = _secret_state(name, auth, present_keys)
    return Connector(
        id=name,
        transport=_detect_transport(entry),
        auth_type=auth,
        enabled=enabled,
        state=_derive_state(enabled, auth, secret),
        endpoint=_endpoint_summary(entry),
        secret_state=secret,
        source=None,
    )


def list_connectors(hermes_home=None) -> list[Connector]:
    """Liste les connecteurs MCP installés avec leur état dérivé (US1).

    ``hermes_home`` cible un profil précis (MCP PAR AGENT) ; None = profil courant du bridge.
    """
    servers = _load_mcp_servers(hermes_home)
    present_keys = hermes_adapter._present_env_keys()
    # YAML 1.1 peut parser certaines clés (off/on/yes/no) en bool : on force str et on trie dessus.
    return [
        _to_connector(str(name), entry, present_keys)
        for name, entry in sorted(servers.items(), key=lambda kv: str(kv[0]))
    ]


# --- US2 : catalogue, installation, clé, OAuth -------------------------------

# Introspection du catalogue via l'interpréteur de Hermes (renvoie du JSON sur stdout).
_CATALOG_SCRIPT = """
import json
from hermes_cli import mcp_catalog as mc

def _attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

out = []
for e in mc.list_catalog():
    transport = _attr(e, "transport")
    auth = _attr(e, "auth")
    out.append({
        "name": _attr(e, "name"),
        "description": _attr(e, "description", "") or "",
        "transport": _attr(transport, "type", "http"),
        "auth": _attr(auth, "type", "none"),
        "source_url": _attr(e, "source"),
    })
print(json.dumps(out))
"""


def _mcp_introspect(script: str, timeout: int = 30, hermes_home=None):
    """Exécute un script Python via l'interpréteur de Hermes et parse le JSON renvoyé.

    ``hermes_home`` cible un profil précis (passé via l'env ``HERMES_HOME`` au sous-process).
    """
    python = hermes_adapter.HERMES_PYTHON
    if not Path(python).exists():
        raise hermes_adapter.HermesUnavailable(f"interpréteur Hermes introuvable: {python}")
    import os

    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home or hermes_adapter.HERMES_HOME)
    try:
        res = subprocess.run(
            [python, "-c", script], capture_output=True, text=True, timeout=timeout, env=env
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise hermes_adapter.HermesUnavailable(str(exc)) from exc
    if res.returncode != 0:
        raise hermes_adapter.HermesUnavailable(res.stderr.strip()[:300] or "introspection MCP échouée")
    return json.loads(res.stdout)


def _map_catalog_transport(raw: str | None) -> McpTransport:
    raw = (raw or "").lower()
    if raw == "stdio":
        return McpTransport.stdio
    if raw == "sse":
        return McpTransport.sse
    return McpTransport.http


def _map_catalog_auth(raw: str | None) -> McpAuthType:
    raw = (raw or "").lower()
    if raw == "oauth":
        return McpAuthType.oauth
    if raw in ("api_key", "key"):
        return McpAuthType.key
    return McpAuthType.none


def _safe_list_connectors() -> list[Connector]:
    """``list_connectors`` tolérant : [] si le moteur est indisponible."""
    try:
        return list_connectors()
    except hermes_adapter.HermesUnavailable:
        return []


def _safe_engine_catalog() -> list[dict]:
    """Catalogue moteur (introspection) tolérant : [] si le moteur est indisponible."""
    try:
        return _mcp_introspect(_CATALOG_SCRIPT)
    except hermes_adapter.HermesUnavailable:
        return []


def list_catalog() -> list[CatalogEntry]:
    """Catalogue MCP fusionné : catalogue moteur (installable en 1 clic) + registre distant
    des ~55 MCP (affichage), rangé par catégorie et trié visible/expert (cf. mcp_curation).

    Tolérant aux pannes : si le moteur est KO on garde le registre, et inversement. Le
    dédoublonnage se fait par id (ex. Linear, présent des deux côtés, n'apparaît qu'une fois).
    """
    installed = {c.id for c in _safe_list_connectors()}

    # 1) Catalogue moteur : installable tout de suite (`hermes mcp install <name>`).
    by_id: dict[str, dict] = {}
    for it in _safe_engine_catalog():
        cid = str(it.get("name") or "").strip().lower()
        if not cid:
            continue
        by_id[cid] = {
            "name": cid,
            "label": "",
            "description": it.get("description", "") or "",
            "transport": _map_catalog_transport(it.get("transport")),
            "auth_type": _map_catalog_auth(it.get("auth")),
            "source_url": it.get("source_url"),
            "icon_url": None,
            "tags": [],
            "installable": True,
            "url": None,
            "install_method": "engine",  # installable via `hermes mcp install`
        }

    # 2) Registre distant : enrichit l'existant (logo, libellé) ou ajoute les nouveaux
    #    (affichés ; installation en 1 clic = étape ultérieure, d'où installable=False).
    for reg in mcp_registry.fetch_registry_mcps():
        cid = reg["id"]
        if cid in by_id:
            existing = by_id[cid]
            existing["label"] = existing["label"] or reg.get("label", "")
            existing["icon_url"] = existing["icon_url"] or reg.get("icon_url")
            existing["source_url"] = existing["source_url"] or reg.get("source_url")
            existing["tags"] = existing["tags"] or reg.get("tags", [])
            if not existing["description"]:
                existing["description"] = reg.get("description", "")
            continue
        by_id[cid] = {
            "name": cid,
            "label": reg.get("label", ""),
            "description": reg.get("description", ""),
            "transport": _map_catalog_transport(reg.get("transport")),
            "auth_type": _map_catalog_auth(reg.get("auth")),
            "source_url": reg.get("source_url"),
            "icon_url": reg.get("icon_url"),
            "tags": reg.get("tags", []),
            "installable": bool(reg.get("installable", False)),
            "url": reg.get("url"),
            "install_method": reg.get("install_method", ""),
            "config_fields": reg.get("config_fields", []),
        }

    # 3) Curation (catégorie + visibilité) + état installé, trié par libellé.
    out: list[CatalogEntry] = []
    for cid, e in by_id.items():
        category, visibility = mcp_curation.classify(cid)
        out.append(
            CatalogEntry(
                name=e["name"],
                label=e["label"],
                description=e["description"],
                transport=e["transport"],
                auth_type=e["auth_type"],
                installed=cid in installed,
                source_url=e["source_url"],
                icon_url=e["icon_url"],
                category=category,
                visibility=visibility,
                tags=e["tags"],
                installable=e["installable"],
                url=e.get("url"),
                install_method=e.get("install_method", ""),
                config_fields=[ConfigField(**f) for f in e.get("config_fields", [])],
            )
        )
    out.sort(key=lambda c: (c.label or c.name).lower())
    return out


def _registry_env_var(name: str, key: str) -> str:
    """Nom de variable .env namespacée pour un champ de MCP du registre (évite les collisions)."""
    safe = "".join(c if c.isalnum() else "_" for c in f"{name}_{key}").upper()
    return f"MCP_{safe}"


def install_from_registry(entry_id: str, values: dict | None = None) -> Connector:
    """Installe un MCP du registre distant en résolvant son manifest côté bridge.

    - remote / app locale (http/sse) : ajout custom (+ OAuth pour le remote).
    - stdio : construit command/args/env depuis le manifest. Les valeurs saisies vont dans
      ``~/.hermes/.env`` (référencées par ``${VAR}`` dans la config, jamais en clair) ; Hermes
      les interpole au lancement. Les champs ``array`` / chemins vont dans ``args``.

    Lève ``ValueError`` si l'id est inconnu/non installable ou si un champ requis manque,
    ``NameConflict`` si un connecteur du même nom existe déjà.
    """
    values = values or {}
    entry = mcp_registry.find(entry_id)
    if entry is None or not entry.get("installable"):
        raise ValueError(f"connecteur introuvable ou non installable: {entry_id}")
    name = entry["id"]
    kind = entry["install_kind"]

    if kind in ("remote", "local_app"):
        auth = "oauth" if kind == "remote" else "none"
        return add_custom(name, entry.get("transport", "http"), url=entry.get("url"), auth_type=auth)

    # stdio : on assemble la config et on stocke les secrets dans .env.
    command = entry.get("command")
    if not command:
        raise ValueError(f"manifest stdio incomplet pour {name}")
    # Défense en profondeur (finding HAUTE #3) : re-vérifier l'allowlist ici, pas seulement au
    # moment du catalogue (``mcp_registry._install_kind``) — un ``entry`` obtenu autrement
    # (cache périmé, appelant qui construit son propre dict) ne doit jamais pouvoir faire
    # persister une commande hors liste dans ``config.yaml``, qui serait ensuite exécutée par
    # Hermes en subprocess.
    if not mcp_registry._is_safe_stdio_command(command):
        raise ValueError(f"commande stdio hors liste autorisée pour {name}: {command!r}")
    args = list(entry.get("args") or [])
    if not mcp_registry._is_safe_stdio_args(args):
        raise ValueError(f"arguments stdio non sûrs pour {name}")
    env: dict[str, str] = {}
    for field in entry.get("config_fields", []):
        key = field["key"]
        target = field.get("target", "env")
        val = values.get(key)
        if field.get("required") and (val is None or val == "" or val == []):
            raise ValueError(f"champ requis manquant: {key}")
        if val in (None, "", []):
            continue
        if target == "args_list":
            args.extend(str(x) for x in (val if isinstance(val, list) else [val]))
        elif target == "arg_value":
            args.append(str(val))
        else:  # env : secret dans .env, référence ${VAR} dans la config (FR-011)
            var = _registry_env_var(name, key)
            hermes_adapter._set_env_value(var, str(val))
            env[key] = f"${{{var}}}"
    if not mcp_registry._is_safe_stdio_args(args):
        raise ValueError(f"arguments stdio non sûrs pour {name} (champs de config)")
    # Traçabilité (finding HAUTE #3, mesure optionnelle demandée) : un humain doit pouvoir
    # relire, dans les logs du bridge, exactement quelle commande a été persistée pour ce
    # connecteur — utile en cas de doute a posteriori sur un manifest du registre distant.
    _logger.info(
        "installation MCP stdio depuis le registre distant : name=%r command=%r args=%r",
        name, command, args,
    )
    return add_custom(name, "stdio", command=command, args=args, env=env or None)


def set_key(connector_id: str, value: str) -> str:
    """Enregistre la clé API d'un connecteur (``MCP_<NAME>_API_KEY`` dans ~/.hermes/.env).

    La valeur n'est jamais renvoyée ni journalisée (FR-011). Retourne le nom de la variable.
    """
    env_key = _env_key_for(connector_id)
    hermes_adapter._set_env_value(env_key, value)
    return env_key


def install_from_catalog(name: str) -> None:
    """Lance ``hermes mcp install <name>`` en arrière-plan (git clone + bootstrap + config).

    Asynchrone : suivre via ``install_status``. La clé API éventuelle doit être posée AVANT
    (via ``set_key``) pour que l'installation non-interactive ne la redemande pas.
    """
    hermes_adapter._start_bg_run(
        f"mcp_install_{name}", [hermes_adapter.HERMES_BIN, "mcp", "install", name]
    )


def install_status(name: str) -> dict:
    return hermes_adapter._bg_status(f"mcp_install_{name}")


_AUTH_URL_RE = re.compile(r"https?://[^\s\"']+")


def start_oauth(name: str) -> None:
    """Démarre ``hermes mcp login <name>`` (navigateur ouvert sur l'hôte) en arrière-plan."""
    hermes_adapter._start_bg_run(
        f"mcp_oauth_{name}", [hermes_adapter.HERMES_BIN, "mcp", "login", name]
    )


def oauth_status(name: str) -> dict:
    """État du flux OAuth + URL d'autorisation extraite du log (fallback copier-coller, research D4)."""
    status = hermes_adapter._bg_status(f"mcp_oauth_{name}")
    match = _AUTH_URL_RE.search(status.get("log", ""))
    status["auth_url"] = match.group(0) if match else None
    return status


# --- US4 : activer/désactiver, tester, supprimer -----------------------------

_SET_ENABLED_SCRIPT = """
import json
from hermes_cli.mcp_config import _get_mcp_servers, _save_mcp_server
name = {name}
enabled = {enabled}
servers = _get_mcp_servers()
if name not in servers:
    print(json.dumps({{"found": False}}))
else:
    cfg = dict(servers[name])
    cfg["enabled"] = enabled
    ok = _save_mcp_server(name, cfg)
    print(json.dumps({{"found": True, "ok": bool(ok)}}))
"""

_PROBE_SCRIPT = """
import json
from hermes_cli.mcp_config import _get_mcp_servers, _probe_single_server
name = {name}
servers = _get_mcp_servers()
if name not in servers:
    print(json.dumps({{"ok": False, "reason": "connecteur inconnu"}}))
else:
    try:
        tools = _probe_single_server(name, servers[name], connect_timeout=20)
        print(json.dumps({{"ok": True, "tools_count": len(tools)}}))
    except Exception as exc:
        print(json.dumps({{"ok": False, "reason": str(exc)[:200]}}))
"""

_REMOVE_SCRIPT = """
import json
from hermes_cli.mcp_config import _remove_mcp_server
name = {name}
removed = _remove_mcp_server(name)
print(json.dumps({{"removed": bool(removed)}}))
"""


def set_enabled(name: str, enabled: bool, hermes_home=None) -> bool:
    """Active/désactive un connecteur (champ ``enabled`` de config.yaml du profil). False si inconnu."""
    script = _SET_ENABLED_SCRIPT.format(name=json.dumps(name), enabled=json.dumps(bool(enabled)))
    result = _mcp_introspect(script, hermes_home=hermes_home)
    return bool(result.get("found"))


def test_connection(name: str) -> dict:
    """Probe réelle du connecteur (connexion + liste des outils). Timeout borné."""
    script = _PROBE_SCRIPT.format(name=json.dumps(name))
    return _mcp_introspect(script, timeout=40)


def _purge_oauth_tokens(name: str) -> None:
    """Supprime les fichiers de token OAuth du connecteur retiré (présence seule auparavant).

    Défense en profondeur (finding HAUTE #1) : un ``name`` contenant un séparateur de chemin
    ou une référence relative ne doit jamais pouvoir faire sortir la suppression de
    ``mcp-tokens/`` — même si aucun appelant connu ne peut aujourd'hui fournir un tel nom
    (le charset est déjà validé à la création par ``add_custom``/le registre distant).
    """
    if not _SAFE_CONNECTOR_NAME_RE.match(name or ""):
        _logger.warning("nom de connecteur invalide ignoré par _purge_oauth_tokens: %r", name)
        return
    tokens_dir = hermes_adapter.HERMES_HOME / "mcp-tokens"
    for suffix in (".json", ".client.json", ".meta.json"):
        f = tokens_dir / f"{name}{suffix}"
        if f.exists():
            f.unlink()


def remove_connector(name: str) -> bool:
    """Supprime un connecteur (entrée config.yaml + tokens). False si introuvable.

    Action initiée par l'admin (confirmation UI, FR-010) ; ne retire que ce connecteur.
    """
    script = _REMOVE_SCRIPT.format(name=json.dumps(name))
    result = _mcp_introspect(script)
    removed = bool(result.get("removed"))
    if removed:
        _purge_oauth_tokens(name)
    return removed


# --- US5 : connecteur custom -------------------------------------------------

_SAVE_SCRIPT = """
import json
from hermes_cli.mcp_config import _save_mcp_server
name = {name}
cfg = json.loads({cfg})
ok = _save_mcp_server(name, cfg)
print(json.dumps({{"ok": bool(ok)}}))
"""


class NameConflict(ValueError):
    """Un connecteur du même nom existe déjà (FR-017)."""


def add_custom(
    name: str,
    transport: str,
    *,
    url: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    auth_type: str = "none",
) -> Connector:
    """Ajoute un connecteur MCP custom (http/stdio).

    Lève ``NameConflict`` si le nom existe (409), ``ValueError`` si champs invalides ou
    config rejetée par la validation Hermes (422).
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("nom requis")
    if not _SAFE_CONNECTOR_NAME_RE.match(name):
        raise ValueError(
            "nom de connecteur invalide : lettres, chiffres, tiret ou underscore uniquement"
        )
    if name in _load_mcp_servers():
        raise NameConflict(f"un connecteur nommé « {name} » existe déjà")

    transport = (transport or "").lower()
    cfg: dict = {"enabled": True}
    if transport in ("http", "sse"):
        if not url:
            raise ValueError("URL requise pour un connecteur HTTP")
        cfg["url"] = url
        if transport == "sse":
            cfg["transport"] = "sse"
        if auth_type == "key":
            cfg["headers"] = {"Authorization": f"Bearer ${{{_env_key_for(name)}}}"}
    elif transport == "stdio":
        if not command:
            raise ValueError("commande requise pour un connecteur stdio")
        cfg["command"] = command
        if args:
            cfg["args"] = args
        if env:
            cfg["env"] = env
    else:
        raise ValueError(f"transport inconnu: {transport}")

    if auth_type == "oauth":
        cfg["auth"] = "oauth"

    script = _SAVE_SCRIPT.format(name=json.dumps(name), cfg=json.dumps(json.dumps(cfg)))
    result = _mcp_introspect(script)
    if not result.get("ok"):
        raise ValueError("configuration rejetée (validation de sécurité)")

    present_keys = hermes_adapter._present_env_keys()
    return _to_connector(name, cfg, present_keys)
