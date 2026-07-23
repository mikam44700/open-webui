"""Garde-fous des missions Hermes longues.

Une mission de veille ou de génération de document peut légitimement durer plusieurs
minutes. Elle ne doit pas être confondue avec une requête de chat ordinaire, mais elle
ne doit jamais devenir illimitée non plus.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncIterator

MISSION_MAX_SECONDS = 30 * 60
MISSION_IDLE_SECONDS = 3 * 60
MISSION_HEARTBEAT_SECONDS = 10
MISSION_PROGRESS_TOOL = 'lunaria_long_mission'
MISSION_PROGRESS_CALL_ID = 'lunaria-long-mission'


class MissionIdleTimeout(TimeoutError):
    """Aucun octet n'a été reçu du moteur pendant la fenêtre d'inactivité."""


class MissionMaximumDuration(TimeoutError):
    """La mission a atteint sa durée maximale autorisée."""


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
