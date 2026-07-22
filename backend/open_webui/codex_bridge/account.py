"""Projection publique de l'état d'authentification Codex."""

from __future__ import annotations

from typing import Any


def safe_account(result: dict[str, Any]) -> dict[str, Any] | None:
    account = result.get('account')
    if not isinstance(account, dict):
        return None
    # Liste blanche stricte : les réponses de l'API LunarIA ne pourront jamais contenir
    # un access token si le protocole Codex évolue.
    return {
        key: account.get(key)
        for key in ('type', 'email', 'planType', 'credentialSource')
        if key in account
    }

