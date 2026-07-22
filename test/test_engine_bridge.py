import pytest

from open_webui.codex_bridge.direct_response import _conversation
from open_webui.engine_bridge import direct_response as engine_direct


def test_engine_defaults_to_hermes(monkeypatch):
    monkeypatch.delenv('LUNARIA_ENGINE', raising=False)
    assert engine_direct.active_engine() == 'hermes'


def test_codex_engine_is_an_explicit_reversible_choice(monkeypatch):
    monkeypatch.setenv('LUNARIA_ENGINE', 'codex')
    assert engine_direct.active_engine() == 'codex'
    assert engine_direct.is_direct_candidate(
        {'stream': True, 'messages': [{'role': 'user', 'content': 'Bonjour'}]}
    )


def test_unknown_engine_never_disables_safe_hermes_fallback(monkeypatch):
    monkeypatch.setenv('LUNARIA_ENGINE', 'moteur-inconnu')
    assert engine_direct.active_engine() == 'hermes'


def test_codex_prompt_preserves_persona_and_recent_conversation():
    developer, transcript = _conversation(
        {
            'messages': [
                {'role': 'system', 'content': 'Tu es Luna.'},
                {'role': 'user', 'content': 'Bonjour'},
                {'role': 'assistant', 'content': 'Bonjour Michael'},
                {'role': 'user', 'content': 'Résume notre échange.'},
            ]
        }
    )
    assert 'Tu es Luna.' in developer
    assert "n'utilise aucun outil" in developer
    assert 'USER: Bonjour' in transcript
    assert 'ASSISTANT: Bonjour Michael' in transcript
    assert transcript.endswith('USER: Résume notre échange.')


def test_codex_prompt_refuses_payload_without_user_message():
    with pytest.raises(ValueError, match='aucun message utilisateur'):
        _conversation({'messages': [{'role': 'system', 'content': 'Règle'}]})
