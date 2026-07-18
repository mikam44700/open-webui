"""Plugins moteur « maison » (restauration V1) + installeur.

Les plugins vivent ICI, versionnés dans le repo, et sont copiés au démarrage du
backend vers ``$HERMES_HOME/plugins/model-providers/`` — l'emplacement « plugins
utilisateur » du moteur Hermes (cf. ``providers/__init__.py`` du moteur), préservé
par ``hermes update`` qui ne remplace que ``hermes-agent/``. C'est la leçon de la
V1 : ses plugins vivaient DANS le moteur et ont disparu avec son re-clonage du
2026-07-17.

Copie additive et idempotente : on crée/écrase UNIQUEMENT nos propres dossiers de
plugin, on ne supprime jamais rien d'autre chez le client.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

_SRC = Path(__file__).resolve().parent / "model-providers"


def _hermes_home() -> Path:
    return Path(os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes")))


def install_engine_plugins() -> None:
    """Copie les plugins maison vers ``$HERMES_HOME/plugins/model-providers/``.

    Silencieux en cas d'échec (warning en log) : un poste sans moteur Hermes ne
    doit pas empêcher le backend de démarrer.
    """
    if not _SRC.is_dir():
        return
    dst_root = _hermes_home() / "plugins" / "model-providers"
    try:
        dst_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("plugins moteur : impossible de créer %s (%s)", dst_root, exc)
        return
    installed: list[str] = []
    for plugin in sorted(_SRC.iterdir()):
        if not plugin.is_dir() or plugin.name.startswith(("_", ".")):
            continue
        try:
            shutil.copytree(
                plugin,
                dst_root / plugin.name,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            installed.append(plugin.name)
        except OSError as exc:
            log.warning("plugins moteur : copie de %s échouée (%s)", plugin.name, exc)
    if installed:
        log.info("plugins moteur maison installés (%s) → %s", ", ".join(installed), dst_root)
