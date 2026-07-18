"""Recherche par mot dans le coffre (spec 020, User Story 1).

Index texte **SQLite FTS5** (qualité BM25) sur les notes ``.md`` du coffre, + repli ``grep`` pour
l'exact que le tokenizer FTS5 pourrait rater. Aucune dépendance externe (FTS5 est dans la stdlib).

L'index est un **cache reconstructible** posé à la racine du coffre (``.search_index.db``, fichier
caché → jamais listé dans l'arborescence ni indexé). Le coffre ``.md`` reste la seule source de
vérité : rien n'est supprimé ni modifié ici, on lit et on indexe.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from . import memory_adapter
from .models import SearchResult

INDEX_FILENAME = ".search_index.db"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_TITLE_RE = re.compile(r"^(?:titre|title)\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_FM_TAGS_RE = re.compile(r"^tags\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_INLINE_TAG_RE = re.compile(r"(?:^|\s)#([A-Za-zÀ-ÿ0-9][\w/-]*)")
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


# ── Extraction (helpers) ──────────────────────────────────────────────────────


def _note_title(rel_path: str, content: str) -> str:
    """Titre lisible d'une note : frontmatter ``titre/title`` → 1er ``#`` → nom de fichier."""
    fm = _FRONTMATTER_RE.match(content)
    if fm:
        m = _FM_TITLE_RE.search(fm.group(1))
        if m:
            return m.group(1).strip().strip("\"'")
    h1 = _H1_RE.search(content)
    if h1:
        return h1.group(1).strip()
    return Path(rel_path).stem


def _extract_tags(content: str) -> list[str]:
    """Tags de la note : frontmatter ``tags`` (liste ou CSV) + ``#tags`` inline. Dédupliqués."""
    tags: list[str] = []
    fm = _FRONTMATTER_RE.match(content)
    body = content
    if fm:
        raw = _FM_TAGS_RE.search(fm.group(1))
        if raw:
            cleaned = raw.group(1).strip().strip("[]")
            tags += [t.strip().strip("\"'") for t in re.split(r"[,\s]+", cleaned) if t.strip()]
        body = content[fm.end():]
    tags += _INLINE_TAG_RE.findall(body)
    seen: dict[str, None] = {}
    for t in tags:
        if t and t not in seen:
            seen[t] = None
    return list(seen.keys())


def _extract_links(content: str) -> list[str]:
    """Cibles des wikilinks ``[[cible]]`` / ``[[cible|alias]]``. Liens vides ignorés (pas de crash)."""
    out: list[str] = []
    for target in _WIKILINK_RE.findall(content):
        target = target.strip()
        if target:
            out.append(target)
    return out


# ── Index FTS5 ────────────────────────────────────────────────────────────────


def _index_path(root: Path) -> Path:
    return root / INDEX_FILENAME


def _iter_notes(root: Path):
    """Itère les notes ``.md`` du coffre (ignore dossiers cachés/techniques)."""
    for path in root.rglob(f"*{memory_adapter.NOTE_SUFFIX}"):
        parts = path.relative_to(root).parts
        if any(p.startswith(".") or p in memory_adapter._IGNORED for p in parts):
            continue
        yield path


def _connect(root: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(_index_path(root))
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
        "USING fts5(chemin UNINDEXED, titre, contenu, tags)"
    )
    return conn


def _index_one(conn: sqlite3.Connection, root: Path, path: Path) -> None:
    rel = path.relative_to(root).as_posix()
    content = path.read_text(encoding="utf-8", errors="replace")
    conn.execute("DELETE FROM notes_fts WHERE chemin = ?", (rel,))
    conn.execute(
        "INSERT INTO notes_fts (chemin, titre, contenu, tags) VALUES (?, ?, ?, ?)",
        (rel, _note_title(rel, content), content, " ".join(_extract_tags(content))),
    )


def build_index() -> int:
    """(Re)construit l'index complet depuis les ``.md`` du coffre. Retourne le nombre de notes."""
    root = memory_adapter._vault_root()
    idx = _index_path(root)
    if idx.exists():
        idx.unlink()  # cache reconstructible : on repart propre (aucune note du coffre touchée)
    conn = _connect(root)
    count = 0
    with conn:
        for path in _iter_notes(root):
            _index_one(conn, root, path)
            count += 1
    conn.close()
    return count


def upsert_note(rel_path: str) -> None:
    """Met à jour (ou insère) une seule note dans l'index, sans tout reconstruire."""
    root = memory_adapter._vault_root()
    if not _index_path(root).exists():
        build_index()
        return
    path = memory_adapter._safe_note_path(rel_path)
    conn = _connect(root)
    with conn:
        if path.is_file():
            _index_one(conn, root, path)
        else:
            conn.execute("DELETE FROM notes_fts WHERE chemin = ?", (rel_path,))
    conn.close()


# ── Réindexation ciblée d'un sous-arbre (dossier renommé/déplacé/supprimé/restauré) ──────────────
# Un renommage/déplacement/suppression/restauration de DOSSIER ne touche jamais le reste du coffre :
# reconstruire tout l'index (potentiellement des milliers de notes) pour ça est un gaspillage.
# ``build_index()`` reste réservé à l'initialisation et à la réparation (index absent/corrompu).


