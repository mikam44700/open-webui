"""Client asynchrone minimal pour le protocole JSONL de Codex App Server.

Ce pont utilise exclusivement le transport ``stdio`` : aucun port Codex n'est exposé
dans Docker. Il ne branche encore aucun parcours utilisateur ; il constitue le prototype
isolé prévu par ``SPEC-migration-hermes-vers-codex``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


class CodexProtocolError(RuntimeError):
    """Erreur explicite du protocole ou arrêt inattendu d'App Server."""


@dataclass(slots=True)
class CodexEvent:
    type: Literal['started', 'delta', 'tool_started', 'tool_completed', 'done', 'warning', 'error']
    text: str = ''
    thread_id: str = ''
    turn_id: str = ''
    item_id: str = ''
    item_type: str = ''
    status: str = ''
    duration_ms: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    message: str = ''


_TERMINAL_TURN_STATUSES = frozenset({'completed', 'failed', 'interrupted', 'cancelled'})


def notification_to_event(message: Mapping[str, Any]) -> CodexEvent | None:
    """Traduit la surface Codex utile en événements stables propres à LunarIA."""
    method = str(message.get('method') or '')
    params = message.get('params')
    if not isinstance(params, Mapping):
        return None

    thread_id = str(params.get('threadId') or '')
    turn_id = str(params.get('turnId') or '')

    if method == 'turn/started':
        turn = params.get('turn')
        if isinstance(turn, Mapping):
            turn_id = str(turn.get('id') or turn_id)
        return CodexEvent(type='started', thread_id=thread_id, turn_id=turn_id)

    if method == 'item/agentMessage/delta':
        return CodexEvent(
            type='delta',
            text=str(params.get('delta') or ''),
            thread_id=thread_id,
            turn_id=turn_id,
            item_id=str(params.get('itemId') or ''),
            item_type='agentMessage',
        )

    if method in {'item/started', 'item/completed'}:
        item = params.get('item')
        if not isinstance(item, Mapping):
            return None
        item_type = str(item.get('type') or '')
        if item_type not in {'commandExecution', 'mcpToolCall', 'dynamicToolCall'}:
            return None
        return CodexEvent(
            type='tool_started' if method == 'item/started' else 'tool_completed',
            thread_id=thread_id,
            turn_id=turn_id,
            item_id=str(item.get('id') or ''),
            item_type=item_type,
            status=str(item.get('status') or ''),
        )

    if method == 'thread/tokenUsage/updated':
        usage = params.get('tokenUsage')
        return CodexEvent(
            type='warning',
            thread_id=thread_id,
            turn_id=turn_id,
            usage=dict(usage) if isinstance(usage, Mapping) else {},
            message='token_usage',
        )

    if method == 'warning':
        return CodexEvent(
            type='warning',
            thread_id=thread_id,
            turn_id=turn_id,
            message=str(params.get('message') or ''),
        )

    if method == 'turn/completed':
        turn = params.get('turn')
        turn_data = turn if isinstance(turn, Mapping) else {}
        status = str(turn_data.get('status') or '')
        error = turn_data.get('error')
        event_type: Literal['done', 'error'] = 'done' if status == 'completed' else 'error'
        return CodexEvent(
            type=event_type,
            thread_id=thread_id,
            turn_id=str(turn_data.get('id') or turn_id),
            status=status,
            duration_ms=int(turn_data.get('durationMs') or 0),
            message=_error_message(error),
        )

    return None


def _error_message(error: Any) -> str:
    if isinstance(error, Mapping):
        return str(error.get('message') or error.get('code') or '')
    return str(error or '')


