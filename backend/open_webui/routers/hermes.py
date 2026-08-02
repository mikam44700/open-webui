"""Admin-only Hermes Agent control-plane integration.

The browser never talks to Hermes directly. Open WebUI keeps the Hermes URL
and API key server-side, exposes a small allow-listed surface, and sanitizes
upstream failures before they reach the UI.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp
import yaml
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.auth import get_admin_user
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)
router = APIRouter()

HERMES_API_URL = os.getenv('HERMES_API_URL', '').rstrip('/')
HERMES_CONFIG_FILE = os.getenv('HERMES_CONFIG_FILE', '')


def _load_api_key() -> str:
    key = os.getenv('HERMES_API_KEY', '')
    if key or not HERMES_CONFIG_FILE:
        return key

    try:
        with open(HERMES_CONFIG_FILE, encoding='utf-8') as config_file:
            config = yaml.safe_load(config_file) or {}
        return str(config.get('platforms', {}).get('api_server', {}).get('extra', {}).get('key', ''))
    except (OSError, AttributeError, TypeError, yaml.YAMLError) as exc:
        log.warning('Unable to read the Hermes API key from its config file: %s', exc)
        return ''


HERMES_API_KEY = _load_api_key()

try:
    HERMES_REQUEST_TIMEOUT = max(1.0, float(os.getenv('HERMES_REQUEST_TIMEOUT', '15')))
except ValueError:
    HERMES_REQUEST_TIMEOUT = 15.0

_TIMEOUT = aiohttp.ClientTimeout(total=HERMES_REQUEST_TIMEOUT)


class HermesUpstreamError(Exception):
    def __init__(self, code: str, message: str, http_status: int = status.HTTP_503_SERVICE_UNAVAILABLE):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _headers() -> dict[str, str]:
    headers = {'Accept': 'application/json'}
    if HERMES_API_KEY:
        headers['Authorization'] = f'Bearer {HERMES_API_KEY}'
    return headers


async def _request(path: str) -> dict[str, Any]:
    if not HERMES_API_URL:
        raise HermesUpstreamError('not_configured', 'Hermes Agent is not configured.')

    session = await get_session()
    try:
        async with session.get(
            f'{HERMES_API_URL}{path}',
            headers=_headers(),
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=_TIMEOUT,
        ) as response:
            if response.status in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
                raise HermesUpstreamError(
                    'authentication_failed',
                    'Hermes Agent rejected the configured credentials.',
                    status.HTTP_502_BAD_GATEWAY,
                )
            if not response.ok:
                raise HermesUpstreamError(
                    'upstream_error',
                    'Hermes Agent returned an unexpected response.',
                    status.HTTP_502_BAD_GATEWAY,
                )

            body = await response.json(content_type=None)
            if not isinstance(body, dict):
                raise HermesUpstreamError(
                    'invalid_response',
                    'Hermes Agent returned an invalid response.',
                    status.HTTP_502_BAD_GATEWAY,
                )
            return body
    except HermesUpstreamError:
        raise
    except (aiohttp.ClientError, TimeoutError) as exc:
        log.info('Hermes Agent is unavailable: %s', exc)
        raise HermesUpstreamError('unavailable', 'Hermes Agent is unavailable.') from exc


def _http_error(exc: HermesUpstreamError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={'error': {'code': exc.code, 'message': exc.message}},
    )


@router.get('/status')
async def get_hermes_status(user=Depends(get_admin_user)):
    """Return a dashboard-safe status even when Hermes is offline."""
    if not HERMES_API_URL:
        return {
            'configured': False,
            'state': 'not_configured',
            'version': None,
            'model': None,
            'active_agents': 0,
        }

    try:
        health = await _request('/health/detailed')
        capabilities = await _request('/v1/capabilities')
    except HermesUpstreamError as exc:
        return {
            'configured': True,
            'state': exc.code,
            'version': None,
            'model': None,
            'active_agents': 0,
        }

    readiness = health.get('readiness') if isinstance(health.get('readiness'), dict) else {}
    upstream_status = str(health.get('status') or readiness.get('status') or '').lower()
    state = 'operational' if upstream_status in {'ok', 'ready', 'healthy', 'operational'} else 'degraded'

    return {
        'configured': True,
        'state': state,
        'version': health.get('version'),
        'model': capabilities.get('model'),
        'active_agents': health.get('active_agents', 0),
        'gateway_state': health.get('gateway_state'),
        'gateway_busy': health.get('gateway_busy', False),
        'updated_at': health.get('updated_at'),
        'platforms': health.get('platforms', {}),
        'readiness': readiness,
    }


@router.get('/capabilities')
async def get_hermes_capabilities(user=Depends(get_admin_user)):
    try:
        return await _request('/v1/capabilities')
    except HermesUpstreamError as exc:
        raise _http_error(exc) from exc


@router.get('/skills')
async def get_hermes_skills(user=Depends(get_admin_user)):
    try:
        return await _request('/v1/skills')
    except HermesUpstreamError as exc:
        raise _http_error(exc) from exc


@router.get('/toolsets')
async def get_hermes_toolsets(user=Depends(get_admin_user)):
    try:
        return await _request('/v1/toolsets')
    except HermesUpstreamError as exc:
        raise _http_error(exc) from exc
