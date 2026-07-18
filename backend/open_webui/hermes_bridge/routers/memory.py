"""Mémoire / Second Cerveau (feature 005).

Le coffre Obsidian (dossier de fichiers .md) est la seule mémoire du produit. Lecture +
correction humaine, initialisation de la structure PARA, et dépôt en Boîte de réception
(zone d'écriture autonome de l'agent). Chemins toujours relatifs au coffre, confinés
(anti path traversal).
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException

from .. import memory_adapter, search_adapter, sync_adapter
from ..deps import require_bridge_key
from ..models import (
    FolderCreateBody,
    FolderMoveBody,
    FolderRenameBody,
    FolderRestoreBody,
    InboxNoteBody,
    ManagedNoteBody,
    MemoryInitResponse,
    MemoryNode,
    MemoryStatus,
    MemoryTreeResponse,
    NoteContent,
    NoteMoveBody,
    NoteRenameBody,
    NoteRestoreBody,
    NoteWriteBody,
    SearchBody,
    SearchResponse,
    TrashResponse,
)

router = APIRouter(dependencies=[Depends(require_bridge_key)])
logger = logging.getLogger(__name__)


def _touch_search_index(rel_path: str) -> None:
    """Met à jour l'index de recherche pour une note écrite (best-effort).

    L'index FTS5 est un cache : une erreur d'indexation ne doit JAMAIS faire échouer l'écriture
    d'une note (le coffre reste la source de vérité). D'où le try/except silencieux — mais
    journalisé, sinon un index qui dérive silencieusement du coffre réel (une note introuvable
    en recherche alors qu'elle existe) est indiscernable d'un simple "rien à chercher".
    """
    try:
        search_adapter.upsert_note(rel_path)
    except Exception:  # noqa: BLE001 — cache non critique, ne jamais casser une écriture
        logger.warning("indexation FTS5 échouée pour %r (note écrite normalement)", rel_path, exc_info=True)


def _reindex_folder_subtree(old_prefix: str | None, new_prefix: str | None) -> None:
    """Réindexe (best-effort) le SEUL sous-arbre déplacé/renommé/supprimé/restauré.

    Un renommage/déplacement/suppression/restauration de dossier ne change JAMAIS le reste du
    coffre : reconstruire tout l'index (potentiellement des milliers de notes) pour ça serait un
    gaspillage. ``search_adapter.reindex_subtree`` purge l'ancien préfixe et/ou réindexe le nouveau
    selon l'opération (voir sa docstring) ; retombe sur une reconstruction complète si l'index est
    absent. Jamais bloquant (cache non critique, ne doit jamais casser l'opération sur le dossier).
    """
    try:
        search_adapter.reindex_subtree(old_prefix=old_prefix, new_prefix=new_prefix)
    except Exception:  # noqa: BLE001 — cache non critique, ne jamais casser l'opération
        logger.warning(
            "réindexation FTS5 échouée (old_prefix=%r, new_prefix=%r) — opération dossier appliquée quand même",
            old_prefix,
            new_prefix,
            exc_info=True,
        )


def _restore_conflict_or_bad_path(exc: ValueError, kind: str) -> HTTPException:
    """Traduit l'échec d'une restauration en réponse HTTP lisible par le dirigeant.

    Un ``RestoreConflict`` n'est pas une erreur de chemin mais un conflit : quelque chose occupe
    déjà la place d'origine. On refuse plutôt que d'écraser (l'écrasement ferait perdre le
    contenu actuel sans que personne ne l'ait demandé). Distingué par son TYPE dédié
    (``memory_adapter.RestoreConflict``), pas par un match littéral du message d'exception — un
    futur changement de texte ne doit jamais faire régresser silencieusement le code HTTP.
    """
    if isinstance(exc, memory_adapter.RestoreConflict):
        return HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "destination_exists",
                    "message": (
                        f"un {kind} porte déjà ce nom à cet endroit — renommez-le, "
                        "puis restaurez à nouveau"
                    ),
                }
            },
        )
    return HTTPException(
        status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
    )


def _note_conflict_or_bad_path(exc: ValueError) -> HTTPException:
    """Traduit un échec d'écriture de note en réponse HTTP lisible (même principe que
    ``_restore_conflict_or_bad_path``).

    Un ``NoteConflict`` n'est pas un chemin invalide mais un conflit de concurrence : la note a
    changé depuis la dernière lecture de l'appelant (autre éditeur ouvert, agent, synchro). On
    refuse plutôt que d'écraser ce travail. Distingué par son TYPE dédié
    (``memory_adapter.NoteConflict``), pas par un match littéral du message d'exception.
    """
    if isinstance(exc, memory_adapter.NoteConflict):
        return HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "note_conflict",
                    "message": (
                        "cette note a changé depuis son ouverture — rechargez-la avant "
                        "d'enregistrer, pour ne pas écraser la dernière version"
                    ),
                }
            },
        )
    return HTTPException(
        status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
    )


@router.get("/memory/tree")
def get_memory_tree() -> MemoryTreeResponse:
    """Arborescence du coffre (dossiers métier + notes), sans le contenu des notes."""
    return MemoryTreeResponse(tree=memory_adapter.read_tree())


@router.get("/memory/trash")
def get_memory_trash() -> TrashResponse:
    """Corbeille : notes/dossiers supprimés dans LunarIA, récupérables (récents d'abord)."""
    return TrashResponse(items=memory_adapter.list_trash())


@router.delete("/memory/trash/item")
def purge_memory_trash_item(ref: str) -> dict:
    """Suppression DÉFINITIVE d'un élément de la corbeille (irréversible, confirmée côté UI).

    Le produit ne purge jamais tout seul : c'est le dirigeant qui décide d'aller au bout.
    """
    try:
        memory_adapter.purge_trash_item(ref)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"élément introuvable: {ref}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    return {"ok": True, "ref": ref}


@router.delete("/memory/trash")
def empty_memory_trash() -> dict:
    """Vide la corbeille (définitif). Ne touche que les éléments visibles dans LunarIA."""
    return {"ok": True, "purged": memory_adapter.empty_trash()}


@router.get("/memory/status")
def get_memory_status() -> MemoryStatus:
    """Statut honnête du coffre (accessible, nombre de notes, copie locale reliée ou non)."""
    return memory_adapter.status()


@router.post("/memory/init")
def init_memory_vault() -> MemoryInitResponse:
    """Crée la structure PARA du coffre (00-Réception, 01-En cours, … + INDEX). Idempotent.

    Indexe aussi (best-effort) l'INDEX et les notes-guides fraîchement posées : sinon elles restent
    invisibles à la recherche tant qu'aucune AUTRE écriture ne les touche individuellement (l'index
    FTS5 déjà présent ne se reconstruit jamais tout seul).
    """
    created = memory_adapter.ensure_structure()
    for rel_path in created:
        if rel_path.endswith(memory_adapter.NOTE_SUFFIX):
            _touch_search_index(rel_path)
    return MemoryInitResponse(created=created)


@router.post("/memory/folder")
def create_memory_folder(body: FolderCreateBody) -> MemoryNode:
    """Crée un dossier dans le coffre (rangement manuel du dirigeant, sans collision)."""
    try:
        return memory_adapter.create_folder(body.parent, body.name)
    except memory_adapter.FolderConflict as exc:
        # Type dédié (sous-classe de ValueError, cf. RestoreConflict) : conflit hors-process
        # malgré le _VAULT_LOCK — jamais un 500 brut, un 409 propre.
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "already_exists", "message": str(exc)}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )


@router.get("/memory/note")
def get_memory_note(path: str) -> NoteContent:
    """Contenu d'une note (``path`` relatif au coffre)."""
    try:
        return memory_adapter.read_note(path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"note introuvable: {path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )


@router.post("/memory/note")
def write_memory_note(body: NoteWriteBody) -> NoteContent:
    """Crée ou corrige une note (relecture/correction humaine du Second Cerveau).

    409 (``note_conflict``) si ``expected_modified`` est fourni et ne correspond plus au fichier
    (modifié depuis l'ouverture — voir ``memory_adapter.NoteConflict``) : on refuse d'écraser
    plutôt que de perdre le travail fait entre-temps par un autre éditeur, l'agent, ou une synchro.
    """
    try:
        note = memory_adapter.write_note(body.path, body.content, body.expected_modified)
    except ValueError as exc:
        raise _note_conflict_or_bad_path(exc)
    _touch_search_index(note.path)
    return note


@router.delete("/memory/note")
def delete_memory_note(path: str) -> dict:
    """Suppression DOUCE d'une note (déplacée en corbeille, récupérable via /restore)."""
    try:
        trash_ref = memory_adapter.delete_note(path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"note introuvable: {path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _touch_search_index(path)  # fichier absent → la note sort de l'index FTS5
    return {"ok": True, "path": path, "trash_ref": trash_ref}


@router.post("/memory/note/restore")
def restore_memory_note(body: NoteRestoreBody) -> NoteContent:
    """Restaure une note supprimée (annulation) depuis la corbeille."""
    try:
        note = memory_adapter.restore_note(body.trash_ref, body.path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "note introuvable en corbeille"}},
        )
    except ValueError as exc:
        raise _restore_conflict_or_bad_path(exc, "note")
    _touch_search_index(note.path)
    return note


@router.post("/memory/note/rename")
def rename_memory_note(body: NoteRenameBody) -> NoteContent:
    """Renomme une note (titre lisible, même dossier)."""
    try:
        note = memory_adapter.rename_note(body.path, body.title)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"note introuvable: {body.path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _touch_search_index(body.path)  # ancien chemin retiré de l'index
    _touch_search_index(note.path)  # nouveau chemin ajouté
    return note


@router.post("/memory/note/move")
def move_memory_note(body: NoteMoveBody) -> NoteContent:
    """Déplace une note vers un autre dossier du coffre (rangement)."""
    try:
        note = memory_adapter.move_note(body.path, body.dest)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"note introuvable: {body.path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _touch_search_index(body.path)  # ancien chemin retiré de l'index
    _touch_search_index(note.path)  # nouveau chemin ajouté
    return note


@router.post("/memory/folder/rename")
def rename_memory_folder(body: FolderRenameBody) -> MemoryNode:
    """Renomme un dossier (non structurel). Les dossiers PARA du squelette sont protégés (400)."""
    try:
        node = memory_adapter.rename_folder(body.path, body.name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"dossier introuvable: {body.path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _reindex_folder_subtree(old_prefix=body.path, new_prefix=node.path)
    return node


@router.post("/memory/folder/move")
def move_memory_folder(body: FolderMoveBody) -> MemoryNode:
    """Déplace un dossier vers un autre parent (« » = racine). PARA/Réception protégés (400)."""
    try:
        node = memory_adapter.move_folder(body.path, body.dest)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"dossier introuvable: {body.path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _reindex_folder_subtree(old_prefix=body.path, new_prefix=node.path)
    return node


@router.delete("/memory/folder")
def delete_memory_folder(path: str) -> dict:
    """Suppression DOUCE d'un dossier (corbeille, récupérable). Dossiers PARA protégés (400)."""
    try:
        trash_ref = memory_adapter.delete_folder(path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"dossier introuvable: {path}"}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "bad_path", "message": str(exc)}}
        )
    _reindex_folder_subtree(old_prefix=path, new_prefix=None)
    return {"ok": True, "path": path, "trash_ref": trash_ref}


