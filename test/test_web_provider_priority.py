import pytest

from open_webui.hermes_bridge import hermes_adapter, tool_connection_adapter
from open_webui.routers.retrieval import RetrievalConfig, _lunaria_web_search_plan


def test_explicit_connected_provider_is_activated(monkeypatch):
    writes = []
    monkeypatch.setattr(
        hermes_adapter,
        'read_env_value',
        lambda key: 'secret-present' if key == 'TAVILY_API_KEY' else None,
    )
    monkeypatch.setattr(
        hermes_adapter,
        'set_web_backend',
        lambda search, extract=None: writes.append((search, extract)),
    )

    backend = tool_connection_adapter.activate_web_provider('tavily')

    assert backend == 'tavily'
    assert writes == [('tavily', 'tavily')]


def test_unconnected_provider_cannot_be_selected(monkeypatch):
    monkeypatch.setattr(hermes_adapter, 'read_env_value', lambda _key: None)
    with pytest.raises(ValueError, match="connecte d'abord"):
        tool_connection_adapter.activate_web_provider('exa')


def test_chat_uses_client_choice_then_other_connections_then_duckduckgo(monkeypatch):
    monkeypatch.setattr(
        hermes_adapter,
        'get_web_backends',
        lambda: {'search': 'brave-free', 'extract': ''},
    )
    values = {
        'BRAVE_SEARCH_API_KEY': 'brave-secret',
        'EXA_API_KEY': 'exa-secret',
    }
    monkeypatch.setattr(hermes_adapter, 'read_env_value', lambda key: values.get(key))
    config = RetrievalConfig({})

    plan = _lunaria_web_search_plan(config)

    assert plan == ['brave', 'exa', 'duckduckgo']
    assert config.BRAVE_SEARCH_API_KEY == 'brave-secret'
    assert config.EXA_API_KEY == 'exa-secret'


def test_duckduckgo_is_last_when_a_client_provider_is_connected(monkeypatch):
    monkeypatch.setattr(
        hermes_adapter,
        'get_web_backends',
        lambda: {'search': 'ddgs', 'extract': ''},
    )
    monkeypatch.setattr(
        hermes_adapter,
        'read_env_value',
        lambda key: 'exa-secret' if key == 'EXA_API_KEY' else None,
    )

    assert _lunaria_web_search_plan(RetrievalConfig({})) == ['exa', 'duckduckgo']
