"""Automatisations (feature 013) — pilote le planificateur (cron) natif de Hermes.

Page « Automatisations » d'Agent OS : le dirigeant voit/crée/modifie/active/déclenche ses
automatisations, exécutées par Hermes (source de vérité unique). Le bridge relaie vers
l'API jobs d'Hermes et épure les secrets (cf. automations_adapter).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import automations_adapter
from ..automations_adapter import AutomationInvalid, AutomationNotFound
from ..deps import hermes_unavailable, require_bridge_key
from ..hermes_adapter import HermesUnavailable
from ..schemas import AutomationCreate, AutomationUpdate

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": "automatisation inconnue"}},
    )


def _invalid(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": {"code": "invalid", "message": str(exc) or "données invalides"}},
    )


@router.get("/automations")
def list_automations(expert: bool = False) -> dict:
    """Liste les automatisations réelles connues d'Hermes."""
    try:
        return {"automations": automations_adapter.list_automations(expert)}
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/automations/{automation_id}")
def get_automation(automation_id: str, expert: bool = False) -> dict:
    try:
        return {"automation": automations_adapter.get_automation(automation_id, expert)}
    except AutomationNotFound:
        raise _not_found()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/automations")
def create_automation(body: AutomationCreate, expert: bool = False) -> dict:
    try:
        automation = automations_adapter.create_automation(body.model_dump(), expert)
        return {"automation": automation}
    except AutomationInvalid as exc:
        raise _invalid(exc)
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.patch("/automations/{automation_id}")
def update_automation(automation_id: str, body: AutomationUpdate, expert: bool = False) -> dict:
    try:
        automation = automations_adapter.update_automation(
            automation_id, body.model_dump(exclude_unset=True), expert
        )
        return {"automation": automation}
    except AutomationNotFound:
        raise _not_found()
    except AutomationInvalid as exc:
        raise _invalid(exc)
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/automations/{automation_id}/pause")
def pause_automation(automation_id: str, expert: bool = False) -> dict:
    try:
        return {"automation": automations_adapter.pause_automation(automation_id, expert)}
    except AutomationNotFound:
        raise _not_found()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/automations/{automation_id}/resume")
def resume_automation(automation_id: str, expert: bool = False) -> dict:
    try:
        return {"automation": automations_adapter.resume_automation(automation_id, expert)}
    except AutomationNotFound:
        raise _not_found()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/automations/{automation_id}/run")
def run_automation(automation_id: str, expert: bool = False) -> dict:
    """« Lancer maintenant » : programme l'exécution au prochain passage du planificateur."""
    try:
        automation = automations_adapter.run_automation(automation_id, expert)
        return {
            "automation": automation,
            "queued": True,
            "message": "Lancement programmé à l'instant",
        }
    except AutomationNotFound:
        raise _not_found()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.delete("/automations/{automation_id}")
def delete_automation(automation_id: str) -> dict:
    try:
        return automations_adapter.delete_automation(automation_id)
    except AutomationNotFound:
        raise _not_found()
    except HermesUnavailable as exc:
        raise hermes_unavailable(exc)
