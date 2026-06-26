"""Router /api/v1/knowledge-agent — pont Connaissances → coffre Hermes (feature 015).

Admin-only. Copie le contenu texte des documents d'une base de connaissances OpenWebUI dans
le **coffre Hermes** (via le bridge ``/memory/note``), pour qu'Agent OS puisse les lire.

Pont volontairement « partiel » : la recherche sémantique (RAG) reste côté OpenWebUI ; ici on
rend seulement le contenu **lisible par Hermes**. Lecture seule du natif (Knowledges/Files) —
rien n'est modifié ni supprimé côté OpenWebUI.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


def _slug(value: str) -> str:
    """Nom de fichier sûr pour le coffre (alphanum, tirets ; pas de traversal)."""
    value = (value or "sans-nom").strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-.") or "sans-nom"


@router.post("/{knowledge_id}/sync-agent")
async def sync_to_agent(
    knowledge_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Rend les documents d'une base de connaissances lisibles par Agent OS (coffre Hermes)."""
    kb = await Knowledges.get_knowledge_by_id(knowledge_id, db=db)
    if not kb:
        raise HTTPException(status_code=404, detail="Base de connaissances introuvable")

    file_ids = (kb.data or {}).get("file_ids", []) if kb.data else []
    base_dir = f"connaissances/{_slug(kb.name)}"
    synced, skipped = 0, 0

    for fid in file_ids:
        try:
            f = await Files.get_file_by_id(fid, db=db)
        except Exception:
            f = None
        content = ((f.data or {}).get("content") if f and f.data else None) or ""
        if not content.strip():
            skipped += 1
            continue
        filename = _slug(getattr(f, "filename", None) or fid)
        title = getattr(f, "filename", None) or fid
        note = f"# {title}\n\n{content}"
        await _bridge("POST", "/memory/note", json={"path": f"{base_dir}/{filename}.md", "content": note})
        synced += 1

    return {"ok": True, "synced": synced, "skipped": skipped, "folder": base_dir}
