"""Cycle de vie du processus Codex App Server résident."""

from __future__ import annotations

import asyncio
import os

from .client import CodexAppServerClient


_client: CodexAppServerClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> CodexAppServerClient:
    """Retourne le processus local partagé par le worker backend courant."""
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


async def stop_client() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.stop()
            _client = None

