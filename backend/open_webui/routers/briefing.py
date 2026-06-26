"""Router /api/v1/briefing — Briefing du jour assemblé par Hermes (feature 015).

Admin-only. Proxifie vers le Providers Bridge (``/briefing``), qui agrège agenda + tâches +
automatisations de façon déterministe. Aligné sur le « briefing matinal » de la VISION.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_briefing(user=Depends(get_admin_user)):
    """Briefing du jour (agenda + tâches + automatisations)."""
    return await _bridge("GET", "/briefing")
