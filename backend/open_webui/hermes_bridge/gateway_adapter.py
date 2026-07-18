"""Adapter Gateway — supervision du gateway Hermes + plateformes de messagerie.

Pilote, depuis le bridge, la page « Gateway » d'Agent OS (portage de la page Gateway de
Hermes Desktop). Trois domaines :

- ÉTAT du gateway : tourne ou non (PID file), port de l'API server, présence de la clé API.
- CLÉ API serveur : ``API_SERVER_KEY`` dans ``~/.hermes/.env`` (présence + (re)génération).
- PLATEFORMES de messagerie : Telegram/Discord/Slack/WhatsApp/Signal — tokens (``~/.hermes/.env``),
  activation (``config.yaml`` ``platforms.<id>.enabled``), état (configuré/activé), test « soft ».

Source de vérité = Hermes, pilotée par introspection Python (cf. ``hermes_adapter.introspect``).
Le CATALOGUE des plateformes (clés d'env, libellés) vit ici, comme Hermes Desktop le maintient
de son côté : Hermes connaît les plateformes mais n'expose pas un schéma de formulaire prêt à l'emploi.

Garde-fou : le start/stop du gateway est délégué à la supervision (launchd/systemd). On n'expose
que ``restart`` (le vrai besoin après un changement de config) — jamais d'arrêt sauvage.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

from . import hermes_adapter
from .ttl_cache import TTLCache
from .models import (
    DiscordApplyResult,
    DiscordBotInfo,
    EmailApplyResult,
    GatewayStatus,
    MessagingActionResult,
    MessagingEnvVar,
    MessagingPlatform,
    MessagingPlatformsResponse,
    MessagingUser,
    MessagingUsersResponse,
    SlackApplyResult,
    SlackBotInfo,
    TelegramBotInfo,
    TelegramPairingApplyResult,
    TelegramPairingStart,
    TelegramPairingStatus,
)

# --- CATALOGUE des plateformes grand public ----------------------------------
# Chaque entrée décrit le formulaire de configuration (clés ~/.hermes/.env).
# `required` : clé indispensable pour que la plateforme soit « configurée ».
# `password` : champ masqué dans l'UI. `advanced` : repliable (réglages fins).
_CATALOG: list[dict] = [
    {
        "id": "telegram",
        "name": "Telegram",
        "emoji": "📱",
        "description": "Branchez un bot Telegram : vos agents répondent dans Telegram.",
        "docs_url": "https://core.telegram.org/bots#how-do-i-create-a-bot",
        "recommended": True,  # le plus simple à brancher (1 clic, sans rien installer)
        "env_vars": [
            {"key": "TELEGRAM_BOT_TOKEN", "prompt": "Token du bot", "description": "Obtenu via @BotFather.", "required": True, "is_password": True, "advanced": False},
            {"key": "TELEGRAM_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "IDs séparés par des virgules (vide = tous).", "required": False, "is_password": False, "advanced": True},
        ],
    },
    {
        "id": "discord",
        "name": "Discord",
        "emoji": "💬",
        "description": "Branchez un bot Discord : vos agents répondent dans vos serveurs.",
        "docs_url": "https://discord.com/developers/applications",
        "env_vars": [
            {"key": "DISCORD_BOT_TOKEN", "prompt": "Token du bot", "description": "Onglet Bot de votre application Discord.", "required": True, "is_password": True, "advanced": False},
            {"key": "DISCORD_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "IDs séparés par des virgules (vide = tous).", "required": False, "is_password": False, "advanced": True},
        ],
    },
    {
        "id": "slack",
        "name": "Slack",
        "emoji": "💼",
        "description": "Branchez une app Slack : vos agents répondent dans vos canaux.",
        "docs_url": "https://api.slack.com/apps",
        "env_vars": [
            {"key": "SLACK_BOT_TOKEN", "prompt": "Bot token (xoxb-…)", "description": "OAuth & Permissions de votre app Slack.", "required": True, "is_password": True, "advanced": False},
            {"key": "SLACK_APP_TOKEN", "prompt": "App token (xapp-…)", "description": "Socket Mode de votre app Slack.", "required": True, "is_password": True, "advanced": False},
            {"key": "SLACK_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "IDs séparés par des virgules. Vide = tout votre workspace peut parler au bot ; renseignez des IDs pour restreindre.", "required": False, "is_password": False, "advanced": True},
        ],
    },
    {
        "id": "whatsapp_cloud",
        "name": "WhatsApp Business",
        "emoji": "📱",
        "description": "Branchez l'API WhatsApp Cloud (Meta) : vos agents répondent sur WhatsApp.",
        "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api",
        # Noms de clés alignés sur ce que lit le moteur Hermes
        # (_refs/hermes-agent/gateway/platforms/whatsapp_cloud.py & gateway/config.py).
        # NE PAS renommer sans mettre à jour le moteur ET tests/test_gateway_whatsapp.py.
        "env_vars": [
            {"key": "WHATSAPP_CLOUD_PHONE_NUMBER_ID", "prompt": "Phone Number ID", "description": "ID interne Meta du numéro (15-17 chiffres) — PAS le numéro lui-même. API Setup → sous « From ».", "required": True, "is_password": False, "advanced": False},
            {"key": "WHATSAPP_CLOUD_ACCESS_TOKEN", "prompt": "Access token", "description": "Token d'accès Meta (commence par « EAA »). API Setup → « Generate access token ».", "required": True, "is_password": True, "advanced": False},
            {"key": "WHATSAPP_CLOUD_VERIFY_TOKEN", "prompt": "Webhook verify token", "description": "Jeton de vérification du webhook, à coller dans Meta → Configuration.", "required": True, "is_password": True, "advanced": False},
            {"key": "WHATSAPP_CLOUD_APP_SECRET", "prompt": "App secret", "description": "Settings → Basic → « App secret » (32 caractères hex). Obligatoire : sans lui, les messages entrants sont refusés.", "required": True, "is_password": True, "advanced": False},
            {"key": "WHATSAPP_CLOUD_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "Numéros séparés par des virgules (vide = tous).", "required": False, "is_password": False, "advanced": True},
        ],
        # Grisé côté UI tant que le parcours Meta n'est pas mis en place (cf. Messagerie.md).
        "available": False,
        "unavailable_reason": "Nécessite une configuration Meta (compte Business + numéro dédié). Bientôt disponible.",
    },
    {
        "id": "signal",
        "name": "Signal",
        "emoji": "📡",
        "description": "Branchez Signal (via signal-cli REST API) : vos agents répondent sur Signal.",
        "docs_url": "https://github.com/bbernhard/signal-cli-rest-api",
        # Réservé aux techniciens : nécessite d'auto-héberger un serveur signal-cli REST.
        "expert_only": True,
        "env_vars": [
            {"key": "SIGNAL_ACCOUNT", "prompt": "Numéro du compte", "description": "Numéro au format international (+33…).", "required": True, "is_password": False, "advanced": False},
            {"key": "SIGNAL_HTTP_URL", "prompt": "URL de l'API REST", "description": "Endpoint signal-cli REST (ex. http://localhost:8080).", "required": True, "is_password": False, "advanced": False},
            {"key": "SIGNAL_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "Numéros séparés par des virgules (vide = tous).", "required": False, "is_password": False, "advanced": True},
        ],
    },
    {
        "id": "email",
        "name": "Email",
        "emoji": "📧",
        "description": "Branchez une boîte mail (IMAP/SMTP) : vos agents répondent par e-mail.",
        "docs_url": "https://support.google.com/mail/answer/185833",
        "env_vars": [
            {"key": "EMAIL_ADDRESS", "prompt": "Adresse e-mail", "description": "L'adresse de la boîte (ex. agent@exemple.com).", "required": True, "is_password": False, "advanced": False},
            {"key": "EMAIL_PASSWORD", "prompt": "Mot de passe", "description": "Mot de passe ou « app password » (Gmail/Outlook).", "required": True, "is_password": True, "advanced": False},
            {"key": "EMAIL_IMAP_HOST", "prompt": "Serveur IMAP", "description": "Réception (ex. imap.gmail.com).", "required": True, "is_password": False, "advanced": False},
            {"key": "EMAIL_SMTP_HOST", "prompt": "Serveur SMTP", "description": "Envoi (ex. smtp.gmail.com).", "required": True, "is_password": False, "advanced": False},
        ],
    },
    {
        "id": "sms",
        "name": "SMS (Twilio)",
        "emoji": "📲",
        "description": "Envoyez et recevez des SMS via Twilio : vos agents répondent par texto.",
        "docs_url": "https://www.twilio.com/docs/messaging",
        "env_vars": [
            {"key": "TWILIO_ACCOUNT_SID", "prompt": "Identifiant du compte", "description": "Console Twilio → page d'accueil, encart « Account Info ». Commence par « AC ».", "required": True, "is_password": False, "advanced": False},
            {"key": "TWILIO_AUTH_TOKEN", "prompt": "Jeton d'authentification", "description": "Console Twilio → « Account Info », juste sous l'identifiant. Cliquez « Show » pour le révéler.", "required": True, "is_password": True, "advanced": False},
            {"key": "TWILIO_PHONE_NUMBER", "prompt": "Numéro d'envoi", "description": "Votre numéro Twilio (à acheter dans Phone Numbers), au format international (+1…).", "required": True, "is_password": False, "advanced": False},
        ],
    },
    {
        "id": "bluebubbles",
        "name": "BlueBubbles (iMessage)",
        "emoji": "🍏",
        "description": "Branchez iMessage via un serveur BlueBubbles : vos agents répondent sur iMessage.",
        "docs_url": "https://bluebubbles.app/install/",
        # Réservé aux techniciens : nécessite un Mac dédié allumé en permanence + BlueBubbles.
        "expert_only": True,
        "env_vars": [
            {"key": "BLUEBUBBLES_SERVER_URL", "prompt": "URL du serveur", "description": "URL de votre serveur BlueBubbles.", "required": True, "is_password": False, "advanced": False},
            {"key": "BLUEBUBBLES_PASSWORD", "prompt": "Mot de passe du serveur", "description": "Mot de passe défini dans BlueBubbles.", "required": True, "is_password": True, "advanced": False},
            {"key": "BLUEBUBBLES_ALLOWED_USERS", "prompt": "Utilisateurs autorisés", "description": "Numéros/contacts séparés par des virgules (vide = tous).", "required": False, "is_password": False, "advanced": True},
        ],
    },
]

_CATALOG_BY_ID = {p["id"]: p for p in _CATALOG}


def _all_keys() -> list[str]:
    return [v["key"] for p in _CATALOG for v in p["env_vars"]]


# --- ÉTAT du gateway ----------------------------------------------------------

_STATUS_SCRIPT = """
import json

