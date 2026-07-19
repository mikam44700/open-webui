"""Pré-connexion du MCP « recherche-entreprises » (la porte entreprises de data.gouv).

Le MCP officiel data.gouv ne couvre que le catalogue de datasets : pour LISTER des
entreprises (SIREN, nom, dirigeants), la bonne porte est l'API publique officielle
recherche-entreprises.api.gouv.fr — sans MCP hébergé. Notre mini-serveur MCP stdio
(``hermes_skills/lunaria-app/prospection-lunaria/entreprises_mcp.py``, embarqué dans
l'image) fait ce pont ; ce module le DÉCLARE dans la config Hermes au démarrage.

Même esprit que ``crawl4ai_adapter.start_preconnect_if_managed`` : uniquement en mode
géré (stack deploy/), thread daemon non bloquant, idempotent (déjà déclaré = no-op).
L'enregistrement passe par ``mcp_adapter.add_custom`` — exactement le chemin du bouton
« Installer » de l'interface, validation de sécurité Hermes comprise. Tout est additif :
on n'écrase ni ne supprime jamais un connecteur existant.

Au passage, on garantit aussi le connecteur ``data-gouv-fr`` (catalogue officiel,
HTTP) : sur le poste de Michael il vient du seed ~/.hermes, mais une installation
client neuve n'a pas ce seed — sans ce filet, les agents n'auraient pas data.gouv.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from . import hermes_adapter, mcp_adapter

logger = logging.getLogger(__name__)

# Même marqueur de déploiement que crawl4ai_adapter : la stack deploy/ pose CRAWL4AI_MANAGED=1.
MANAGED = os.environ.get("CRAWL4AI_MANAGED", "").strip().lower() in ("1", "true", "yes")

MCP_NAME = "recherche-entreprises"
DATAGOUV_NAME = "data-gouv-fr"
DATAGOUV_URL = "https://mcp.data.gouv.fr/mcp"
# Chemin IMAGE (lecture seule, versionné) — pas la copie du volume, modifiable par l'utilisateur.
SERVER_PATH = Path("/app/backend/hermes_skills/lunaria-app/prospection-lunaria/entreprises_mcp.py")


def _ensure(name: str, **kwargs) -> None:
    """Déclare le connecteur s'il manque ; silencieux s'il existe déjà (idempotent)."""
    try:
        if name in mcp_adapter._load_mcp_servers():
            return
        mcp_adapter.add_custom(name, **kwargs)
        logger.info("connecteur MCP « %s » déclaré (pré-connexion LunarIA).", name)
    except mcp_adapter.NameConflict:
        pass  # course bénigne : déjà déclaré entre le check et l'ajout


def _preconnect(attempts: int = 3) -> None:
    """Quelques tentatives espacées : add_custom valide via le venv Hermes, prêt ou presque."""
    for i in range(attempts):
        try:
            _ensure(
                MCP_NAME,
                transport="stdio",
                command=hermes_adapter.HERMES_PYTHON,
                args=[str(SERVER_PATH)],
            )
            _ensure(DATAGOUV_NAME, transport="http", url=DATAGOUV_URL)
            logger.info("MCP entreprises pré-connectés (mode géré).")
            return
        except Exception:  # noqa: BLE001 — on retente, puis on laisse la main aux logs
            logger.warning(
                "pré-connexion MCP entreprises échouée (tentative %d/%d)",
                i + 1, attempts, exc_info=True,
            )
            time.sleep(30)
    logger.error("MCP « recherche-entreprises » n'a pas pu être déclaré au démarrage.")


def start_preconnect_if_managed() -> None:
    """No-op hors mode géré (dev local : on ne touche jamais au ~/.hermes du poste)."""
    if not MANAGED:
        return
    if not SERVER_PATH.exists():
        logger.error("serveur MCP entreprises introuvable dans l'image : %s", SERVER_PATH)
        return
    threading.Thread(target=_preconnect, name="entreprises-preconnect", daemon=True).start()
