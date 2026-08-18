from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import TimelineEntry


class RenderError(RuntimeError):
    """Raised when a normalized timeline cannot be rendered."""


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RenderError(detail[-1] if detail else f"FFmpeg exited with code {result.returncode}")


def render_timeline(
    entries: list[TimelineEntry],
    output_dir: str | Path,
    *,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    video_short_strategy: str = "trim",
) -> dict:
    """Render normalized image/video + audio scenes into one MP4."""

    ffmpeg = shutil.which("ffmpeg")
    output = Path(output_dir)
    segments = output / "segments"
    segments.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    if not ffmpeg:
        return {"status": "degraded", "video": None, "ffmpeg": None, "warnings": ["FFmpeg was not found"]}
    if video_short_strategy not in {"trim", "loop"}:
        raise ValueError("video_short_strategy must be trim or loop")

    segment_paths: list[Path] = []
    for entry in entries:
        media = Path(entry.media_asset.asset_path)
        audio = Path(entry.audio_asset.audio_path)
        if not media.is_file():
            raise RenderError(f"missing media asset: {media}")
        if not audio.is_file():
            raise RenderError(f"missing audio asset: {audio}")
        segment = segments / f"scene-{entry.scene_id}.mp4"
        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        if entry.media_asset.asset_type == "video":
            input_flags = ["-stream_loop", "-1"] if video_short_strategy == "loop" else []
            video_filter = scale_filter
            if video_short_strategy == "trim" and entry.media_asset.metadata.get("source_duration_probed") is False:
                warnings.append(f"scene {entry.scene_id}: source video duration could not be probed")
            if video_short_strategy == "trim" and entry.media_asset.duration < entry.duration - 1e-6:
                warnings.append(f"scene {entry.scene_id}: source video is shorter than scene; padded with black frames")
                video_filter += f",tpad=stop_mode=add:stop_duration={entry.duration:.6f}"
            command = [ffmpeg, "-y", *input_flags, "-i", str(media), "-i", str(audio), "-t", f"{entry.duration:.6f}", "-vf", video_filter, "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(segment)]
        else:
            command = [ffmpeg, "-y", "-loop", "1", "-i", str(media), "-i", str(audio), "-t", f"{entry.duration:.6f}", "-vf", scale_filter, "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(segment)]
        _run(command)
        segment_paths.append(segment)

    concat = output / "segments.txt"
    concat.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in segment_paths) + "\n", encoding="utf-8")
    video = output / "video.mp4"
    _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(video)])
    return {"status": "rendered", "video": str(video), "ffmpeg": ffmpeg, "warnings": warnings}
