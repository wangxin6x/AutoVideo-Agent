from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Scene:
    """One renderable scene from a Markdown script."""

    index: int
    title: str
    visual: str
    narration: str
    duration: float = 3.0
    color: str = "#172033"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Project:
    title: str
    scenes: tuple[Scene, ...]
    source: str

    @property
    def duration(self) -> float:
        return sum(scene.duration for scene in self.scenes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "duration": self.duration,
            "scene_count": len(self.scenes),
            "scenes": [scene.to_dict() for scene in self.scenes],
        }


@dataclass(frozen=True)
class MediaArtifact:
    """Normalized media output consumed by the renderer."""

    scene_id: str
    asset_type: str
    asset_path: str
    duration: float
    provider: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioArtifact:
    """Normalized audio output consumed by the renderer."""

    scene_id: str
    audio_path: str
    duration: float
    provider: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimelineEntry:
    scene_id: str
    start: float
    end: float
    duration: float
    media_asset: MediaArtifact
    audio_asset: AudioArtifact
    subtitle: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "media_asset": self.media_asset.to_dict(),
            "audio_asset": self.audio_asset.to_dict(),
            "subtitle": self.subtitle,
        }
