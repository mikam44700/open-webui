"""Briefing Agent OS (feature 015) — endpoint du briefing du jour assemblé par Hermes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import briefing_adapter
from ..deps import require_bridge_key

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/briefing")
def get_briefing() -> dict:
    """Briefing du jour (agenda + tâches + automatisations), structuré + texte."""
    return briefing_adapter.build_briefing()
