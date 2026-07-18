"""Router Hermes — le fork parle directement à l'installation Hermes locale.

Adapté du bridge de la v1 (agent-os/app/bridge/hermes_adapter.py), sans service
intermédiaire : le backend du fork tourne sur l'hôte et peut lire ~/.hermes/
et exécuter la CLI hermes.

Lectures seules dans ce chantier : config.yaml (modèle actif), `hermes --version`,
date du dernier commit du dépôt installé, joignabilité de l'API server, et
`hermes update --check` (ne modifie rien). Jamais de lecture de clés/secrets.
"""

import logging
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

HERMES_HOME = Path(os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes")))
HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
DEFAULT_API_SERVER_PORT = 8642


class ActiveModel(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None


class ApiServerStatus(BaseModel):
    port: int
    reachable: bool


class HermesStatus(BaseModel):
    installed: bool
    version: Optional[str] = None
    last_update: Optional[str] = None  # date ISO (YYYY-MM-DD) du dernier commit installé
    active: Optional[ActiveModel] = None
    api_server: ApiServerStatus


class UpdateCheckResult(BaseModel):
    up_to_date: Optional[bool] = None  # None = sortie non interprétable
    output: str


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# `hermes --version` est lente (~1 s) et ne change qu'après une mise à jour :
# petit cache mémoire, invalidé par l'endpoint update/check.
_version_cache: dict = {"at": 0.0, "version": None, "last_update": None}
_VERSION_TTL = 300  # secondes


def _invalidate_version_cache() -> None:
    _version_cache["at"] = 0.0


def _version_and_last_update() -> tuple[Optional[str], Optional[str]]:
    now = time.monotonic()
    if now - _version_cache["at"] < _VERSION_TTL and _version_cache["version"]:
        return _version_cache["version"], _version_cache["last_update"]

    version = None
    last_update = None
    try:
        res = _run([HERMES_BIN, "--version"], timeout=15)
        text = (res.stdout or res.stderr or "").strip()
        if text:
            # ex : "Hermes Agent v0.18.2 (2026.7.7.2) · upstream 0bf44d55"
            match = re.search(r"v[\d][\w.\-]*", text.splitlines()[0])
            version = match.group(0) if match else text.splitlines()[0]
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning(f"hermes --version indisponible: {exc}")

    repo = HERMES_HOME / "hermes-agent"
    if repo.exists():
        try:
            res = _run(["git", "-C", str(repo), "log", "-1", "--format=%cs"], timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                last_update = res.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning(f"date de mise à jour Hermes illisible: {exc}")

    if version:
        _version_cache.update(
            {"at": now, "version": version, "last_update": last_update}
        )
    return version, last_update


def _get_active() -> Optional[ActiveModel]:
    """Modèle actif lu dans ~/.hermes/config.yaml (model.provider / model.default)."""
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    except (yaml.YAMLError, OSError) as exc:
        log.warning(f"config Hermes illisible: {exc}")
        return None
    model = cfg.get("model") or {}
    default = model.get("default") or model.get("model")
    if not default:
        return None
    return ActiveModel(provider=model.get("provider"), model=str(default))


def _api_server_port() -> int:
    """Port de l'API server Hermes — lu dans ~/.hermes/.env (noms seulement)."""
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_PORT") and "=" in line:
                try:
                    return int(line.split("=", 1)[1].strip())
                except ValueError:
                    pass
    return DEFAULT_API_SERVER_PORT


def _api_server_reachable(port: int) -> bool:
    """Le serveur Hermes répond-il ? (une réponse HTTP même 401/403 = joignable)."""
    url = f"http://127.0.0.1:{port}/v1/models"
    try:
        urllib.request.urlopen(url, timeout=4)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


@router.get("/status", response_model=HermesStatus)
def get_hermes_status(user=Depends(get_admin_user)):
    version, last_update = _version_and_last_update()
    port = _api_server_port()
    return HermesStatus(
        installed=(HERMES_HOME / "hermes-agent").exists(),
        version=version,
        last_update=last_update,
        active=_get_active(),
        api_server=ApiServerStatus(port=port, reachable=_api_server_reachable(port)),
    )


@router.post("/update/check", response_model=UpdateCheckResult)
def check_hermes_update(user=Depends(get_admin_user)):
    """`hermes update --check` : vérifie sans rien modifier."""
    try:
        res = _run([HERMES_BIN, "update", "--check"], timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=503, detail=f"Hermes injoignable: {exc}")
    _invalidate_version_cache()
    output = ((res.stdout or "") + (res.stderr or "")).strip()
    lowered = output.lower()
    up_to_date: Optional[bool] = None
    if any(s in lowered for s in ("up to date", "up-to-date", "à jour", "already")):
        up_to_date = True
    elif any(s in lowered for s in ("update available", "new version", "mise à jour disponible", "behind")):
        up_to_date = False
    return UpdateCheckResult(up_to_date=up_to_date, output=output[:2000])
