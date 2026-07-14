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


class SearchBody(BaseModel):
    query: str
    limit: int = 8


class NoteRenameBody(BaseModel):
    path: str
    title: str


class NoteRestoreBody(BaseModel):
    trash_ref: str
    path: str


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


@router.post("/search")
async def search_memory(body: SearchBody, user=Depends(get_admin_user)):
    """Recherche par mot dans les notes du coffre (spec 020). Résultats lisibles (titre + chemin)."""
    return await _bridge("POST", "/memory/search", json=body.model_dump())


@router.delete("/note")
async def delete_memory_note(path: str, user=Depends(get_admin_user)):
    """Suppression douce d'une note (déplacée en corbeille, récupérable)."""
    return await _bridge("DELETE", f"/memory/note?path={quote(path)}")


@router.post("/note/rename")
async def rename_memory_note(body: NoteRenameBody, user=Depends(get_admin_user)):
    """Renomme une note (titre lisible, même dossier)."""
    return await _bridge("POST", "/memory/note/rename", json=body.model_dump())


@router.post("/note/restore")
async def restore_memory_note(body: NoteRestoreBody, user=Depends(get_admin_user)):
    """Restaure une note supprimée (annulation)."""
    return await _bridge("POST", "/memory/note/restore", json=body.model_dump())


@router.post("/init")
async def init_memory_vault(user=Depends(get_admin_user)):
    """Crée la structure PARA du coffre (00-Réception, 01-Projets, … + INDEX). Idempotent."""
    return await _bridge("POST", "/memory/init")


@router.post("/inbox")
async def write_inbox_note(body: InboxNoteBody, user=Depends(get_admin_user)):
    """Dépose une note dans la Boîte de réception (zone d'écriture sûre de l'agent)."""
    return await _bridge("POST", "/memory/inbox", json=body.model_dump())


@router.get("/sync/pack")
async def get_sync_pack(user=Depends(get_admin_user)):
    """Pack Syncthing pré-appairé pour connecter le coffre du client (feature 005 US5).

    Renvoie le zip en base64 ; le front le décode et le fait télécharger. 503 si la synchro n'est
    pas encore provisionnée (Syncthing non démarré sur ce serveur)."""
    return await _bridge("GET", "/memory/sync/pack")


# ── Réglages du cerveau (feature 017) : Persona / Profil / Souvenirs ──────────


class ContentBody(BaseModel):
    content: str


class PersonaWriteBody(BaseModel):
    content: str
    allow_empty: bool = False


@router.get("/persona")
async def get_persona(user=Depends(get_admin_user)):
    """Personnalité de l'assistant (SOUL.md)."""
    return await _bridge("GET", "/memory/persona")


@router.put("/persona")
async def put_persona(body: PersonaWriteBody, user=Depends(get_admin_user)):
    """Écrit la personnalité (sauvegarde explicite)."""
    return await _bridge("PUT", "/memory/persona", json=body.model_dump())


@router.post("/persona/reset")
async def reset_persona(user=Depends(get_admin_user)):
    """Gabarit FR par défaut à charger dans l'éditeur (n'écrit pas sur disque)."""
    return await _bridge("POST", "/memory/persona/reset")


@router.get("/profile")
async def get_profile(user=Depends(get_admin_user)):
    """Profil du dirigeant (USER.md)."""
    return await _bridge("GET", "/memory/profile")


@router.put("/profile")
async def put_profile(body: ContentBody, user=Depends(get_admin_user)):
    """Écrit le profil du dirigeant."""
    return await _bridge("PUT", "/memory/profile", json=body.model_dump())


@router.get("/entries")
async def get_entries(user=Depends(get_admin_user)):
    """Liste des souvenirs (MEMORY.md)."""
    return await _bridge("GET", "/memory/entries")


@router.post("/entries")
async def add_entry(body: ContentBody, user=Depends(get_admin_user)):
    """Ajoute un souvenir."""
    return await _bridge("POST", "/memory/entries", json=body.model_dump())


@router.put("/entries/{index}")
async def update_entry(index: int, body: ContentBody, user=Depends(get_admin_user)):
    """Modifie le souvenir ``index``."""
    return await _bridge("PUT", f"/memory/entries/{index}", json=body.model_dump())


@router.delete("/entries/{index}")
async def delete_entry(index: int, user=Depends(get_admin_user)):
    """Supprime le souvenir ``index`` (confirmation côté UI)."""
    return await _bridge("DELETE", f"/memory/entries/{index}")
