"""Configuration OpenCodex gérée par LunarIA, sans duplication de clés API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "adapter": "openai-responses",
        "baseUrl": "https://chatgpt.com/backend-api/codex",
        "authMode": "forward",
        "codexAccountMode": "pool",
    },
    "openrouter": {
        "adapter": "openai-chat",
        "baseUrl": "https://openrouter.ai/api/v1",
        "apiKey": "${OPENROUTER_API_KEY}",
    },
    "openai-apikey": {
        "adapter": "openai-responses",
        "baseUrl": "https://api.openai.com/v1",
        "apiKey": "${OPENAI_API_KEY}",
    },
    "anthropic-apikey": {
        "adapter": "anthropic",
        "baseUrl": "https://api.anthropic.com",
        "apiKey": "${ANTHROPIC_API_KEY}",
    },
    "kimi-code": {
        "adapter": "openai-chat",
        "baseUrl": "https://api.kimi.com/coding/v1",
        "apiKey": "${KIMI_API_KEY}",
    },
    "zai": {
        "adapter": "openai-chat",
        "baseUrl": "https://api.z.ai/api/coding/paas/v4",
        "apiKey": "${ZAI_API_KEY}",
    },
    "deepseek": {
        "adapter": "openai-chat",
        "baseUrl": "https://api.deepseek.com",
        "apiKey": "${DEEPSEEK_API_KEY}",
    },
    "google": {
        "adapter": "google",
        "baseUrl": "https://generativelanguage.googleapis.com",
        "apiKey": "${GEMINI_API_KEY}",
    },
    "mistral": {
        "adapter": "openai-chat",
        "baseUrl": "https://api.mistral.ai/v1",
        "apiKey": "${MISTRAL_API_KEY}",
    },
    "qwen-cloud": {
        "adapter": "openai-chat",
        "baseUrl": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        "apiKey": "${QWEN_API_KEY}",
    },
    "xai": {
        "adapter": "openai-chat",
        "baseUrl": "https://api.x.ai/v1",
        "apiKey": "${XAI_API_KEY}",
    },
}


PROVIDER_ALIASES = {
    "openai-codex": "openai",
    "openai": "openai-apikey",
    "claude": "anthropic-apikey",
    "anthropic": "anthropic-apikey",
    "kimi-coding": "kimi-code",
    "kimi-coding-cn": "kimi-code",
    "zai": "zai",
    "zai-coding": "zai",
    "deepseek": "deepseek",
    "gemini": "google",
    "google": "google",
    "mistral": "mistral",
    "qwen": "qwen-cloud",
    "qwen-cloud": "qwen-cloud",
    "xai": "xai",
    "grok": "xai",
    "openrouter": "openrouter",
}


def resolve_lunaria_selection(config_path: Path | str) -> tuple[str | None, str | None]:
    """Retourne le modèle routé OpenCodex et le provider natif Codex éventuel."""
    try:
        import yaml

        loaded = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return None, None
    model_config = loaded.get("model") if isinstance(loaded, dict) else None
    if not isinstance(model_config, dict):
        return None, None
    provider = str(model_config.get("provider") or "").strip().lower()
    model = str(model_config.get("default") or model_config.get("model") or "").strip()
    alias = PROVIDER_ALIASES.get(provider)
    if not alias or not model:
        return None, None
    if alias == "openai":
        return model, None
    # OpenCodex expose les modèles non OpenAI sous la forme provider/modèle.
    return f"{alias}/{model}", None


def managed_config() -> dict[str, Any]:
    return {
        "port": 10100,
        "providers": PROVIDERS,
        "defaultProvider": "openai",
        "websockets": False,
        "codexAutoStart": True,
    }


def write_managed_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(managed_config(), indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def main() -> int:
    home = Path(os.environ.get("OPENCODEX_HOME", "/app/backend/data/opencodex"))
    write_managed_config(home / "config.json")
    print(f"providers={len(PROVIDERS)} config=managed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
