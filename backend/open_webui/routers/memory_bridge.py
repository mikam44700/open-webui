"""Router /api/v1/memory — Mémoire / Second Cerveau (Agent OS).

Admin-only. Proxifie vers le Providers Bridge (qui accède au coffre Obsidian, source de vérité).
Surface DISTINCTE de la mémoire native d'OpenWebUI (router ``memories``, désactivée via
``ENABLE_MEMORIES=false``). Lecture + correction humaine. Cf. specs/005-memoire.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class NoteWriteBody(BaseModel):
    path: str
    content: str


class InboxNoteBody(BaseModel):
    title: str
    content: str


@router.get("/tree")
async def memory_tree(user=Depends(get_admin_user)):
    """Arborescence du coffre (dossiers métier + notes)."""
    return await _bridge("GET", "/memory/tree")


@router.get("/status")
async def memory_status(user=Depends(get_admin_user)):
    """Statut honnête du coffre."""
    return await _bridge("GET", "/memory/status")


@router.get("/note")
async def memory_note(path: str, user=Depends(get_admin_user)):
    """Contenu d'une note (``path`` relatif au coffre)."""
    return await _bridge("GET", f"/memory/note?path={quote(path)}")


@router.post("/note")
async def write_memory_note(body: NoteWriteBody, user=Depends(get_admin_user)):
    """Crée/corrige une note (relecture/correction humaine)."""
    return await _bridge("POST", "/memory/note", json=body.model_dump())


@router.post("/init")
async def init_memory_vault(user=Depends(get_admin_user)):
    """Crée la structure PARA du coffre (00-Réception, 01-Projets, … + INDEX). Idempotent."""
    return await _bridge("POST", "/memory/init")


@router.post("/inbox")
async def write_inbox_note(body: InboxNoteBody, user=Depends(get_admin_user)):
    """Dépose une note dans la Boîte de réception (zone d'écriture sûre de l'agent)."""
    return await _bridge("POST", "/memory/inbox", json=body.model_dump())
