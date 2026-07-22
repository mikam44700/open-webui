"""Sélection réversible du moteur pour le parcours conversationnel."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from open_webui.codex_bridge import direct_response as codex_direct
from open_webui.hermes_bridge import direct_response as hermes_direct

# Le contrat de routage et le format SSE sont stables et possédés par LunarIA. Ils sont
# encore physiquement dans l'ancien module pendant la transition, puis seront déplacés
# lorsque toutes les actions auront quitté Hermes.
DirectEvent = hermes_direct.DirectEvent
HermesAction = hermes_direct.HermesAction
ACTION_CAPABILITIES = hermes_direct.ACTION_CAPABILITIES
BOUNDED_CAPABILITIES = hermes_direct.BOUNDED_CAPABILITIES
parse_action = hermes_direct.parse_action
looks_like_action_prefix = hermes_direct.looks_like_action_prefix
action_handoff_policy = hermes_direct.action_handoff_policy
openai_delta = hermes_direct.openai_delta
openai_tool_progress = hermes_direct.openai_tool_progress
openai_done = hermes_direct.openai_done


def active_engine() -> str:
    value = os.environ.get('LUNARIA_ENGINE', 'hermes').strip().lower()
    return 'codex' if value == 'codex' else 'hermes'


def is_direct_candidate(payload: dict) -> bool:
    if active_engine() == 'codex':
        return bool(
            payload.get('stream') is True
            and isinstance(payload.get('messages'), list)
            and any(
                isinstance(message, dict) and message.get('role') == 'user'
                for message in payload['messages']
            )
        )
    return hermes_direct.is_direct_candidate(payload)


async def stream_direct_events(payload: dict) -> AsyncIterator[DirectEvent]:
    backend = codex_direct if active_engine() == 'codex' else hermes_direct
    async for event in backend.stream_direct_events(payload):
        yield event


async def stream_action_events(payload: dict, action: HermesAction) -> AsyncIterator[DirectEvent]:
    # Transition volontaire : les actions ne passent à Codex qu'après branchement et tests
    # réels de leurs MCP. Le repli n'est jamais utilisé pour une action déjà commencée.
    async for event in hermes_direct.stream_action_events(payload, action):
        yield event

