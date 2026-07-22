import json
from pathlib import Path

from open_webui.codex_bridge.opencodex_config import (
    managed_config,
    resolve_lunaria_selection,
    write_managed_config,
)


def test_managed_config_references_environment_without_secret_values(tmp_path: Path):
    target = tmp_path / "config.json"
    write_managed_config(target)
    raw = target.read_text()
    parsed = json.loads(raw)

    assert parsed["defaultProvider"] == "openai"
    assert parsed["providers"]["openrouter"]["apiKey"] == "${OPENROUTER_API_KEY}"
    assert "sk-" not in raw
    assert target.stat().st_mode & 0o777 == 0o600


def test_selection_uses_native_openai_model(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("model:\n  provider: openai-codex\n  default: gpt-5.6-sol\n")
    assert resolve_lunaria_selection(config) == ("gpt-5.6-sol", None)


def test_selection_prefixes_openrouter_model(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("model:\n  provider: openrouter\n  default: moonshotai/kimi-k2.7-code\n")
    assert resolve_lunaria_selection(config) == (
        "openrouter/moonshotai/kimi-k2.7-code",
        None,
    )