running = False
pid = None
try:
    from gateway.status import get_running_pid
    pid = get_running_pid()
    running = pid is not None
except Exception:
    pass

def _env(key, default=None):
    try:
        from hermes_cli.config import get_env_value
        return get_env_value(key)
    except Exception:
        return default

port = 8645
try:
    raw = _env("API_SERVER_PORT")
    if raw:
        port = int(raw)
except Exception:
    pass

api_key_present = bool(_env("API_SERVER_KEY"))

print(json.dumps({"running": bool(running), "pid": pid, "port": port, "api_key_present": api_key_present}))
"""


# Cache TTL COURT (cf. audit perf Haute #1) : le front poll gateway_status()/list_platforms()
# toutes les 10 s tant que l'onglet Messagerie reste ouvert (``GatewayList.svelte``), et
# chaque appel relançait jusque-là un subprocess Hermes complet (introspection Python :
# interpréteur + imports hermes_cli/gateway.status) SANS aucune mémoïsation — coût continu,
# sans borne de durée. Le TTL est COURT : il absorbe le poll rapproché, jamais un vrai
# changement d'état (connexion/déconnexion d'une plateforme, redémarrage du gateway).
#
# INVARIANT D'HONNÊTETÉ (prime sur la perf) : toute action qui change l'état d'une
# plateforme ou du gateway (``update_platform``, ``generate_api_key``, ``restart_gateway``,
# les parcours ``*_apply``/``disconnect_platform``) DOIT invalider ces deux caches avant de
# rendre la main, via ``_invalidate_gateway_cache()``.
_GATEWAY_STATUS_CACHE_TTL_S = float(os.environ.get("GATEWAY_STATUS_CACHE_TTL_S", "5"))
_GATEWAY_STATUS_CACHE = TTLCache(_GATEWAY_STATUS_CACHE_TTL_S)
_LIST_PLATFORMS_CACHE_TTL_S = float(os.environ.get("GATEWAY_PLATFORMS_CACHE_TTL_S", "5"))
_LIST_PLATFORMS_CACHE = TTLCache(_LIST_PLATFORMS_CACHE_TTL_S)


def _invalidate_gateway_cache() -> None:
    """Vide les caches ``gateway_status()``/``list_platforms()``.

    À appeler après TOUTE action de connexion/déconnexion/activation d'une plateforme, ou
    après un redémarrage du gateway (cf. docstring des caches ci-dessus) — jamais servir un
    état périmé après une action utilisateur explicite.
    """
    _GATEWAY_STATUS_CACHE.clear()
    _LIST_PLATFORMS_CACHE.clear()


def gateway_status() -> GatewayStatus:
    """État du gateway : tourne ou non (PID), port de l'API server, présence de la clé API.

    Caché (TTL court, cf. ``_GATEWAY_STATUS_CACHE``) : le poll 10 s du front partage le
    résultat au lieu de relancer un subprocess Hermes à chaque tick."""
    cached = _GATEWAY_STATUS_CACHE.fresh()
    if cached is not None:
        return cached
    raw = hermes_adapter.introspect(_STATUS_SCRIPT)
    status = GatewayStatus(
        running=bool(raw.get("running", False)),
        port=int(raw.get("port") or 8645),
        api_key_present=bool(raw.get("api_key_present", False)),
    )
    _GATEWAY_STATUS_CACHE.store(status)
    return status


# --- PLATEFORMES : lecture de l'état -----------------------------------------
# Le script reçoit le catalogue (clés par plateforme) et renvoie, par clé :
# présence (is_set) + valeur masquée (redacted) — jamais la valeur en clair.
# Plus, par plateforme : enabled (config.yaml). Plus l'état global du gateway.

_PLATFORMS_SCRIPT = """
import json

CATALOG = json.loads({catalog})

def _env(key):
    try:
        from hermes_cli.config import get_env_value
        return get_env_value(key)
    except Exception:
        return None

def _redact(val):
    if not val:
        return ""
    s = str(val)
    if len(s) <= 6:
        return "••••"
    return s[:3] + "••••" + s[-2:]

# enabled par plateforme : config.yaml platforms.<id>.enabled
enabled_map = {{}}
try:
    from hermes_cli.config import read_raw_config
    cfg = read_raw_config() or {{}}
    plats = cfg.get("platforms", {{}}) or {{}}
    for pid, pconf in plats.items():
        if isinstance(pconf, dict):
            enabled_map[pid] = bool(pconf.get("enabled", False))
except Exception:
    pass

running = False
try:
    from gateway.status import get_running_pid
    running = get_running_pid() is not None
except Exception:
    pass

