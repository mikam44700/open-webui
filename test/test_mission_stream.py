import asyncio
import json

import pytest
from open_webui.hermes_bridge.mission_stream import (
    INTERACTIVE_MAX_TOOL_CALLS,
    MISSION_MAX_TOOL_CALLS,
    MissionIdleTimeout,
    MissionMaximumDuration,
    ToolCallBudget,
    is_long_mission_request,
    progress_event,
    stream_with_limits,
)
from open_webui.utils.hermes_tool_labels import humanize_tool_progress


async def delayed_stream(delays_and_chunks):
    for delay, chunk in delays_and_chunks:
        await asyncio.sleep(delay)
        yield chunk


async def collect(stream):
    return [chunk async for chunk in stream]


def event_payload(chunk: bytes) -> dict:
    data_line = next(line for line in chunk.decode().splitlines() if line.startswith('data:'))
    return json.loads(data_line.removeprefix('data:').strip())


def test_active_mission_is_not_cut_by_the_old_total_timeout_shape():
    chunks = asyncio.run(
        collect(
            stream_with_limits(
                delayed_stream([(0.04, b'first'), (0.04, b'second')]),
                maximum_seconds=0.3,
                idle_seconds=0.15,
                heartbeat_seconds=0.01,
            )
        )
    )

    assert b'first' in chunks
    assert b'second' in chunks
    assert event_payload(chunks[-1])['status'] == 'completed'


def test_silent_mission_emits_visible_progress_without_counting_a_tool():
    chunks = asyncio.run(
        collect(
            stream_with_limits(
                delayed_stream([(0.04, b'answer')]),
                maximum_seconds=0.3,
                idle_seconds=0.2,
                heartbeat_seconds=0.01,
            )
        )
    )

    progress = [event_payload(chunk) for chunk in chunks if chunk.startswith(b'event:')]
    assert progress[0]['status'] == 'progress'
    assert progress[0]['internal'] is True
    assert progress[-1]['status'] == 'completed'


def test_real_upstream_inactivity_stops_the_mission():
    async def scenario():
        return await collect(
            stream_with_limits(
                delayed_stream([(0.2, b'too late')]),
                maximum_seconds=0.4,
                idle_seconds=0.05,
                heartbeat_seconds=0.01,
            )
        )

    with pytest.raises(MissionIdleTimeout):
        asyncio.run(scenario())


def test_total_duration_remains_bounded_even_when_upstream_is_active():
    async def endless_active_stream():
        while True:
            await asyncio.sleep(0.01)
            yield b'activity'

    async def scenario():
        return await collect(
            stream_with_limits(
                endless_active_stream(),
                maximum_seconds=0.06,
                idle_seconds=0.05,
                heartbeat_seconds=0.01,
            )
        )

    with pytest.raises(MissionMaximumDuration):
        asyncio.run(scenario())


def test_progress_completion_event_is_not_an_external_tool_call():
    payload = event_payload(progress_event(70, done=True))
    assert payload == {
        'tool': 'lunaria_long_mission',
        'toolCallId': 'lunaria-long-mission',
        'status': 'completed',
        'label': 'depuis 2 min',
        'internal': True,
    }


def test_long_mission_progress_is_humanized_for_the_client():
    assert humanize_tool_progress('lunaria_long_mission', 'depuis 4 min') == (
        '⏳ Mission approfondie en cours depuis 4 min'
    )


def tool_event(tool: str, call_id: str, label: str) -> bytes:
    data = {
        'tool': tool,
        'toolCallId': call_id,
        'status': 'running',
        'label': label,
    }
    return f'event: hermes.tool.progress\ndata: {json.dumps(data)}\n\n'.encode()


def test_long_mission_fallback_is_detected_when_the_llm_router_times_out():
    payload = {
        'messages': [
            {
                'role': 'user',
                'content': (
                    'Analyse mon marché, surveille cinq concurrents et génère '
                    'un rapport PDF avec les sources.'
                ),
            }
        ]
    }
    assert is_long_mission_request(payload) is True
    assert is_long_mission_request(
        {'messages': [{'role': 'user', 'content': 'Quel temps fait-il ?'}]}
    ) is False
    assert is_long_mission_request(
        {'messages': []}, action_capability='complex'
    ) is True


def test_long_mission_accepts_more_than_the_interactive_tool_budget():
    budget = ToolCallBudget(maximum_calls=MISSION_MAX_TOOL_CALLS)
    for index in range(INTERACTIVE_MAX_TOOL_CALLS + 1):
        assert budget.observe(
            tool_event('web_search', f'call-{index}', f'requête différente {index}')
        ) is None
    assert budget.count == INTERACTIVE_MAX_TOOL_CALLS + 1


def test_tool_budget_ignores_duplicate_sse_events_but_stops_a_real_loop():
    budget = ToolCallBudget(maximum_calls=MISSION_MAX_TOOL_CALLS)
    first = tool_event('web_search', 'same-call', 'même requête')
    assert budget.observe(first) is None
    assert budget.observe(first) is None
    assert budget.count == 1

    for index in range(1, 4):
        reason = budget.observe(
            tool_event('web_search', f'retry-{index}', 'même requête')
        )
    assert reason == 'repeated'


def test_interactive_tool_budget_remains_strict():
    budget = ToolCallBudget(maximum_calls=INTERACTIVE_MAX_TOOL_CALLS)
    for index in range(INTERACTIVE_MAX_TOOL_CALLS):
        assert budget.observe(
            tool_event('integration', f'call-{index}', f'action {index}')
        ) is None
    assert budget.observe(tool_event('integration', 'too-many', 'action finale')) == 'total'