@router.post("/memory/folder/restore")
def restore_memory_folder(body: FolderRestoreBody) -> MemoryNode:
    """Restaure un dossier supprimé (annulation) depuis la corbeille."""
    try:
        node = memory_adapter.restore_folder(body.trash_ref, body.path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "dossier introuvable en corbeille"}},
        )
    except ValueError as exc:
        raise _restore_conflict_or_bad_path(exc, "dossier")
    _reindex_folder_subtree(old_prefix=None, new_prefix=node.path)
    return node


@router.post("/memory/search")
def search_memory(body: SearchBody) -> SearchResponse:
    """Recherche par mot dans les notes du coffre (spec 020).

    Retourne des résultats LISIBLES (titre + chemin + extrait) pour qu'Adam relise puis cite par
    titre. ``results: []`` si rien trouvé (Adam dira « le coffre n'a pas cette information »).
    """
    if not body.query or not body.query.strip():
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "empty_query", "message": "requête vide"}},
        )
    try:
        results = search_adapter.search(body.query, limit=body.limit)
    except Exception as exc:  # noqa: BLE001 — statut honnête : jamais de 500 brut sur la recherche
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "search_unavailable",
                    "message": "recherche momentanément indisponible, réessayez",
                }
            },
        ) from exc
    return SearchResponse(ok=True, query=body.query, results=results, count=len(results))


