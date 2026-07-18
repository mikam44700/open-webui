"""Adapter Intégrations — état réel des skills connectables de Hermes (onglet Intégrations).

Dérive l'état de chaque intégration du catalogue curé à partir de signaux RÉELS côté Hermes :
- mode ``key`` : présence de la variable dans ~/.hermes/.env (jamais la valeur) ;
- mode ``account`` / ``credentials`` : présence du fichier de token/config attestant la connexion ;
- mode ``local`` : pas de secret — état neutre (la connexion se vérifie à l'usage).

Aucune valeur de secret n'est lue ni transportée. Cf. specs/004-integrations.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx

from . import hermes_adapter, oauth_engine, profiles_adapter
from .integrations_catalog import CATALOG, IntegrationDef, by_id
from .models import AuthMode, Integration, IntegrationStateEnum, SecretState

logger = logging.getLogger(__name__)


def _all_profile_env_paths() -> list[Path]:
    """Le ``.env`` de CHAQUE profil (chaque agent lit le sien — pas de global partagé).

    Fallback robuste : si Hermes est injoignable, on cible au moins le ``.env`` courant du bridge
    (comportement historique), pour ne jamais échouer une connexion d'intégration.
    """
    paths = [hermes_adapter.HERMES_HOME / ".env"]
    try:
        for home in profiles_adapter.profile_homes():
            candidate = Path(home) / ".env"
            if candidate not in paths:
                paths.append(candidate)
    except Exception:  # noqa: BLE001 — repli sur le .env courant, ne jamais casser une connexion
        logger.debug("liste des profils Hermes indisponible (repli sur le .env courant)", exc_info=True)
    return paths


def _state_file_path(entry: IntegrationDef) -> Path | None:
    """Chemin du fichier dont la présence atteste la connexion (modes account/credentials)."""
    if not entry.state_file:
        return None
    base = Path.home() if entry.state_file_home else hermes_adapter.HERMES_HOME
    return base / entry.state_file


def _derive_state(
    entry: IntegrationDef, present_env: set[str]
) -> tuple[IntegrationStateEnum, SecretState | None]:
    """Calcule (état, état du secret) d'une intégration à partir des signaux réels."""
    if entry.auth_mode == "key":
        present = bool(entry.secret_env) and entry.secret_env in present_env
        if present:
            return IntegrationStateEnum.key_present, SecretState.present
        return IntegrationStateEnum.not_connected, SecretState.absent

    if entry.auth_mode == "path":
        # Un chemin de dossier (ex. coffre Obsidian) : pas un secret. Renseigné ⇒ connecté.
        present = bool(entry.secret_env) and entry.secret_env in present_env
        if present:
            return IntegrationStateEnum.connected, None
        return IntegrationStateEnum.not_connected, None

    if entry.auth_mode in ("account", "credentials"):
        state_file = _state_file_path(entry)
        if state_file is not None and state_file.exists():
            return IntegrationStateEnum.connected, None
        return IntegrationStateEnum.not_connected, None

    # mode local : aucun secret à détecter, on ne prétend pas connecté
    return IntegrationStateEnum.not_connected, None


def _oauth_connected(integration_id: str) -> bool:
    """Vrai si un token OAuth centralisé existe pour cette intégration (échange réussi).

    Preuve réelle de connexion : le fournisseur a délivré un token via le flux OAuth 1-clic.
    Prioritaire sur « clé enregistrée » quand l'access_token OAuth est aussi recopié en env_key
    (ex. Notion : NOTION_API_KEY présent ⇒ sinon la carte afficherait « Clé enregistrée »
    alors que la connexion est réelle). Cohérent avec le mode « account » (Google) qui est déjà
    « connecté » dès que son token existe.
    """
    try:
        return oauth_engine.token_status(integration_id) == "connected"
    except Exception:
        # Intégration sans flux OAuth centralisé (clé manuelle, chemin…) → non concernée.
        return False


def list_integrations() -> list[Integration]:
    """Liste le catalogue curé avec l'état réel de chaque intégration (sans aucun secret)."""
    present_env = hermes_adapter._present_env_keys()
    integrations: list[Integration] = []
    for entry in CATALOG:
        state, secret_state = _derive_state(entry, present_env)
        # Un token OAuth centralisé présent = connexion réelle → « connecté » (prioritaire sur
        # « clé enregistrée » : l'access_token OAuth est parfois aussi recopié en env_key).
        if state != IntegrationStateEnum.connected and _oauth_connected(entry.id):
            state = IntegrationStateEnum.connected
        integrations.append(
            Integration(
                id=entry.id,
                auth_mode=AuthMode(entry.auth_mode),
                state=state,
                secret_state=secret_state,
                subservices=list(entry.subservices),
                visible=entry.default_visible,
                local_only=entry.local_only,
            )
        )
    return integrations


