import json

from open_webui.hermes_bridge import direct_response as direct


def test_exact_action_contract_is_accepted():
    action = direct.parse_action(
        json.dumps(
            {
                'hermes_action': True,
                'capacite': 'web',
                'objectif': 'Consulter le site officiel et relever le tarif actuel.',
            }
        )
    )

    assert action is not None
    assert action.objectif == 'Consulter le site officiel et relever le tarif actuel.'
    assert action.capacite == 'web'


def test_text_around_action_contract_is_rejected():
    assert direct.parse_action(
        'Je vais le faire. {"hermes_action":true,"capacite":"integration","objectif":"Envoyer le message"}'
    ) is None


def test_extra_keys_cannot_select_a_tool_or_bypass_permissions():
    assert direct.parse_action(
        '{"hermes_action":true,"capacite":"web","objectif":"Lire le site","outil":"terminal"}'
    ) is None


def test_false_or_empty_action_is_rejected():
    assert direct.parse_action(
        '{"hermes_action":false,"capacite":"integration","objectif":"Envoyer"}'
    ) is None
    assert direct.parse_action('{"hermes_action":true,"capacite":"web","objectif":"   "}') is None
    assert direct.parse_action('{"hermes_action":true,"capacite":"inconnue","objectif":"Lire"}') is None


def test_oversized_action_is_rejected():
    payload = json.dumps(
        {
            'hermes_action': True,
            'capacite': 'document',
            'objectif': 'x' * (direct.MAX_ACTION_OBJECTIVE + 1),
        }
    )
    assert direct.parse_action(payload) is None


def test_action_prefix_is_buffered_but_normal_text_is_not():
    assert direct.looks_like_action_prefix('') is True
    assert direct.looks_like_action_prefix('  {') is True
    assert direct.looks_like_action_prefix('Bonjour') is False


def test_direct_mode_has_an_immediate_kill_switch(monkeypatch):
    payload = {'stream': True, 'messages': [{'role': 'user', 'content': 'Salut'}]}
    monkeypatch.setenv(direct.DIRECT_MODE_ENV, '0')
    assert direct.is_direct_candidate(payload) is False

    monkeypatch.setenv(direct.DIRECT_MODE_ENV, '1')
    assert direct.is_direct_candidate(payload) is True


def test_non_streaming_and_empty_payloads_keep_the_historical_route(monkeypatch):
    monkeypatch.setenv(direct.DIRECT_MODE_ENV, '1')
    assert direct.is_direct_candidate({'stream': False, 'messages': []}) is False
    assert direct.is_direct_candidate({'stream': True, 'messages': []}) is False


def test_handoff_never_authorizes_success_without_a_tool_result():
    policy = direct.action_handoff_policy('Envoyer un email à Paul', 'integration')
    assert 'outils autorisés' in policy
    assert 'confirmations humaines' in policy
    assert "résultat d'outil confirmé" in policy
    assert 'maximum trois outils' in policy


def test_only_bounded_capabilities_use_the_restricted_runtime():
    assert direct.BOUNDED_CAPABILITIES == {'web', 'document', 'memory'}
    assert 'integration' in direct.ACTION_CAPABILITIES
    assert 'complex' in direct.ACTION_CAPABILITIES


def test_existing_web_sources_force_direct_synthesis_without_second_search():
    payload = {
        'messages': [
            {'role': 'system', 'content': '<source id="1">Résultat vérifié</source>'},
            {'role': 'user', 'content': 'Quelles sont les actualités ?'},
        ]
    }
    policy = direct.routing_policy_for_payload(payload)
    assert 'sources web vérifiées sont déjà présentes' in policy
    assert 'ne demande jamais une nouvelle action web' in policy


def test_normal_prompt_keeps_standard_routing_policy():
    payload = {'messages': [{'role': 'user', 'content': 'Salut'}]}
    assert direct.routing_policy_for_payload(payload) == direct.ROUTING_POLICY
