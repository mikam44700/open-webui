"""Réglages du cerveau de l'assistant (feature 017) — Persona / Profil / Souvenirs.

Expose en lecture/écriture les TROIS fichiers réels que le moteur Hermes lit à chaque
conversation, SANS modifier le moteur :

- Persona  → ``<HERMES_HOME>/SOUL.md``            (personnalité, texte libre)
- Profil   → ``<HERMES_HOME>/memories/USER.md``   (qui est le dirigeant)
- Souvenirs→ ``<HERMES_HOME>/memories/MEMORY.md`` (faits retenus, entrées ``\\n§\\n``)

On réplique le contrat minimal du moteur (``tools/memory_tool.py``) : délimiteur ``\\n§\\n``,
limites en caractères (MEMORY=2200, USER=1375), verrou fichier ``.lock`` partagé et écriture
ATOMIQUE (``os.replace``) pour éviter l'écrasement mutuel quand l'agent écrit en parallèle.

Garde-fou projet : on n'écrase jamais un contenu non vide par du vide sans intention explicite.

Garde-fou souvenirs : le moteur (``tools/memory_tool.py``) mute ``MEMORY.md`` par correspondance
de CONTENU, le bridge adresse par INDEX (position dans la liste) — deux modes d'adressage
différents sur le même fichier partagé. ``update_entry``/``remove_entry`` acceptent un
``expected_content`` optionnel (concurrence optimiste) : si fourni, il DOIT correspondre au
contenu actuel de l'entrée visée, sinon ``EntryConflictError`` est levée au lieu d'écraser/
supprimer une autre entrée que celle vue par l'appelant.
"""

from __future__ import annotations

from pathlib import Path

from . import fsutil, hermes_adapter

# Contrat moteur (miroir de tools/memory_tool.py) — NE PAS diverger.
ENTRY_DELIMITER = "\n§\n"
MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375

# Personnalité par défaut (FR, à nous) proposée au « Réinitialiser ». Le moteur a la sienne en
# anglais (default_soul.py, non déployée avec le bridge) : on maîtrise le ton français.
DEFAULT_PERSONA_FR = (
    "# Mon assistant\n\n"
    "Tu es mon bras droit au quotidien. Tu vas droit au but, en français clair, "
    "sans jargon.\n\n"
    "## Comment tu m'aides\n\n"
    "- Tu réponds de façon concise et actionnable.\n"
    "- Tu poses une question quand une consigne est ambiguë, plutôt que de deviner.\n"
    "- Tu n'inventes jamais : si tu ne sais pas, tu le dis.\n"
    "- Tu gardes en tête mon contexte (voir « Mon profil ») pour personnaliser tes réponses.\n"
)


class EmptyOverwriteError(Exception):
    """Tentative d'écraser un contenu non vide par du vide sans intention explicite."""


class TooLongError(Exception):
    """Le contenu dépasse la limite de caractères du fichier concerné."""

    def __init__(self, char_count: int, char_limit: int) -> None:
        super().__init__(f"{char_count}/{char_limit} caractères")
        self.char_count = char_count
        self.char_limit = char_limit


class EntryNotFoundError(Exception):
    """Index de souvenir hors bornes."""


class EntryConflictError(Exception):
    """Le contenu attendu à cet index ne correspond plus à l'état actuel du fichier.

    ``MEMORY.md`` est muté par DEUX acteurs qui n'adressent pas les entrées de la même façon :
    le moteur (``tools/memory_tool.py``) mute par correspondance de sous-chaîne de contenu,
    le bridge par position (``index``). Si le moteur ajoute/retire une entrée entre le
    ``GET /memory/entries`` qui a rempli l'écran du dirigeant et le ``PUT``/``DELETE`` qu'il
    déclenche ensuite, l'index qu'il croit viser peut pointer sur une AUTRE entrée. Lever cette
    erreur (plutôt qu'écraser/supprimer en silence) exige que l'appelant prouve, via
    ``expected_content``, qu'il vise toujours la même entrée que celle vue au ``GET``.
    """


# ── Chemins ─────────────────────────────────────────────────────────────────