def _escape_like(value: str) -> str:
    """Échappe les jokers SQL LIKE (``%``, ``_``) pour un préfixe qui peut contenir ces caractères
    littéralement dans un nom de dossier (sinon un dossier ``a_b`` matcherait aussi ``aXb``)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _purge_prefix(conn: sqlite3.Connection, prefix: str) -> None:
    """Retire de l'index la note ``prefix`` elle-même ET toute note sous ce dossier (descendants)."""
    prefix = prefix.strip("/")
    if not prefix:
        return
    conn.execute("DELETE FROM notes_fts WHERE chemin = ?", (prefix,))
    conn.execute(
        "DELETE FROM notes_fts WHERE chemin LIKE ? ESCAPE '\\'", (f"{_escape_like(prefix)}/%",)
    )


def _iter_notes_under(root: Path, prefix: str):
    """Itère les notes ``.md`` SOUS ``prefix`` uniquement (pas tout le coffre) — cœur de la perf."""
    prefix = prefix.strip("/")
    base = root / prefix if prefix else root
    if not base.is_dir():
        return
    for path in base.rglob(f"*{memory_adapter.NOTE_SUFFIX}"):
        parts = path.relative_to(root).parts
        if any(p.startswith(".") or p in memory_adapter._IGNORED for p in parts):
            continue
        yield path


def reindex_subtree(old_prefix: str | None = None, new_prefix: str | None = None) -> None:
    """Réindexe UNIQUEMENT le sous-arbre concerné par une opération de dossier — jamais tout le coffre.

    ``old_prefix`` : chemin (avant l'opération) à purger de l'index, ou ``None`` si rien à purger
    (ex. une restauration n'a rien à retirer : la corbeille n'est jamais indexée).
    ``new_prefix`` : chemin (après l'opération) désormais présent sur le disque, à (ré)indexer, ou
    ``None`` si rien à ajouter (ex. une suppression ne fait que retirer).

    - Renommage/déplacement : ``old_prefix`` = chemin avant, ``new_prefix`` = chemin après.
    - Suppression (corbeille) : seulement ``old_prefix``.
    - Restauration : seulement ``new_prefix`` (l'ancien chemin, dans ``.trash``, n'était pas indexé).

    Si l'index n'existe pas encore (première utilisation / réparation après incident), reconstruit
    tout via ``build_index()`` — mêmes garanties que l'ancien comportement, jamais un résultat
    incohérent.
    """
    root = memory_adapter._vault_root()
    if not _index_path(root).exists():
        build_index()
        return
    conn = _connect(root)
    with conn:
        if old_prefix:
            _purge_prefix(conn, old_prefix)
        if new_prefix:
            for path in _iter_notes_under(root, new_prefix):
                _index_one(conn, root, path)
    conn.close()


# ── Recherche ─────────────────────────────────────────────────────────────────


def _grep_fallback(root: Path, tokens: list[str], limit: int) -> list[SearchResult]:
    """Repli plein texte (sous-chaîne, insensible à la casse) pour l'exact raté par FTS5."""
    needles = [t.lower() for t in tokens]
    out: list[SearchResult] = []
    for path in _iter_notes(root):
        content = path.read_text(encoding="utf-8", errors="replace")
        low = content.lower()
        if all(n in low for n in needles):
            pos = low.find(needles[0])
            extrait = content[max(0, pos - 40): pos + 80].strip()
            rel = path.relative_to(root).as_posix()
            out.append(
                SearchResult(
                    titre=_note_title(rel, content),
                    chemin=rel,
                    extrait=extrait,
                    score=0.0,
                    source_type="note",
                )
            )
            if len(out) >= limit:
                break
    return out


def search(query: str, limit: int = 8) -> list[SearchResult]:
    """Cherche par mots-clés dans les notes du coffre. Résultats classés par pertinence (BM25).

    Construit l'index à la volée s'il est absent. Repli ``grep`` si FTS5 ne trouve rien — ET si
    l'index lui-même est inaccessible (verrouillé, corrompu…) : le contrat produit est un statut
    honnête, jamais un 500 brut sur une recherche. ``build_index``/``_connect`` peuvent échouer
    (ex. « database is locked ») ; dans ce cas on se rabat directement sur le grep plutôt que de
    laisser fuir l'exception SQLite jusqu'à l'appelant.
    """
    tokens = _WORD_RE.findall(query or "")
    if not tokens:
        return []
    root = memory_adapter._vault_root()
    try:
        if not _index_path(root).exists():
            build_index()
        conn = _connect(root)
    except sqlite3.Error:
        return _grep_fallback(root, tokens, limit)
    match = " OR ".join(f'"{t}"' for t in tokens)
    try:
        rows = conn.execute(
            "SELECT chemin, titre, snippet(notes_fts, 2, '', '', '…', 12), bm25(notes_fts) "
            "FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    results = [
        SearchResult(
            titre=titre, chemin=chemin, extrait=extrait,
            score=round(-score, 3), source_type="note",
        )
        for chemin, titre, extrait, score in rows
    ]
    if not results:
        results = _grep_fallback(root, tokens, limit)
    return results
