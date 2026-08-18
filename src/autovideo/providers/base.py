from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import AudioArtifact, MediaArtifact, Scene


class ProviderError(RuntimeError):
    """A provider failed without exposing credentials in the message."""


class MediaProvider(ABC):
    name = "media"

    @abstractmethod
    def render_scene(self, scene: Scene, output_dir: Path) -> MediaArtifact:
        raise NotImplementedError


class TTSProvider(ABC):
    name = "tts"

    @abstractmethod
    def synthesize_scene(self, scene: Scene, output_dir: Path) -> AudioArtifact:
        raise NotImplementedError


def provider_options(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get("providers", {}).get(key, {})
    if not isinstance(value, dict):
        raise ProviderError(f"providers.{key} must be a mapping")
    return value
