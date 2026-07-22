from open_webui.codex_bridge.client import notification_to_event


def test_agent_delta_is_translated_for_lunaria_streaming():
    event = notification_to_event(
        {
            'method': 'item/agentMessage/delta',
            'params': {
                'threadId': 'thread-1',
                'turnId': 'turn-1',
                'itemId': 'message-1',
                'delta': 'Bonjour',
            },
        }
    )

    assert event is not None
    assert event.type == 'delta'
    assert event.text == 'Bonjour'
    assert event.thread_id == 'thread-1'
    assert event.turn_id == 'turn-1'


def test_completed_turn_is_a_terminal_event():
    event = notification_to_event(
        {
            'method': 'turn/completed',
            'params': {
                'threadId': 'thread-1',
                'turn': {
                    'id': 'turn-1',
                    'status': 'completed',
                    'durationMs': 2059,
                    'error': None,
                },
            },
        }
    )

    assert event is not None
    assert event.type == 'done'
    assert event.duration_ms == 2059


def test_failed_turn_never_looks_successful():
    event = notification_to_event(
        {
            'method': 'turn/completed',
            'params': {
                'threadId': 'thread-1',
                'turn': {
                    'id': 'turn-1',
                    'status': 'failed',
                    'error': {'message': 'provider unavailable'},
                },
            },
        }
    )

    assert event is not None
    assert event.type == 'error'
    assert event.message == 'provider unavailable'


def test_tool_progress_is_explicit_and_separate_from_text():
    event = notification_to_event(
        {
            'method': 'item/started',
            'params': {
                'threadId': 'thread-1',
                'turnId': 'turn-1',
                'item': {
                    'id': 'tool-1',
                    'type': 'mcpToolCall',
                    'status': 'inProgress',
                },
            },
        }
    )

    assert event is not None
    assert event.type == 'tool_started'
    assert event.item_type == 'mcpToolCall'


def test_unknown_notification_is_ignored():
    assert notification_to_event({'method': 'account/rateLimits/updated', 'params': {}}) is None