@router.get("/memory/sync/pack")
def get_sync_pack() -> dict:
    """Pack Syncthing PRÉ-APPAIRÉ pour connecter le coffre du client (feature 005 US5).

    Le client télécharge ce zip → lance install.sh → son Syncthing se connecte tout seul au coffre.
    Renvoyé en base64 (le pack fait quelques Ko). 503 si la synchro n'est pas encore provisionnée.
    """
    try:
        filename, content = sync_adapter.generate_client_pack()
    except sync_adapter.SyncUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "sync_unavailable", "message": str(exc)}},
        )
    return {
        "filename": filename,
        "content_b64": base64.b64encode(content).decode("ascii"),
        "size": len(content),
    }


@router.post("/memory/inbox")
def write_inbox_note(body: InboxNoteBody) -> NoteContent:
    """Dépose une note dans la Boîte de réception (00-Réception) — zone d'écriture sûre de l'agent.

    Le dirigeant relit puis classe. N'écrase jamais une note existante.
    """
    note = memory_adapter.write_inbox_note(body.title, body.content)
    _touch_search_index(note.path)
    return note


@router.post("/memory/managed-note")
def upsert_managed_note(body: ManagedNoteBody) -> NoteContent:
    """Crée ou met à jour une note GÉRÉE (identité ``note_id``) — idempotent.

    Pour les notes que le produit réécrit à chaque rejeu (fiche entreprise de l'onboarding) : la
    note est mise à jour sur place, où que le dirigeant l'ait rangée. Aucun doublon, jamais.
    """
    try:
        note = memory_adapter.upsert_managed_note(body.note_id, body.title, body.content)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "empty_content", "message": str(exc)}},
        )
    _touch_search_index(note.path)
    return note
