from __future__ import annotations

from pathlib import Path

from .models import Scene, TimelineEntry


def _timestamp(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: str | Path, scenes: tuple[Scene, ...], entries: list[TimelineEntry]) -> Path:
    output = Path(path)
    lines: list[str] = []
    scene_by_id = {str(scene.index): scene for scene in scenes}
    number = 1
    for entry in entries:
        text = scene_by_id[entry.scene_id].narration.strip()
        if not text:
            continue
        lines.extend([str(number), f"{_timestamp(entry.start)} --> {_timestamp(entry.end)}", text, ""])
        number += 1
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
