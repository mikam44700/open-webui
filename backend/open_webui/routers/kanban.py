"""Router /api/v1/kanban — tableau de tâches multi-agents de Hermes (page « Tâches »).

Admin-only. Proxifie vers le Providers Bridge (réutilise ``_bridge`` du router providers).
Hermes est la source de vérité (kanban.db, piloté par la CLI ``hermes kanban``).

Page « Tâches » d'Agent OS — portage de la page Kanban de Hermes Desktop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.routers.providers import _bridge
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


class BoardCreate(BaseModel):
    slug: str
    name: str | None = None


class TaskCreate(BaseModel):
    title: str
    body: str | None = None
    assignee: str | None = None
    priority: int | None = None
    workspace: str | None = None
    triage: bool = False
    board: str | None = None


class TaskAction(BaseModel):
    board: str | None = None
    reason: str | None = None
    result: str | None = None
    assignee: str | None = None


@router.get("/boards")
async def list_boards(include_archived: bool = False, user=Depends(get_admin_user)):
    """Liste les boards Kanban avec compteurs par statut."""
    return await _bridge("GET", f"/kanban/boards?include_archived={str(include_archived).lower()}")


@router.post("/boards")
async def create_board(body: BoardCreate, user=Depends(get_admin_user)):
    """Crée un board."""
    return await _bridge("POST", "/kanban/boards", json=body.model_dump(exclude_none=True))


@router.post("/boards/{slug}/switch")
async def switch_board(slug: str, user=Depends(get_admin_user)):
    """Définit le board actif."""
    return await _bridge("POST", f"/kanban/boards/{slug}/switch")


@router.get("/tasks")
async def list_tasks(
    board: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    include_archived: bool = False,
    user=Depends(get_admin_user),
):
    """Liste les tâches d'un board (filtres optionnels)."""
    params = [f"include_archived={str(include_archived).lower()}"]
    if board:
        params.append(f"board={board}")
    if status:
        params.append(f"status={status}")
    if assignee:
        params.append(f"assignee={assignee}")
    return await _bridge("GET", "/kanban/tasks?" + "&".join(params))


@router.get("/tasks/{task_id}")
async def task_detail(task_id: str, board: str | None = None, user=Depends(get_admin_user)):
    """Détail d'une tâche : task + comments + events + runs."""
    suffix = f"?board={board}" if board else ""
    return await _bridge("GET", f"/kanban/tasks/{task_id}{suffix}")


@router.post("/tasks")
async def create_task(body: TaskCreate, user=Depends(get_admin_user)):
    """Crée une tâche."""
    return await _bridge("POST", "/kanban/tasks", json=body.model_dump(exclude_none=True))


@router.post("/tasks/{task_id}/{verb}")
async def task_action(task_id: str, verb: str, body: TaskAction, user=Depends(get_admin_user)):
    """Transition d'une tâche (complete/block/unblock/promote/schedule/reclaim/specify/archive/assign)."""
    return await _bridge("POST", f"/kanban/tasks/{task_id}/{verb}", json=body.model_dump(exclude_none=True))


@router.post("/dispatch")
async def dispatch(body: TaskAction, dry_run: bool = False, user=Depends(get_admin_user)):
    """Lance une passe du dispatcher (promeut les tâches prêtes, lance les workers)."""
    return await _bridge(
        "POST", f"/kanban/dispatch?dry_run={str(dry_run).lower()}", json=body.model_dump(exclude_none=True)
    )
