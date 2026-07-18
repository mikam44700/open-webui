"""Réglages du cerveau de l'assistant (feature 017).

Expose Persona (SOUL.md), Profil (USER.md) et Souvenirs (MEMORY.md) — les trois fichiers que
le moteur Hermes lit à chaque conversation — en versions francisées pour le dirigeant.
Zéro modif du moteur : accès fichier direct via ``brain_adapter``. Aucun backend mémoire externe.

Erreurs : ``HTTPException`` avec ``detail = {"error": {"code", "message"}}`` (comme l'existant).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import brain_adapter
from ..deps import require_bridge_key
from ..models import (
    MemoryEntriesResponse,
    MemoryEntry,
    MemoryEntryBody,
    PersonaContent,
    PersonaWriteBody,
    ProfileContent,
    ProfileWriteBody,
)

router = APIRouter(dependencies=[Depends(require_bridge_key)])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})


def _entries_response(result: tuple[list[dict], int, int]) -> MemoryEntriesResponse:
    entries, char_count, char_limit = result
    return MemoryEntriesResponse(
        entries=[MemoryEntry(**e) for e in entries],
        char_count=char_count,
        char_limit=char_limit,
    )


# ── Persona (SOUL.md) ────────────────────────────────────────────────────────


@router.get("/memory/persona")
def get_persona() -> PersonaContent:
    """Personnalité de l'assistant (vide si non encore définie)."""
    try:
        return PersonaContent(content=brain_adapter.read_persona())
    except OSError as exc:
        raise _err(502, "engine_unreadable", f"lecture impossible: {exc}")


@router.put("/memory/persona")
def put_persona(body: PersonaWriteBody) -> PersonaContent:
    """Écrit la personnalité (sauvegarde explicite ; refuse d'écraser par du vide sans intention)."""
    try:
        return PersonaContent(content=brain_adapter.write_persona(body.content, body.allow_empty))
    except brain_adapter.EmptyOverwriteError:
        raise _err(400, "empty_overwrite", "refus d'effacer la personnalité existante par du vide")
    except OSError as exc:
        raise _err(502, "engine_unwritable", f"écriture impossible: {exc}")


@router.post("/memory/persona/reset")
def reset_persona() -> PersonaContent:
    """Retourne le gabarit FR par défaut à charger dans l'éditeur (n'écrit PAS sur disque)."""
    return PersonaContent(content=brain_adapter.default_persona())


# ── Profil (USER.md) ─────────────────────────────────────────────────────────


@router.get("/memory/profile")
def get_profile() -> ProfileContent:
    """Profil du dirigeant + compteurs."""
    try:
        content, count, limit = brain_adapter.read_profile()
        return ProfileContent(content=content, char_count=count, char_limit=limit)
    except OSError as exc:
        raise _err(502, "engine_unreadable", f"lecture impossible: {exc}")


@router.put("/memory/profile")
def put_profile(body: ProfileWriteBody) -> ProfileContent:
    """Écrit le profil. 413 si trop long (message doux côté UI, saisie non perdue)."""
    try:
        content, count, limit = brain_adapter.write_profile(body.content)
        return ProfileContent(content=content, char_count=count, char_limit=limit)
    except brain_adapter.TooLongError as exc:
        raise _err(413, "too_long", f"c'est un peu long ({exc.char_count}/{exc.char_limit})")
    except OSError as exc:
        raise _err(502, "engine_unwritable", f"écriture impossible: {exc}")


# ── Souvenirs (MEMORY.md) ────────────────────────────────────────────────────


@router.get("/memory/entries")
def get_entries() -> MemoryEntriesResponse:
    """Liste des souvenirs + compteurs."""
    try:
        return _entries_response(brain_adapter.list_entries())
    except OSError as exc:
        raise _err(502, "engine_unreadable", f"lecture impossible: {exc}")


@router.post("/memory/entries")
def post_entry(body: MemoryEntryBody) -> MemoryEntriesResponse:
    """Ajoute un souvenir. 413 si dépassement de la limite totale."""
    try:
        return _entries_response(brain_adapter.add_entry(body.content))
    except brain_adapter.TooLongError as exc:
        raise _err(413, "too_long", f"mémoire pleine ({exc.char_count}/{exc.char_limit})")


@router.put("/memory/entries/{index}")
def put_entry(index: int, body: MemoryEntryBody) -> MemoryEntriesResponse:
    """Modifie le souvenir ``index``. 404 si hors bornes, 409 si l'entrée a changé depuis le
    dernier ``GET`` (``expected_content`` fourni et divergent — voir ``EntryConflictError``),
    413 si dépassement."""
    try:
        return _entries_response(
            brain_adapter.update_entry(index, body.content, body.expected_content)
        )
    except brain_adapter.EntryNotFoundError:
        raise _err(404, "not_found", f"souvenir introuvable: {index}")
    except brain_adapter.EntryConflictError:
        raise _err(
            409,
            "entry_conflict",
            "ce souvenir a changé depuis l'affichage, rafraîchis puis réessaie",
        )
    except brain_adapter.TooLongError as exc:
        raise _err(413, "too_long", f"mémoire pleine ({exc.char_count}/{exc.char_limit})")


@router.delete("/memory/entries/{index}")
def delete_entry(
    index: int, expected_content: str | None = Query(default=None)
) -> MemoryEntriesResponse:
    """Supprime le souvenir ``index`` (la confirmation est côté UI). 404 si hors bornes, 409 si
    l'entrée a changé depuis le dernier ``GET`` (``expected_content`` fourni et divergent)."""
    try:
        return _entries_response(brain_adapter.remove_entry(index, expected_content))
    except brain_adapter.EntryNotFoundError:
        raise _err(404, "not_found", f"souvenir introuvable: {index}")
    except brain_adapter.EntryConflictError:
        raise _err(
            409,
            "entry_conflict",
            "ce souvenir a changé depuis l'affichage, rafraîchis puis réessaie",
        )
