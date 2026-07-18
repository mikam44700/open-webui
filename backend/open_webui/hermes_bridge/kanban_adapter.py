"""Adapter Kanban — tableau de tâches multi-agents de Hermes (page « Tâches »).

Pilote le Kanban Hermes (SQLite partagé entre profils) via la CLI ``hermes kanban ... --json``,
exactement comme Hermes Desktop le fait de son côté. Le Kanban est le cockpit de l'orchestration :
chaque tâche est assignée à un agent (profil), passe par des statuts (triage → ready → running →
done…), et un *dispatcher* peut promouvoir les tâches prêtes et lancer les workers.

Source de vérité = Hermes. On ne stocke rien ici : on traduit les commandes CLI en JSON.

Garde-fou : aucune suppression destructive — on **archive** (réversible côté Hermes), jamais ``rm``.
"""

from __future__ import annotations

import json
import subprocess

from . import hermes_adapter
from .models import KanbanBoard, KanbanBoardsResponse, KanbanTask, KanbanTasksResponse


def _run(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    """Exécute ``hermes kanban <args>``. Lève HermesUnavailable si le binaire est injoignable."""
    try:
        return subprocess.run(
            [hermes_adapter.HERMES_BIN, "kanban", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise hermes_adapter.HermesUnavailable(str(exc)) from exc


def _run_json(args: list[str], timeout: int = 90):
    """Exécute une commande kanban qui renvoie du JSON sur stdout.

    Une sortie non-JSON (CLI mis à jour, avertissement imprévu sur stdout...) est traitée
    comme une indisponibilité de Hermes (503 honnête côté API), jamais comme un 500 brut.
    """
    res = _run(args, timeout=timeout)
    if res.returncode != 0:
        raise hermes_adapter.HermesUnavailable(
            (res.stderr or res.stdout).strip()[:300] or "commande kanban échouée"
        )
    try:
        return json.loads(res.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        raise hermes_adapter.HermesUnavailable(
            f"réponse kanban illisible: {res.stdout.strip()[:200]}"
        ) from exc


def _run_ok(args: list[str], timeout: int = 90) -> dict:
    """Exécute une commande kanban « action » (sortie texte). Renvoie ``{ok, message}``."""
    res = _run(args, timeout=timeout)
    if res.returncode != 0:
        return {"ok": False, "message": (res.stderr or res.stdout).strip()[:300]}
    return {"ok": True, "message": res.stdout.strip()[:300]}


def _board_args(board: str | None) -> list[str]:
    """Préfixe ``--board <slug>`` si un board précis est ciblé (sinon board courant)."""
    return ["--board", board] if board else []


# --- BOARDS -------------------------------------------------------------------


def list_boards(include_archived: bool = False) -> KanbanBoardsResponse:
    """Liste les boards (un par projet/flux de travail) avec compteurs par statut."""
    args = ["boards", "list", "--json"]
    if include_archived:
        args.append("--all")
    raw = _run_json(args)
    boards = [
        KanbanBoard(
            slug=b["slug"],
            name=b.get("name") or b["slug"],
            description=b.get("description") or "",
            icon=b.get("icon") or "",
            color=b.get("color") or "",
            is_current=bool(b.get("is_current", False)),
            archived=bool(b.get("archived", False)),
            total=int(b.get("total", 0) or 0),
            counts=b.get("counts") or {},
        )
        for b in raw
    ]
    current = next((b.slug for b in boards if b.is_current), boards[0].slug if boards else "default")
    return KanbanBoardsResponse(boards=boards, current=current)


def create_board(slug: str, name: str | None = None) -> dict:
    """Crée un board. Renvoie ``{ok, message}``."""
    args = ["boards", "create", slug]
    if name:
        args += ["--name", name]
    return _run_ok(args)


def switch_board(slug: str) -> dict:
    """Définit le board actif pour les appels suivants."""
    return _run_ok(["boards", "switch", slug])


# --- TÂCHES : lecture ---------------------------------------------------------


def _task_from(raw: dict) -> KanbanTask:
    task_id = raw.get("id")
    if task_id is None:
        # Réponse kanban malformée (item sans identifiant) : signalé honnêtement, jamais un
        # KeyError brut qui remonterait en 500 non enveloppé.
        raise hermes_adapter.HermesUnavailable("réponse kanban invalide: tâche sans identifiant")
    return KanbanTask(
        id=task_id,
        title=raw.get("title") or "",
        body=raw.get("body"),
        assignee=raw.get("assignee"),
        status=raw.get("status") or "todo",
        priority=int(raw.get("priority", 0) or 0),
        tenant=raw.get("tenant"),
        workspace_kind=raw.get("workspace_kind") or "scratch",
        workspace_path=raw.get("workspace_path"),
        branch_name=raw.get("branch_name"),
        created_by=raw.get("created_by"),
        created_at=raw.get("created_at"),
        started_at=raw.get("started_at"),
        completed_at=raw.get("completed_at"),
        result=raw.get("result"),
        skills=raw.get("skills") or [],
        max_retries=raw.get("max_retries"),
    )


def list_tasks(
    board: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    include_archived: bool = False,
) -> KanbanTasksResponse:
    """Liste les tâches du board (filtres optionnels statut/assignee/archivées)."""
    args = [*_board_args(board), "list", "--json"]
    if status:
        args += ["--status", status]
    if assignee:
        args += ["--assignee", assignee]
    if include_archived:
        args.append("--archived")
    raw = _run_json(args)
    return KanbanTasksResponse(tasks=[_task_from(t) for t in raw])


def get_task(task_id: str, board: str | None = None) -> dict:
    """Détail d'une tâche : task + comments + events + runs + dépendances."""
    raw = _run_json([*_board_args(board), "show", task_id, "--json"])
    task = raw.get("task") or {}
    return {
        "task": _task_from(task).model_dump() if task else None,
        "latest_summary": raw.get("latest_summary"),
        "parents": raw.get("parents") or [],
        "children": raw.get("children") or [],
        "comments": raw.get("comments") or [],
        "events": raw.get("events") or [],
        "runs": raw.get("runs") or [],
    }


# --- TÂCHES : écriture / transitions -----------------------------------------


def create_task(
    title: str,
    body: str | None = None,
    assignee: str | None = None,
    priority: int | None = None,
    workspace: str | None = None,
    triage: bool = False,
    board: str | None = None,
) -> dict:
    """Crée une tâche. Renvoie la tâche créée (JSON) avec son id."""
    args = [*_board_args(board), "create", title, "--json"]
    if body:
        args += ["--body", body]
    if assignee:
        args += ["--assignee", assignee]
    if priority is not None:
        args += ["--priority", str(priority)]
    if workspace:
        args += ["--workspace", workspace]
    if triage:
        args.append("--triage")
    raw = _run_json(args)
    return {"ok": True, "task": _task_from(raw).model_dump()}


def _action(verb: str, task_id: str, board: str | None, extra: list[str] | None = None) -> dict:
    return _run_ok([*_board_args(board), verb, task_id, *(extra or [])])


def complete_task(task_id: str, result: str | None = None, board: str | None = None) -> dict:
    return _action("complete", task_id, board, (["--result", result] if result else None))


def block_task(task_id: str, reason: str | None = None, board: str | None = None) -> dict:
    return _action("block", task_id, board, ([reason] if reason else None))


def unblock_task(task_id: str, board: str | None = None) -> dict:
    return _action("unblock", task_id, board)


def promote_task(task_id: str, board: str | None = None) -> dict:
    return _action("promote", task_id, board)


def schedule_task(task_id: str, reason: str | None = None, board: str | None = None) -> dict:
    return _action("schedule", task_id, board, ([reason] if reason else None))


def reclaim_task(task_id: str, reason: str | None = None, board: str | None = None) -> dict:
    return _action("reclaim", task_id, board, (["--reason", reason] if reason else None))


def specify_task(task_id: str, board: str | None = None) -> dict:
    return _action("specify", task_id, board)


def archive_task(task_id: str, board: str | None = None) -> dict:
    """Archive une tâche (réversible côté Hermes ; jamais de suppression destructive)."""
    return _action("archive", task_id, board)


def assign_task(task_id: str, assignee: str, board: str | None = None) -> dict:
    """(Ré)assigne une tâche à un profil agent."""
    return _run_ok([*_board_args(board), "assign", task_id, assignee])


def dispatch(board: str | None = None, dry_run: bool = False) -> dict:
    """Lance une passe du dispatcher : promeut les tâches prêtes et lance les workers."""
    args = [*_board_args(board), "dispatch", "--json"]
    if dry_run:
        args.append("--dry-run")
    res = _run(args, timeout=120)
    if res.returncode != 0:
        return {"ok": False, "message": (res.stderr or res.stdout).strip()[:300]}
    try:
        return {"ok": True, "data": json.loads(res.stdout)}
    except (ValueError, json.JSONDecodeError):
        return {"ok": True, "message": res.stdout.strip()[:300]}
