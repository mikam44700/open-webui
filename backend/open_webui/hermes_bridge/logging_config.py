"""Configuration centralisée du logging applicatif du bridge.

Avant ce module, aucun ``logging.basicConfig``/``dictConfig`` n'existait nulle part dans
``providers_bridge`` : les quelques ``logger.warning(...)`` déjà présents (``hermes_adapter``,
``mcp_adapter``, ``mcp_registry``, ``routers/agents``, ``routers/crawl4ai``) tombaient sur le
handler de dernier recours de Python (``logging.lastResort``), qui n'a pas de formatter — ni
horodatage, ni niveau, ni nom de module dans la sortie. Sur un VPS client (systemd/journald),
`journald` réinjecte un timestamp indépendamment de l'appli ; mais en dev/macOS (launchd, fichier
plat), rien ne permettait de savoir QUAND un incident avait eu lieu (audit observabilité
2026-07-16, Haute #2).

Appelé une seule fois, au démarrage du process (``main.py``, avant la création de l'app FastAPI).
Idempotent : un second appel (ex. rechargement de module en test) ne duplique pas les handlers.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False

# Format volontairement simple et lisible en `tail -f` : horodatage, niveau, logger, message.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _resolve_level(raw: str | None) -> int:
    """Convertit ``LOG_LEVEL`` (ex. "INFO", "debug", "30") en niveau ``logging``.

    Valeur absente ou invalide → INFO (défaut sûr : ni trop bavard, ni silencieux).
    """
    if not raw:
        return logging.INFO
    candidate = raw.strip().upper()
    level = logging.getLevelName(candidate)
    # getLevelName renvoie une str du type "Level 42" quand `candidate` n'est pas reconnu.
    if isinstance(level, int):
        return level
    return logging.INFO


def configure_logging(*, force: bool = False) -> None:
    """Installe le format + niveau de logging pour tout le process.

    ``LOG_LEVEL`` (variable d'env, défaut ``INFO``) règle le niveau racine — permet de monter en
    ``DEBUG`` à distance chez un client sans redéployer de code. ``force=True`` permet de
    ré-appliquer la config (utile en test, où le root logger peut déjà avoir des handlers hérités
    d'un run précédent dans le même process).
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return
    level = _resolve_level(os.environ.get("LOG_LEVEL"))
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
        force=force,
    )
    _CONFIGURED = True
