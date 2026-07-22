"""Chemin conversationnel Codex compatible avec le flux actuel de LunarIA.

Les réponses directes et les actions MCP bornées passent par App Server. Le choix reste
réversible avec ``LUNARIA_ENGINE=hermes|codex`` et ne modifie aucune donnée utilisateur.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator

from open_webui.hermes_bridge.direct_response import (
    BOUNDED_CAPABILITIES,
    DirectEvent,
    HermesAction,
    ROUTING_POLICY,
    action_handoff_policy,
)

from .client import CodexProtocolError
from .opencodex_config import resolve_lunaria_selection
from .runtime import get_client


def _selected_model() -> tuple[str | None, str | None]:
    configured_model, configured_provider = resolve_lunaria_selection(
        os.path.join(
            os.environ.get('HERMES_HOME', '/app/backend/data/hermes'),
            'config.yaml',
        )
    )
    model = os.environ.get('LUNARIA_CODEX_MODEL', '').strip() or configured_model
    provider = os.environ.get('LUNARIA_CODEX_PROVIDER', '').strip() or configured_provider
    return model, provider


def _conversation(payload: dict, *, allow_tools: bool = False) -> tuple[str, str]:
    """Sépare les instructions de l'historique transmis au tour éphémère Codex."""
    instructions: list[str] = []
    history: list[str] = []
    messages = payload.get('messages')
    if not isinstance(messages, list):
        raise ValueError('messages Codex absents')

    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get('role') or 'user')
        content = message.get('content')
        if isinstance(content, list):
            content = '\n'.join(
                str(part.get('text') or '')
                for part in content
                if isinstance(part, dict) and part.get('type') in {'text', 'input_text'}
            )
        text = str(content or '').strip()
        if not text:
            continue
        if role in {'system', 'developer'}:
            instructions.append(text)
        elif role in {'user', 'assistant'}:
            history.append(f'{role.upper()}: {text}')

    if not any(line.startswith('USER:') for line in history):
        raise ValueError('aucun message utilisateur pour Codex')

    # L'interface fournit déjà tout l'historique utile. Le thread est éphémère afin de ne
    # pas créer une deuxième source de vérité pour les conversations LunarIA.
    transcript = '\n\n'.join(history[-24:])[-48_000:]
    developer = '\n\n'.join(instructions)[-24_000:]
    developer = f'{developer}\n\n{ROUTING_POLICY}'.strip()
    if not allow_tools:
        developer = (
            f'{developer}\n\n'
            "Contrainte du tour direct : n'utilise aucun outil, terminal, fichier ou accès web. "
            "Réponds directement ou émets uniquement le contrat JSON LunarIA demandé."
        )
    return developer, transcript


async def stream_direct_events(payload: dict) -> AsyncIterator[DirectEvent]:
    """Transforme un tour App Server en événements déjà compris par le frontend."""
    started = time.perf_counter()
    developer, transcript = _conversation(payload)
    model, provider = _selected_model()
    effort = os.environ.get('LUNARIA_CODEX_EFFORT', 'low').strip() or None

    try:
        client = await get_client()
        thread_id = await client.start_thread(
            model=model,
            model_provider=provider,
            developer_instructions=developer,
            ephemeral=True,
        )
        answer: list[str] = []
        yield DirectEvent(type='started', model=model or 'codex')
        async for event in client.stream_turn(
            thread_id,
            transcript,
            model=model,
            effort=effort,
            timeout=float(os.environ.get('LUNARIA_CODEX_TURN_TIMEOUT', '90')),
        ):
            if event.type == 'delta' and event.text:
                answer.append(event.text)
                yield DirectEvent(type='delta', text=event.text, model=model or 'codex')
            elif event.type == 'tool_started':
                # Un outil sur ce tour est contraire au contrat direct. Il est en lecture
                # seule mais le résultat n'est jamais présenté comme une réponse valide.
                await client.interrupt_turn(event.thread_id, event.turn_id)
                yield DirectEvent(
                    type='error',
                    error_type='UnexpectedCodexTool',
                    message=event.item_type,
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                )
                return
            elif event.type == 'error':
                yield DirectEvent(
                    type='error',
                    error_type='CodexTurnFailed',
                    message=event.message,
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                )
                return
            elif event.type == 'done':
                yield DirectEvent(
                    type='done',
                    answer=''.join(answer),
                    model=model or 'codex',
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                )
                return
    except (CodexProtocolError, OSError, TimeoutError, ValueError) as exc:
        yield DirectEvent(
            type='error',
            error_type=type(exc).__name__,
            message=str(exc)[:300],
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )


async def stream_action_events(payload: dict, action: HermesAction) -> AsyncIterator[DirectEvent]:
    """Exécute les actions bornées avec les MCP Codex, sans boucle Hermes."""
    if action.capacite not in BOUNDED_CAPABILITIES:
        yield DirectEvent(type='error', error_type='UnboundedCapability', message=action.capacite)
        return

    started = time.perf_counter()
    instructions, transcript = _conversation(payload, allow_tools=True)
    instructions = (
        f"{instructions}\n\n{action_handoff_policy(action.objectif, action.capacite)}\n"
        "Tu peux maintenant utiliser les MCP configurés. N'utilise le terminal que si aucun "
        "MCP adapté n'existe. Maximum trois appels d'outils."
    )
    model, provider = _selected_model()
    effort = os.environ.get('LUNARIA_CODEX_EFFORT', 'low').strip() or None
    answer: list[str] = []
    tool_count = 0

    try:
        client = await get_client()
        thread_id = await client.start_thread(
            model=model,
            model_provider=provider,
            developer_instructions=instructions,
            ephemeral=True,
        )
        yield DirectEvent(type='started', model=model or 'codex')
        async for event in client.stream_turn(
            thread_id,
            f"{transcript}\n\nACTION À EXÉCUTER : {action.objectif}",
            model=model,
            effort=effort,
            timeout=float(os.environ.get('LUNARIA_CODEX_ACTION_TIMEOUT', '120')),
        ):
            if event.type == 'delta' and event.text:
                answer.append(event.text)
                yield DirectEvent(type='delta', text=event.text, model=model or 'codex')
            elif event.type == 'tool_started':
                tool_count += 1
                if tool_count > 3:
                    await client.interrupt_turn(event.thread_id, event.turn_id)
                    yield DirectEvent(
                        type='error',
                        error_type='CodexToolBudgetExceeded',
                        message='maximum 3 outils',
                        tool_count=tool_count,
                    )
                    return
                yield DirectEvent(
                    type='tool_started',
                    tool=event.tool or event.item_type,
                    tool_call_id=event.item_id,
                    tool_count=tool_count,
                )
            elif event.type == 'tool_completed':
                yield DirectEvent(
                    type='tool_completed',
                    tool=event.tool or event.item_type,
                    tool_call_id=event.item_id,
                    tool_count=tool_count,
                )
            elif event.type == 'error':
                yield DirectEvent(
                    type='error',
                    error_type='CodexActionFailed',
                    message=event.message,
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                )
                return
            elif event.type == 'done':
                yield DirectEvent(
                    type='done',
                    answer=''.join(answer),
                    model=model or 'codex',
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                    tool_count=tool_count,
                )
                return
    except (CodexProtocolError, OSError, TimeoutError, ValueError) as exc:
        yield DirectEvent(
            type='error',
            error_type=type(exc).__name__,
            message=str(exc)[:300],
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )
