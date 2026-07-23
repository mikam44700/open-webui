"""Garde-fous des missions Hermes longues.

Une mission de veille ou de génération de document peut légitimement durer plusieurs
minutes. Elle ne doit pas être confondue avec une requête de chat ordinaire, mais elle
ne doit jamais devenir illimitée non plus.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import time
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

MISSION_MAX_SECONDS = 30 * 60
MISSION_IDLE_SECONDS = 3 * 60
MISSION_HEARTBEAT_SECONDS = 10
INTERACTIVE_MAX_TOOL_CALLS = 8
MISSION_MAX_TOOL_CALLS = 40
MISSION_MAX_REPEATED_TOOL_CALLS = 3
MISSION_PROGRESS_TOOL = 'lunaria_long_mission'
MISSION_PROGRESS_CALL_ID = 'lunaria-long-mission'

_RESEARCH_MARKERS = (
    'analyse',
    'analyze',
    'concurrent',
    'competitor',
    'marché',
    'market',
    'recherche',
    'research',
    'source',
    'surveille',
    'monitor',
    'tendance',
    'trend',
    'veille',
)
_DELIVERABLE_MARKERS = (
    "plan d'action",
    'action plan',
    'document',
    'dossier',
    'pdf',
    'présentation',
    'presentation',
    'rapport',
    'report',
    'tableau',
)


class MissionIdleTimeout(TimeoutError):
    """Aucun octet n'a été reçu du moteur pendant la fenêtre d'inactivité."""


class MissionMaximumDuration(TimeoutError):
    """La mission a atteint sa durée maximale autorisée."""


def _latest_user_text(payload: dict) -> str:
    for message in reversed(payload.get('messages') or []):
        if not isinstance(message, dict) or message.get('role') != 'user':
            continue
        content = message.get('content')
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return ' '.join(
                str(part.get('text') or '')
                for part in content
                if isinstance(part, dict) and part.get('type') in {'text', 'input_text'}
            )
    return ''


def is_long_mission_request(payload: dict, *, action_capability: str = '') -> bool:
    """Distingue une mission multi-étapes d'une action interactive ordinaire.

    Le routeur LLM reste la source principale (`complex`). Les marqueurs textuels ne
    servent que de repli lorsque ce premier routeur expire avant de rendre son contrat.
    """

    if action_capability == 'complex':
        return True
    text = re.sub(r'\s+', ' ', _latest_user_text(payload).lower()).strip()
    return (
        any(marker in text for marker in _RESEARCH_MARKERS)
        and any(marker in text for marker in _DELIVERABLE_MARKERS)
    )


@dataclass(slots=True)
class ToolCallBudget:
    """Compte les appels réels sans confondre les doublons SSE avec de nouveaux outils."""

    maximum_calls: int
    maximum_repeated_calls: int = MISSION_MAX_REPEATED_TOOL_CALLS
    count: int = 0
    _seen_call_ids: set[str] = field(default_factory=set)
    _signatures: Counter[str] = field(default_factory=Counter)

    def observe(self, chunk: bytes | str) -> str | None:
        """Retourne `total` ou `repeated` lorsque le garde-fou est dépassé."""

        text = chunk.decode('utf-8', errors='replace') if isinstance(chunk, bytes) else str(chunk)
        for line in text.splitlines():
            if not line.startswith('data:'):
                continue
            raw = line.removeprefix('data:').strip()
            if not raw or raw == '[DONE]':
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or data.get('status') != 'running':
                continue

            tool = str(data.get('tool') or '').strip()
            call_id = str(data.get('toolCallId') or '').strip()
            label = re.sub(r'\s+', ' ', str(data.get('label') or '')).strip().lower()
            if not tool or (call_id and call_id in self._seen_call_ids):
                continue
            if call_id:
                self._seen_call_ids.add(call_id)

            self.count += 1
            if label:
                signature = f'{tool}\0{label}'
                self._signatures[signature] += 1
                if self._signatures[signature] > self.maximum_repeated_calls:
                    return 'repeated'
            if self.count > self.maximum_calls:
                return 'total'
        return None


def progress_event(elapsed_seconds: float, *, done: bool = False) -> bytes:
    """Événement SSE compris par le chat, sans être compté comme appel d'outil."""

    elapsed_minutes = max(1, int(elapsed_seconds // 60) + 1)
    data = {
        'tool': MISSION_PROGRESS_TOOL,
        'toolCallId': MISSION_PROGRESS_CALL_ID,
        # Le budget historique ne compte que `running`. `progress` reste visuellement
        # actif dans le middleware, mais ne consomme aucun appel d'outil.
        'status': 'completed' if done else 'progress',
        'label': f'depuis {elapsed_minutes} min',
        'internal': True,
    }
    return (f'event: hermes.tool.progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n').encode()


async def stream_with_limits(  # noqa: C901 - les trois horloges partagent le même lecteur
    stream: AsyncIterator[bytes],
    *,
    maximum_seconds: float = MISSION_MAX_SECONDS,
    idle_seconds: float = MISSION_IDLE_SECONDS,
    heartbeat_seconds: float = MISSION_HEARTBEAT_SECONDS,
) -> AsyncIterator[bytes]:
    """Diffuse ``stream`` avec plafond total, inactivité et battements de progression.

    Le battement informe uniquement le client ; il ne remet jamais à zéro l'inactivité.
    Seul un vrai élément reçu du moteur prouve que l'amont progresse encore.
    """

    if min(maximum_seconds, idle_seconds, heartbeat_seconds) <= 0:
        raise ValueError('mission stream limits must be positive')

    iterator = stream.__aiter__()
    started_at = time.monotonic()
    last_upstream_activity = started_at
    next_chunk: asyncio.Task | None = None
    progress_announced = False

    try:
        while True:
            now = time.monotonic()
            total_remaining = maximum_seconds - (now - started_at)
            idle_remaining = idle_seconds - (now - last_upstream_activity)
            if total_remaining <= 0:
                raise MissionMaximumDuration
            if idle_remaining <= 0:
                raise MissionIdleTimeout

            if next_chunk is None:
                next_chunk = asyncio.create_task(iterator.__anext__())

            wait_seconds = min(heartbeat_seconds, total_remaining, idle_remaining)
            completed, _ = await asyncio.wait({next_chunk}, timeout=wait_seconds)
            if completed:
                try:
                    chunk = next_chunk.result()
                except StopAsyncIteration:
                    if progress_announced:
                        yield progress_event(time.monotonic() - started_at, done=True)
                    return
                next_chunk = None
                last_upstream_activity = time.monotonic()
                yield chunk
                continue

            now = time.monotonic()
            if now - started_at >= maximum_seconds:
                raise MissionMaximumDuration
            if now - last_upstream_activity >= idle_seconds:
                raise MissionIdleTimeout

            progress_announced = True
            yield progress_event(now - started_at)
    finally:
        if next_chunk is not None and not next_chunk.done():
            next_chunk.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await next_chunk

        close = getattr(iterator, 'aclose', None)
        if close is not None:
            with contextlib.suppress(Exception):
                await close()
