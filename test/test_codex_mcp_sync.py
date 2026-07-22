from pathlib import Path
from subprocess import CompletedProcess

from open_webui.codex_bridge.sync_mcp import sync_mcp_servers


def test_syncs_enabled_stdio_and_http_without_shell(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mcp_servers:
  documents:
    enabled: true
    command: python
    args: [document_server.py]
  recherche:
    enabled: true
    url: http://127.0.0.1:9000/mcp
  inactif:
    enabled: false
    command: ignored
"""
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, "", "")

    report = sync_mcp_servers(
        hermes_config=config,
        codex_bin="codex",
        environment={"CODEX_HOME": str(tmp_path / "codex")},
        run=fake_run,
    )

    assert report == {"synced": ["documents", "recherche"], "skipped": [], "failed": []}
    assert calls[0][0] == ["codex", "mcp", "add", "documents", "--", "python", "document_server.py"]
    assert calls[1][0] == ["codex", "mcp", "add", "recherche", "--url", "http://127.0.0.1:9000/mcp"]
    assert all(call[1].get("shell") is not True for call in calls)


def test_secret_headers_are_not_copied_to_codex_arguments(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mcp_servers:
  crawl:
    enabled: true
    url: http://crawl4ai:11235/mcp/sse
    headers:
      Authorization: Bearer secret-value
"""
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 0, "", "")

    report = sync_mcp_servers(
        hermes_config=config,
        codex_bin="codex",
        run=fake_run,
    )

    assert report["skipped"] == ["crawl"]
    assert calls == []
