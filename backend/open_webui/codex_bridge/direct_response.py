"""Chemin conversationnel Codex compatible avec le flux actuel de LunarIA.

Cette première étape remplace uniquement le tour LLM sans outil. Les actions restent
temporairement confiées au chemin Hermes existant jusqu'au portage de leurs MCP. Le choix
est réversible avec ``LUNARIA_ENGINE=hermes|codex`` et ne modifie aucune donnée utilisateur.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator

from open_webui.hermes_bridge.direct_response import DirectEvent, ROUTING_POLICY

from .client import CodexAppServerClient, CodexProtocolError


_client: CodexAppServerClient | None = None
_client_lock = asyncio.Lock()


def _conversation(payload: dict) -> tuple[str, str]:
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
    developer = (
        f'{developer}\n\n{ROUTING_POLICY}\n\n'
        "Contrainte du tour direct : n'utilise aucun outil, terminal, fichier ou accès web. "
        "Réponds directement ou émets uniquement le contrat JSON LunarIA demandé."
    ).strip()
    return developer, transcript


async def _resident_client() -> CodexAppServerClient:
    global _client
    async with _client_lock:
        if _client is None or not _client.running:
            if _client is not None:
                await _client.stop()
            _client = CodexAppServerClient(
                codex_bin=os.environ.get('LUNARIA_CODEX_BIN', 'codex'),
                codex_home=os.environ.get('LUNARIA_CODEX_HOME', '/app/backend/data/codex'),
                cwd=os.environ.get('LUNARIA_CODEX_WORKDIR', '/tmp'),
            )
            await _client.start()
        return _client


async def stream_direct_events(payload: dict) -> AsyncIterator[DirectEvent]:
    """Transforme un tour App Server en événements déjà compris par le frontend."""
    started = time.perf_counter()
    developer, transcript = _conversation(payload)
    model = os.environ.get('LUNARIA_CODEX_MODEL', '').strip() or None
    provider = os.environ.get('LUNARIA_CODEX_PROVIDER', '').strip() or None
    effort = os.environ.get('LUNARIA_CODEX_EFFORT', 'low').strip() or None

    try:
        client = await _resident_client()
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
