from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .timeline import TIMELINE_EPSILON, validate_timeline


def _probe_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return None
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=False)
    try:
        return float(result.stdout.strip()) if result.returncode == 0 else None
    except ValueError:
        return None


def qa_build(build_dir: str | Path) -> dict[str, Any]:
    build = Path(build_dir)
    checks: list[dict[str, str]] = []
    warnings: list[str] = []
    failures: list[str] = []
    manifest_path = build / "manifest.json"
    report_path = build / "report.json"
    if not manifest_path.is_file():
        failures.append("manifest.json is missing")
        manifest: dict[str, Any] = {}
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append("manifest.json is invalid JSON")
            manifest = {}
        if not isinstance(manifest, dict):
            failures.append("manifest.json root must be an object")
            manifest = {}
    checks.append({"name": "manifest exists", "status": "PASS" if manifest_path.is_file() else "FAIL"})
    entries = manifest.get("timeline", [])
    if entries:
        if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
            failures.append("timeline must be a list of objects")
            checks.append({"name": "timeline continuity", "status": "FAIL"})
            entries = []
        else:
            try:
                parsed_entries = _entries_from_dict(entries)
                timeline_errors = validate_timeline(parsed_entries, TIMELINE_EPSILON)
            except (AttributeError, KeyError, TypeError, ValueError):
                timeline_errors = ["timeline contains invalid values"]
            failures.extend(timeline_errors)
            checks.append({"name": "timeline continuity", "status": "PASS" if not timeline_errors else "FAIL"})
    if entries:
        for entry in entries:
            media = _build_path(build, entry.get("media_asset", {}).get("asset_path", ""))
            audio = _build_path(build, entry.get("audio_asset", {}).get("audio_path", ""))
            if not media.is_file():
                failures.append(f"scene {entry.get('scene_id')}: media missing")
            if not audio.is_file():
                failures.append(f"scene {entry.get('scene_id')}: audio missing")
            if entry.get("subtitle") is None:
                warnings.append(f"scene {entry.get('scene_id')}: subtitle missing")
        checks.append({"name": "media and audio exist", "status": "PASS" if not any("missing" in item for item in failures) else "FAIL"})
    else:
        warnings.append("timeline is not present; this may be a v0.1 offline build")
        if not any(check["name"] == "timeline continuity" for check in checks):
            checks.append({"name": "timeline continuity", "status": "WARNING"})
    video = build / "video.mp4"
    render_data = manifest.get("render", {}) if isinstance(manifest.get("render", {}), dict) else {}
    render_status = render_data.get("status") or manifest.get("status")
    warnings.extend(str(item) for item in render_data.get("warnings", []) if item)
    if video.is_file():
        checks.append({"name": "FFmpeg output exists", "status": "PASS"})
        expected = float(manifest.get("duration", 0) or 0)
        actual = _probe_duration(video)
        if actual is None:
            warnings.append("final duration could not be probed")
        elif expected and abs(actual - expected) > 0.25:
            warnings.append(f"final duration {actual:.3f}s differs from expected {expected:.3f}s")
        checks.append({"name": "final duration", "status": "PASS" if actual is not None and (not expected or abs(actual - expected) <= 0.25) else "WARNING"})
    else:
        warnings.append("FFmpeg output is missing; offline/degraded render")
        checks.append({"name": "FFmpeg output exists", "status": "WARNING"})
    status = "FAIL" if failures else "WARNING" if warnings else "PASS"
    result = {"status": status, "checks": checks, "warnings": warnings, "failures": failures, "build_dir": str(build.resolve()), "render_status": render_status}
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def _build_path(build: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else build / path


def _entries_from_dict(values: list[dict[str, Any]]):
    from .models import AudioArtifact, MediaArtifact, TimelineEntry

    entries = []
    for value in values:
        media = value.get("media_asset", {})
        audio = value.get("audio_asset", {})
        entries.append(TimelineEntry(str(value.get("scene_id")), float(value.get("start", 0)), float(value.get("end", 0)), float(value.get("duration", 0)), MediaArtifact(str(media.get("scene_id")), str(media.get("asset_type")), str(media.get("asset_path")), float(media.get("duration", 0)), str(media.get("provider")), media.get("metadata", {})), AudioArtifact(str(audio.get("scene_id")), str(audio.get("audio_path")), float(audio.get("duration", 0)), str(audio.get("provider")), audio.get("metadata", {})), value.get("subtitle")))
    return entries
