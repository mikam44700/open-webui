"""API d'administration du moteur Codex, sans exposition d'App Server."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from open_webui.utils.auth import get_admin_user

from .account import safe_account
from .client import CodexProtocolError
from .runtime import get_client, stop_client


router = APIRouter()


async def _version() -> str | None:
    binary = os.environ.get('LUNARIA_CODEX_BIN', 'codex')
    if not shutil.which(binary) and not os.path.isfile(binary):
        return None
    try:
        process = await asyncio.create_subprocess_exec(
            binary,
            '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
    except (OSError, TimeoutError):
        return None
    text = stdout.decode(errors='replace').strip().splitlines()
    if not text:
        return None
    match = re.search(r'\d+\.\d+\.\d+(?:[-\w.]*)?', text[0])
    return match.group(0) if match else text[0][:80]


@router.get('/status')
async def codex_status(_user=Depends(get_admin_user)) -> dict[str, Any]:
    version = await _version()
    selected_engine = (
        'codex' if os.environ.get('LUNARIA_ENGINE', 'hermes').strip().lower() == 'codex' else 'hermes'
    )
    common = {
        'selected_engine': selected_engine,
        'enabled': selected_engine == 'codex',
        'opencodex_enabled': os.environ.get('LUNARIA_OPENCODEX_ENABLED', '0').strip().lower()
        in {'1', 'true', 'yes', 'on'},
    }
    if version is None:
        return {
            **common,
            'installed': False,
            'version': None,
            'reachable': False,
            'account': None,
        }
    # Conserver Codex installé permet un retour arrière, mais consulter la page Moteur
    # ne doit pas démarrer son App Server lorsque Hermes est le moteur sélectionné.
    if selected_engine != 'codex':
        return {
            **common,
            'installed': True,
            'version': version,
            'reachable': False,
            'account': None,
            'requires_openai_auth': False,
        }
    try:
        client = await get_client()
        account_result = await client.account_read(refresh_token=False)
        return {
            **common,
            'installed': True,
            'version': version,
            'reachable': client.running,
            'account': safe_account(account_result),
            'requires_openai_auth': bool(account_result.get('requiresOpenaiAuth')),
        }
    except (CodexProtocolError, OSError, TimeoutError) as exc:
        return {
            **common,
            'installed': True,
            'version': version,
            'reachable': False,
            'account': None,
            'error': type(exc).__name__,
        }


@router.post('/login/device')
async def codex_device_login(_user=Depends(get_admin_user)) -> dict[str, str]:
    try:
        result = await (await get_client()).start_chatgpt_device_login()
    except (CodexProtocolError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail='Connexion Codex indisponible') from exc
    allowed = {
        key: str(result.get(key) or '')
        for key in ('type', 'loginId', 'verificationUrl', 'userCode')
    }
    if not allowed['verificationUrl'] or not allowed['userCode']:
        raise HTTPException(status_code=502, detail='Réponse de connexion Codex incomplète')
    return allowed


@router.post('/login/cancel/{login_id}')
async def codex_cancel_login(login_id: str, _user=Depends(get_admin_user)) -> dict[str, bool]:
    await (await get_client()).cancel_login(login_id)
    return {'cancelled': True}


@router.post('/logout')
async def codex_logout(_user=Depends(get_admin_user)) -> dict[str, bool]:
    client = await get_client()
    await client.logout()
    # Redémarrage explicite : aucune session chargée ne conserve l'ancien compte.
    await stop_client()
    return {'logged_out': True}
