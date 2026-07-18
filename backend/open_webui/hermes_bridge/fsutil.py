"""Primitives fichier partagées : verrou exclusif + écriture atomique.

Consolidation (audit phases 1-3) : plusieurs modules (``brain_adapter``, ``google_direct``,
``hermes_adapter``, ``memory_adapter``) avaient chacun réimplémenté, indépendamment, le MÊME
verrou fichier ``fcntl.flock`` sur ``<path>.lock`` et la MÊME écriture atomique
(``tempfile.mkstemp`` dans le dossier cible + ``os.replace``). Source unique ici.

Ne couvre PAS :
- ``profiles_adapter._ATOMIC_WRITE_HELPER`` : ce code tourne dans un sous-processus Hermes
  isolé (``python -c``, cf. ``introspect()``) qui ne peut pas importer ``providers_bridge`` —
  il reste dupliqué en texte, volontairement.
- ``oauth_engine._write_secure`` : sémantique différente (création directe en 0600 dès
  l'ouverture, pas de fichier temporaire) — écarté d'une fusion pour ne pas changer son
  comportement ni sa garantie de permissions.
"""

from __future__ import annotations

import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:  # verrou POSIX (VPS Linux / macOS)
    import fcntl
except ImportError:  # pragma: no cover - Windows n'est pas une cible
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Verrou exclusif inter-process sur ``path`` (fichier dédié ``<path>.lock``).

    Pas de verrou (no-op) si ``fcntl`` est indisponible (Windows, hors cible produit).
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:  # pragma: no cover
        yield
        return
    fd = open(lock_path, "a+", encoding="utf-8")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:  # pragma: no cover
            logger.debug("libération du verrou fichier %s échouée (non bloquant)", lock_path, exc_info=True)
        fd.close()


def atomic_write_text(path: Path, content: str, mode: int | None = None) -> None:
    """Écrit ``content`` dans ``path`` de façon atomique (fichier temporaire dans le même
    dossier + ``os.replace``) : jamais de fichier tronqué/vide visible en cas de crash
    pendant l'écriture (contrairement à ``write_text``/``"w"``, qui tronque IMMÉDIATEMENT).

    ``mode`` (optionnel) : permissions POSIX explicites (ex. ``0o600`` pour un ``.env``
    contenant des secrets), posées sur le temporaire AVANT écriture puis reconfirmées sur
    la cible APRÈS le ``replace`` — ``None`` (défaut) ne touche à aucune permission.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        if mode is not None:
            os.chmod(tmp, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp, path)
        if mode is not None:
            os.chmod(path, mode)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
