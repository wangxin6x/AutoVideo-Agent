from __future__ import annotations

import math
from typing import Iterable

from .models import AudioArtifact, MediaArtifact, Scene, TimelineEntry


TIMELINE_EPSILON = 1e-6


def build_timeline(
    scenes: Iterable[Scene],
    media: dict[str, MediaArtifact],
    audio: dict[str, AudioArtifact],
    subtitles: dict[str, dict],
) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    cursor = 0.0
    for scene in scenes:
        scene_id = str(scene.index)
        media_asset = media[scene_id]
        audio_asset = audio[scene_id]
        duration = audio_asset.duration if audio_asset.duration > 0 else scene.duration
        start = cursor
        end = start + duration
        subtitle = subtitles.get(scene_id)
        if subtitle is not None:
            subtitle = {**subtitle, "start": start, "end": end, "duration": duration}
        entries.append(TimelineEntry(scene_id, start, end, duration, media_asset, audio_asset, subtitle))
        cursor = end
    return entries


def validate_timeline(entries: list[TimelineEntry], epsilon: float = TIMELINE_EPSILON) -> list[str]:
    errors: list[str] = []
    expected_start = 0.0
    for index, entry in enumerate(entries, start=1):
        if entry.duration <= 0 or not math.isfinite(entry.duration):
            errors.append(f"scene {entry.scene_id}: invalid duration")
        if abs(entry.end - entry.start - entry.duration) > epsilon:
            errors.append(f"scene {entry.scene_id}: end does not equal start + duration")
        if abs(entry.start - expected_start) > epsilon:
            relation = "gap" if entry.start > expected_start else "overlap"
            errors.append(f"scene {entry.scene_id}: timeline {relation} at index {index}")
        expected_start = entry.end
    return errors
