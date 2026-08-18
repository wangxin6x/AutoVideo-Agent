from __future__ import annotations

from pathlib import Path

from ..models import MediaArtifact, Scene
from ..render import _write_ppm
from .base import MediaProvider


class PlaceholderMediaProvider(MediaProvider):
    name = "placeholder"

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height

    def render_scene(self, scene: Scene, output_dir: Path) -> MediaArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"scene-{scene.index:03d}.ppm"
        _write_ppm(path, scene, self.width, self.height)
        return MediaArtifact(
            scene_id=str(scene.index),
            asset_type="image",
            asset_path=str(path),
            duration=scene.duration,
            provider=self.name,
            metadata={"deterministic": True, "visual": scene.visual},
        )