class CodexAppServerClient:
    """Processus Codex résident et multiplexage simple des notifications par thread."""

    def __init__(
        self,
        *,
        codex_bin: str | None = None,
        codex_home: str | Path | None = None,
        cwd: str | Path = '/tmp',
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.codex_bin = codex_bin or os.environ.get('LUNARIA_CODEX_BIN', 'codex')
        self.codex_home = Path(
            codex_home or os.environ.get('LUNARIA_CODEX_HOME', '/app/backend/data/codex')
        )
        self.cwd = Path(cwd)
        self.environment = dict(environment or {})
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._thread_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._ready = asyncio.Event()

    @property
    def running(self) -> bool:
        return bool(self._process and self._process.returncode is None and self._ready.is_set())

    async def start(self) -> None:
        if self.running:
            return
        self.codex_home.mkdir(parents=True, exist_ok=True, mode=0o700)
        env = {
            **os.environ,
            **self.environment,
            'CODEX_HOME': str(self.codex_home),
        }
        self._process = await asyncio.create_subprocess_exec(
            self.codex_bin,
            'app-server',
            '--listen',
            'stdio://',
            cwd=str(self.cwd),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._read_stderr())
        result = await self.request(
            'initialize',
            {
                'clientInfo': {
                    'name': 'lunaria',
                    'title': 'LunarIA',
                    'version': '0.1.0',
                },
                'capabilities': {
                    'optOutNotificationMethods': ['remoteControl/status/changed'],
                },
            },
            timeout=15,
        )
        if not result.get('userAgent'):
            await self.stop()
            raise CodexProtocolError('Codex initialize sans userAgent')
        await self.notify('initialized', {})
        self._ready.set()

    async def stop(self) -> None:
        self._ready.clear()
        process = self._process
        self._process = None
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()
        for task in (self._reader_task, self._stderr_task):
            if task and not task.done():
                task.cancel()
        self._reader_task = None
        self._stderr_task = None
        error = CodexProtocolError('Codex App Server arrêté')
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
        self._pending.clear()
        self._thread_queues.clear()

    async def __aenter__(self) -> 'CodexAppServerClient':
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.stop()

    async def start_thread(
        self,
        *,
        model: str | None = None,
        model_provider: str | None = None,
        developer_instructions: str = '',
        ephemeral: bool = True,
    ) -> str:
        await self.start()
        params: dict[str, Any] = {
            'cwd': str(self.cwd),
            'approvalPolicy': 'never',
            'sandbox': 'read-only',
            'ephemeral': ephemeral,
        }
        if model:
            params['model'] = model
        if model_provider:
            params['modelProvider'] = model_provider
        if developer_instructions:
            params['developerInstructions'] = developer_instructions
        result = await self.request('thread/start', params, timeout=30)
        thread = result.get('thread')
        thread_id = str(thread.get('id') or '') if isinstance(thread, Mapping) else ''
        if not thread_id:
            raise CodexProtocolError('thread/start sans identifiant')
        self._thread_queues.setdefault(thread_id, asyncio.Queue())
        return thread_id

    async def stream_turn(
        self,
        thread_id: str,
        text: str,
        *,
        model: str | None = None,
        effort: str | None = None,
        timeout: float = 120,
    ) -> AsyncIterator[CodexEvent]:
        if not text.strip():
            raise ValueError('message Codex vide')
        queue = self._thread_queues.setdefault(thread_id, asyncio.Queue())
        params: dict[str, Any] = {
            'threadId': thread_id,
            'input': [{'type': 'text', 'text': text}],
        }
        if model:
            params['model'] = model
        if effort:
            params['effort'] = effort
        result = await self.request('turn/start', params, timeout=30)
        turn = result.get('turn')
        turn_id = str(turn.get('id') or '') if isinstance(turn, Mapping) else ''
        if not turn_id:
            raise CodexProtocolError('turn/start sans identifiant')

        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
            except TimeoutError as exc:
                raise CodexProtocolError(f'tour Codex expiré après {timeout:g} s') from exc
            event = notification_to_event(message)
            if event is None or (event.turn_id and event.turn_id != turn_id):
                continue
            yield event
            if event.type in {'done', 'error'}:
                return

    async def request(self, method: str, params: Mapping[str, Any], *, timeout: float) -> dict[str, Any]:
        process = self._process
        if not process or not process.stdin or process.returncode is not None:
            raise CodexProtocolError('Codex App Server indisponible')
        self._request_id += 1
        request_id = self._request_id
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        await self._write({'method': method, 'id': request_id, 'params': dict(params)})
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(request_id, None)

    async def notify(self, method: str, params: Mapping[str, Any]) -> None:
        await self._write({'method': method, 'params': dict(params)})

    async def _write(self, message: Mapping[str, Any]) -> None:
        process = self._process
        if not process or not process.stdin or process.returncode is not None:
            raise CodexProtocolError('Codex App Server indisponible')
        process.stdin.write((json.dumps(message, ensure_ascii=False) + '\n').encode())
        await process.stdin.drain()

    async def _read_stdout(self) -> None:
        assert self._process and self._process.stdout
        try:
            while line := await self._process.stdout.readline():
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning('Ligne non JSON ignorée sur stdout Codex')
                    continue
                response_id = message.get('id')
                if response_id is not None and ('result' in message or 'error' in message):
                    future = self._pending.get(int(response_id))
                    if not future or future.done():
                        continue
                    if 'error' in message:
                        future.set_exception(CodexProtocolError(_error_message(message['error'])))
                    else:
                        result = message.get('result')
                        future.set_result(dict(result) if isinstance(result, Mapping) else {})
                    continue
                params = message.get('params')
                if not isinstance(params, Mapping):
                    continue
                thread_id = str(params.get('threadId') or '')
                if thread_id:
                    await self._thread_queues.setdefault(thread_id, asyncio.Queue()).put(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Lecture stdout Codex interrompue')
        finally:
            error = CodexProtocolError('Codex App Server a fermé stdout')
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(error)

    async def _read_stderr(self) -> None:
        assert self._process and self._process.stderr
        try:
            while line := await self._process.stderr.readline():
                # Ne jamais recopier les corps de requêtes ou secrets potentiels. Les logs
                # structurés détaillés seront traités par une liste blanche dans Docker.
                text = line.decode(errors='replace').strip()
                if text:
                    logger.debug('codex_app_server stderr reçu (%d caractères)', len(text))
        except asyncio.CancelledError:
            raise
