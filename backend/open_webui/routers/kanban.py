"""Router Kanban — LunarIA V2.

Le moteur tient un registre de taches durable (SQLite, WAL) et l'expose par un
plugin de son tableau de bord, sous `/api/plugins/kanban/`. Ce router en relaie
cinq routes, et cinq seulement.

Il est distinct de `routers/hermes.py` pour une raison de fond : le kanban est un
plugin, qui peut ne pas etre installe. Cette distinction porte tout le
comportement d'erreur de la page — un 404 (« pas de registre ici ») et un 503
(« le moteur ne repond pas ») veulent dire des choses opposees, et les confondre
ferait annoncer une panne a quelqu'un dont le moteur va parfaitement bien.

Ce qui est reutilise de `hermes.py` plutot que recopie : la session
authentifiee, la reconnexion sur 401, et la traduction des erreurs reseau en
503/504 lisibles. Deux copies d'un client HTTP finiraient par diverger.

Trois regles tenues ici :
  1. Le navigateur ne connait ni l'adresse du moteur, ni sa cle.
  2. Une seule ecriture est possible : debloquer. La liste blanche porte sur les
     routes ET sur les champs — voir `modifier_tache`.
  3. Tout est reserve a l'administrateur, comme le reste du pilotage.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from open_webui.routers.hermes import _appeler
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter()

BASE = "/api/plugins/kanban"

# Champs retenus d'une tache. Le moteur en porte une quarantaine ; les rouages
# (workspace, claim_lock, worker_pid, model_override, tenant...) n'apprennent
# rien a un dirigeant et n'ont pas a sortir du serveur.
_CHAMPS_TACHE = {
    "id": "id",
    "title": "titre",
    "status": "statut",
    "block_kind": "typeBlocage",
    "assignee": "responsable",
    "priority": "priorite",
    "created_at": "creeLe",
    "started_at": "demarreLe",
    "completed_at": "termineLe",
    "consecutive_failures": "echecsConsecutifs",
    "block_recurrences": "reblocages",
}

# Champs supplementaires de la fiche detaillee.
_CHAMPS_FICHE = {
    **_CHAMPS_TACHE,
    "body": "consigne",
    "result": "resultat",
    "last_failure_error": "derniereErreur",
}


def _projeter(brut: Any, champs: dict) -> dict:
    """Ne garde d'une tache que ce que l'ecran affiche."""
    if not isinstance(brut, dict):
        return {}

    return {sortie: brut.get(entree) for entree, sortie in champs.items() if entree in brut}


def _taches(charge: Any, champs: dict) -> list:
    """Extrait la liste de taches.

    Le plugin ne rend PAS une liste a plat : il rend les taches deja rangees par
    colonne, sous la forme

        {"columns": [{"name": "triage", "tasks": [...]}, {"name": "todo", ...}]}

    Une lecture qui cherche `tasks` a la racine trouve donc toujours vide, et
    l'appel repond 200 — un ecran vide sans le moindre message d'erreur. C'est
    exactement ce qui est arrive.

    On aplatit ici plutot que de reprendre leur decoupage : le regroupement en
    six colonnes appartient a `lib/kanban/colonnes.ts`, qui est teste, et
    dependre du leur ferait perdre la distinction entre un statut inconnu et un
    statut range d'office (le plugin fait `col = t.status if t.status in columns
    else "todo"` — precisement le repli silencieux qu'on refuse).
    """
    if isinstance(charge, list):
        brutes = charge
    elif isinstance(charge, dict):
        colonnes = charge.get("columns")
        if isinstance(colonnes, list):
            brutes = [
                tache
                for colonne in colonnes
                if isinstance(colonne, dict)
                for tache in (colonne.get("tasks") or [])
            ]
        else:
            brutes = charge.get("tasks") or charge.get("taches") or []
    else:
        brutes = []

    return [_projeter(tache, champs) for tache in brutes if isinstance(tache, dict)]


def _dependances(charge: Any) -> dict:
    """Combien de parents et d'enfants par tache.

    Le plugin ne rend pas la liste des liens : il rend un compte par tache
    (`link_counts`), plus une progression (`progress`) sur les taches qui ont
    des enfants. C'est suffisant pour dire « cette tache en attend une autre »
    sans un aller-retour de plus.
    """
    if not isinstance(charge, dict):
        return {}

    colonnes = charge.get("columns")
    if not isinstance(colonnes, list):
        return {}

    comptes: dict = {}
    for colonne in colonnes:
        if not isinstance(colonne, dict):
            continue
        for tache in colonne.get("tasks") or []:
            if not isinstance(tache, dict):
                continue
            liens = tache.get("link_counts") or {}
            progression = tache.get("progress") or {}
            comptes[tache.get("id")] = {
                "parents": liens.get("parents", 0),
                "enfants": liens.get("children", 0),
                "faits": progression.get("done"),
                "total": progression.get("total"),
            }

    return comptes


# --------------------------------------------------------------------------
# Lecture
# --------------------------------------------------------------------------


@router.get("/config")
async def configuration(user=Depends(get_admin_user)):
    """Les tableaux disponibles, et surtout : le registre existe-t-il ?

    Un 404 remonte tel quel au navigateur. C'est volontaire : la page doit
    pouvoir dire « ce moteur n'a pas de registre de taches » sans le confondre
    avec une panne.
    """
    charge = await _appeler(f"{BASE}/config")
    if not isinstance(charge, dict):
        return {"tableaux": [], "tableauCourant": None}

    return {
        "tableaux": charge.get("boards") or charge.get("tableaux") or [],
        "tableauCourant": charge.get("current_board") or charge.get("board"),
    }


@router.get("/board")
async def tableau(
    tableau: Optional[str] = Query(None),
    inclure_archivees: bool = Query(False),
    user=Depends(get_admin_user),
):
    """Les taches du tableau, elaguees de leurs rouages."""
    parametres = []
    if tableau:
        parametres.append(f"board={tableau}")
    if inclure_archivees:
        parametres.append("include_archived=true")
    suffixe = f"?{'&'.join(parametres)}" if parametres else ""

    charge = await _appeler(f"{BASE}/board{suffixe}")

    return {"taches": _taches(charge, _CHAMPS_TACHE), "dependances": _dependances(charge)}


@router.get("/tasks/{task_id}")
async def fiche_tache(task_id: str, user=Depends(get_admin_user)):
    """Le detail d'une tache : consigne, resultat, echanges."""
    charge = await _appeler(f"{BASE}/tasks/{task_id}")
    fiche = _projeter(charge, _CHAMPS_FICHE)

    messages = []
    if isinstance(charge, dict):
        for message in charge.get("comments") or charge.get("messages") or []:
            if isinstance(message, dict):
                messages.append(
                    {
                        "auteur": message.get("author") or message.get("auteur"),
                        "texte": message.get("body") or message.get("text") or message.get("texte"),
                        "ecritLe": message.get("created_at") or message.get("ecritLe"),
                    }
                )

    fiche["messages"] = messages
    return fiche


# --------------------------------------------------------------------------
# La seule ecriture : debloquer
# --------------------------------------------------------------------------


class ChangementStatut(BaseModel):
    statut: str = Field(..., description="Seule la valeur « ready » est acceptee.")


@router.patch("/tasks/{task_id}")
async def modifier_tache(
    task_id: str, corps: ChangementStatut, user=Depends(get_admin_user)
):
    """Debloque une tache, et rien d'autre.

    Le corps accepte par le moteur (`UpdateTaskBody`) porte aussi `title`,
    `body`, `result`, `assignee`, `priority`, `block_reason` et `metadata`.
    Rien de tout cela ne doit pouvoir etre ecrit depuis cette page : le modele
    ci-dessus ne connait qu'un champ, et la verification ci-dessous ne laisse
    passer qu'une valeur.

    C'est ensuite le moteur qui applique sa propre transition — il appelle
    `unblock_task()` quand la tache courante est `blocked` ou `scheduled`. On ne
    reimplemente pas cette regle ici : elle lui appartient.
    """
    statut = f"{corps.statut}".strip().lower()
    if statut != "ready":
        raise HTTPException(
            status_code=400,
            detail="Cette page ne sait que debloquer une tache.",
        )

    charge = await _appeler(
        f"{BASE}/tasks/{task_id}", methode="PATCH", corps={"status": "ready"}
    )

    # On renvoie l'etat reel rendu par le moteur, jamais l'etat espere.
    return _projeter(charge, _CHAMPS_FICHE) or {"id": task_id, "statut": None}


class NouveauMessage(BaseModel):
    texte: str = Field(..., min_length=1, max_length=4000)


@router.post("/tasks/{task_id}/comments")
async def ecrire_message(
    task_id: str, corps: NouveauMessage, user=Depends(get_admin_user)
):
    """Le message qui accompagne la decision, conserve dans l'historique."""
    charge = await _appeler(
        f"{BASE}/tasks/{task_id}/comments",
        methode="POST",
        corps={"body": corps.texte.strip()},
    )

    if not isinstance(charge, dict):
        return {"ok": True}

    return {
        "auteur": charge.get("author") or charge.get("auteur"),
        "texte": charge.get("body") or charge.get("texte"),
        "ecritLe": charge.get("created_at") or charge.get("ecritLe"),
    }
