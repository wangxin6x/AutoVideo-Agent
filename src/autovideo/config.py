from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a provider configuration is missing or unsafe."""


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")
    try:
        import yaml
    except ImportError as exc:
        raise ConfigError("YAML config requires PyYAML; install with: python -m pip install pyyaml") from exc
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML config: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError("Config root must be a mapping")
    return loaded


def config_json(config: dict[str, Any]) -> str:
    return json.dumps(config, indent=2, ensure_ascii=False)


def config_provider_type(config: dict[str, Any], group: str, default: str) -> str:
    providers = config.get("providers", {})
    value = providers.get(group, {}) if isinstance(providers, dict) else {}
    if not isinstance(value, dict):
        raise ConfigError(f"providers.{group} must be a mapping")
    provider_type = value.get("type", default)
    if not isinstance(provider_type, str) or not provider_type.strip():
        raise ConfigError(f"providers.{group}.type must be a non-empty string")
    return provider_type.lower().strip()