out = []
for p in CATALOG:
    fields = []
    required_set = True
    any_set = False
    for v in p["env_vars"]:
        val = _env(v["key"])
        is_set = bool(val)
        if is_set:
            any_set = True
        if v.get("required") and not is_set:
            required_set = False
        fields.append({{
            "key": v["key"], "prompt": v["prompt"], "description": v.get("description", ""),
            "required": bool(v.get("required", False)), "is_password": bool(v.get("is_password", False)),
            "advanced": bool(v.get("advanced", False)), "is_set": is_set,
            # On ne masque QUE les secrets (mots de passe, tokens). L'adresse e-mail, les
            # serveurs, les numéros, etc. ne sont pas secrets → affichés en clair (UX).
            "redacted_value": (_redact(val) if v.get("is_password") else (val or "")),
        }})
    configured = bool(required_set and any_set)
    enabled = bool(enabled_map.get(p["id"], False))
    out.append({{
        "id": p["id"], "name": p["name"], "emoji": p.get("emoji", ""),
        "description": p.get("description", ""), "docs_url": p.get("docs_url", ""),
        "configured": configured, "enabled": enabled, "env_vars": fields,
    }})

print(json.dumps({{"platforms": out, "gateway_running": bool(running)}}))
"""


def _platform_state(configured: bool, enabled: bool, gateway_running: bool) -> str:
    """Libellé d'état dérivé (aligné sur Hermes Desktop)."""
    if not enabled:
        return "disabled"
    if not configured:
        return "needs_setup"
    if not gateway_running:
        return "ready"
    return "connected"


def list_platforms() -> MessagingPlatformsResponse:
    """Liste les plateformes du catalogue avec leur état (configuré/activé/connecté).

    Caché (TTL court, cf. ``_LIST_PLATFORMS_CACHE``) : même rationale que ``gateway_status``."""
    cached = _LIST_PLATFORMS_CACHE.fresh()
    if cached is not None:
        return cached
    raw = hermes_adapter.introspect(_PLATFORMS_SCRIPT.format(catalog=json.dumps(json.dumps(_CATALOG))))
    gateway_running = bool(raw.get("gateway_running", False))
    platforms = []
    for it in raw.get("platforms", []):
        env_vars = [
            MessagingEnvVar(
                key=f["key"], prompt=f["prompt"], description=f.get("description", ""),
                required=bool(f.get("required", False)), is_password=bool(f.get("is_password", False)),
                advanced=bool(f.get("advanced", False)), is_set=bool(f.get("is_set", False)),
                redacted_value=f.get("redacted_value", ""),
            )
            for f in it.get("env_vars", [])
        ]
        configured = bool(it.get("configured", False))
        enabled = bool(it.get("enabled", False))
        # ``available`` / ``unavailable_reason`` viennent du catalogue statique local
        # (pas de l'introspection d'état), source unique de vérité.
        meta = _CATALOG_BY_ID.get(it["id"], {})
        platforms.append(
            MessagingPlatform(
                id=it["id"], name=it["name"], emoji=it.get("emoji", ""),
                description=it.get("description", ""), docs_url=it.get("docs_url", ""),
                configured=configured, enabled=enabled,
                state=_platform_state(configured, enabled, gateway_running),
                env_vars=env_vars,
                available=bool(meta.get("available", True)),
                unavailable_reason=meta.get("unavailable_reason", ""),
                recommended=bool(meta.get("recommended", False)),
                expert_only=bool(meta.get("expert_only", False)),
            )
        )
    resp = MessagingPlatformsResponse(platforms=platforms, gateway_running=gateway_running)
    _LIST_PLATFORMS_CACHE.store(resp)
    return resp


# --- PLATEFORMES : écriture (tokens + activation) ----------------------------

_UPDATE_SCRIPT = """
import json

env = json.loads({env})
clear_env = json.loads({clear_env})
enabled = json.loads({enabled})
platform_id = {platform_id}

errors = []

# 1) tokens (~/.hermes/.env)
try:
    from hermes_cli.config import save_env_value
    for k, v in env.items():
        save_env_value(k, v)
    for k in clear_env:
        save_env_value(k, "")
except Exception as exc:
    errors.append("env: " + str(exc)[:150])

# 2) activation (config.yaml platforms.<id>.enabled)
if enabled is not None:
    try:
        from hermes_cli.config import write_platform_config_field
        write_platform_config_field(platform_id, "enabled", bool(enabled))
    except Exception as exc:
        errors.append("enable: " + str(exc)[:150])

print(json.dumps({{"ok": not errors, "errors": errors}}))
"""


def _reconcile_slack_allow_all(
    platform_id: str,
    safe_env: dict[str, str],
    safe_clear: list[str] | None = None,
) -> dict[str, str]:
    """Réconcilie SLACK_ALLOW_ALL_USERS avec l'allowlist enregistrée.

    Côté moteur, le flag allow-all prime sur SLACK_ALLOWED_USERS : sans ça,
    « Restreindre l'accès » n'aurait aucun effet (le client restreindrait dans le
    vide). Une allowlist non vide coupe donc l'allow-all ; une allowlist vidée le
    réactive, pour que « vide = tout le workspace » reste vrai. Clé dérivée (hors
    catalogue), posée ici et jamais exposée à l'utilisateur. Renvoie un nouveau
    dict (pas de mutation de l'entrée).

    ``safe_clear`` (effacement via ``clear_env``) est traité comme une valeur
    vide au même titre que ``env={"SLACK_ALLOWED_USERS": ""}`` : les deux
    mécanismes produisent le même effet final côté ``.env`` (``save_env_value``)
    et doivent donc déclencher la même réconciliation — sinon vider l'allowlist
    via ``clear_env`` laisse ``SLACK_ALLOW_ALL_USERS`` bloqué à ``false`` et rend
    le bot muet en silence (allowlist vide ET allow-all désactivé).
    """
    key = "SLACK_ALLOWED_USERS"
    cleared = key in (safe_clear or [])
    if platform_id != "slack" or (key not in safe_env and not cleared):
        return safe_env
    value = safe_env[key] if key in safe_env else ""
    flag = "false" if value.strip() else "true"
    return {**safe_env, "SLACK_ALLOW_ALL_USERS": flag}


def update_platform(
    platform_id: str,
    env: dict[str, str] | None = None,
    clear_env: list[str] | None = None,
    enabled: bool | None = None,
) -> dict:
    """Met à jour une plateforme : tokens (.env) et/ou activation (config.yaml).

    Renvoie ``{"ok": bool, "errors": [...]}``. ``platform_id`` inconnu => KeyError.
    """
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    # on n'accepte que les clés du catalogue (garde-fou anti-injection de var arbitraire)
    allowed = {v["key"] for v in _CATALOG_BY_ID[platform_id]["env_vars"]}
    safe_env = {k: v for k, v in (env or {}).items() if k in allowed}
    safe_clear = [k for k in (clear_env or []) if k in allowed]
    safe_env = _reconcile_slack_allow_all(platform_id, safe_env, safe_clear)
    script = _UPDATE_SCRIPT.format(
        env=json.dumps(json.dumps(safe_env)),
        clear_env=json.dumps(json.dumps(safe_clear)),
        enabled=json.dumps(json.dumps(enabled)),
        platform_id=json.dumps(platform_id),
    )
    res = hermes_adapter.introspect(script, timeout=60)
    # Tokens et/ou activation viennent (potentiellement) de changer côté .env/config.yaml —
    # jamais servir l'ancien état au prochain poll (cf. invariant d'honnêteté du cache).
    _invalidate_gateway_cache()
    return res


def test_platform(platform_id: str) -> dict:
    """Test « soft » : vérifie la présence des clés requises (pas d'appel réseau).

    Hermes n'expose pas de test de connectivité unifié ; un vrai test se fait au
    démarrage de l'adaptateur. On valide donc la complétude de la config.
    """
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    resp = list_platforms()
    platform = next((p for p in resp.platforms if p.id == platform_id), None)
    if platform is None:
        raise KeyError(platform_id)
    missing = [v.key for v in platform.env_vars if v.required and not v.is_set]
    if missing:
        return {"ok": False, "message": "Clés manquantes : " + ", ".join(missing)}
    if not platform.enabled:
        return {"ok": False, "message": "Plateforme configurée mais désactivée (active le toggle)."}
    if not resp.gateway_running:
        return {"ok": False, "message": "Configuration complète. Redémarre le gateway pour connecter."}
    return {"ok": True, "message": "Configuration complète et plateforme active."}


