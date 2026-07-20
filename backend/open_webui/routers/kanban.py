"""Router Kanban — l'onglet Tâches parle au tableau du moteur Hermes.

Le tableau de bord du travail (SPEC-kanban-taches.md) n'a PAS de base à lui :
les tâches vivent déjà dans le kanban.db du moteur Hermes, piloté par la CLI
`hermes kanban`. Ce router shelle cette CLI (sortie --json) exactement comme
hermes.py le fait pour la page Capacités.

Règle posée dans la spec : on ne touche JAMAIS kanban.db directement. La v1
avait un dashboard web qui écrivait le statut en base — c'est le raccourci
qu'on refuse ici. Un seul chemin : les verbes officiels du moteur.

Palier 1 = lecture + actions sûres : lister, créer, faire avancer. Aucun verbe
destructif n'est exposé (ni delete, ni archive) — destructif par construction
impossible, pas seulement interdit (même principe que luna-app-actions).
"""

import json
import logging
import os
import subprocess
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter()

HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
_TIMEOUT = 20

# Les 9 statuts du moteur regroupés dans les 4 colonnes montrées au patron
# (décision de cadrage validée : un dirigeant de TPE n'a pas besoin de 8 lanes).
COLONNES: list[dict] = [
    {"cle": "triage", "titre": "Triage", "aide": "À trier — ces tâches attendent une décision."},
    {"cle": "a_faire", "titre": "À faire", "aide": "Prêtes à être prises en charge."},
    {"cle": "en_cours", "titre": "En cours", "aide": "Un agent travaille dessus en ce moment."},
    {"cle": "termine", "titre": "Terminé", "aide": "Travail fini."},
]

# statut moteur -> colonne affichée. Une tâche bloquée remonte en Triage : elle
# a besoin d'une décision humaine, c'est le sens de cette colonne.
_STATUT_VERS_COLONNE = {
    "triage": "triage",
    "blocked": "triage",
    "todo": "a_faire",
    "scheduled": "a_faire",
    "ready": "a_faire",
    "running": "en_cours",
    "review": "termine",
    "done": "termine",
}


class Tache(BaseModel):
    id: str
    titre: str
    description: Optional[str] = None
    colonne: str
    agent: Optional[str] = None  # assignee du moteur
    bloquee: bool = False
    cree_le: Optional[int] = None  # epoch secondes


class Tableau(BaseModel):
    colonnes: list[dict]
    taches: list[Tache]
    total: int


class CreationTache(BaseModel):
    titre: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)


class AvancementTache(BaseModel):
    # Cible volontairement limitée : on n'expose que les mouvements sûrs.
    vers: Literal["a_faire", "en_cours", "termine"]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    """Exécute `hermes kanban ...`. Aucun argument n'est interpolé dans un shell."""
    try:
        return subprocess.run(
            [HERMES_BIN, "kanban", *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Le moteur Hermes n'est pas disponible.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Le moteur Hermes n'a pas répondu à temps.") from exc


def _run_json(args: list[str]):
    proc = _run([*args, "--json"])
    if proc.returncode != 0:
        # stderr du moteur = message technique : journalisé, jamais renvoyé au client.
        log.warning("hermes kanban %s a échoué (code %s): %s", args, proc.returncode, proc.stderr.strip())
        raise HTTPException(status_code=502, detail="Le tableau des tâches est momentanément indisponible.")
    sortie = (proc.stdout or "").strip()
    if not sortie:
        return None
    try:
        return json.loads(sortie)
    except json.JSONDecodeError as exc:
        log.warning("Sortie inattendue de hermes kanban %s: %s", args, sortie[:200])
        raise HTTPException(status_code=502, detail="Réponse inattendue du moteur des tâches.") from exc


def _vers_tache(brut: dict) -> Optional[Tache]:
    statut = (brut.get("status") or "").strip()
    colonne = _STATUT_VERS_COLONNE.get(statut)
    if colonne is None:  # archived, ou statut inconnu d'une version plus récente
        return None
    return Tache(
        id=brut.get("id") or "",
        titre=brut.get("title") or "(sans titre)",
        description=brut.get("body"),
        colonne=colonne,
        agent=brut.get("assignee"),
        bloquee=statut == "blocked",
        cree_le=brut.get("created_at"),
    )


@router.get("/board", response_model=Tableau)
def get_board(user=Depends(get_verified_user)):
    """Le tableau complet : colonnes + tâches actives (les archivées sont exclues)."""
    brut = _run_json(["list"]) or []
    taches = [t for t in (_vers_tache(b) for b in brut if isinstance(b, dict)) if t is not None]
    return Tableau(colonnes=COLONNES, taches=taches, total=len(taches))


@router.post("/tasks", response_model=Tache)
def create_task(form: CreationTache, user=Depends(get_verified_user)):
    """Crée une tâche. Elle atterrit dans « À faire » (statut moteur `ready`)."""
    args = ["create", form.titre]
    if form.description:
        args += ["--body", form.description]
    args += ["--created-by", "patron"]

    brut = _run_json(args)
    if not isinstance(brut, dict):
        raise HTTPException(status_code=502, detail="La tâche n'a pas pu être créée.")
    tache = _vers_tache(brut)
    if tache is None:
        raise HTTPException(status_code=502, detail="La tâche a été créée dans un état inattendu.")
    return tache


@router.post("/tasks/{task_id}/move", response_model=Tache)
def move_task(task_id: str, form: AvancementTache, user=Depends(get_verified_user)):
    """Fait avancer une tâche d'une colonne à l'autre, via les verbes du moteur.

    Aucun verbe destructif n'est atteignable depuis ici : `vers` est un littéral
    fermé, et la table ci-dessous ne contient que des mouvements réversibles.
    """
    verbes = {
        "a_faire": ["unblock", task_id],  # ramène une tâche bloquée/en triage dans le flux
        "en_cours": ["claim", task_id],  # une tâche prise en charge passe en `running`
        "termine": ["complete", task_id],
    }
    _run(verbes[form.vers])

    # Le moteur signale certains refus par un message sur un code de sortie 0
    # (ex. « cannot unblock ... (not blocked?) ») : le code retour ne suffit pas.
    # On relit donc l'état réel et on vérifie que la tâche est bien arrivée.
    apres = _run_json(["show", task_id])
    brut = apres.get("task") if isinstance(apres, dict) and "task" in apres else apres
    if not isinstance(brut, dict):
        raise HTTPException(status_code=502, detail="Tâche introuvable après déplacement.")
    tache = _vers_tache(brut)
    if tache is None:
        raise HTTPException(status_code=502, detail="La tâche est dans un état non affichable.")
    if tache.colonne != form.vers:
        log.info("Déplacement %s -> %s refusé par le moteur (reste en %s)", task_id, form.vers, tache.colonne)
        raise HTTPException(
            status_code=409,
            detail="Le moteur n'autorise pas ce déplacement pour cette tâche.",
        )
    return tache
