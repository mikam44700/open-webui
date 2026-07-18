"""Agent Hermes : statut + mise à jour."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import hermes_adapter
from ..deps import hermes_unavailable, require_bridge_key

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/hermes/status")
def hermes_status() -> dict:
    """Vue d'ensemble Hermes : version, cerveau actif, joignabilité."""
    return hermes_adapter.hermes_status()


@router.post("/hermes/update/check")
def hermes_update_check() -> dict:
    """Vérifie si une mise à jour Hermes est disponible (sans rien installer)."""
    try:
        return hermes_adapter.update_check()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/hermes/update/start")
def hermes_update_start() -> dict[str, bool]:
    """Lance la mise à jour Hermes (`hermes update --yes --backup`) en arrière-plan."""
    try:
        hermes_adapter.start_update()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    return {"started": True}


@router.get("/hermes/update/status")
def hermes_update_status() -> dict:
    """État de la mise à jour en cours (running / success / log)."""
    return hermes_adapter.update_status()