# --- CLÉ API serveur ----------------------------------------------------------

_GENERATE_KEY_SCRIPT = """
import json, secrets
try:
    from hermes_cli.config import save_env_value
    key = "owui-" + secrets.token_hex(24)
    save_env_value("API_SERVER_KEY", key)
    save_env_value("API_SERVER_ENABLED", "true")
    print(json.dumps({"ok": True}))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)[:200]}))
"""


def generate_api_key() -> dict:
    """(Re)génère ``API_SERVER_KEY`` dans ``~/.hermes/.env``. Renvoie ``{"ok": bool}``."""
    res = hermes_adapter.introspect(_GENERATE_KEY_SCRIPT, timeout=30)
    # api_key_present (gateway_status) vient potentiellement de changer.
    _invalidate_gateway_cache()
    return res


# --- REDÉMARRAGE du gateway ---------------------------------------------------


def restart_gateway() -> dict:
    """Redémarre le gateway via la CLI Hermes (``hermes gateway restart``).

    Start/stop sont délégués à la supervision (launchd/systemd) ; seul restart est exposé,
    car c'est le besoin réel après un changement de config plateforme.
    """
    import subprocess

    try:
        res = subprocess.run(
            [hermes_adapter.HERMES_BIN, "gateway", "restart"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise hermes_adapter.HermesUnavailable(str(exc)) from exc
    # Un redémarrage (réussi OU en échec partiel) peut avoir changé l'état "running" —
    # invalider systématiquement, jamais servir l'état pré-restart au prochain poll.
    _invalidate_gateway_cache()
    if res.returncode != 0:
        return {"ok": False, "error": (res.stderr or res.stdout).strip()[:300]}
    return {"ok": True}


def _safe_restart_gateway() -> dict:
    """``restart_gateway()`` sans jamais lever : à tous ses points d'appel, la
    config (token, activation, auto-approbation…) a déjà été écrite AVANT ce
    redémarrage. Si ``restart_gateway`` lève ``HermesUnavailable`` (binaire
    introuvable, timeout), ce succès partiel réel ne doit pas être maquillé en
    exception qui remonte en 503 — on renvoie plutôt ``{"ok": False, "error":
    ...}``, cohérent avec le cas déjà géré où la CLI répond par un code non nul.
    """
    try:
        return restart_gateway()
    except hermes_adapter.HermesUnavailable as exc:
        return {"ok": False, "error": str(exc)[:300]}


# --- ONBOARDING TELEGRAM « managed bot » (parcours QR 1-clic) ------------------
# Le client scanne un QR (feature Telegram Managed Bots via le service Nous), crée
# son bot sans @BotFather, et le bridge enchaîne tout : token → activation →
# auto-approbation du propriétaire → home channel → redémarrage. Trois étapes :
#   start  → crée le pairing, renvoie le QR/lien (le secret poll_token reste ici)
#   poll   → interroge le service jusqu'à obtenir le token + owner_user_id
#   apply  → branche + active + auto-approuve + home channel + restart
#
# ``introspect`` étant sans état (subprocess éphémère), on garde le poll_token et le
# token du bot côté process bridge, jamais renvoyés à l'UI.

_PAIRINGS: dict[str, dict] = {}
_PAIRINGS_LOCK = threading.Lock()


def _pairing_expired(expires_at: str | None, now: datetime) -> bool:
    """True si ``expires_at`` (ISO 8601, ex. ``2026-07-08T06:25:00Z``) est dépassé.

    Format absent/inconnu => jamais expiré : on ne purge jamais par erreur une
    entrée qu'on ne sait pas dater avec certitude.
    """
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp <= now


def _purge_expired_pairings() -> None:
    """Purge les pairings Telegram dont l'expiration est dépassée.

    ``_PAIRINGS`` est un dict module-level sur un process long-lived (supervision
    launchd/systemd) : un pairing démarré puis simplement abandonné (modale
    fermée sans « Annuler ») restait sinon en mémoire indéfiniment — fuite non
    bornée. Appelée à chaque ``start``/``poll`` plutôt qu'un thread de purge dédié
    (coût négligeable, pas de tâche de fond supplémentaire à superviser).
    """
    now = datetime.now(timezone.utc)
    with _PAIRINGS_LOCK:
        expired_ids = [
            pid for pid, slot in _PAIRINGS.items() if _pairing_expired(slot.get("expires_at"), now)
        ]
        for pid in expired_ids:
            _PAIRINGS.pop(pid, None)


_PAIRING_START_SCRIPT = """
import json
try:
    from hermes_cli.telegram_managed_bot import create_pairing
    p = create_pairing(bot_name={bot_name})
    if p is None:
        print(json.dumps({{"ok": False, "error": "service de pairing injoignable"}}))
    else:
        print(json.dumps({{
            "ok": True,
            "pairing_id": p.pairing_id,
            "poll_token": p.poll_token,
            "suggested_username": p.suggested_username,
            "deep_link": p.deep_link,
            "qr_payload": p.qr_payload,
            "expires_at": p.expires_at,
        }}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)[:200]}}))
"""


def telegram_pairing_start(bot_name: str = "LunarIA") -> TelegramPairingStart:
    """Démarre un pairing Telegram « managed bot ». Renvoie de quoi afficher le QR.

    Le ``poll_token`` (bearer secret) est conservé côté bridge, jamais exposé.
    """
    _purge_expired_pairings()
    script = _PAIRING_START_SCRIPT.format(bot_name=json.dumps(bot_name))
    res = hermes_adapter.introspect(script, timeout=30)
    if not res.get("ok"):
        raise hermes_adapter.HermesUnavailable(res.get("error") or "pairing indisponible")
    with _PAIRINGS_LOCK:
        _PAIRINGS[res["pairing_id"]] = {
            "poll_token": res["poll_token"],
            "expires_at": res.get("expires_at"),
        }
    return TelegramPairingStart(
        pairing_id=res["pairing_id"],
        suggested_username=res.get("suggested_username", ""),
        deep_link=res["deep_link"],
        qr_payload=res.get("qr_payload") or res["deep_link"],
        expires_at=res.get("expires_at"),
    )


_PAIRING_POLL_SCRIPT = """
import json
try:
    from hermes_cli.telegram_managed_bot import TelegramPairing, poll_pairing_result_once
    pairing = TelegramPairing(
        pairing_id={pairing_id}, poll_token={poll_token},
        suggested_username="", deep_link="", qr_payload="",
    )
    result = poll_pairing_result_once(None, pairing)
    if result is None:
        print(json.dumps({{"status": "waiting"}}))
    else:
        print(json.dumps({{
            "status": "ready",
            "token": result.token,
            "bot_username": result.bot_username,
            "owner_user_id": result.owner_user_id,
        }}))
except Exception as exc:
    print(json.dumps({{"status": "error", "error": str(exc)[:200]}}))
"""


def telegram_pairing_poll(pairing_id: str) -> TelegramPairingStatus:
    """Interroge le service : ``waiting`` tant que le bot n'est pas créé, puis ``ready``.

    À ``ready``, mémorise le token du bot + ``owner_user_id`` côté bridge (pour l'apply).
    ``pairing_id`` inconnu/expiré => KeyError (404).
    """
    _purge_expired_pairings()
    with _PAIRINGS_LOCK:
        entry = _PAIRINGS.get(pairing_id)
    if not entry:
        raise KeyError(pairing_id)
    script = _PAIRING_POLL_SCRIPT.format(
        pairing_id=json.dumps(pairing_id),
        poll_token=json.dumps(entry["poll_token"]),
    )
    res = hermes_adapter.introspect(script, timeout=20)
    if res.get("status") == "ready":
        with _PAIRINGS_LOCK:
            slot = _PAIRINGS.get(pairing_id)
            if slot is not None:
                slot["token"] = res["token"]
                slot["bot_username"] = res.get("bot_username")
                slot["owner_user_id"] = res.get("owner_user_id")
        if slot is None:
            # Annulé pendant l'appel réseau (fenêtre de course avec `cancel`) : le
            # token fraîchement obtenu n'est persisté nulle part côté bridge — ne
            # pas prétendre "ready" (un `apply` ultérieur lèverait KeyError).
            return TelegramPairingStatus(status="cancelled", expires_at=entry.get("expires_at"))
        return TelegramPairingStatus(
            status="ready",
            bot_username=res.get("bot_username"),
            owner_user_id=res.get("owner_user_id"),
            expires_at=entry.get("expires_at"),
        )
    # waiting (ou erreur réseau transitoire : on laisse le front re-poller)
    return TelegramPairingStatus(status="waiting", expires_at=entry.get("expires_at"))


_PAIRING_APPLY_SCRIPT = """
import json
errors = []
token = {token}
owner_id = {owner_id}
name = {name}
try:
    from hermes_cli.config import save_env_value, write_platform_config_field
    save_env_value("TELEGRAM_BOT_TOKEN", token)
    if owner_id:
        save_env_value("TELEGRAM_ALLOWED_USERS", owner_id)
        save_env_value("TELEGRAM_HOME_CHANNEL", owner_id)
    write_platform_config_field("telegram", "enabled", True)
except Exception as exc:
    errors.append("config: " + str(exc)[:150])
if owner_id:
    try:
        from gateway.pairing import PairingStore
        store = PairingStore()
        with store._lock:
            store._approve_user("telegram", owner_id, name or "")
    except Exception as exc:
        errors.append("approve: " + str(exc)[:150])
print(json.dumps({{"ok": not errors, "errors": errors}}))
"""


def telegram_pairing_apply(pairing_id: str) -> TelegramPairingApplyResult:
    """Applique un pairing prêt : branche le token, active le canal, auto-approuve le
    propriétaire, définit le home channel, puis redémarre le gateway.

    ``pairing_id`` inconnu ou pas encore ``ready`` => KeyError (404).
    """
    with _PAIRINGS_LOCK:
        entry = _PAIRINGS.get(pairing_id)
        ready = bool(entry and entry.get("token"))
    if not ready:
        raise KeyError(pairing_id)
    owner_id = entry.get("owner_user_id")
    owner_str = str(owner_id) if owner_id else ""
    script = _PAIRING_APPLY_SCRIPT.format(
        token=json.dumps(entry["token"]),
        owner_id=json.dumps(owner_str),
        name=json.dumps("Propriétaire"),
    )
    res = hermes_adapter.introspect(script, timeout=60)
    # Le script peut avoir écrit une partie de la config même en cas d'erreur partielle
    # (ex. token posé mais activation échouée) : invalider dans tous les cas, jamais après
    # coup seulement (cf. invariant d'honnêteté du cache).
    _invalidate_gateway_cache()
    if not res.get("ok"):
        return TelegramPairingApplyResult(
            ok=False, error="; ".join(res.get("errors") or ["échec de configuration"])
        )
    restart = _safe_restart_gateway()
    with _PAIRINGS_LOCK:
        _PAIRINGS.pop(pairing_id, None)
    return TelegramPairingApplyResult(
        ok=True,
        bot_username=entry.get("bot_username"),
        owner_user_id=owner_id,
        needs_restart=True,
        restart_ok=bool(restart.get("ok")),
        restart_error=restart.get("error"),
    )


def telegram_pairing_cancel(pairing_id: str) -> dict:
    """Annule/oublie un pairing en cours (le front a fermé la modale, expiration…)."""
    with _PAIRINGS_LOCK:
        existed = _PAIRINGS.pop(pairing_id, None) is not None
    return {"ok": True, "existed": existed}


# --- PARTAGE : allowlist des utilisateurs d'une plateforme --------------------
# Un bot = utilisateurs illimités. Hermes protège l'accès par une allowlist : chaque
# nouvel utilisateur reçoit un code (en attente) que le propriétaire approuve. On
# expose ça en UI (« Accès & partage ») plutôt qu'en commande CLI.


_LIST_USERS_SCRIPT = """
import json
platform = {platform}
try:
    from gateway.pairing import PairingStore
    store = PairingStore()
    print(json.dumps({{
        "ok": True,
        "approved": store.list_approved(platform),
        "pending": store.list_pending(platform),
    }}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)[:200]}}))
"""


def _to_user(platform_id: str, raw: dict, *, pending: bool) -> MessagingUser:
    return MessagingUser(
        platform=raw.get("platform") or platform_id,
        user_id=str(raw.get("user_id") or ""),
        user_name=raw.get("user_name") or "",
        approved_at=raw.get("approved_at"),
        pending_code=raw.get("code") if pending else None,
        age_minutes=raw.get("age_minutes") if pending else None,
    )


def list_platform_users(platform_id: str) -> MessagingUsersResponse:
    """Liste les utilisateurs autorisés + les demandes en attente d'une plateforme."""
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    script = _LIST_USERS_SCRIPT.format(platform=json.dumps(platform_id))
    res = hermes_adapter.introspect(script, timeout=30)
    if not res.get("ok"):
        raise hermes_adapter.HermesUnavailable(res.get("error") or "allowlist indisponible")
    return MessagingUsersResponse(
        approved=[_to_user(platform_id, u, pending=False) for u in res.get("approved", [])],
        pending=[_to_user(platform_id, u, pending=True) for u in res.get("pending", [])],
    )


_APPROVE_USER_SCRIPT = """
import json
platform = {platform}
code = {code}
user_id = {user_id}
name = {name}
try:
    from gateway.pairing import PairingStore
    store = PairingStore()
    if code:
        ok = store.approve_code(platform, code) is not None
    elif user_id:
        with store._lock:
            store._approve_user(platform, user_id, name or "")
        ok = True
    else:
        ok = False
    print(json.dumps({{"ok": ok}}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)[:200]}}))
"""


def approve_platform_user(
    platform_id: str,
    code: str | None = None,
    user_id: str | None = None,
    user_name: str = "",
) -> MessagingActionResult:
    """Autorise un utilisateur : via un code en attente (``code``) ou directement (``user_id``)."""
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    script = _APPROVE_USER_SCRIPT.format(
        platform=json.dumps(platform_id),
        code=json.dumps(code or ""),
        user_id=json.dumps(user_id or ""),
        name=json.dumps(user_name or ""),
    )
    res = hermes_adapter.introspect(script, timeout=30)
    return MessagingActionResult(ok=bool(res.get("ok")), error=res.get("error"))


_REVOKE_USER_SCRIPT = """
import json
try:
    from gateway.pairing import PairingStore
    store = PairingStore()
    ok = store.revoke({platform}, {user_id})
    print(json.dumps({{"ok": bool(ok)}}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)[:200]}}))
"""


def revoke_platform_user(platform_id: str, user_id: str) -> MessagingActionResult:
    """Retire l'accès d'un utilisateur (le sort de l'allowlist)."""
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    script = _REVOKE_USER_SCRIPT.format(
        platform=json.dumps(platform_id),
        user_id=json.dumps(str(user_id)),
    )
    res = hermes_adapter.introspect(script, timeout=30)
    return MessagingActionResult(ok=bool(res.get("ok")), error=res.get("error"))


# --- DÉCONNEXION : efface le token + désactive + purge l'allowlist + restart ---
# Clés dérivées (non présentes dans le catalogue) à effacer en plus des clés du formulaire.
_DISCONNECT_EXTRA_KEYS: dict[str, list[str]] = {
    "telegram": ["TELEGRAM_HOME_CHANNEL", "TELEGRAM_HOME_CHANNEL_THREAD_ID"],
    "discord": [
        "DISCORD_HOME_CHANNEL",
        "DISCORD_HOME_CHANNEL_NAME",
        "DISCORD_ALLOWED_ROLES",
        "DISCORD_ALLOW_ALL_USERS",
    ],
    "slack": [
        "SLACK_HOME_CHANNEL",
        "SLACK_HOME_CHANNEL_NAME",
        "SLACK_ALLOW_ALL_USERS",
    ],
}


_DISCONNECT_SCRIPT = """
import json
platform = {platform}
keys = json.loads({keys})
errors = []
try:
    from hermes_cli.config import remove_env_value, write_platform_config_field
    for k in keys:
        try:
            remove_env_value(k)
        except Exception as exc:
            errors.append("remove_env " + k + ": " + str(exc)[:150])
    write_platform_config_field(platform, "enabled", False)
except Exception as exc:
    errors.append("config: " + str(exc)[:150])
try:
    from gateway.pairing import PairingStore
    store = PairingStore()
    store.clear_pending(platform)
    for u in store.list_approved(platform):
        uid = u.get("user_id")
        try:
            store.revoke(platform, uid)
        except Exception as exc:
            errors.append("revoke " + str(uid) + ": " + str(exc)[:150])
except Exception as exc:
    errors.append("pairing: " + str(exc)[:150])
print(json.dumps({{"ok": not errors, "errors": errors}}))
"""


def disconnect_platform(platform_id: str) -> MessagingActionResult:
    """Déconnecte totalement une plateforme : efface ses clés (.env), la désactive
    (config.yaml), purge l'allowlist, puis redémarre le gateway.

    Chaque effacement de clé et chaque révocation d'utilisateur est individuellement
    protégé, mais un échec par item est remonté dans ``errors`` (jamais avalé en
    silence) : si un seul token ou un seul utilisateur n'a pas pu être révoqué,
    ``ok=False`` — on ne dit jamais « déconnecté » sur un état partiel.
    """
    if platform_id not in _CATALOG_BY_ID:
        raise KeyError(platform_id)
    keys = [v["key"] for v in _CATALOG_BY_ID[platform_id]["env_vars"]]
    keys += _DISCONNECT_EXTRA_KEYS.get(platform_id, [])
    script = _DISCONNECT_SCRIPT.format(
        platform=json.dumps(platform_id),
        keys=json.dumps(json.dumps(keys)),
    )
    res = hermes_adapter.introspect(script, timeout=60)
    # Idem : invalider dans tous les cas, même en cas d'échec partiel (cf. telegram_pairing_apply).
    _invalidate_gateway_cache()
    if not res.get("ok"):
        return MessagingActionResult(
            ok=False, error="; ".join(res.get("errors") or ["échec de déconnexion"])
        )
    restart = _safe_restart_gateway()
    return MessagingActionResult(
        ok=True,
        needs_restart=True,
        restart_ok=bool(restart.get("ok")),
        restart_error=restart.get("error"),
    )


# --- INFO du bot Telegram (nom/lien à partager) -------------------------------

_BOT_INFO_SCRIPT = """
import json
try:
    from hermes_cli.config import get_env_value
    token = get_env_value("TELEGRAM_BOT_TOKEN")
    if not token:
        print(json.dumps({"ok": False}))
    else:
        import httpx
        r = httpx.get("https://api.telegram.org/bot" + token + "/getMe", timeout=10)
        data = r.json()
        if data.get("ok"):
            res = data.get("result", {})
            print(json.dumps({"ok": True, "username": res.get("username"), "name": res.get("first_name")}))
        else:
            print(json.dumps({"ok": False}))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)[:200]}))
"""


def telegram_bot_info() -> TelegramBotInfo:
    """Nom + lien du bot Telegram connecté (via getMe), pour l'afficher/le partager.

    Renvoie des champs vides si le token est absent ou l'appel échoue (best-effort).
    """
    try:
        res = hermes_adapter.introspect(_BOT_INFO_SCRIPT, timeout=20)
    except hermes_adapter.HermesUnavailable:
        return TelegramBotInfo()
    username = res.get("username") if res.get("ok") else None
    return TelegramBotInfo(
        username=username,
        name=res.get("name") if res.get("ok") else None,
        link=f"https://t.me/{username}" if username else None,
    )


# --- ONBOARDING DISCORD (parcours guidé : token → branché + invite 1-clic) -----
# Discord n'a PAS de « managed bot » (contrairement à Telegram) : impossible de
# créer un bot sans passer par le portail développeur. Le client colle donc le
# token de son app, et le bridge fait le reste :
#   apply  → valide le token (API Discord), branche + active + redémarre
#   bot-info → nom du bot + URL d'invitation OAuth2 (« Ajouter à mon serveur »)
#
# Partage : Discord filtre via une allowlist statique (DISCORD_ALLOWED_USERS /
# _ROLES). Défaut = AUCUNE allowlist = tout membre du serveur du client peut
# écrire à l'assistant (cf. adapter Discord Hermes : « no allowlist = everyone »).
# On n'utilise donc PAS le PairingStore réactif (propre à Telegram) ici.

# Permissions Discord (bitfield OAuth2) pour un assistant conversationnel :
# voir les salons, écrire (salons + fils), lire l'historique, embeds, fichiers,
# réactions, émojis externes. Assez pour discuter, jamais Administrator.
_DISCORD_PERMISSIONS = str(
    (1 << 10)  # VIEW_CHANNEL
    | (1 << 11)  # SEND_MESSAGES
    | (1 << 38)  # SEND_MESSAGES_IN_THREADS
    | (1 << 34)  # CREATE_PUBLIC_THREADS
    | (1 << 16)  # READ_MESSAGE_HISTORY
    | (1 << 14)  # EMBED_LINKS
    | (1 << 15)  # ATTACH_FILES
    | (1 << 6)  # ADD_REACTIONS
    | (1 << 18)  # USE_EXTERNAL_EMOJIS
)


def _discord_invite_url(application_id: str) -> str:
    """URL OAuth2 « Ajouter à mon serveur » pour un bot donné (scopes bot + slash)."""
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={application_id}"
        f"&permissions={_DISCORD_PERMISSIONS}"
        "&scope=bot+applications.commands"
    )


# Valide le token via l'API Discord (l'id du bot user = l'application id, d'où
# l'URL d'invitation), puis — seulement si le token est bon — branche + active.
# Récupère aussi le PROPRIÉTAIRE de l'application (owner.id) pour l'auto-autoriser :
# sans allowlist, le moteur refuse les expéditeurs inconnus → le client ne pourrait
# jamais parler à son propre bot. On l'ajoute donc tout seul (comme l'owner Telegram).
_DISCORD_APPLY_SCRIPT = """
import json
token = {token}
errors = []
warnings = []
identity = None
owner_id = None
try:
    import httpx
    r = httpx.get(
        "https://discord.com/api/v10/users/@me",
        headers={{"Authorization": "Bot " + token}},
        timeout=10,
    )
    if r.status_code == 200:
        d = r.json()
        identity = {{"id": str(d.get("id") or ""), "username": d.get("username")}}
    else:
        errors.append("token_invalid")
    # Propriétaire de l'app = le client qui l'a créée → à auto-autoriser.
    if identity and not errors:
        ra = httpx.get(
            "https://discord.com/api/v10/oauth2/applications/@me",
            headers={{"Authorization": "Bot " + token}},
            timeout=10,
        )
        if ra.status_code == 200:
            app = ra.json()
            team = app.get("team") or {{}}
            owner = app.get("owner") or {{}}
            owner_id = str(team.get("owner_user_id") or owner.get("id") or "") or None
        else:
            # Échec du 2e appel (rate limit, timeout…) : le token reste valide et le
            # bot doit quand même se brancher, mais l'auto-autorisation n'a pas eu
            # lieu — signalé à part (``warnings``), jamais dans ``errors`` (qui
            # piloterait ``ok``) pour ne pas faire échouer tout le branchement.
            warnings.append("owner_lookup_failed")
except Exception as exc:
    errors.append("token: " + str(exc)[:150])

if identity and not errors:
    try:
        from hermes_cli.config import save_env_value, write_platform_config_field
        try:
            from hermes_cli.config import get_env_value
        except Exception:
            get_env_value = None
        save_env_value("DISCORD_BOT_TOKEN", token)
        # Auto-autorisation du propriétaire : on l'ajoute à l'allowlist sans écraser
        # d'éventuels utilisateurs déjà autorisés (collègues ajoutés à la main).
        if owner_id:
            existing = ""
            if get_env_value:
                try:
                    existing = (get_env_value("DISCORD_ALLOWED_USERS") or "").strip()
                except Exception:
                    existing = ""
            ids = [x.strip() for x in existing.split(",") if x.strip()]
            if owner_id not in ids:
                ids.append(owner_id)
            save_env_value("DISCORD_ALLOWED_USERS", ",".join(ids))
        write_platform_config_field("discord", "enabled", True)
    except Exception as exc:
        errors.append("config: " + str(exc)[:150])

print(json.dumps({{"ok": not errors, "errors": errors, "warnings": warnings, "identity": identity, "owner_id": owner_id}}))
"""


def discord_apply(token: str) -> DiscordApplyResult:
    """Branche Discord depuis un token collé : valide le token (API Discord), branche
    + active + redémarre le gateway, et renvoie l'URL d'invitation « Ajouter à mon
    serveur ».

    Ne dit jamais « connecté » sans avoir validé le token : token invalide/vide =>
    ``ok=False`` + message, aucun redémarrage.
    """
    token = (token or "").strip()
    if not token:
        return DiscordApplyResult(ok=False, error="Aucun token fourni.")
    script = _DISCORD_APPLY_SCRIPT.format(token=json.dumps(token))
    res = hermes_adapter.introspect(script, timeout=60)
    _invalidate_gateway_cache()
    if not res.get("ok"):
        errs = res.get("errors") or []
        if "token_invalid" in errs or any(str(e).startswith("token:") for e in errs):
            msg = "Ce token ne fonctionne pas. Vérifiez que vous l'avez bien copié (bouton « Reset Token » puis « Copy »)."
        else:
            msg = "; ".join(errs) or "échec de configuration"
        return DiscordApplyResult(ok=False, error=msg)
    identity = res.get("identity") or {}
    app_id = identity.get("id") or ""
    restart = _safe_restart_gateway()
    warning = None
    if "owner_lookup_failed" in (res.get("warnings") or []):
        warning = (
            "Bot branché, mais l'auto-autorisation du propriétaire a échoué : "
            "ajoutez-le manuellement à DISCORD_ALLOWED_USERS si besoin."
        )
    return DiscordApplyResult(
        ok=True,
        bot_name=identity.get("username"),
        invite_url=_discord_invite_url(app_id) if app_id else None,
        needs_restart=True,
        restart_ok=bool(restart.get("ok")),
        restart_error=restart.get("error"),
        error=warning,
    )


_DISCORD_BOT_INFO_SCRIPT = """
import json
try:
    from hermes_cli.config import get_env_value
    token = get_env_value("DISCORD_BOT_TOKEN")
    if not token:
        print(json.dumps({"ok": False}))
    else:
        import httpx
        r = httpx.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": "Bot " + token},
            timeout=10,
        )
        if r.status_code == 200:
            d = r.json()
            print(json.dumps({"ok": True, "id": str(d.get("id") or ""), "username": d.get("username")}))
        else:
            print(json.dumps({"ok": False}))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)[:200]}))
"""


def discord_bot_info() -> DiscordBotInfo:
    """Nom du bot Discord connecté + URL d'invitation « Ajouter à mon serveur ».

    Renvoie des champs vides si le token est absent ou l'appel échoue (best-effort).
    """
    try:
        res = hermes_adapter.introspect(_DISCORD_BOT_INFO_SCRIPT, timeout=20)
    except hermes_adapter.HermesUnavailable:
        return DiscordBotInfo()
    if not res.get("ok"):
        return DiscordBotInfo()
    app_id = res.get("id") or ""
    return DiscordBotInfo(
        name=res.get("username"),
        application_id=app_id or None,
        invite_url=_discord_invite_url(app_id) if app_id else None,
    )


# --- Onboarding Slack (parcours guidé : 2 tokens → branché) -------------------
# Slack exige DEUX tokens : le bot token (xoxb-…) pour l'API Web, et le app-level
# token (xapp-…) pour Socket Mode (le moteur écoute via une WebSocket). On valide
# les deux avant de brancher — sinon on mentirait sur l'état :
#   • xoxb → auth.test          (renvoie team / user / url du workspace)
#   • xapp → apps.connections.open  (ouvre une connexion Socket Mode = token bon)
# Contrairement à Discord, pas d'URL d'invitation : l'app est déjà installée dans
# le workspace au moment où le xoxb est émis.
_SLACK_APPLY_SCRIPT = """
import json
bot_token = {bot_token}
app_token = {app_token}
errors = []
identity = None
try:
    import httpx
    r = httpx.post(
        "https://slack.com/api/auth.test",
        headers={{"Authorization": "Bearer " + bot_token}},
        timeout=10,
    )
    d = r.json()
    if d.get("ok"):
        identity = {{
            "team": d.get("team"),
            "team_id": str(d.get("team_id") or ""),
            "user": d.get("user"),
            "url": d.get("url"),
        }}
    else:
        errors.append("bot_token_invalid")
except Exception as exc:
    errors.append("bot_token: " + str(exc)[:150])

# Valide séparément le app-level token (Socket Mode) : ouvrir une connexion
# confirme que le xapp- est bon et porte bien le scope connections:write.
if identity and not errors:
    try:
        import httpx
        r2 = httpx.post(
            "https://slack.com/api/apps.connections.open",
            headers={{"Authorization": "Bearer " + app_token}},
            timeout=10,
        )
        if not r2.json().get("ok"):
            errors.append("app_token_invalid")
    except Exception as exc:
        errors.append("app_token: " + str(exc)[:150])

if identity and not errors:
    try:
        from hermes_cli.config import save_env_value, write_platform_config_field
        try:
            from hermes_cli.config import get_env_value
        except Exception:
            get_env_value = None
        save_env_value("SLACK_BOT_TOKEN", bot_token)
        save_env_value("SLACK_APP_TOKEN", app_token)
        # Auto-autorisation : par défaut tout le workspace peut parler au bot. Un
        # workspace Slack est un périmètre fermé (on n'y entre que sur invitation),
        # donc « tous les membres » = les gens que le client a déjà laissés entrer.
        # Sans ça, le moteur applique un default-deny (allowlist vide = personne) et
        # le client ne pourrait jamais parler à son propre bot. On ne pose le flag
        # QUE s'il n'a pas déjà restreint via une allowlist explicite — sinon on
        # écraserait sa restriction (côté moteur, allow-all prime sur l'allowlist).
        existing_allow = ""
        if get_env_value:
            try:
                existing_allow = (get_env_value("SLACK_ALLOWED_USERS") or "").strip()
            except Exception:
                existing_allow = ""
        if not existing_allow:
            save_env_value("SLACK_ALLOW_ALL_USERS", "true")
        write_platform_config_field("slack", "enabled", True)
    except Exception as exc:
        errors.append("config: " + str(exc)[:150])

print(json.dumps({{"ok": not errors, "errors": errors, "identity": identity}}))
"""


def slack_apply(bot_token: str, app_token: str) -> SlackApplyResult:
    """Branche Slack depuis les 2 tokens collés : valide le bot token (auth.test)
    et le app-level token (Socket Mode), branche + active + redémarre le gateway,
    et renvoie le nom du workspace + du bot.

    Ne dit jamais « connecté » sans avoir validé les DEUX tokens : token
    invalide/manquant => ``ok=False`` + message, aucun redémarrage.
    """
    bot_token = (bot_token or "").strip()
    app_token = (app_token or "").strip()
    if not bot_token or not app_token:
        return SlackApplyResult(
            ok=False, error="Les deux tokens sont requis : le bot token (xoxb-…) et le app token (xapp-…)."
        )
    script = _SLACK_APPLY_SCRIPT.format(
        bot_token=json.dumps(bot_token),
        app_token=json.dumps(app_token),
    )
    res = hermes_adapter.introspect(script, timeout=60)
    _invalidate_gateway_cache()
    if not res.get("ok"):
        errs = res.get("errors") or []
        if "bot_token_invalid" in errs or any(str(e).startswith("bot_token:") for e in errs):
            msg = "Le bot token (xoxb-…) ne fonctionne pas. Vérifiez « OAuth & Permissions » de votre app Slack."
        elif "app_token_invalid" in errs or any(str(e).startswith("app_token:") for e in errs):
            msg = "Le app token (xapp-…) ne fonctionne pas. Vérifiez « Socket Mode » (scope connections:write)."
        else:
            msg = "; ".join(errs) or "échec de configuration"
        return SlackApplyResult(ok=False, error=msg)
    identity = res.get("identity") or {}
    restart = _safe_restart_gateway()
    return SlackApplyResult(
        ok=True,
        bot_name=identity.get("user"),
        team_name=identity.get("team"),
        workspace_url=identity.get("url"),
        needs_restart=True,
        restart_ok=bool(restart.get("ok")),
        restart_error=restart.get("error"),
    )


_SLACK_BOT_INFO_SCRIPT = """
import json
try:
    from hermes_cli.config import get_env_value
    token = get_env_value("SLACK_BOT_TOKEN")
    if not token:
        print(json.dumps({"ok": False}))
    else:
        import httpx
        r = httpx.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": "Bearer " + token},
            timeout=10,
        )
        d = r.json()
        if d.get("ok"):
            print(json.dumps({"ok": True, "user": d.get("user"), "team": d.get("team"), "url": d.get("url")}))
        else:
            print(json.dumps({"ok": False}))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)[:200]}))
"""


def slack_bot_info() -> SlackBotInfo:
    """Nom du bot Slack connecté + workspace (via l'API Slack ``auth.test``).

    Renvoie des champs vides si le token est absent ou l'appel échoue (best-effort).
    """
    try:
        res = hermes_adapter.introspect(_SLACK_BOT_INFO_SCRIPT, timeout=20)
    except hermes_adapter.HermesUnavailable:
        return SlackBotInfo()
    if not res.get("ok"):
        return SlackBotInfo()
    return SlackBotInfo(
        name=res.get("user"),
        team_name=res.get("team"),
        workspace_url=res.get("url"),
    )


# --- Onboarding Email (validation réelle : login IMAP + SMTP → auto-activation) -
# On TESTE vraiment la connexion avant de dire « connecté » : login IMAP (réception,
# + compte les mails = preuve concrète) et login SMTP (envoi). Certificats via certifi
# si dispo. Si les deux passent : enregistre + active + laisse le gateway redémarrer.
# NB : on garde les espaces internes du mot de passe (les app-passwords Gmail en ont).
_EMAIL_APPLY_SCRIPT = """
import json, imaplib, smtplib, ssl
address = {address}
password = {password}
imap_host = {imap_host}
smtp_host = {smtp_host}
errors = []
count = None

ctx = ssl.create_default_context()
try:
    import certifi
    ctx.load_verify_locations(certifi.where())
except Exception:
    pass

# Réception (IMAP) — login + compte des messages de l'INBOX
try:
    c = imaplib.IMAP4_SSL(imap_host, 993, ssl_context=ctx, timeout=20)
    c.login(address, password)
    c.select("INBOX")
    typ, data = c.search(None, "ALL")
    count = len(data[0].split()) if data and data[0] else 0
    c.logout()
except imaplib.IMAP4.error as exc:
    errors.append("imap_auth: " + str(exc)[:150])
except Exception as exc:
    errors.append("imap: " + str(exc)[:150])

# Envoi (SMTP) — essaie SSL 465 puis STARTTLS 587
if not errors:
    smtp_err = None
    try:
        s = smtplib.SMTP_SSL(smtp_host, 465, context=ctx, timeout=20)
        s.login(address, password)
        s.quit()
    except smtplib.SMTPAuthenticationError as exc:
        smtp_err = "smtp_auth: " + str(exc)[:150]
    except Exception:
        try:
            s = smtplib.SMTP(smtp_host, 587, timeout=20)
            s.starttls(context=ctx)
            s.login(address, password)
            s.quit()
        except smtplib.SMTPAuthenticationError as exc:
            smtp_err = "smtp_auth: " + str(exc)[:150]
        except Exception as exc:
            smtp_err = "smtp: " + str(exc)[:150]
    if smtp_err:
        errors.append(smtp_err)

# Tout bon → enregistre + active le canal (auto-activation, pas de toggle à trouver)
if not errors:
    try:
        from hermes_cli.config import save_env_value, write_platform_config_field
        save_env_value("EMAIL_ADDRESS", address)
        save_env_value("EMAIL_PASSWORD", password)
        save_env_value("EMAIL_IMAP_HOST", imap_host)
        save_env_value("EMAIL_SMTP_HOST", smtp_host)
        write_platform_config_field("email", "enabled", True)
    except Exception as exc:
        errors.append("config: " + str(exc)[:150])

print(json.dumps({{"ok": not errors, "errors": errors, "count": count}}))
"""


def email_apply(address: str, password: str, imap_host: str, smtp_host: str) -> EmailApplyResult:
    """Branche Email en testant RÉELLEMENT la connexion (login IMAP + SMTP) : si les
    deux réussissent, enregistre les identifiants, **active le canal tout seul** et
    redémarre le gateway. Sinon ``ok=False`` + message clair, rien n'est activé.

    Le client n'a aucun toggle à trouver : succès = déjà branché et allumé.
    """
    address = (address or "").strip()
    imap_host = (imap_host or "").strip()
    smtp_host = (smtp_host or "").strip()
    # Ne strip que les bords : les app-passwords Gmail contiennent des espaces internes.
    password = (password or "").strip()
    if not (address and password and imap_host and smtp_host):
        return EmailApplyResult(
            ok=False, error="Adresse, mot de passe et serveurs (IMAP/SMTP) sont requis."
        )
    script = _EMAIL_APPLY_SCRIPT.format(
        address=json.dumps(address),
        password=json.dumps(password),
        imap_host=json.dumps(imap_host),
        smtp_host=json.dumps(smtp_host),
    )
    res = hermes_adapter.introspect(script, timeout=90)
    _invalidate_gateway_cache()
    if not res.get("ok"):
        errs = res.get("errors") or []
        if any(str(e).startswith(("imap_auth", "smtp_auth")) for e in errs):
            msg = "Identifiants refusés. Pour Gmail/Outlook, utilisez un « mot de passe d'application » (pas votre mot de passe habituel), et vérifiez qu'il est bien copié."
        elif any(str(e).startswith("imap") for e in errs):
            msg = "Impossible de joindre le serveur de réception (IMAP). Vérifiez l'adresse du serveur."
        elif any(str(e).startswith("smtp") for e in errs):
            msg = "La réception fonctionne mais l'envoi échoue (SMTP). Vérifiez le serveur d'envoi."
        else:
            msg = "; ".join(errs) or "échec de configuration"
        return EmailApplyResult(ok=False, error=msg)
    restart = _safe_restart_gateway()
    return EmailApplyResult(
        ok=True,
        address=address,
        mailbox_count=res.get("count"),
        needs_restart=True,
        restart_ok=bool(restart.get("ok")),
        restart_error=restart.get("error"),
    )
