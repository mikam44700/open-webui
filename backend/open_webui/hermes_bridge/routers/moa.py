"""Mixture of Agents : configuration + activation (feature 018-multi-agents).

Expose la config du provider natif « moa » du moteur : proposeurs + agrégateur, et
l'activation (met MoA comme cerveau actif). Zéro modif moteur (cf. moa_adapter).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import moa_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..hermes_adapter import HermesUnavailable

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/moa/config")
def moa_get_config() -> dict:
    """Config MoA courante : proposeurs, agrégateur, activé/actif."""
    try:
        return moa_adapter.get_config()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/moa/config")
def moa_set_config(body: dict) -> dict:
    """Enregistre le preset MoA (≥2 proposeurs + 1 agrégateur, pas de récursion)."""
    try:
        return moa_adapter.set_config(body.get("reference_models"), body.get("aggregator"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_moa_config", "message": str(exc)}},
        )
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/moa/activate")
def moa_activate() -> dict:
    """Active MoA comme cerveau (le chat l'utilise alors automatiquement)."""
    try:
        return moa_adapter.activate()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/moa/deactivate")
def moa_deactivate() -> dict:
    """Éteint MoA : revient au cerveau précédent (ou au 1er connecté)."""
    try:
        return moa_adapter.deactivate()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "no_previous_brain", "message": str(exc)}},
        )
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)
