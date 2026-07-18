"""Kanban : tableau de tâches multi-agents (page « Tâches »)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import hermes_adapter, kanban_adapter
from ..deps import hermes_unavailable, require_bridge_key
from ..models import KanbanBoardsResponse, KanbanTasksResponse
from ..schemas import KanbanActionBody, KanbanBoardCreateBody, KanbanTaskCreateBody

router = APIRouter(dependencies=[Depends(require_bridge_key)])


@router.get("/kanban/boards")
def kanban_boards(include_archived: bool = False) -> KanbanBoardsResponse:
    """Liste les boards Kanban avec compteurs par statut."""
    try:
        return kanban_adapter.list_boards(include_archived=include_archived)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/kanban/boards")
def kanban_create_board(body: KanbanBoardCreateBody) -> dict:
    """Crée un board."""
    try:
        return kanban_adapter.create_board(body.slug, body.name)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/kanban/boards/{slug}/switch")
def kanban_switch_board(slug: str) -> dict:
    """Définit le board actif."""
    try:
        return kanban_adapter.switch_board(slug)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/kanban/tasks")
def kanban_tasks(
    board: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    include_archived: bool = False,
) -> KanbanTasksResponse:
    """Liste les tâches d'un board (filtres optionnels)."""
    try:
        return kanban_adapter.list_tasks(
            board=board, status=status, assignee=assignee, include_archived=include_archived
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.get("/kanban/tasks/{task_id}")
def kanban_task_detail(task_id: str, board: str | None = None) -> dict:
    """Détail d'une tâche : task + comments + events + runs + dépendances."""
    try:
        return kanban_adapter.get_task(task_id, board=board)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/kanban/tasks")
def kanban_create_task(body: KanbanTaskCreateBody) -> dict:
    """Crée une tâche."""
    try:
        return kanban_adapter.create_task(
            title=body.title, body=body.body, assignee=body.assignee,
            priority=body.priority, workspace=body.workspace, triage=body.triage, board=body.board,
        )
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)


@router.post("/kanban/tasks/{task_id}/{verb}")
def kanban_task_action(task_id: str, verb: str, body: KanbanActionBody) -> dict:
    """Transition d'une tâche : complete | block | unblock | promote | schedule | reclaim |
    specify | archive | assign. (Pas de suppression : archive uniquement.)"""
    board = body.board
    try:
        if verb == "complete":
            return kanban_adapter.complete_task(task_id, result=body.result, board=board)
        if verb == "block":
            return kanban_adapter.block_task(task_id, reason=body.reason, board=board)
        if verb == "unblock":
            return kanban_adapter.unblock_task(task_id, board=board)
        if verb == "promote":
            return kanban_adapter.promote_task(task_id, board=board)
        if verb == "schedule":
            return kanban_adapter.schedule_task(task_id, reason=body.reason, board=board)
        if verb == "reclaim":
            return kanban_adapter.reclaim_task(task_id, reason=body.reason, board=board)
        if verb == "specify":
            return kanban_adapter.specify_task(task_id, board=board)
        if verb == "archive":
            return kanban_adapter.archive_task(task_id, board=board)
        if verb == "assign":
            if not body.assignee:
                raise HTTPException(
                    status_code=422,
                    detail={"error": {"code": "invalid", "message": "assignee requis"}},
                )
            return kanban_adapter.assign_task(task_id, body.assignee, board=board)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
    raise HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": f"action inconnue: {verb}"}},
    )


@router.post("/kanban/dispatch")
def kanban_dispatch(body: KanbanActionBody, dry_run: bool = False) -> dict:
    """Lance une passe du dispatcher (promeut les tâches prêtes, lance les workers)."""
    try:
        return kanban_adapter.dispatch(board=body.board, dry_run=dry_run)
    except hermes_adapter.HermesUnavailable as exc:
        raise hermes_unavailable(exc)
