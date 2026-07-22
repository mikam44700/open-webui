"""Runtime Hermes résident pour le chat LunarIA.

Le gateway Hermes reste le repli universel. Ce petit serveur local évite toutefois de
redémarrer un interpréteur Python et de réimporter tout Hermes à chaque réponse directe.
Il sait aussi exécuter les actions ordinaires avec une surface d'outils et des budgets
strictement bornés. Le protocole est du NDJSON local, jamais exposé hors du conteneur.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from typing import Any

from aiohttp import web


HERMES_DIR = os.environ.get("HERMES_AGENT_DIR", "/opt/hermes-agent")
if HERMES_DIR not in sys.path:
    sys.path.insert(0, HERMES_DIR)

from gateway.run import (  # noqa: E402
    GatewayRunner,
    _resolve_gateway_model,
    _resolve_runtime_agent_kwargs,
)
from run_agent import AIAgent  # noqa: E402


HOST = os.environ.get("LUNARIA_HERMES_RUNTIME_HOST", "127.0.0.1")
PORT = int(os.environ.get("LUNARIA_HERMES_RUNTIME_PORT", "8643"))

# Les noms sont ceux de ``_get_platform_tools`` dans Hermes. Une action qui ne rentre
# pas dans ces familles bornées reste prise en charge par le gateway complet.
CAPABILITY_TOOLSETS: dict[str, list[str]] = {
    "web": ["sources-publiques"],
    "document": ["file", "terminal"],
    "memory": ["memory", "session_search"],
}

CAPABILITY_GUIDES = {
    "web": "research/sources-publiques-lunaria/SKILL.md",
    "document": "lunaria-app/documents-lunaria/SKILL.md",
}

# Le runtime est un processus distinct du gateway : son registre Python ne partage donc
# pas les connexions MCP déjà ouvertes sur le port 8642. On ne précharge que le serveur
# nécessaire au parcours web borné, pas les cinq MCP ni leurs 36 outils.
RUNTIME_MCP_SERVERS = frozenset({"sources-publiques"})


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") in {"text", "input_text", "output_text"}:
            parts.append(str(part.get("text") or ""))
    return "\n".join(part for part in parts if part)


def _conversation(messages: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user")
        text = _text_content(message.get("content"))
        if role in {"system", "developer"}:
            if text:
                system_parts.append(text)
        elif role in {"user", "assistant"} and text:
            normalized.append({"role": role, "content": text})
    last_user = next(
        (i for i in range(len(normalized) - 1, -1, -1) if normalized[i]["role"] == "user"),
        None,
    )
    if last_user is None:
        raise ValueError("aucun message utilisateur exploitable")
    # Un long chat ne doit pas ralentir chaque message suivant. On conserve les douze
    # derniers échanges, avec un plafond de caractères pris depuis la fin.
    history = normalized[:last_user][-12:]
    kept: list[dict[str, Any]] = []
    remaining = 24_000
    for message in reversed(history):
        text = str(message.get("content") or "")
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[-remaining:]
        kept.append({"role": message["role"], "content": text})
        remaining -= len(text)
    kept.reverse()
    persona = "\n\n".join(system_parts)[:16_000]
    return persona, normalized[last_user]["content"], kept


def _capability_guide(capability: str) -> str:
    relative = CAPABILITY_GUIDES.get(capability)
    if not relative:
        return ""
    path = os.path.join(os.environ.get("HERMES_HOME", "/root/.hermes"), "skills", relative)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read(12_000)
    except OSError:
        return ""


def _runtime() -> tuple[str, dict[str, Any], Any, Any]:
    runtime_kwargs = _resolve_runtime_agent_kwargs()
    model = runtime_kwargs.pop("model", None) or _resolve_gateway_model()
    for key in ("max_tokens", "max_iterations", "enabled_toolsets", "disabled_toolsets"):
        runtime_kwargs.pop(key, None)
    return (
        model,
        runtime_kwargs,
        GatewayRunner._load_fallback_model(),
        GatewayRunner._load_reasoning_config(),
    )


def _execute(payload: dict[str, Any], emit) -> None:
    started = time.perf_counter()
    mode = str(payload.get("mode") or "direct")
    capability = str(payload.get("capability") or "")
    timeout_seconds = int(payload.get("timeout_seconds") or (60 if mode == "action" else 45))
    # Le premier appel LLM de routage est fait par LunarIA avant ce runtime : trois
    # tours ici donnent bien le plafond produit de quatre appels LLM au total.
    max_iterations = int(payload.get("max_iterations") or (3 if mode == "action" else 1))
    max_tools = int(payload.get("max_tools") or (3 if mode == "action" else 0))
    max_iterations = max(1, min(max_iterations, 8))
    max_tools = max(0, min(max_tools, 8))

    persona, user_message, history = _conversation(payload.get("messages") or [])
    model, runtime_kwargs, fallback_model, reasoning_config = _runtime()
    chunks: list[str] = []
    tool_count = 0
    timed_out = threading.Event()
    tool_budget_hit = threading.Event()
    agent_box: list[AIAgent | None] = [None]

    def on_delta(delta: Any) -> None:
        text = str(delta or "")
        if text:
            chunks.append(text)
            emit("delta", text=text, model=model)

    def on_tool_start(tool_call_id, function_name, function_args) -> None:
        nonlocal tool_count
        tool_count += 1
        emit(
            "tool_started",
            tool_call_id=str(tool_call_id or ""),
            tool=str(function_name or ""),
            tool_count=tool_count,
        )
        if tool_count > max_tools:
            tool_budget_hit.set()
            current = agent_box[0]
            if current is not None:
                current.interrupt()

    def on_tool_complete(tool_call_id, function_name, function_args, function_result) -> None:
        emit(
            "tool_completed",
            tool_call_id=str(tool_call_id or ""),
            tool=str(function_name or ""),
            tool_count=tool_count,
        )

    enabled_toolsets = [] if mode == "direct" else CAPABILITY_TOOLSETS.get(capability)
    if mode == "action" and enabled_toolsets is None:
        raise ValueError(f"capacité non bornée: {capability}")

    agent = AIAgent(
        model=model,
        **runtime_kwargs,
        max_iterations=max_iterations,
        max_tokens=payload.get("max_tokens"),
        quiet_mode=True,
        verbose_logging=False,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=[],
        skip_context_files=True,
        skip_memory=(mode == "direct"),
        platform="api_server",
        stream_delta_callback=on_delta,
        tool_start_callback=on_tool_start if mode == "action" else None,
        tool_complete_callback=on_tool_complete if mode == "action" else None,
        fallback_model=fallback_model,
        reasoning_config=reasoning_config,
    )
    agent_box[0] = agent
    if mode == "action":
        # La découverte progressive est utile quand Hermes expose des dizaines de MCP.
        # Ici la famille est déjà fermée (web/document/mémoire) : l'enveloppe
        # tool_search -> tool_describe -> tool_call ajouterait deux tours LLM sans
        # réduire davantage la surface. On fournit donc directement les schémas de
        # cette seule famille au modèle.
        from model_tools import get_tool_definitions

        agent.tools = get_tool_definitions(
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=[],
            quiet_mode=True,
            skip_tool_search_assembly=True,
        )
        agent.valid_tool_names = {
            tool["function"]["name"]
            for tool in agent.tools
            if isinstance(tool, dict) and isinstance(tool.get("function"), dict)
        }
        # Hermes 0.19 rafraîchit normalement les MCP au début de chaque tour et
        # reconstruirait alors l'enveloppe progressive. Ce runtime a préchargé son
        # unique MCP avant de créer l'agent : sa photographie est déjà complète et
        # volontairement immuable pendant cette action courte.
        agent._skip_mcp_refresh = True
    # Aucune revue mémoire/skill en arrière-plan sur le chemin interactif. Ces tâches
    # doivent être planifiées hors de la réponse client, avec leur propre modèle/budget.
    agent._memory_nudge_interval = 0
    agent._skill_nudge_interval = 0

    def stop_for_deadline() -> None:
        timed_out.set()
        agent.interrupt()

    timer = threading.Timer(timeout_seconds, stop_for_deadline)
    timer.daemon = True
    timer.start()
    try:
        policy = str(payload.get("policy") or "")
        guide = _capability_guide(capability) if mode == "action" else ""
        if guide:
            policy = f"{policy}\n\nProcédure métier autorisée pour cette action :\n{guide}"
        result = agent.run_conversation(
            user_message,
            system_message=f"{persona}\n\n{policy}" if policy else persona,
            conversation_history=history,
        )
    finally:
        timer.cancel()

    if timed_out.is_set():
        emit("budget", reason="timeout", timeout_seconds=timeout_seconds, tool_count=tool_count)
        return
    if tool_budget_hit.is_set():
        emit("budget", reason="tool_limit", max_tools=max_tools, tool_count=tool_count)
        return

    answer = str(result.get("final_response") or result.get("response") or "".join(chunks) or "")
    if answer and not chunks:
        emit("delta", text=answer, model=model)
    usage = result.get("usage") if isinstance(result, dict) else None
    emit(
        "done",
        answer=answer,
        model=model,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        usage=usage if isinstance(usage, dict) else {},
        tool_count=tool_count,
        max_iterations=max_iterations,
    )


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "lunaria-hermes-runtime"})


async def run(request: web.Request) -> web.StreamResponse:
    payload = await request.json()
    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "application/x-ndjson", "Cache-Control": "no-cache"},
    )
    await response.prepare(request)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    run_id = uuid.uuid4().hex

    def emit(kind: str, **data: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"v": 2, "type": kind, "run_id": run_id, **data})

    async def worker() -> None:
        try:
            await asyncio.to_thread(_execute, payload, emit)
        except Exception as exc:  # repli géré par LunarIA
            emit("error", error_type=type(exc).__name__, message=str(exc)[:300])
        finally:
            await queue.put(None)

    task = asyncio.create_task(worker())
    try:
        emit("started")
        while True:
            event = await queue.get()
            if event is None:
                break
            await response.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
    except (ConnectionResetError, asyncio.CancelledError):
        task.cancel()
        raise
    finally:
        if not task.done():
            task.cancel()
    return response


def main() -> None:
    try:
        from tools.mcp_tool import _load_mcp_config, register_mcp_servers

        configured = _load_mcp_config()
        selected = {
            name: config
            for name, config in configured.items()
            if name in RUNTIME_MCP_SERVERS
        }
        register_mcp_servers(selected)
    except Exception as exc:  # le chat direct reste disponible sans MCP
        print(f"runtime Hermes: préchargement MCP web impossible: {exc}", flush=True)
    app = web.Application(client_max_size=4 * 1024 * 1024)
    app.router.add_get("/health", health)
    app.router.add_post("/run", run)
    web.run_app(app, host=HOST, port=PORT, print=None, access_log=None)


if __name__ == "__main__":
    main()
