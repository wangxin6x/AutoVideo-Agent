from pathlib import Path

from autovideo.models import AudioArtifact, MediaArtifact, TimelineEntry
from autovideo.renderer_v2 import render_timeline


def entry(tmp_path: Path, asset_type: str, media_duration: float, duration: float = 1.0):
    media = tmp_path / ("source.mp4" if asset_type == "video" else "source.ppm")
    audio = tmp_path / "source.wav"
    media.write_bytes(b"media")
    audio.write_bytes(b"audio")
    return TimelineEntry("1", 0, duration, duration, MediaArtifact("1", asset_type, str(media), media_duration, "test", {}), AudioArtifact("1", str(audio), duration, "test", {}), {"text": "hello"})


def test_renderer_mixes_image_and_audio(tmp_path, monkeypatch):
    monkeypatch.setattr("autovideo.renderer_v2.shutil.which", lambda name: "ffmpeg.exe")

    def fake_run(command):
        Path(command[-1]).write_bytes(b"encoded")

    monkeypatch.setattr("autovideo.renderer_v2._run", fake_run)
    result = render_timeline([entry(tmp_path, "image", 1)], tmp_path / "build")
    assert result["status"] == "rendered"
    assert Path(result["video"]).exists()


def test_renderer_warns_for_short_video_in_trim_mode(tmp_path, monkeypatch):
    monkeypatch.setattr("autovideo.renderer_v2.shutil.which", lambda name: "ffmpeg.exe")
    monkeypatch.setattr("autovideo.renderer_v2._run", lambda command: Path(command[-1]).write_bytes(b"encoded"))
    result = render_timeline([entry(tmp_path, "video", 0.2)], tmp_path / "build", video_short_strategy="trim")
    assert any("shorter" in warning for warning in result["warnings"])


def test_renderer_loop_strategy_has_no_short_video_warning(tmp_path, monkeypatch):
    monkeypatch.setattr("autovideo.renderer_v2.shutil.which", lambda name: "ffmpeg.exe")
    monkeypatch.setattr("autovideo.renderer_v2._run", lambda command: Path(command[-1]).write_bytes(b"encoded"))
    result = render_timeline([entry(tmp_path, "video", 0.2)], tmp_path / "build", video_short_strategy="loop")
    assert result["warnings"] == []
