"""Router /api/v1/google — services Google additionnels (Chemin A).

Admin-only. Proxifie vers le Providers Bridge (``/google/*``), qui pilote Slides /
Analytics / Search Console directement via ``google_direct`` (jeton Google partagé,
moteur Hermes intact). Source de vérité = Google.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/slides")
async def create_presentation(body: dict, user=Depends(get_admin_user)):
    """Crée une présentation Google Slides (titre + plan optionnel)."""
    return await _bridge("POST", "/google/slides", json=body)
