from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import Project, Scene


class ScriptParseError(ValueError):
    """Raised when a Markdown script cannot become a valid project."""

_MAX_SCRIPT_LEN = 500_000
_MAX_SCENES = 200


_FIELD_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?([A-Za-z][\w -]*)(?:\*\*)?\s*:\s*(.*?)\s*$")
_SCENE_RE = re.compile(r"^##\s+(?:Scene\s*\d*\s*[:.-]?\s*)?(.*?)\s*$", re.IGNORECASE)


def _color_for(index: int, title: str) -> str:
    digest = hashlib.sha256(f"{index}:{title}".encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"


def _parse_duration(value: str, scene_number: int) -> float:
    try:
        duration = float(value.rstrip("sS").strip())
    except ValueError as exc:
        raise ScriptParseError(f"Scene {scene_number}: duration must be a number") from exc
    if duration <= 0:
        raise ScriptParseError(f"Scene {scene_number}: duration must be greater than zero")
    if duration > 3600:
        raise ScriptParseError(f"Scene {scene_number}: duration cannot exceed one hour")
    return duration


def parse_script(text: str, source: str = "<string>") -> Project:
    """Parse a small, human-friendly Markdown storyboard format.

    A scene starts at a level-two heading. Fields can be bullets or plain lines,
    for example ``- visual: a city at night`` and ``narration: ...``.
    """

    if len(text) > _MAX_SCRIPT_LEN:
        raise ScriptParseError(f"Script exceeds maximum length of {_MAX_SCRIPT_LEN} characters")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    title = "Untitled video"
    scenes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip() or title
            continue
        heading = _SCENE_RE.match(stripped)
        if heading:
            if current is not None:
                scenes.append(current)
            heading_title = heading.group(1).strip()
            current = {"title": heading_title or f"Scene {len(scenes) + 1}"}
            continue
        field = _FIELD_RE.match(stripped)
        if field and current is not None:
            key = re.sub(r"\s+", "_", field.group(1).lower())
            current[key] = field.group(2).strip()
        elif current is not None and "narration" not in current:
            current["narration"] = stripped
    if current is not None:
        scenes.append(current)
    if not scenes:
        raise ScriptParseError(f"{source}: no scenes found; add at least one '## Scene' heading")
    if len(scenes) > _MAX_SCENES:
        raise ScriptParseError(f"Script has {len(scenes)} scenes, exceeding maximum of {_MAX_SCENES}")

    parsed: list[Scene] = []
    for index, raw in enumerate(scenes, start=1):
        scene_title = raw.get("title", f"Scene {index}").strip() or f"Scene {index}"
        visual = raw.get("visual", raw.get("prompt", "")).strip()
        if not visual:
            raise ScriptParseError(f"Scene {index} '{scene_title}': missing 'visual' field")
        narration = raw.get("narration", "").strip()
        duration = _parse_duration(raw.get("duration", "3"), index)
        parsed.append(Scene(index, scene_title, visual, narration, duration, _color_for(index, scene_title)))
    return Project(title=title, scenes=tuple(parsed), source=source)


def parse_script_file(path: str | Path) -> Project:
    script_path = Path(path)
    if not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")
    return parse_script(script_path.read_text(encoding="utf-8"), str(script_path))