def _home() -> Path:
    """Racine Hermes courante (lue à chaque appel, pour rester testable)."""
    return Path(hermes_adapter.HERMES_HOME)


def _persona_path() -> Path:
    return _home() / "SOUL.md"


def _profile_path() -> Path:
    return _home() / "memories" / "USER.md"


def _profile_user_paths() -> list[Path]:
    """``memories/USER.md`` de chaque profil agent existant (miroirs du profil global).

    Un agent profilé a son propre ``HERMES_HOME`` (``<root>/profiles/<agent>/``) et lit
    donc ``profiles/<agent>/memories/USER.md`` — jamais le global. Le moteur ne synchronise
    PAS le global vers les profils. Écrire le profil du dirigeant doit donc atteindre chaque
    copie profil (write-through), sinon les agents gardent leur ancienne copie (spec 019)."""
    root = _home() / "profiles"
    if not root.is_dir():
        return []
    return [d / "memories" / "USER.md" for d in sorted(root.iterdir()) if d.is_dir()]


def _memory_path() -> Path:
    return _home() / "memories" / "MEMORY.md"


# ── Lecture / écriture bas niveau (sûres) ───────────────────────────────────


def _read_text(path: Path) -> str:
    """Contenu du fichier, ou chaîne vide s'il est absent (état vide = valide)."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


# Verrou + écriture atomique : source unique dans ``fsutil`` (identique à l'ancienne
# implémentation locale, cf. ``fsutil.file_lock``/``fsutil.atomic_write_text``). Alias
# conservés ici (mêmes noms) pour que les tests puissent continuer à monkeypatcher
# ``brain_adapter._file_lock``/``brain_adapter._write_unlocked`` directement.
_file_lock = fsutil.file_lock


def _write_unlocked(path: Path, content: str) -> None:
    """Écriture atomique (tmp + ``os.replace``) SANS verrou — l'appelant doit déjà le détenir."""
    fsutil.atomic_write_text(path, content)


def _atomic_write(path: Path, content: str) -> None:
    """Écrit ``content`` de façon atomique sous le verrou du fichier (prend le verrou lui-même)."""
    with _file_lock(path):
        _write_unlocked(path, content)


def _guard_empty_overwrite(path: Path, content: str, allow_empty: bool) -> None:
    """Refuse d'écraser un fichier non vide par du vide, sauf intention explicite."""
    if content.strip() == "" and not allow_empty and _read_text(path).strip() != "":
        raise EmptyOverwriteError()


# ── Entrées ``\n§\n`` ────────────────────────────────────────────────────────


def _parse_entries(content: str) -> list[str]:
    """Découpe le contenu en entrées (trim, on jette les vides). Préserve les ``§`` internes."""
    if not content.strip():
        return []
    return [e.strip() for e in content.split(ENTRY_DELIMITER) if e.strip()]


def _serialize_entries(entries: list[str]) -> str:
    return ENTRY_DELIMITER.join(entries)


# ── Persona (SOUL.md) ────────────────────────────────────────────────────────


def read_persona() -> str:
    """Personnalité de l'assistant (texte libre), ou vide si absente."""
    return _read_text(_persona_path())


def write_persona(content: str, allow_empty: bool = False) -> str:
    """Écrit la personnalité (sauvegarde explicite). Refuse le vide sur non-vide sans ``allow_empty``."""
    path = _persona_path()
    _guard_empty_overwrite(path, content, allow_empty)
    _atomic_write(path, content)
    return content


def default_persona() -> str:
    """Gabarit de personnalité par défaut (FR) — proposé au « Réinitialiser », non écrit sur disque."""
    return DEFAULT_PERSONA_FR


# ── Profil (USER.md) ─────────────────────────────────────────────────────────


def read_profile() -> tuple[str, int, int]:
    """(contenu, nb caractères, limite) du profil du dirigeant."""
    content = _read_text(_profile_path())
    return content, len(content), USER_CHAR_LIMIT


