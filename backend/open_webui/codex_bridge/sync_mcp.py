"""Synchronise les MCP activés de LunarIA vers la configuration Codex.

La configuration produit existante reste la source de vérité pendant la migration. Le
programme appelle la CLI officielle sans shell et ne journalise ni en-tête ni secret.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import yaml


Run = Callable[..., subprocess.CompletedProcess[str]]


def _enabled_servers(config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    servers = config.get("mcp_servers")
    if not isinstance(servers, dict):
        return []
    return [
        (str(name), value)
        for name, value in servers.items()
        if isinstance(value, dict) and value.get("enabled") is True
    ]


def sync_mcp_servers(
    *,
    hermes_config: Path,
    codex_bin: str,
    environment: dict[str, str] | None = None,
    run: Run = subprocess.run,
) -> dict[str, list[str]]:
    """Ajoute ou actualise les MCP compatibles, sans supprimer les entrées existantes."""
    report: dict[str, list[str]] = {"synced": [], "skipped": [], "failed": []}
    if not hermes_config.is_file():
        return report
    try:
        loaded = yaml.safe_load(hermes_config.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        report["failed"].append("config")
        return report
    if not isinstance(loaded, dict):
        return report

    env = {**os.environ, **(environment or {})}
    codex_home = env.get("CODEX_HOME")
    if codex_home:
        Path(codex_home).mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, server in _enabled_servers(loaded):
        # Un en-tête peut contenir une clé. Codex accepte un token via variable d'env,
        # jamais une valeur secrète en argument ; ces cas seront portés séparément.
        if server.get("headers"):
            report["skipped"].append(name)
            continue
        command = server.get("command")
        url = server.get("url")
        args = server.get("args")
        if isinstance(url, str) and url.strip():
            cmd = [codex_bin, "mcp", "add", name, "--url", url.strip()]
        elif isinstance(command, str) and command.strip():
            safe_args = [str(value) for value in args] if isinstance(args, list) else []
            cmd = [codex_bin, "mcp", "add", name, "--", command.strip(), *safe_args]
        else:
            report["skipped"].append(name)
            continue
        try:
            result = run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            report["failed"].append(name)
            continue
        report["synced" if result.returncode == 0 else "failed"].append(name)
    return report


def main() -> int:
    home = Path(os.environ.get("HERMES_HOME", "/app/backend/data/hermes"))
    report = sync_mcp_servers(
        hermes_config=home / "config.yaml",
        codex_bin=os.environ.get("LUNARIA_CODEX_BIN", "codex"),
    )
    # Uniquement des noms de connecteurs et des états, jamais leur configuration.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