# --- Connexion Google Workspace (mode account, v1 : le client fournit son app) -----
# Pilote le script natif de la skill Hermes : ~/.hermes/skills/productivity/google-workspace/
# scripts/setup.py (flow OAuth non-interactif conçu pour être piloté par un agent/une UI).


def _google_setup_script() -> Path:
    return (
        hermes_adapter.HERMES_HOME
        / "skills"
        / "productivity"
        / "google-workspace"
        / "scripts"
        / "setup.py"
    )


def _run_google_setup(args: list[str], timeout: int = 120) -> tuple[int, str]:
    """Exécute setup.py avec l'interpréteur Hermes. Retourne (code de sortie, sortie texte)."""
    script = _google_setup_script()
    if not script.exists():
        raise hermes_adapter.HermesUnavailable("skill google-workspace introuvable côté Hermes")
    python = hermes_adapter.HERMES_PYTHON
    if not Path(python).exists():
        raise hermes_adapter.HermesUnavailable(f"interpréteur Hermes introuvable: {python}")
    try:
        res = subprocess.run(
            [python, str(script), *args], capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise hermes_adapter.HermesUnavailable(str(exc)) from exc
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def google_set_client_secret(client_secret_json: dict) -> None:
    """Enregistre l'app Google du client (client_secret.json) via setup.py --client-secret."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(client_secret_json, fh)
        tmp = fh.name
    try:
        code, out = _run_google_setup(["--client-secret", tmp, "--quiet"])
    finally:
        Path(tmp).unlink(missing_ok=True)
    if code != 0:
        raise hermes_adapter.HermesUnavailable(out.strip()[:300] or "client_secret invalide")


def google_auth_url() -> str:
    """Retourne l'URL d'autorisation Google à présenter au client."""
    code, out = _run_google_setup(["--auth-url"])
    match = re.search(r"https://accounts\.google\.com/\S+", out)
    if not match:
        raise hermes_adapter.HermesUnavailable(out.strip()[:300] or "URL d'autorisation indisponible")
    return match.group(0)


def google_submit_code(auth_code: str) -> bool:
    """Échange le code de redirection contre un token. True si la connexion est confirmée."""
    code, _ = _run_google_setup(["--auth-code", auth_code])
    if code != 0:
        return False
    return google_status() == "connected"


def google_status() -> str:
    """État réel de la connexion Google : 'connected' ou 'not_connected' (via --check)."""
    code, _ = _run_google_setup(["--check"])
    return "connected" if code == 0 else "not_connected"


def google_disconnect() -> None:
    """Révoque et supprime le token Google (setup.py --revoke)."""
    _run_google_setup(["--revoke"])


# --- Connexion par clé / chemin (Notion, GitHub, Airtable, Obsidian) ---------------
# Test d'accès réel par service : (URL, en-têtes) à partir de la clé. La valeur est lue
# côté serveur uniquement pour le test, jamais renvoyée à l'interface.

_KEY_TEST = {
    "notion": lambda v: (
        "https://api.notion.com/v1/users/me",
        {"Authorization": f"Bearer {v}", "Notion-Version": "2022-06-28"},
    ),
    "github": lambda v: (
        "https://api.github.com/user",
        {"Authorization": f"Bearer {v}", "Accept": "application/vnd.github+json"},
    ),
    "airtable": lambda v: (
        "https://api.airtable.com/v0/meta/bases",
        {"Authorization": f"Bearer {v}"},
    ),
    # Cal.com v1 : la clé passe en query (?apiKey=). GET /v1/me → 200 si la clé est valide.
    "cal-com": lambda v: (
        f"https://api.cal.com/v1/me?apiKey={quote(v)}",
        {},
    ),
}


def _read_env_value(key: str) -> str | None:
    """Lit la valeur d'une variable dans ~/.hermes/.env (interne — jamais renvoyée à l'UI)."""
    return hermes_adapter.read_env_value(key)


def _unset_env_value(key: str) -> None:
    """Supprime une variable du ``.env`` de TOUS les profils (cohérence à la déconnexion)."""
    for env_path in _all_profile_env_paths():
        hermes_adapter._remove_env_kv(env_path, key)


def set_secret(integration_id: str, value: str) -> SecretState:
    """Enregistre la clé (mode key) ou le chemin du dossier (mode path). Valeur jamais renvoyée."""
    entry = by_id(integration_id)
    if entry is None:
        raise KeyError(integration_id)
    if entry.auth_mode not in ("key", "path") or not entry.secret_env:
        raise ValueError(f"intégration {integration_id} ne se connecte pas par clé/chemin")
    # Propage la clé/chemin au .env de TOUS les profils : chaque agent lit le sien (pas de
    # .env global dans Hermes). Les agents créés ensuite l'héritent par clonage.
    for env_path in _all_profile_env_paths():
        hermes_adapter._write_env_kv(env_path, entry.secret_env, value.strip())
    return SecretState.present


def test_access(integration_id: str) -> tuple[str, str | None]:
    """Teste l'accès réel. Retourne (état, raison) — état honnête, jamais 'connected' sans preuve."""
    entry = by_id(integration_id)
    if entry is None:
        raise KeyError(integration_id)

    if entry.auth_mode == "path":
        value = _read_env_value(entry.secret_env) if entry.secret_env else None
        if value and Path(os.path.expanduser(value)).is_dir():
            return "connected", None
        return "error", "dossier introuvable"

    if entry.auth_mode == "key":
        value = _read_env_value(entry.secret_env) if entry.secret_env else None
        if not value:
            return "not_connected", "aucune clé enregistrée"
        builder = _KEY_TEST.get(integration_id)
        if builder is None:
            return "key_present", None  # pas de test dispo → on reste honnête
        url, headers = builder(value)
        try:
            resp = httpx.get(url, headers=headers, timeout=10.0)
        except httpx.RequestError:
            return "error", "service injoignable"
        if resp.status_code == 200:
            return "connected", None
        return "error", f"accès refusé (HTTP {resp.status_code})"

    return "error", "test non disponible pour cette intégration"


