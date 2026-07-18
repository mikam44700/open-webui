"""Helpers Docker / docker-compose partagés (services optionnels à la demande).

Mutualise la plomberie commune aux services installables par bouton (Crawl4AI…) :
résolution du binaire docker, localisation du docker-compose.yml, lancement de `compose`,
détection d'un conteneur en marche.

2 détails « production » gérés ici :
  - docker appelé par CHEMIN ABSOLU (le PATH des services launchd/systemd ne voit pas
    /usr/local/bin) ;
  - chemin du docker-compose.yml configurable via ``AGENTOS_COMPOSE_FILE`` (sinon résolu
    relativement, cas VPS où le bridge tourne depuis le dépôt).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


# Répertoires où vivent docker ET ses credential helpers (docker-credential-desktop…).
# Les services supervisés (launchd/systemd) ont un PATH minimal : sans ces chemins, un
# `docker pull` qui consulte ~/.docker/config.json (credsStore: desktop) échoue avec
# « docker-credential-desktop: executable file not found in $PATH », même pour une image
# publique. On enrichit donc le PATH de tout sous-processus docker.
_DOCKER_PATH_DIRS = (
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    "/Applications/Docker.app/Contents/Resources/bin",
)


def docker_bin() -> str:
    """Chemin absolu de docker (services supervisés = PATH minimal sans /usr/local/bin)."""
    for d in _DOCKER_PATH_DIRS:
        cand = os.path.join(d, "docker")
        if os.path.exists(cand):
            return cand
    return shutil.which("docker") or "docker"


def _docker_env() -> dict:
    """Environnement du sous-processus docker, avec un PATH élargi aux dossiers Docker
    (pour que `docker pull` retrouve son credential helper même sous launchd/systemd)."""
    env = os.environ.copy()
    existing = env.get("PATH", "")
    parts = list(_DOCKER_PATH_DIRS) + ([existing] if existing else [])
    env["PATH"] = ":".join(parts)
    return env


def compose_file() -> Path:
    """Localise le docker-compose.yml. Priorité à ``AGENTOS_COMPOSE_FILE`` (app/.env)."""
    env = os.environ.get("AGENTOS_COMPOSE_FILE")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "docker-compose.yml"
        if cand.exists():
            return cand
    raise FileNotFoundError(
        "docker-compose.yml introuvable — définir AGENTOS_COMPOSE_FILE dans app/.env."
    )


def compose(
    *args: str, timeout: int = 180, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    """Lance `docker compose`. ``extra_env`` injecte des variables (ex. un token) que le
    compose interpole dans le service (``${VAR}``) — utile pour passer un secret au conteneur
    sans l'écrire sur disque."""
    env = _docker_env()
    if extra_env:
        env.update(extra_env)
    cmd = [docker_bin(), "compose", "-f", str(compose_file()), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)


def container_running(name: str) -> bool:
    try:
        r = subprocess.run(
            [docker_bin(), "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=15, env=_docker_env(),
        )
        return name in (r.stdout or "")
    except Exception:
        return False


def remove_image(image: str, timeout: int = 90) -> None:
    """Supprime une image Docker (best-effort, pour libérer l'espace à la désinstallation)."""
    try:
        r = subprocess.run(
            [docker_bin(), "rmi", "-f", image],
            capture_output=True, text=True, timeout=timeout, env=_docker_env(),
        )
        if r.returncode != 0:
            logger.warning(
                "suppression de l'image Docker %s échouée (code %s) — espace disque non libéré : %s",
                image,
                r.returncode,
                (r.stderr or r.stdout or "").strip()[:500],
            )
    except Exception:  # noqa: BLE001 — suppression best-effort, jamais bloquante
        logger.warning("suppression de l'image Docker %s échouée (exception)", image, exc_info=True)


def pull(image: str, timeout: int = 900) -> subprocess.CompletedProcess:
    """`docker pull <image>` — télécharge/rafraîchit l'image (étape longue d'une mise à jour).

    Le PATH élargi (_docker_env) permet au credential helper de fonctionner sous launchd/
    systemd. Timeout large par défaut : une image lourde (Chromium) peut prendre plusieurs
    minutes au premier téléchargement.
    """
    return subprocess.run(
        [docker_bin(), "pull", image],
        capture_output=True, text=True, timeout=timeout, env=_docker_env(),
    )


def container_image(name: str) -> str:
    """Tag de l'image avec laquelle le conteneur ``name`` tourne (vide si conteneur absent).

    Sert à détecter qu'une mise à jour est disponible : si l'image courante du conteneur
    diffère de l'image cible (version épinglée dans le code), une MAJ est proposée.
    """
    try:
        r = subprocess.run(
            [docker_bin(), "inspect", "--format", "{{.Config.Image}}", name],
            capture_output=True, text=True, timeout=15, env=_docker_env(),
        )
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""
