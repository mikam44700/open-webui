"""Processus Hermes sans outil utilisé par le parcours conversationnel LunarIA.

Ce fichier est exécuté avec l'interpréteur Python de l'installation Hermes, pas avec
celui d'OpenWebUI. Son protocole stdout est volontairement minuscule et versionné : une
ligne JSON préfixée par ``LUNARIA_DIRECT_EVENT `` pour chaque delta puis un événement
final. Tout autre stdout éventuel d'un provider est ignoré par le processus parent.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

EVENT_PREFIX = 'LUNARIA_DIRECT_EVENT '


def _emit(kind: str, **data: Any) -> None:
    print(
        EVENT_PREFIX + json.dumps({'v': 1, 'type': kind, **data}, ensure_ascii=False),
        flush=True,
    )


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or '')
    parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get('type') in {'text', 'input_text', 'output_text'}:
            parts.append(str(part.get('text') or ''))
    return '\n'.join(part for part in parts if part)


def _conversation(messages: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get('role') or 'user')
        text = _text_content(message.get('content'))
        if role in {'system', 'developer'}:
            if text:
                system_parts.append(text)
            continue
        if role in {'user', 'assistant'} and text:
            normalized.append({'role': role, 'content': text})

    last_user = next(
        (index for index in range(len(normalized) - 1, -1, -1) if normalized[index]['role'] == 'user'),
        None,
    )
    if last_user is None:
        raise ValueError('aucun message utilisateur exploitable')
    user_message = normalized[last_user]['content']
    history = normalized[:last_user]
    return '\n\n'.join(system_parts), user_message, history


def main() -> int:
    started = time.perf_counter()
    try:
        request = json.load(sys.stdin)
        messages = request.get('messages') or []
        persona, user_message, history = _conversation(messages)

        # Le checkout Hermes est configurable et placé en tête pour éviter qu'un paquet
        # Python global d'une autre version ne soit chargé après une mise à jour.
        hermes_dir = os.environ.get('HERMES_AGENT_DIR', '/opt/hermes-agent')
        if hermes_dir not in sys.path:
            sys.path.insert(0, hermes_dir)

        from gateway.run import (  # pylint: disable=import-outside-toplevel
            GatewayRunner,
            _resolve_gateway_model,
            _resolve_runtime_agent_kwargs,
        )
        from run_agent import AIAgent  # pylint: disable=import-outside-toplevel

        runtime_kwargs = _resolve_runtime_agent_kwargs()
        model = runtime_kwargs.pop('model', None) or _resolve_gateway_model()
        # Certains providers placent déjà ces options dans les kwargs résolus. Le pont
        # impose ses propres bornes sans jamais passer deux fois le même argument.
        runtime_kwargs.pop('max_tokens', None)
        runtime_kwargs.pop('max_iterations', None)
        runtime_kwargs.pop('enabled_toolsets', None)
        runtime_kwargs.pop('disabled_toolsets', None)
        fallback_model = GatewayRunner._load_fallback_model()
        reasoning_config = GatewayRunner._load_reasoning_config()

        chunks: list[str] = []

        def on_delta(delta: Any) -> None:
            text = str(delta or '')
            if not text:
                return
            chunks.append(text)
            _emit('delta', text=text)

        agent = AIAgent(
            model=model,
            **runtime_kwargs,
            max_iterations=1,
            max_tokens=request.get('max_tokens'),
            quiet_mode=True,
            verbose_logging=False,
            enabled_toolsets=[],
            disabled_toolsets=[],
            skip_context_files=True,
            skip_memory=True,
            platform='api_server',
            stream_delta_callback=on_delta,
            fallback_model=fallback_model,
            reasoning_config=reasoning_config,
        )
        result = agent.run_conversation(
            user_message,
            system_message=f'{persona}\n\n{request["routing_policy"]}',
            conversation_history=history,
        )
        answer = str(result.get('final_response') or result.get('response') or ''.join(chunks) or '')
        if answer and not chunks:
            _emit('delta', text=answer)
        usage = result.get('usage') if isinstance(result, dict) else None
        _emit(
            'done',
            answer=answer,
            model=model,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            usage=usage if isinstance(usage, dict) else {},
        )
        return 0
    except Exception as exc:  # le parent replie vers le parcours Hermes actuel
        _emit(
            'error',
            error_type=type(exc).__name__,
            message=str(exc)[:300],
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