# --- Connexion Email (Himalaya IMAP/SMTP) ----------------------------------------
# Serveurs des fournisseurs courants (l'UI peut les surcharger).

_EMAIL_PROVIDERS = {
    "gmail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 587),
    "googlemail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 587),
    "outlook.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "hotmail.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "live.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "yahoo.com": ("imap.mail.yahoo.com", 993, "smtp.mail.yahoo.com", 587),
    "icloud.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587),
}


def email_guess_servers(email: str) -> dict | None:
    """Devine les serveurs IMAP/SMTP d'après le domaine de l'email (ou None)."""
    domain = email.rsplit("@", 1)[-1].lower().strip()
    found = _EMAIL_PROVIDERS.get(domain)
    if not found:
        return None
    imap_host, imap_port, smtp_host, smtp_port = found
    return {
        "imap_host": imap_host,
        "imap_port": imap_port,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
    }


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def set_email_credentials(
    email: str, password: str, imap_host: str, imap_port: int, smtp_host: str, smtp_port: int
) -> None:
    """Écrit la config Himalaya (~/.config/himalaya/config.toml). Mot de passe jamais renvoyé."""
    imap_enc = "tls" if int(imap_port) == 993 else "start-tls"
    smtp_enc = "tls" if int(smtp_port) == 465 else "start-tls"
    e = _toml_escape(email)
    p = _toml_escape(password)
    toml = f"""[accounts.default]
email = "{e}"
default = true

backend.type = "imap"
backend.host = "{_toml_escape(imap_host)}"
backend.port = {int(imap_port)}
backend.encryption.type = "{imap_enc}"
backend.login = "{e}"
backend.auth.type = "password"
backend.auth.raw = "{p}"

message.send.backend.type = "smtp"
message.send.backend.host = "{_toml_escape(smtp_host)}"
message.send.backend.port = {int(smtp_port)}
message.send.backend.encryption.type = "{smtp_enc}"
message.send.backend.login = "{e}"
message.send.backend.auth.type = "password"
message.send.backend.auth.raw = "{p}"
"""
    cfg = Path.home() / ".config" / "himalaya" / "config.toml"
    # Mot de passe IMAP/SMTP en clair (contrainte Himalaya) : au minimum, permissions 0600
    # dès la création (jamais de fenêtre en mode large) — réutilise le helper déjà éprouvé
    # pour les tokens OAuth plutôt que de dupliquer la logique d'écriture sécurisée.
    oauth_engine._write_secure(cfg, toml)


def disconnect(integration_id: str) -> None:
    """Déconnecte une intégration selon son mode (révocation Google / effacement clé/chemin)."""
    entry = by_id(integration_id)
    if entry is None:
        raise KeyError(integration_id)
    if integration_id == "google-workspace":
        google_disconnect()
    elif entry.auth_mode in ("key", "path") and entry.secret_env:
        _unset_env_value(entry.secret_env)
    elif entry.auth_mode == "credentials":
        cfg = Path.home() / ".config" / "himalaya" / "config.toml"
        cfg.unlink(missing_ok=True)
    else:
        raise ValueError(f"déconnexion non gérée pour {integration_id}")
