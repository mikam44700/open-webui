"""Router /api/v1/moa — Mixture of Agents piloté par Hermes (feature 018-multi-agents).

Admin-only. Proxifie vers le Providers Bridge (``/moa/*``), qui lit/écrit le preset MoA
du moteur (proposeurs + agrégateur) et l'active comme cerveau. Zéro modif moteur.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/config")
async def moa_config(user=Depends(get_admin_user)):
    """Config MoA courante : proposeurs, agrégateur, activé/actif."""
    return await _bridge("GET", "/moa/config")


@router.post("/config")
async def set_moa_config(body: dict, user=Depends(get_admin_user)):
    """Enregistre le preset MoA (≥2 proposeurs + 1 agrégateur)."""
    return await _bridge("POST", "/moa/config", json=body)


@router.post("/activate")
async def activate_moa(user=Depends(get_admin_user)):
    """Active MoA comme cerveau (le chat l'utilise alors automatiquement)."""
    return await _bridge("POST", "/moa/activate")
