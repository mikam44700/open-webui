import asyncio

from open_webui.codex_bridge import router as codex_router


def test_codex_status_does_not_start_app_server_when_hermes_is_active(monkeypatch):
    monkeypatch.setenv('LUNARIA_ENGINE', 'hermes')
    app_server_started = False

    async def fake_version():
        return '0.145.0'

    async def forbidden_get_client():
        nonlocal app_server_started
        app_server_started = True
        raise AssertionError('Codex App Server ne doit pas démarrer en mode Hermes')

    monkeypatch.setattr(codex_router, '_version', fake_version)
    monkeypatch.setattr(codex_router, 'get_client', forbidden_get_client)

    status = asyncio.run(codex_router.codex_status(_user=object()))

    assert status['selected_engine'] == 'hermes'
    assert status['enabled'] is False
    assert status['installed'] is True
    assert status['reachable'] is False
    assert app_server_started is False


def test_codex_status_still_uses_app_server_when_explicitly_selected(monkeypatch):
    monkeypatch.setenv('LUNARIA_ENGINE', 'codex')

    class FakeClient:
        running = True

        async def account_read(self, refresh_token=False):
            assert refresh_token is False
            return {'account': {'type': 'chatgpt', 'email': 'michael@example.com'}}

    async def fake_version():
        return '0.145.0'

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(codex_router, '_version', fake_version)
    monkeypatch.setattr(codex_router, 'get_client', fake_get_client)

    status = asyncio.run(codex_router.codex_status(_user=object()))

    assert status['selected_engine'] == 'codex'
    assert status['enabled'] is True
    assert status['reachable'] is True
    assert status['account']['type'] == 'chatgpt'
