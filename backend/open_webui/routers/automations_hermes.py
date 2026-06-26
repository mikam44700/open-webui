"""Router /api/v1/automations — Automatisations pilotées par Hermes (feature 013).

Admin-only. Proxifie vers le Providers Bridge (``/automations/*``), qui relaie le
planificateur (cron) natif de Hermes — source de vérité unique. Réutilise le helper
``_bridge`` du router providers (auth admin OpenWebUI + clé partagée du pont).

Remplace la surface native OpenWebUI (``routers/automations.py``, conservée intacte mais
non montée) afin qu'il n'existe qu'une seule logique d'automatisations : celle d'Hermes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


def _q(expert: bool) -> str:
    return "?expert=true" if expert else ""


@router.get("/")
async def list_automations(expert: bool = False, user=Depends(get_admin_user)):
    """Liste les automatisations réelles connues d'Hermes (admin-only)."""
    return await _bridge("GET", f"/automations{_q(expert)}")


@router.get("/{automation_id}")
async def get_automation(automation_id: str, expert: bool = False, user=Depends(get_admin_user)):
    return await _bridge("GET", f"/automations/{automation_id}{_q(expert)}")


@router.post("/")
async def create_automation(body: dict, expert: bool = False, user=Depends(get_admin_user)):
    """Crée une automatisation (instruction + rythme simple)."""
    return await _bridge("POST", f"/automations{_q(expert)}", json=body)


@router.patch("/{automation_id}")
async def update_automation(
    automation_id: str, body: dict, expert: bool = False, user=Depends(get_admin_user)
):
    return await _bridge("PATCH", f"/automations/{automation_id}{_q(expert)}", json=body)


@router.post("/{automation_id}/pause")
async def pause_automation(automation_id: str, expert: bool = False, user=Depends(get_admin_user)):
    return await _bridge("POST", f"/automations/{automation_id}/pause{_q(expert)}")


@router.post("/{automation_id}/resume")
async def resume_automation(automation_id: str, expert: bool = False, user=Depends(get_admin_user)):
    return await _bridge("POST", f"/automations/{automation_id}/resume{_q(expert)}")


@router.post("/{automation_id}/run")
async def run_automation(automation_id: str, expert: bool = False, user=Depends(get_admin_user)):
    """« Lancer maintenant » — programme l'exécution au prochain passage du planificateur."""
    return await _bridge("POST", f"/automations/{automation_id}/run{_q(expert)}")


@router.delete("/{automation_id}")
async def delete_automation(automation_id: str, user=Depends(get_admin_user)):
    """Supprime une automatisation (confirmation côté UI). Propagé à Hermes."""
    return await _bridge("DELETE", f"/automations/{automation_id}")
