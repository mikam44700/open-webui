"""Exécution en arrière-plan des mises à jour de services Docker (Crawl4AI…).

Une mise à jour = télécharger la nouvelle image + recréer le conteneur + re-vérifier qu'il
répond. C'est long (plusieurs minutes pour Crawl4AI), donc on l'exécute dans un thread et le
front suit la progression par polling — MÊME PRINCIPE que la mise à jour du moteur Hermes.

État conservé en mémoire (le bridge tourne en un seul process supervisé). Si le bridge
redémarre pendant une MAJ, l'état est perdu mais Docker finit de recréer le conteneur ;
le client peut relancer une vérification.

L'``target`` reçoit une fonction ``log(msg)`` pour tracer sa progression et DOIT lever une
exception en cas d'échec (le message est remonté au front). C'est le filet de sécurité :
si l'outil ne répond pas après la MAJ, ``target`` lève → la MAJ est marquée en échec.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

# clé service ("crawl4ai") → état de la dernière MAJ lancée.
_RUNS: dict[str, dict] = {}
_LOCK = threading.Lock()


def is_running(key: str) -> bool:
    st = _RUNS.get(key)
    return bool(st and st["running"])


def start(key: str, target: Callable[[Callable[[str], None]], None]) -> dict:
    """Lance ``target`` en arrière-plan. Idempotent : si une MAJ tourne déjà pour ``key``,
    ne relance rien (renvoie ``already_running``)."""
    with _LOCK:
        if is_running(key):
            logger.info("MAJ Docker %r déjà en cours : appel à start() ignoré (idempotent)", key)
            return {"started": True, "already_running": True}
        state = {"running": True, "started": True, "success": None, "log": []}
        _RUNS[key] = state
    logger.info("MAJ Docker démarrée : %s", key)

    def log(msg: str) -> None:
        state["log"].append(msg)
        logger.info("[MAJ Docker %s] %s", key, msg)

    def run() -> None:
        try:
            target(log)
            state["success"] = True
            logger.info("MAJ Docker %r terminée avec succès", key)
        except Exception as exc:  # noqa: BLE001 — message remonté au front (best-effort)
            state["success"] = False
            state["log"].append(f"Échec : {exc}")
            logger.warning("MAJ Docker %r en ÉCHEC : %s", key, exc, exc_info=True)
        finally:
            state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"started": True}


def status(key: str) -> dict:
    """État de la dernière MAJ : {running, started, success, log}. ``started`` est faux si
    aucune MAJ n'a jamais été lancée pour ce service."""
    st = _RUNS.get(key)
    if not st:
        return {"running": False, "started": False, "success": None, "log": ""}
    return {
        "running": st["running"],
        "started": st["started"],
        "success": st["success"],
        "log": "\n".join(st["log"]),
    }


def reset(key: str | None = None) -> None:
    """Réinitialise l'état (usage tests)."""
    if key is None:
        _RUNS.clear()
    else:
        _RUNS.pop(key, None)