def write_profile(content: str, propagate: bool = True) -> tuple[str, int, int]:
    """Écrit le profil du dirigeant dans le global ET, par défaut, dans la copie
    ``memories/USER.md`` de chaque profil agent (write-through).

    Les agents lisent leur propre copie profil, pas le global : sans propagation, un
    profil mis à jour ne les atteindrait jamais. Le global reste la source de vérité ; les
    profils en sont des miroirs (``propagate=False`` n'écrit que le global, pour les cas
    où la propagation est gérée à part). Lève ``TooLongError`` au-delà de la limite."""
    if len(content) > USER_CHAR_LIMIT:
        raise TooLongError(len(content), USER_CHAR_LIMIT)
    _guard_empty_overwrite(_profile_path(), content, allow_empty=True)
    _atomic_write(_profile_path(), content)
    if propagate:
        for path in _profile_user_paths():
            _atomic_write(path, content)
    return content, len(content), USER_CHAR_LIMIT


# ── Souvenirs (MEMORY.md) ────────────────────────────────────────────────────


def list_entries() -> tuple[list[dict], int, int]:
    """(entrées indexées, nb caractères total, limite) des souvenirs."""
    raw = _read_text(_memory_path())
    entries = _parse_entries(raw)
    indexed = [{"index": i, "content": c} for i, c in enumerate(entries)]
    return indexed, len(_serialize_entries(entries)), MEMORY_CHAR_LIMIT


def _write_entries(entries: list[str]) -> tuple[list[dict], int, int]:
    # Appelé UNIQUEMENT depuis add/update/remove qui détiennent déjà le verrou → écriture non
    # verrouillée pour éviter un ré-entrant flock (deadlock).
    serialized = _serialize_entries(entries)
    if len(serialized) > MEMORY_CHAR_LIMIT:
        raise TooLongError(len(serialized), MEMORY_CHAR_LIMIT)
    _write_unlocked(_memory_path(), serialized)
    indexed = [{"index": i, "content": c} for i, c in enumerate(entries)]
    return indexed, len(serialized), MEMORY_CHAR_LIMIT


def add_entry(content: str) -> tuple[list[dict], int, int]:
    """Ajoute un souvenir (relecture sous verrou). Lève ``TooLongError`` si dépassement."""
    with _file_lock(_memory_path()):
        entries = _parse_entries(_read_text(_memory_path()))
        text = content.strip()
        if text:
            entries.append(text)
        return _write_entries(entries)


def update_entry(
    index: int, content: str, expected_content: str | None = None
) -> tuple[list[dict], int, int]:
    """Modifie le souvenir ``index`` (relecture sous verrou).

    ``expected_content``, quand fourni, doit correspondre au contenu ACTUEL de l'entrée à cet
    index (typiquement celui vu par l'appelant lors d'un ``GET`` antérieur) : concurrence
    optimiste contre le décalage d'index (le moteur mute ``MEMORY.md`` par contenu, pas par
    position — voir ``EntryConflictError``). Sans ``expected_content`` (rétro-compatibilité),
    aucune vérification n'est faite au-delà des bornes.

    Lève ``EntryNotFoundError`` si hors bornes, ``EntryConflictError`` si le contenu a changé.
    """
    with _file_lock(_memory_path()):
        entries = _parse_entries(_read_text(_memory_path()))
        if index < 0 or index >= len(entries):
            raise EntryNotFoundError(str(index))
        if expected_content is not None and entries[index] != expected_content.strip():
            raise EntryConflictError(str(index))
        entries[index] = content.strip()
        return _write_entries([e for e in entries if e])


def remove_entry(index: int, expected_content: str | None = None) -> tuple[list[dict], int, int]:
    """Supprime le souvenir ``index`` (relecture sous verrou).

    Même garde de concurrence optimiste que ``update_entry`` (voir ``expected_content`` et
    ``EntryConflictError``).

    Lève ``EntryNotFoundError`` si hors bornes, ``EntryConflictError`` si le contenu a changé.
    """
    with _file_lock(_memory_path()):
        entries = _parse_entries(_read_text(_memory_path()))
        if index < 0 or index >= len(entries):
            raise EntryNotFoundError(str(index))
        if expected_content is not None and entries[index] != expected_content.strip():
            raise EntryConflictError(str(index))
        del entries[index]
        return _write_entries(entries)
