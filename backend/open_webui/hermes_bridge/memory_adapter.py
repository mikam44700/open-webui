"""Mémoire / Second Cerveau (feature 005) — accès au coffre Obsidian.

Le coffre est un dossier de fichiers ``.md`` (le Second Cerveau de l'entreprise) qui vit sur le VPS,
à côté de Hermes (archi « 1 client = 1 VPS »). Le bridge y accède en **fichier local**. Ce module
expose une arborescence lisible, le contenu d'une note, un statut honnête, l'initialisation de la
structure PARA et une zone d'écriture autonome (la Boîte de réception).

Chemin du coffre (unifié) : ``MEMORY_VAULT_PATH`` (override explicite) → sinon ``OBSIDIAN_VAULT_PATH``
de ``~/.hermes/.env`` (le MÊME coffre que la skill Hermes ``note-taking/obsidian``) → sinon
``<HERMES_HOME>/vault``. Ainsi l'UI Mémoire, l'agent Hermes et la skill partagent un seul coffre.

Sécurité : toute opération sur une note est confinée AU coffre (protection anti path traversal).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile  # noqa: F401 — ré-exporté : un test patche le singleton via memory_adapter.tempfile
import threading
import time
from pathlib import Path

import yaml

from . import fsutil, hermes_adapter, sync_adapter
from .models import MemoryNode, MemoryStatus, NoteContent, TrashItem

logger = logging.getLogger(__name__)

NOTE_SUFFIX = ".md"

# Verrou du coffre : sérialise les opérations « vérifier l'absence puis agir » (restaurer, renommer,
# déplacer, créer un dossier, upsert d'une note gérée) contre une course TOCTOU. Les endpoints
# FastAPI synchrones tournent dans un threadpool (Starlette) : une vraie concurrence inter-thread
# existe dans CE process. Le verrou ne couvre que ce process (le produit est mono-dirigeant par VPS,
# pas multi-tenant) — suffisant pour fermer la fenêtre réelle sans complexité de verrou fichier
# inter-process. Non réentrant (threading.Lock, pas RLock) : AUCUNE fonction appelée sous ce lock ne
# doit elle-même tenter de l'acquérir, sous peine de deadlock — vérifié pour chaque section verrouillée
# (create_folder, upsert_managed_note, rename/move/delete/restore de notes et dossiers).
_VAULT_LOCK = threading.Lock()


class RestoreConflict(ValueError):
    """Levée par ``restore_note``/``restore_folder`` quand la destination existe déjà.

    Sous-classe de ``ValueError`` (compat. avec le code existant qui capture ``ValueError``), mais
    un type dédié pour que le routeur traduise le conflit en 409 sans dépendre d'un match littéral
    du message d'exception (fragile : un futur changement de texte ferait régresser le code HTTP).
    """


class FolderConflict(ValueError):
    """Levée par ``create_folder`` quand la collision survient malgré la protection ``_VAULT_LOCK``.

    Le lock ferme la course dans CE process, mais une collision reste possible avec un acteur hors
    process (Syncthing, Obsidian, édition manuelle du disque) : ``mkdir(exist_ok=False)`` peut donc
    encore lever ``FileExistsError``. Converti en type dédié (sous-classe de ``ValueError``, même
    principe que ``RestoreConflict``) pour que le routeur réponde 409 sans jamais fuiter en 500 brut
    et sans dépendre d'un match littéral du message d'exception.
    """


class NoteConflict(ValueError):
    """Levée par ``write_note`` quand la note a changé sur disque depuis la dernière lecture.

    Concurrence optimiste (même principe que ``brain_adapter.EntryConflictError``), mais adressée
    par ``modified`` (mtime epoch) plutôt que par contenu : une note peut être longue, et c'est
    justement le contenu qu'on s'apprête à écraser — pas pratique à faire porter par l'appelant.
    Sans cette garde, un éditeur resté ouvert (``MemoryExplorer`` avec sa sauvegarde débouncée)
    pouvait écraser silencieusement une note pendant qu'Adam (skill ``obsidian``), une synchro
    Syncthing, ou une autre fenêtre du dirigeant venait de la modifier. Sous-classe de
    ``ValueError`` (même famille que ``RestoreConflict``/``FolderConflict``) pour que le routeur
    réponde 409 sans dépendre d'un match littéral du message d'exception.
    """


# Tolérance de comparaison des mtimes (secondes) : certains systèmes de fichiers/plateformes ne
# conservent pas la pleine précision flottante d'un aller-retour JSON. Largement sous la moindre
# résolution de mtime réelle (généralement >= 1 µs, souvent >= 1 ms) : ne masque aucun conflit réel.
_MTIME_TOLERANCE = 1e-6


# Écriture atomique (fichier temporaire dans le même dossier + ``os.replace``, cf. ``fsutil``).
#
# Sans ça, un crash pendant l'écriture (kill -9, redémarrage du service, coupure disque) peut
# tronquer le fichier à sa taille finale avant d'écrire le contenu (``write_text``/``"w"`` tronque
# IMMÉDIATEMENT à l'ouverture) : au redémarrage, on retrouve un fichier vide ou coupé au milieu.
# ``os.replace`` est atomique sur un même système de fichiers : un lecteur concurrent ne voit
# jamais un état intermédiaire, et un crash avant le ``replace`` laisse l'original intact. Alias
# conservé (même nom) pour que les tests puissent continuer à monkeypatcher
# ``memory_adapter._atomic_write_text``.
_atomic_write_text = fsutil.atomic_write_text


# Dossiers techniques jamais exposés au client (plomberie de sync, cache…).
_IGNORED = {".git", ".obsidian", ".trash", "__pycache__", ".stfolder", ".stversions"}

# Boîte de réception : SEULE zone où l'agent écrit en autonomie (garde-fou Inbox/Outbox).
INBOX_DIR = "00-Réception"

# Sommaire du coffre, à la RACINE : épinglé en tête de l'arbre (avant les dossiers).
INDEX_NAME = "INDEX"
INDEX_FILENAME = f"{INDEX_NAME}{NOTE_SUFFIX}"

# Structure du Second Cerveau (méthode PARA, en français). Créée à l'initialisation, idempotente.
VAULT_STRUCTURE: tuple[str, ...] = (
    INBOX_DIR,
    "01-En cours",
    "02-Mes responsabilités",
    "03-Idées & ressources",
    "04-Archivées",
    "05-Journal",
    "06-Contacts",
    "07-Mes réflexions",
    "08-Modèles de notes",
)

# Descriptions courtes affichées dans l'INDEX racine, PAR dossier. L'INDEX lui-même dérive de
# VAULT_STRUCTURE (voir _default_index) : ici on ne porte que le TEXTE, jamais la liste — ainsi
# un dossier ajouté/renommé dans VAULT_STRUCTURE apparaît d'office dans l'INDEX (fini la recopie).
_INDEX_DESCRIPTIONS: dict[str, str] = {
    INBOX_DIR: "entrées à trier (ce qu'Adam dépose ici, à valider)",
    "01-En cours": "travaux en cours, avec objectif/échéance",
    "02-Mes responsabilités": "responsabilités durables (clients, finance, équipe…)",
    "03-Idées & ressources": "références et procédures",
    "04-Archivées": "terminé / inactif",
    "05-Journal": "notes datées (journées, réunions)",
    "06-Contacts": "clients et contacts",
    "07-Mes réflexions": "vos prises de position et idées personnelles",
    "08-Modèles de notes": "vos gabarits réutilisables",
}


def _vault_root() -> Path:
    """Racine du coffre (chemin unifié, voir docstring du module).

    Lu à chaque appel (pas au démarrage) pour rester testable et refléter la config courante.
    Le dossier est créé s'il n'existe pas (un coffre vide est un état valide).
    """
    configured = os.environ.get("MEMORY_VAULT_PATH") or hermes_adapter.read_env_value(
        "OBSIDIAN_VAULT_PATH"
    )
    if configured:
        root = Path(os.path.expanduser(configured))
    else:
        root = Path(hermes_adapter.HERMES_HOME) / "vault"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_note_path(rel_path: str) -> Path:
    """Résout un chemin de note RELATIF en chemin absolu confiné au coffre.

    Lève ``ValueError`` si le chemin sort du coffre (path traversal) ou n'est pas une note ``.md``.
    """
    if not rel_path or rel_path.strip() == "":
        raise ValueError("empty note path")
    root = _vault_root()
    candidate = (root / rel_path).resolve()
    # candidate doit être strictement DANS le coffre.
    if root != candidate and root not in candidate.parents:
        raise ValueError("path outside vault")
    if candidate.suffix != NOTE_SUFFIX:
        raise ValueError("not a note")
    return candidate


def _safe_dir_path(rel_path: str) -> Path:
    """Résout un chemin de DOSSIER relatif en chemin absolu confiné au coffre.

    Lève ``ValueError`` si le chemin sort du coffre (path traversal) ou vise une note ``.md``.
    """
    if not rel_path or rel_path.strip() == "":
        raise ValueError("empty folder path")
    root = _vault_root()
    candidate = (root / rel_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("path outside vault")
    if candidate.suffix == NOTE_SUFFIX:
        raise ValueError("not a folder")
    return candidate


def create_folder(parent: str, name: str) -> MemoryNode:
    """Crée un dossier ``name`` dans ``parent`` (relatif au coffre), sans collision.

    Le nom est assaini (pas de séparateur de chemin). En cas de collision, un suffixe numérique
    est ajouté (« Dossier 2 »). Confiné au coffre (anti path traversal). Retourne le nœud créé.
    """
    safe_name = _safe_filename(name) or "Nouveau dossier"
    parent_rel = (parent or "").strip().strip("/")
    root = _vault_root()

    def _rel(n: str) -> str:
        return f"{parent_rel}/{n}" if parent_rel else n

    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle de collision et le mkdir ne font qu'un
        dest = _safe_dir_path(_rel(safe_name))
        counter = 2
        while dest.exists():
            dest = _safe_dir_path(_rel(f"{safe_name} {counter}"))
            counter += 1
        try:
            dest.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            # Le lock ferme la course DANS ce process ; une collision hors-process (Syncthing,
            # Obsidian) reste possible — jamais un 500 brut pour ça, un conflit propre.
            raise FolderConflict(f"folder already exists: {dest.name}") from exc
    new_rel = dest.relative_to(root).as_posix()
    return MemoryNode(name=dest.name, path=new_rel, type="folder", children=[])


def _is_structural(rel_path: str) -> bool:
    """Un dossier structurel du squelette PARA (top-level) est protégé : ni renommé, ni supprimé.

    Protège le coffre clé en main : le dirigeant range DANS ces dossiers (crée ses casquettes),
    mais ne casse pas le squelette. Ses propres sous-dossiers, eux, sont pleinement modifiables.

    Compare le chemin RÉSOLU (``.resolve()``, comme ``_safe_dir_path``) et non la chaîne brute
    reçue de l'appelant : sinon une variante syntaxique du même chemin réel (``./00-Réception``,
    ``00-Réception/.``) contourne la protection alors qu'elle vise le même dossier physique.
    """
    root = _vault_root()
    try:
        candidate = _safe_dir_path(rel_path)
    except ValueError:
        return False
    try:
        resolved_rel = candidate.relative_to(root).as_posix()
    except ValueError:
        return False
    return resolved_rel in VAULT_STRUCTURE


def rename_folder(rel_path: str, new_name: str) -> MemoryNode:
    """Renomme un dossier (non structurel), sans collision. Retourne le nœud à son nouveau chemin."""
    path = _safe_dir_path(rel_path)
    if not path.is_dir():
        raise FileNotFoundError(rel_path)
    if _is_structural(rel_path):
        raise ValueError("structural folder cannot be renamed")
    safe = _safe_filename(new_name)
    if not safe:
        raise ValueError("empty folder name")
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle de collision et le rename ne font qu'un
        dest = path.parent / safe
        if dest.resolve() != path.resolve():
            counter = 2
            while dest.exists():
                dest = path.parent / f"{safe} {counter}"
                counter += 1
            path.rename(dest)
    root = _vault_root()
    new_rel = dest.resolve().relative_to(root).as_posix()
    return MemoryNode(name=dest.name, path=new_rel, type="folder", children=[])


def delete_folder(rel_path: str) -> str:
    """Suppression DOUCE d'un dossier (non structurel) : déplacé entier vers ``.trash`` (récupérable).

    Retourne la réf. de corbeille. Refuse les dossiers structurels PARA (protection du squelette).
    """
    path = _safe_dir_path(rel_path)
    if not path.is_dir():
        raise FileNotFoundError(rel_path)
    if _is_structural(rel_path):
        raise ValueError("structural folder cannot be deleted")
    trash = _trash_root()
    base = rel_path.strip("/").replace("/", "__")
    with _VAULT_LOCK:  # anti-TOCTOU : réserve le nom de corbeille avant de déplacer
        dest = trash / base
        counter = 2
        while dest.exists():
            dest = trash / f"{base}-{counter}"
            counter += 1
        path.rename(dest)
    _record_trash(dest.name, rel_path.strip("/"), Path(rel_path.strip("/")).name, "folder")
    return dest.name


def move_folder(rel_path: str, dest_parent: str) -> MemoryNode:
    """Déplace un dossier (non structurel) vers ``dest_parent`` (« » = racine), sans collision.

    Refuse : les dossiers structurels PARA, la destination Réception (boîte d'entrée), et tout
    déplacement d'un dossier dans lui-même ou l'un de ses descendants. Confiné au coffre.
    """
    src = _safe_dir_path(rel_path)
    if not src.is_dir():
        raise FileNotFoundError(rel_path)
    if _is_structural(rel_path):
        raise ValueError("structural folder cannot be moved")
    root = _vault_root()
    dest_parent = (dest_parent or "").strip().strip("/")
    # Jamais dans la Réception (zone d'entrée de l'agent, pas une zone de structure).
    if dest_parent == INBOX_DIR or dest_parent.startswith(f"{INBOX_DIR}/"):
        raise ValueError("cannot move into inbox")
    dest_dir = _safe_dir_path(dest_parent) if dest_parent else root
    src_res = src.resolve()
    dest_res = dest_dir.resolve()
    # Pas dans soi-même ni un descendant (cycle).
    if dest_res == src_res or src_res in dest_res.parents:
        raise ValueError("cannot move a folder into itself")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.resolve() == src_res:  # déjà dans ce parent
        return MemoryNode(
            name=src.name, path=src_res.relative_to(root).as_posix(), type="folder", children=[]
        )
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle de collision et le rename ne font qu'un
        counter = 2
        while dest.exists():
            dest = dest_dir / f"{src.name} {counter}"
            counter += 1
        src.rename(dest)
    new_rel = dest.resolve().relative_to(root).as_posix()
    return MemoryNode(name=dest.name, path=new_rel, type="folder", children=[])


def restore_folder(trash_ref: str, original_rel_path: str) -> MemoryNode:
    """Restaure un dossier depuis la corbeille vers son emplacement d'origine (annulation)."""
    src = _trashed_path(trash_ref)
    if not src.is_dir():
        raise FileNotFoundError(trash_ref)
    dest = _safe_dir_path(original_rel_path)
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle « destination libre » et le rename ne font qu'un
        if dest.exists():
            raise RestoreConflict("destination exists")
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
    _forget_trash(trash_ref)
    root = _vault_root()
    new_rel = dest.resolve().relative_to(root).as_posix()
    return MemoryNode(name=dest.name, path=new_rel, type="folder", children=[])


def _build_tree(directory: Path, root: Path) -> list[MemoryNode]:
    """Construit récursivement l'arborescence (dossiers d'abord, puis notes, triés)."""
    folders: list[MemoryNode] = []
    notes: list[MemoryNode] = []
    for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith(".") or entry.name in _IGNORED:
            continue
        rel = entry.relative_to(root).as_posix()
        if entry.is_dir():
            folders.append(
                MemoryNode(
                    name=entry.name,
                    path=rel,
                    type="folder",
                    children=_build_tree(entry, root),
                )
            )
        elif entry.is_file() and entry.suffix == NOTE_SUFFIX:
            notes.append(
                MemoryNode(name=entry.stem, path=rel, type="note", modified=entry.stat().st_mtime)
            )
    # Les notes-guides « À lire — … » restent épinglées en tête de leur dossier (avant les notes
    # du client), sinon le « À » accentué les renvoie en fin de tri alphabétique.
    notes.sort(key=lambda n: (not n.name.startswith("À lire"), n.name.lower()))
    # L'INDEX de la racine est le sommaire du coffre : il passe AVANT les dossiers, sinon la règle
    # « dossiers puis notes » le relègue en dernier, sous les rayons qu'il est censé annoncer.
    # Ailleurs, un INDEX.md n'est qu'une note ordinaire.
    if directory == root:
        index = [n for n in notes if n.name == INDEX_NAME]
        return index + folders + [n for n in notes if n.name != INDEX_NAME]
    return folders + notes


def read_tree() -> list[MemoryNode]:
    """Arborescence complète du coffre (dossiers métier + notes)."""
    root = _vault_root()
    return _build_tree(root, root)


def read_note(rel_path: str) -> NoteContent:
    """Contenu d'une note. Lève ``FileNotFoundError`` si absente, ``ValueError`` si chemin invalide."""
    path = _safe_note_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return NoteContent(
        path=rel_path, content=path.read_text(encoding="utf-8"), modified=path.stat().st_mtime
    )


def write_note(
    rel_path: str, content: str, expected_modified: float | None = None
) -> NoteContent:
    """Crée/corrige une note. Crée les dossiers parents au besoin. ``ValueError`` si chemin invalide.

    Écriture ATOMIQUE (tmp + ``os.replace``, voir ``_atomic_write_text``) : les notes sont le
    contenu le plus précieux du produit (le « second cerveau » du dirigeant) — un crash pendant
    l'écriture ne doit jamais laisser une note tronquée ou vide sur disque.

    ``expected_modified`` (optionnel) porte la concurrence optimiste : le ``modified`` (mtime
    epoch) vu par l'appelant au dernier ``GET /memory/note`` pour CE chemin. Si fourni et que le
    fichier a changé depuis (un autre éditeur ouvert, l'agent via la skill ``obsidian``, une
    synchro Syncthing…), lève ``NoteConflict`` plutôt que d'écraser ce travail en silence. Omis =
    comportement rétro-compatible (aucune vérification) — utilisé par les écrivains qui n'ont
    jamais lu la note avant (nouvelle note, Boîte de réception, note gérée).
    """
    path = _safe_note_path(rel_path)
    if expected_modified is not None:
        if not path.is_file():
            # Vue au dernier GET, disparue depuis (supprimée/déplacée) : plus le même état.
            raise NoteConflict(rel_path)
        actual = path.stat().st_mtime
        if abs(actual - expected_modified) > _MTIME_TOLERANCE:
            raise NoteConflict(rel_path)
    _atomic_write_text(path, content)
    return NoteContent(path=rel_path, content=content, modified=path.stat().st_mtime)


def _safe_filename(title: str) -> str:
    """Nom de fichier LISIBLE (garde la casse et les espaces) mais sûr pour le système de fichiers."""
    text = title.strip().replace("/", "-").replace("\\", "-")
    text = re.sub(r'[:*?"<>|\x00-\x1f]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120].strip() or "Note"


def _trash_root() -> Path:
    """Corbeille du coffre (``.trash``, ignorée de l'arbre) — filet de récupération des suppressions."""
    trash = _vault_root() / ".trash"
    trash.mkdir(parents=True, exist_ok=True)
    return trash


# ─── Manifeste de corbeille ──────────────────────────────────────────────────
# Petit journal des suppressions LunarIA (chemin d'origine + date), pour une vue « Corbeille »
# durable et fiable. On ne s'appuie PAS sur le décodage du nom de fichier (fragile) : le manifeste
# est la source de vérité. Il vit dans .trash (ignoré par Syncthing) → local au bridge.
def _trash_manifest_path() -> Path:
    return _trash_root() / ".lunaria-trash.json"


def _read_trash_manifest() -> list[dict]:
    p = _trash_manifest_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_trash_manifest(entries: list[dict]) -> None:
    # Écriture ATOMIQUE : ce fichier se déclare lui-même « source de vérité » (voir commentaire du
    # module ci-dessus) — un crash pendant un ``write_text`` direct pourrait le tronquer, rendant
    # TOUTES les entrées de corbeille invisibles alors que les fichiers physiques restent orphelins
    # dans ``.trash`` (plus jamais listés ni purgeables proprement).
    _atomic_write_text(
        _trash_manifest_path(), json.dumps(entries, ensure_ascii=False, indent=2)
    )


def _record_trash(ref: str, original_path: str, name: str, node_type: str) -> None:
    """Consigne une suppression (remplace toute entrée de même réf)."""
    entries = [e for e in _read_trash_manifest() if e.get("ref") != ref]
    entries.append(
        {
            "ref": ref,
            "path": original_path,
            "name": name,
            "type": node_type,
            "deleted_at": time.time(),
        }
    )
    _write_trash_manifest(entries)


def _forget_trash(ref: str) -> None:
    """Retire une entrée du manifeste (après restauration)."""
    _write_trash_manifest([e for e in _read_trash_manifest() if e.get("ref") != ref])


def _entry_size(path: Path) -> int:
    """Octets occupés par un élément de corbeille (une note, ou tout le contenu d'un dossier)."""
    try:
        if path.is_file():
            return path.stat().st_size
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    except OSError:
        return 0


def _trashed_path(trash_ref: str) -> Path:
    """Résout une réf. de corbeille en chemin, CONFINÉ à ``.trash`` (anti path traversal).

    Une réf. bricolée (``../INDEX.md``) ne doit jamais atteindre une note vivante du coffre.
    """
    trash = _trash_root()
    src = (trash / trash_ref).resolve()
    if trash.resolve() not in src.parents:
        raise ValueError("bad trash ref")
    return src


def list_trash() -> list[TrashItem]:
    """Corbeille visible : suppressions LunarIA récupérables, les plus récentes d'abord.

    Ne montre que les entrées dont le fichier/dossier existe encore dans .trash (auto-nettoyage
    des références orphelines). Les suppressions internes d'Obsidian ne sont pas listées ici.
    """
    trash = _trash_root()
    manifest = _read_trash_manifest()
    kept: list[dict] = [e for e in manifest if e.get("ref") and (trash / e["ref"]).exists()]
    if len(kept) != len(manifest):
        _write_trash_manifest(kept)  # purge des références orphelines
    items = [
        TrashItem(
            ref=e["ref"],
            path=e.get("path", ""),
            name=e.get("name", e["ref"]),
            type=e.get("type", "note"),
            deleted_at=float(e.get("deleted_at", 0.0)),
            size=_entry_size(trash / e["ref"]),
        )
        for e in kept
    ]
    items.sort(key=lambda i: i.deleted_at, reverse=True)
    return items


def purge_trash_item(trash_ref: str) -> None:
    """Suppression DÉFINITIVE d'un élément de la corbeille (irréversible, réservée à l'humain).

    Le produit ne détruit jamais tout seul (aucun TTL, aucune purge automatique) : c'est le
    dirigeant qui décide, depuis l'UI, après confirmation. Sans cette porte de sortie, la corbeille
    ne serait qu'un cimetière — on pourrait y jeter sans jamais pouvoir vider.
    """
    src = _trashed_path(trash_ref)
    if src.is_dir():
        shutil.rmtree(src)
    elif src.is_file():
        src.unlink()
    else:
        raise FileNotFoundError(trash_ref)
    _forget_trash(trash_ref)


def empty_trash() -> int:
    """Vide la corbeille (définitif) et retourne le nombre d'éléments purgés.

    Ne touche QUE les éléments du manifeste, c'est-à-dire ceux que le dirigeant VOIT dans l'UI.
    Le dossier ``.trash`` accueille aussi les suppressions internes d'Obsidian : elles ne nous
    appartiennent pas, on ne les efface jamais.
    """
    purged = 0
    for item in list_trash():
        try:
            purge_trash_item(item.ref)
            purged += 1
        except (OSError, ValueError, FileNotFoundError):
            continue  # un élément récalcitrant ne doit pas bloquer le vidage des autres
    return purged


def delete_note(rel_path: str) -> str:
    """Suppression DOUCE : déplace la note vers ``.trash`` (récupérable). Retourne la réf. de corbeille.

    Jamais de suppression dure : le dirigeant garde un filet (annulation). Adam, lui, ne supprime
    JAMAIS (garde-fou de son SOUL) — cette action est réservée à l'humain via l'UI.
    """
    path = _safe_note_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    trash = _trash_root()
    base = rel_path.replace("/", "__")
    with _VAULT_LOCK:  # anti-TOCTOU : réserve le nom de corbeille avant de déplacer
        dest = trash / base
        counter = 2
        while dest.exists():
            dest = trash / f"{base[: -len(NOTE_SUFFIX)]}-{counter}{NOTE_SUFFIX}"
            counter += 1
        path.rename(dest)
    _record_trash(dest.name, rel_path, Path(rel_path).stem, "note")
    return dest.name


def restore_note(trash_ref: str, original_rel_path: str) -> NoteContent:
    """Restaure une note depuis la corbeille vers son emplacement d'origine (annulation)."""
    src = _trashed_path(trash_ref)
    if not src.is_file():
        raise FileNotFoundError(trash_ref)
    dest = _safe_note_path(original_rel_path)
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle « destination libre » et le rename ne font qu'un
        if dest.exists():
            raise RestoreConflict("destination exists")
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
    _forget_trash(trash_ref)
    return NoteContent(
        path=original_rel_path, content=dest.read_text(encoding="utf-8"), modified=dest.stat().st_mtime
    )


def rename_note(rel_path: str, new_title: str) -> NoteContent:
    """Renomme une note (même dossier, titre lisible). Retourne la note à son NOUVEAU chemin."""
    path = _safe_note_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    name = _safe_filename(new_title)
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle de collision et le rename ne font qu'un
        dest = path.parent / f"{name}{NOTE_SUFFIX}"
        if dest.resolve() != path.resolve():
            counter = 2
            while dest.exists():
                dest = path.parent / f"{name}-{counter}{NOTE_SUFFIX}"
                counter += 1
            path.rename(dest)
    root = _vault_root()
    new_rel = dest.resolve().relative_to(root).as_posix()
    return NoteContent(path=new_rel, content=dest.read_text(encoding="utf-8"))


def move_note(rel_path: str, dest_folder: str) -> NoteContent:
    """Déplace une note vers ``dest_folder`` (relatif au coffre, "" = racine), sans collision.

    Confiné au coffre (anti path traversal). Retourne la note à son nouveau chemin. No-op si la
    note est déjà dans le dossier cible.
    """
    src = _safe_note_path(rel_path)
    if not src.is_file():
        raise FileNotFoundError(rel_path)
    root = _vault_root()
    dest_folder = (dest_folder or "").strip().strip("/")
    dest_dir = _safe_dir_path(dest_folder) if dest_folder else root
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.resolve() == src.resolve():
        new_rel = src.relative_to(root).as_posix()
        return NoteContent(path=new_rel, content=src.read_text(encoding="utf-8"))
    with _VAULT_LOCK:  # anti-TOCTOU : le contrôle de collision et le rename ne font qu'un
        counter = 2
        while dest.exists():
            dest = dest_dir / f"{src.stem}-{counter}{NOTE_SUFFIX}"
            counter += 1
        src.rename(dest)
    new_rel = dest.resolve().relative_to(root).as_posix()
    return NoteContent(path=new_rel, content=dest.read_text(encoding="utf-8"))


def _default_index() -> str:
    """Carte centrale (INDEX) posée à la RACINE d'un coffre neuf.

    À la racine : c'est la première chose que le dirigeant voit en ouvrant son coffre. La liste
    est DÉRIVÉE de ``VAULT_STRUCTURE`` (une seule source) — un dossier ajouté/renommé y apparaît
    d'office ; les libellés viennent de ``_INDEX_DESCRIPTIONS``.
    """
    lignes = "\n".join(
        f"- **{folder}** — {_INDEX_DESCRIPTIONS.get(folder, '')}" for folder in VAULT_STRUCTURE
    )
    return (
        "---\n"
        "titre: Index du Second Cerveau\n"
        "type: carte\n"
        "---\n\n"
        "# 🧠 Index du Second Cerveau\n\n"
        "Bienvenue dans votre coffre. Voici à quoi sert chaque dossier —\n"
        "et chacun contient une note « À lire — … » qui le détaille.\n\n"
        f"{lignes}\n"
    )


# Notes-guides posées dans chaque dossier à l'initialisation. Objectif : un coffre « clé en main »
# où AUCUN dossier n'est muet (règle « jamais de dossier vide » de PARA/Tiago Forte : un dossier
# vide décourage ; un dossier qui explique son usage guide). Langage dirigeant, pas de jargon.
# Le fichier est nommé « À lire — … » pour rester en tête de dossier et se reconnaître d'un coup d'œil.
_FOLDER_GUIDES: tuple[tuple[str, str, str], ...] = (
    (
        INBOX_DIR,
        "📥 Réception",
        "C'est l'entrée de votre second cerveau. Tout ce qu'Adam capte pour vous atterrit ici, "
        "en attendant que vous le validiez et le rangiez.\n\n"
        "**Rangez ici :**\n"
        "- une note jetée en vitesse, à trier plus tard\n"
        "- ce qu'Adam a trouvé ou résumé pour vous\n"
        "- une idée à ne pas perdre\n\n"
        "*Adam ne dépose QUE dans cette boîte — vous gardez toujours la main sur le rangement.*",
    ),
    (
        "01-En cours",
        "🎯 En cours",
        "Vos chantiers **en cours**, avec un objectif et une échéance. Un projet a une fin.\n\n"
        "**Rangez ici :**\n"
        "- un lancement (produit, site, offre)\n"
        "- un recrutement en cours\n"
        "- un dossier client avec une deadline\n\n"
        "*Terminé ? Glissez le projet dans « 04-Archivées ».*",
    ),
    (
        "02-Mes responsabilités",
        "🧢 Mes responsabilités",
        "Vos responsabilités **durables** — les casquettes que vous portez au quotidien. "
        "Elles n'ont pas de date de fin.\n\n"
        "**Rangez ici, un dossier par casquette :**\n"
        "- Clients · Commercial · Finances\n"
        "- Équipe / RH · Fournisseurs\n"
        "- tout ce dont vous êtes responsable en continu\n\n"
        "*Créez un dossier de casquette quand vous avez la première note à y mettre — pas avant.*",
    ),
    (
        "03-Idées & ressources",
        "📚 Idées & ressources",
        "Votre bibliothèque : tout ce qui peut resservir, sans être un projet ni une responsabilité.\n\n"
        "**Rangez ici :**\n"
        "- procédures et modes d'emploi\n"
        "- fiches produits, argumentaires\n"
        "- articles et veille utiles\n\n"
        "*Adam pioche ici pour vous répondre avec vos propres références.*",
    ),
    (
        "04-Archivées",
        "🗄️ Archivées",
        "Le grenier : ce qui est **terminé ou en pause**. On ne jette pas, on range au calme.\n\n"
        "**Rangez ici :**\n"
        "- projets finis\n"
        "- clients devenus inactifs\n"
        "- anciens documents\n\n"
        "*Rien n'est perdu : tout reste consultable et récupérable.*",
    ),
    (
        "05-Journal",
        "🗓️ Journal",
        "Vos notes **datées** : le fil du temps de l'entreprise.\n\n"
        "**Rangez ici :**\n"
        "- comptes-rendus de réunion\n"
        "- le point d'une journée\n"
        "- une décision prise et sa date\n\n"
        "*Idéal pour retrouver « qu'est-ce qu'on avait décidé en… ? ».*",
    ),
    (
        "06-Contacts",
        "👥 Contacts",
        "Votre carnet de contacts vivant.\n\n"
        "**Rangez ici, une fiche par personne :**\n"
        "- clients et prospects\n"
        "- partenaires et fournisseurs\n"
        "- membres de l'équipe\n\n"
        "*Une fiche par contact = Adam sait de qui vous parlez.*",
    ),
    (
        "07-Mes réflexions",
        "💭 Mes réflexions",
        "Ce que **vous** pensez, par opposition à ce que vous avez seulement collecté.\n\n"
        "**Rangez ici :**\n"
        "- une intuition sur votre marché\n"
        "- une leçon tirée d'un projet\n"
        "- votre avis tranché sur une question\n\n"
        "*C'est le dossier qui rend votre second cerveau vraiment personnel.*",
    ),
    (
        "08-Modèles de notes",
        "🧩 Modèles de notes",
        "Vos gabarits réutilisables, pour créer vite une note toujours bien structurée.\n\n"
        "**Rangez ici :**\n"
        "- modèle de compte-rendu\n"
        "- modèle de fiche client\n"
        "- modèle de projet\n\n"
        "*Dupliquez un modèle plutôt que de repartir de zéro.*",
    ),
)


def _guide_body(emoji_title: str, body: str) -> str:
    """Contenu markdown d'une note-guide (frontmatter discret + titre + corps en langage dirigeant)."""
    return (
        "---\n"
        "type: guide\n"
        "---\n\n"
        f"# 👋 {emoji_title}\n\n"
        f"{body}\n"
    )


def ensure_structure() -> list[str]:
    """Crée la structure PARA du coffre si absente (idempotent). Retourne ce qui a été créé.

    Pose aussi une note-guide « À lire — … » dans chaque dossier : un coffre clé en main où chaque
    dossier explique son usage au dirigeant (aucun dossier muet). Idempotent : n'écrase jamais.
    """
    root = _vault_root()
    created: list[str] = []
    for folder in VAULT_STRUCTURE:
        directory = root / folder
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(folder)
    index = root / INDEX_FILENAME
    if not index.exists():
        # Écriture atomique (MOYENNE, cf. Finding #2 « par ricochet ») : même traitement que
        # write_note pour l'INDEX — pas de raison qu'un crash pendant l'init laisse un sommaire
        # tronqué, même si le risque est plus rare qu'une édition en direct.
        _atomic_write_text(index, _default_index())
        created.append(INDEX_FILENAME)
    for folder, emoji_title, body in _FOLDER_GUIDES:
        # Titre du fichier sans emoji (systèmes de fichiers frileux) mais parlant et trié en tête.
        guide_name = f"À lire — {emoji_title.split(' ', 1)[1]}{NOTE_SUFFIX}"
        guide = root / folder / guide_name
        if not guide.exists():
            guide.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(guide, _guide_body(emoji_title, body))
            created.append(f"{folder}/{guide_name}")
    return created


def _slugify(title: str) -> str:
    """Nom de fichier sûr et lisible (minuscules, tirets, sans séparateur de chemin)."""
    text = title.strip().lower().replace("/", "-").replace("\\", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç_-]", "", text)
    return text.strip("-")


def write_inbox_note(title: str, content: str) -> NoteContent:
    """Dépose une note dans la Boîte de réception (``00-Réception``).

    SEULE zone d'écriture autonome de l'agent (garde-fou Inbox/Outbox) : le dirigeant relit puis
    classe. N'écrase jamais une note existante (suffixe numérique en cas de collision).
    """
    ensure_structure()
    root = _vault_root()
    slug = _slugify(title) or "note"
    rel = f"{INBOX_DIR}/{slug}{NOTE_SUFFIX}"
    counter = 2
    while (root / rel).exists():
        rel = f"{INBOX_DIR}/{slug}-{counter}{NOTE_SUFFIX}"
        counter += 1
    return write_note(rel, content)


# ─── Notes gérées (identité stable) ──────────────────────────────────────────
# Certaines notes sont RÉÉCRITES par le produit à chaque rejeu (la fiche entreprise de l'onboarding).
# ``write_inbox_note`` ne convient pas : il suffixe (-2, -3…) et redéposerait un doublon à chaque fois.
# Une note gérée porte donc un ``lunaria-id`` en frontmatter : c'est SON identité, indépendante de son
# nom de fichier et de son dossier. On la met à jour SUR PLACE, où que le dirigeant l'ait rangée ou
# renommée entre-temps — le coffre est fait pour ranger, la note doit suivre.
_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_ID_RE = re.compile(r"^lunaria-id\s*:\s*(.+?)\s*$", re.MULTILINE)
# Le frontmatter tient dans les premiers octets : on ne lit pas les notes en entier pour le scan.
_FM_SNIFF_BYTES = 512

# ─── Index des notes gérées (cache lunaria-id → chemin) ──────────────────────
# ``find_managed_note`` était O(n) : il rouvrait CHAQUE note du coffre à chaque appel (donc à
# chaque écriture d'une note gérée, potentiellement à chaque tour de l'onboarding). Ce petit index
# évite de rescanner dans le cas courant (le chemin n'a pas bougé depuis le dernier appel). Ce n'est
# QU'UN CACHE : sa valeur est toujours re-vérifiée en relisant le frontmatter de la note visée avant
# d'être renvoyée, jamais renvoyée telle quelle — un index périmé/corrompu ne peut donc jamais faire
# remonter un mauvais résultat. Absent ou incohérent (note déplacée par un humain, entrée
# fantôme…) → repli sur le scan complet d'origine, qui répare l'index au passage (self-healing).
_MANAGED_INDEX_FILENAME = ".lunaria-managed-index.json"


def _managed_index_path() -> Path:
    return _vault_root() / _MANAGED_INDEX_FILENAME


def _read_managed_index() -> dict[str, str]:
    p = _managed_index_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_managed_index(index: dict[str, str]) -> None:
    try:
        _managed_index_path().write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        # cache non critique : une écriture ratée ne doit jamais faire échouer l'appelant — mais
        # une perte silencieuse ici peut faire réapparaître des doublons de note gérée (lunaria-id)
        # sans que rien ne l'explique, d'où un WARNING plutôt qu'un simple debug.
        logger.warning("écriture de l'index des notes gérées échouée (risque de doublon futur)", exc_info=True)


def _remember_managed_path(note_id: str, rel_path: str) -> None:
    index = _read_managed_index()
    if index.get(note_id) != rel_path:
        index[note_id] = rel_path
        _write_managed_index(index)


def _forget_managed_path(note_id: str) -> None:
    index = _read_managed_index()
    if note_id in index:
        del index[note_id]
        _write_managed_index(index)


def _is_ignored_rel(root: Path, path: Path) -> bool:
    """Vrai si ``path`` vit dans un dossier technique/caché (corbeille, ``.git``…) ou hors coffre."""
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True  # hors du coffre : à ignorer par prudence
    return any(part.startswith(".") or part in _IGNORED for part in rel_parts[:-1])


def _read_frontmatter(path: Path) -> dict:
    """Frontmatter YAML existant d'une note, sous forme de dict. ``{}`` si absent/invalide/illisible.

    Lecture bienveillante : un frontmatter cassé ou un fichier illisible ne doit jamais faire
    échouer l'écriture — au pire on perd la fusion pour cette note, jamais on ne plante le produit.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    block = _FM_BLOCK_RE.match(content)
    if not block:
        return {}
    try:
        data = yaml.safe_load(block.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _managed_body(
    note_id: str, title: str, content: str, existing_frontmatter: dict | None = None
) -> str:
    """Markdown d'une note gérée : frontmatter FUSIONNÉ (identité mise à jour, reste préservé) + contenu.

    Ne touche qu'aux clés gérées par le produit (``lunaria-id``, ``titre``) : toute clé ajoutée à la
    main par le dirigeant dans Obsidian (``tags``, ``aliases``, ``cssclass``, une clé personnalisée…)
    est conservée telle quelle. Un rejeu produit (ex. re-crawl de l'onboarding) ne doit JAMAIS effacer
    une métadonnée ajoutée par le dirigeant — c'est la règle de non-destruction appliquée au
    frontmatter, jusque-là seulement appliquée à l'identité (``lunaria-id`` ne bougeait déjà pas).
    """
    frontmatter = dict(existing_frontmatter or {})
    frontmatter["lunaria-id"] = note_id
    frontmatter["titre"] = title
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm_text}\n---\n\n{content.strip()}\n"


def _note_managed_id(path: Path) -> str | None:
    """``lunaria-id`` d'une note, ou None. Ne lit que l'en-tête du fichier."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            head = handle.read(_FM_SNIFF_BYTES)
    except (OSError, UnicodeDecodeError):
        return None
    block = _FM_BLOCK_RE.match(head)
    if not block:
        return None
    found = _FM_ID_RE.search(block.group(1))
    return found.group(1).strip().strip("\"'") if found else None


def find_managed_note(note_id: str) -> str | None:
    """Chemin relatif de la note portant ``note_id``, où qu'elle soit rangée. None si absente.

    Vérifie d'abord le petit cache lunaria-id → chemin (voir plus haut) : si l'entrée pointe vers
    une note VIVANTE (pas en corbeille) qui porte bien cet id, elle est renvoyée sans rouvrir le
    reste du coffre. Sinon (cache absent/périmé/corrompu), repli sur le scan complet d'origine, qui
    répare le cache au passage.

    La corbeille est exclue (``_IGNORED``) : une note supprimée est morte, on ne la ressuscite pas.
    """
    root = _vault_root()
    index = _read_managed_index()
    cached_rel = index.get(note_id)
    if cached_rel:
        candidate = root / cached_rel
        if (
            candidate.is_file()
            and not _is_ignored_rel(root, candidate)
            and _note_managed_id(candidate) == note_id
        ):
            return cached_rel

    found: str | None = None
    for path in sorted(root.rglob(f"*{NOTE_SUFFIX}")):
        if _is_ignored_rel(root, path):
            continue
        if _note_managed_id(path) == note_id:
            found = str(path.relative_to(root))
            break
    if found:
        _remember_managed_path(note_id, found)
    elif cached_rel:
        _forget_managed_path(note_id)  # entrée fantôme : autant ne pas la retenter la prochaine fois
    return found


def upsert_managed_note(note_id: str, title: str, content: str) -> NoteContent:
    """Crée ou met à jour la note gérée ``note_id`` (idempotent : un rejeu ne duplique jamais).

    Si la note existe (n'importe où dans le coffre), elle est réécrite SUR PLACE. Sinon elle est
    créée dans la Boîte de réception, comme toute entrée à valider par le dirigeant.

    Lève ``ValueError`` si le contenu est vide : mieux vaut pas de note qu'une note vide.
    """
    if not content or not content.strip():
        raise ValueError("empty managed note content")
    ensure_structure()

    # HAUTE (Finding #1) : « chercher l'existant → décider → écrire » doit être un bloc atomique.
    # Sans ce lock, deux upserts concurrents pour le même note_id (double-clic « régénérer », retry
    # réseau front après un timeout sur un crawl lent) peuvent tous les deux constater l'absence de
    # la note, calculer le MÊME chemin libre, puis écrire l'un après l'autre : le second écrase le
    # premier en silence, et CHAQUE appelant reçoit malgré tout un retour de succès (write_note
    # construit son retour depuis le contenu passé, pas une relecture du disque) — faux succès, pas
    # seulement perte silencieuse. Pas de réentrance ici : aucune fonction appelée sous ce lock
    # (find_managed_note, write_note, _read_frontmatter, _remember_managed_path…) n'acquiert elle-même
    # _VAULT_LOCK — un threading.Lock simple (non réentrant) suffit, pas besoin de RLock.
    with _VAULT_LOCK:
        existing = find_managed_note(note_id)
        if existing:
            existing_frontmatter = _read_frontmatter(_safe_note_path(existing))
            body = _managed_body(note_id, title, content, existing_frontmatter)
            result = write_note(existing, body)
            _remember_managed_path(note_id, existing)
            return result

        body = _managed_body(note_id, title, content)
        root = _vault_root()
        name = _safe_filename(title)
        rel = f"{INBOX_DIR}/{name}{NOTE_SUFFIX}"
        # Collision avec une note du dirigeant (sans identité) : on ne l'écrase jamais.
        counter = 2
        while (root / rel).exists():
            rel = f"{INBOX_DIR}/{name} {counter}{NOTE_SUFFIX}"
            counter += 1
        result = write_note(rel, body)
        _remember_managed_path(note_id, rel)
        return result


def _count_notes(directory: Path) -> int:
    total = 0
    for entry in directory.iterdir():
        if entry.name.startswith(".") or entry.name in _IGNORED:
            continue
        if entry.is_dir():
            total += _count_notes(entry)
        elif entry.is_file() and entry.suffix == NOTE_SUFFIX:
            total += 1
    return total


def _sync_active(root: Path) -> bool:
    """La copie locale est-elle reliée ? (US5)

    Vrai si une synchro est déclarée (``MEMORY_SYNC_ENABLED``) ou détectée : Syncthing dépose un
    dossier marqueur ``.stfolder`` à la racine du dossier partagé.
    """
    if os.environ.get("MEMORY_SYNC_ENABLED", "").strip().lower() in {"1", "true", "yes"}:
        return True
    return (root / ".stfolder").exists()


def status() -> MemoryStatus:
    """Statut honnête du coffre (accessible, nombre de notes, copie locale reliée ou non)."""
    root = _vault_root()
    return MemoryStatus(
        ok=root.is_dir(),
        note_count=_count_notes(root),
        local_copy=_sync_active(root),
        sync_available=sync_adapter.is_available(),
    )
