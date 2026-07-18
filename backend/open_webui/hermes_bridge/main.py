"""Providers Bridge — service interne (hôte) pilotant Hermes.

Tourne sur l'hôte, à côté de Hermes (accès à la CLI ``hermes`` et à ``~/.hermes/``). Joint par le
backend du fork OpenWebUI via ``host.docker.internal``. Authentifié par clé partagée
(header ``X-Bridge-Key``, comparée à la variable d'env ``BRIDGE_KEY``).

Contrat : specs/001-providers-page/contracts/bridge-api.md
Décisions : specs/001-providers-page/research.md (D2, D3)

Architecture : les endpoints sont découpés par domaine dans ``routers/`` (P8). Ce module ne garde
que la création de l'app, les sondes (/health, /ready) et l'inclusion des routers. L'auth par clé
partagée est appliquée au niveau de chaque router (``Depends(require_bridge_key)``).
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI

from .deps import require_bridge_key
from .logging_config import configure_logging
from .routers import (
    agents,
    automations,
    brain,
    briefing,
    calendar,
    capabilities,
    crawl4ai,
    gateway,
    google_services,
    hermes,
    integrations,
    kanban,
    mcp,
    memory,
    moa,
    oauth,
    onboarding,
    providers,
)


def _docs_enabled() -> bool:
    """Docs interactives (``/docs``, ``/redoc``, ``/openapi.json``) réservées au dev.

    Ces routes sont ajoutées par FastAPI **en dehors** des routers, donc jamais couvertes par
    ``Depends(require_bridge_key)`` (appliqué routeur par routeur, cf. docstring du module) :
    les laisser actives par défaut expose sans authentification tout le schéma des ~90 endpoints
    du bridge (chemins, paramètres, modèles Pydantic) à quiconque atteint le port — audit sécurité
    Haute #2 (2026-07-15). N'active ces routes que si ``BRIDGE_DEV=1`` est posé explicitement
    (jamais en production).
    """
    return os.environ.get("BRIDGE_DEV") == "1"


_DEV_MODE = _docs_enabled()

# Doit être installé AVANT tout logger applicatif (import des routers ci-dessus les crée déjà,
# mais aucun n'émet de log à l'import) — sinon les premiers logs de démarrage retombent sur le
# handler de dernier recours de Python (sans horodatage/niveau). Cf. logging_config.py.
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Providers Bridge",
    version="0.1.0",
    docs_url="/docs" if _DEV_MODE else None,
    redoc_url="/redoc" if _DEV_MODE else None,
    openapi_url="/openapi.json" if _DEV_MODE else None,
)


@app.on_event("startup")
def _prewarm_mcp_catalog() -> None:
    """Préchauffe le catalogue MCP (55 manifests) en arrière-plan dès le démarrage, pour que
    la page MCP soit instantanée — sinon le 1er chargement après (re)démarrage attend ~9 s."""
    from . import mcp_registry

    try:
        mcp_registry.prewarm()
    except Exception:  # noqa: BLE001 — le préchauffage ne doit jamais bloquer le démarrage
        logger.warning("préchauffage du catalogue MCP échoué (non bloquant)", exc_info=True)


@app.get("/health")
def health() -> dict[str, str]:
    """Sonde de vie — publique, sans auth."""
    return {"status": "ok"}


@app.get("/ready", dependencies=[Depends(require_bridge_key)])
def ready() -> dict[str, str]:
    """Endpoint protégé minimal : valide que l'auth par clé partagée fonctionne."""
    return {"status": "authenticated"}


# Routers par domaine (P8) — l'ordre n'affecte pas le routage (chemins distincts).
app.include_router(providers.router)
app.include_router(mcp.router)
app.include_router(capabilities.router)
app.include_router(integrations.router)
app.include_router(oauth.router)
app.include_router(memory.router)
app.include_router(brain.router)
app.include_router(agents.router)
app.include_router(hermes.router)
app.include_router(gateway.router)
app.include_router(kanban.router)
app.include_router(automations.router)
app.include_router(calendar.router)
app.include_router(briefing.router)
app.include_router(google_services.router)
app.include_router(crawl4ai.router)
app.include_router(onboarding.router)
app.include_router(moa.router)
