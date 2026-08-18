from __future__ import annotations

import subprocess
import wave
from pathlib import Path
from typing import Any

from ..models import AudioArtifact, Scene
from ..render import _write_silence
from .base import ProviderError, TTSProvider


def _audio_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as handle:
                return handle.getnframes() / handle.getframerate()
        except (wave.Error, EOFError) as exc:
            raise ProviderError(f"Invalid WAV output: {path}") from exc
    ffprobe = "ffprobe"
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ProviderError(f"Could not probe audio duration: {path}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ProviderError(f"Audio duration was not numeric: {path}") from exc


class MockTTSProvider(TTSProvider):
    name = "mock"

    def synthesize_scene(self, scene: Scene, output_dir: Path) -> AudioArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"scene-{scene.index:03d}.wav"
        _write_silence(path, scene.duration)
        return AudioArtifact(str(scene.index), str(path), scene.duration, self.name, {"fallback": True, "narration": scene.narration})


class CommandTTSProvider(TTSProvider):
    name = "command"

    def __init__(self, command: list[str], *, timeout: float = 120.0, retries: int = 0):
        if not command:
            raise ProviderError("Command TTS requires a non-empty command list")
        self.command = command
        self.timeout = timeout
        self.retries = max(0, int(retries))

    def synthesize_scene(self, scene: Scene, output_dir: Path) -> AudioArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"scene-{scene.index:03d}.wav"
        command = [str(item).replace("{text}", scene.narration).replace("{output}", str(output)) for item in self.command]
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
            except subprocess.TimeoutExpired:
                last_error = f"timed out after {self.timeout:g}s"
                continue
            if result.returncode == 0 and output.is_file():
                duration = _audio_duration(output)
                return AudioArtifact(str(scene.index), str(output), duration, self.name, {"command": command[0]})
            last_error = (result.stderr or result.stdout).strip()[-500:]
        raise ProviderError(f"Command TTS failed after retries: {last_error or 'output was not created'}")
