from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Project
from .providers import CommandTTSProvider, ComfyUIProvider, MockTTSProvider, PlaceholderMediaProvider, ProviderError
from .qa import qa_build
from .renderer_v2 import RenderError, render_timeline
from .subtitles import write_srt
from .timeline import build_timeline


def _provider_config(config: dict[str, Any], group: str) -> dict[str, Any]:
    providers = config.get("providers", {})
    value = providers.get(group, config.get(group, {})) if isinstance(providers, dict) else config.get(group, {})
    if not isinstance(value, dict):
        raise ProviderError(f"providers.{group} must be a mapping")
    return value


def create_providers(config: dict[str, Any], *, config_dir: Path, width: int, height: int):
    media_cfg = _provider_config(config, "media")
    media_type = str(media_cfg.get("type", "placeholder")).lower()
    if media_type == "placeholder":
        media = PlaceholderMediaProvider(width, height)
    elif media_type == "comfyui":
        workflow = media_cfg.get("workflow")
        if not workflow:
            raise ProviderError("providers.media.workflow is required for comfyui")
        workflow_path = Path(workflow)
        if not workflow_path.is_absolute():
            workflow_path = config_dir / workflow_path
        media = ComfyUIProvider(str(media_cfg.get("endpoint", "http://127.0.0.1:8188")), workflow_path, node_mapping=media_cfg.get("node_mapping"), timeout=float(media_cfg.get("timeout", 120)), poll_interval=float(media_cfg.get("poll_interval", 2)), retries=int(media_cfg.get("retries", 2)))
    else:
        raise ProviderError(f"Unsupported media provider: {media_type}")

    tts_cfg = _provider_config(config, "tts")
    tts_type = str(tts_cfg.get("type", "mock")).lower()
    if tts_type == "mock":
        tts = MockTTSProvider()
    elif tts_type == "command":
        command = tts_cfg.get("command")
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ProviderError("providers.tts.command must be a list of strings")
        tts = CommandTTSProvider(command, timeout=float(tts_cfg.get("timeout", 120)), retries=int(tts_cfg.get("retries", 0)))
    else:
        raise ProviderError(f"Unsupported TTS provider: {tts_type}")
    return media, tts


def plan_project(project: Project, config: dict[str, Any]) -> dict[str, Any]:
    media = _provider_config(config, "media")
    tts = _provider_config(config, "tts")
    return {"title": project.title, "scene_count": len(project.scenes), "duration_fallback": project.duration, "providers": {"media": media.get("type", "placeholder"), "tts": tts.get("type", "mock")}, "will_call_providers": False, "scenes": [{"scene_id": str(scene.index), "title": scene.title, "duration_fallback": scene.duration} for scene in project.scenes]}


def build_with_providers(project: Project, config: dict[str, Any], output_dir: str | Path, *, config_dir: Path) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    render_cfg = config.get("render", {}) if isinstance(config.get("render", {}), dict) else {}
    width, height = int(render_cfg.get("width", 1280)), int(render_cfg.get("height", 720))
    media_provider, tts_provider = create_providers(config, config_dir=config_dir, width=width, height=height)
    media_dir, audio_dir = output / "media", output / "audio"
    media = {}
    audio = {}
    try:
        for scene in project.scenes:
            media[str(scene.index)] = media_provider.render_scene(scene, media_dir)
            audio[str(scene.index)] = tts_provider.synthesize_scene(scene, audio_dir)
    except (ProviderError, OSError) as exc:
        failure = {"status": "FAIL", "stage": "provider", "error": str(exc), "output_dir": str(output)}
        (output / "report.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        raise
    subtitles = {str(scene.index): {"text": scene.narration} for scene in project.scenes}
    entries = build_timeline(project.scenes, media, audio, subtitles)
    subtitle_path = write_srt(output / "subtitles.srt", project.scenes, entries)
    manifest = {"autovideo_version": "0.2.0", "title": project.title, "source": project.source, "duration": entries[-1].end if entries else 0, "scene_count": len(entries), "timeline": [entry.to_dict() for entry in entries], "subtitle_file": str(subtitle_path)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        render_result = render_timeline(entries, output, width=width, height=height, fps=int(render_cfg.get("fps", 30)), video_short_strategy=str(render_cfg.get("video_short_strategy", "trim")))
    except RenderError as exc:
        failure = {"status": "FAIL", "stage": "renderer", "error": str(exc), "output_dir": str(output)}
        (output / "report.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        raise
    manifest["render"] = render_result
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return qa_build(output)
