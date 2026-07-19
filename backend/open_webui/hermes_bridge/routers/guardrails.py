"""Router Garde-fous (chantier Guardrails) : état des protections + file d'approbation mémoire.

Monté sous /api/v1/guardrails, admin-only (même garde que les autres routers bridge :
``require_bridge_key`` surchargé par ``get_admin_user`` dans main.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import guardrails_adapter, hermes_adapter
from ..deps import hermes_unavailable, require_bridge_key

router = APIRouter(dependencies=[Depends(require_bridge_key)])


class MemoryDecisionBody(BaseModel):
    """Cible d'une décision sur la file mémoire : un id précis ou ``all``."""

    id: str


@router.get("/guardrails")
def get_guardrails() -> dict:
    """État des protections (disjoncteur, approbation mémoire, compteur en attente)."""
    try:
        return guardrails_adapter.get_state()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/guardrails/arm")
def arm_guardrails() -> dict:
    """Arme les protections (idempotent) et renvoie l'état à jour."""
    try:
        return guardrails_adapter.arm()
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/guardrails/memory/pending")
def get_pending_memory() -> dict:
    """Écritures mémoire en attente d'approbation."""
    try:
        return {"pending": guardrails_adapter.list_pending_memory()}
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/guardrails/memory/approve")
def approve_memory(body: MemoryDecisionBody) -> dict:
    """Approuve une écriture (l'applique réellement à la mémoire, puis la retire de la file)."""
    try:
        return guardrails_adapter.decide_memory(body.id, "approve")
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/guardrails/memory/reject")
def reject_memory(body: MemoryDecisionBody) -> dict:
    """Rejette une écriture en attente (retirée de la file, la mémoire reste inchangée)."""
    try:
        return guardrails_adapter.decide_memory(body.id, "reject")
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
