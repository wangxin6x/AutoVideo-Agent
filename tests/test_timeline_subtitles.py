from pathlib import Path

import pytest

from autovideo.models import AudioArtifact, MediaArtifact, Scene
from autovideo.subtitles import write_srt
from autovideo.timeline import build_timeline, validate_timeline


def artifacts(scene_id, duration=1.0):
    return MediaArtifact(scene_id, "image", f"media-{scene_id}.ppm", duration, "test", {}), AudioArtifact(scene_id, f"audio-{scene_id}.wav", duration, "test", {})


def test_timeline_is_contiguous():
    scenes = (Scene(1, "A", "v", "a", 1), Scene(2, "B", "v", "b", 2))
    media = {"1": artifacts("1")[0], "2": artifacts("2", 2)[0]}
    audio = {"1": artifacts("1")[1], "2": artifacts("2", 2)[1]}
    entries = build_timeline(scenes, media, audio, {})
    assert entries[0].start == 0
    assert entries[0].end == entries[1].start
    assert entries[1].end == pytest.approx(3)
    assert not validate_timeline(entries)


def test_timeline_detects_gap_and_overlap():
    media1, audio1 = artifacts("1")
    media2, audio2 = artifacts("2")
    from autovideo.models import TimelineEntry

    gap = [TimelineEntry("1", 0, 1, 1, media1, audio1, None), TimelineEntry("2", 2, 3, 1, media2, audio2, None)]
    overlap = [TimelineEntry("1", 0, 2, 2, media1, audio1, None), TimelineEntry("2", 1, 2, 1, media2, audio2, None)]
    assert "gap" in validate_timeline(gap)[0]
    assert "overlap" in validate_timeline(overlap)[0]


def test_timeline_detects_invalid_duration():
    media, audio = artifacts("1")
    from autovideo.models import TimelineEntry

    assert validate_timeline([TimelineEntry("1", 0, 0, 0, media, audio, None)])


def test_srt_uses_audio_timeline(tmp_path: Path):
    scenes = (Scene(1, "A", "v", "hello", 1), Scene(2, "B", "v", "world", 1))
    media1, audio1 = artifacts("1", 1.25)
    media2, audio2 = artifacts("2", 0.75)
    from autovideo.models import TimelineEntry

    entries = [TimelineEntry("1", 0, 1.25, 1.25, media1, audio1, {"text": "hello"}), TimelineEntry("2", 1.25, 2, 0.75, media2, audio2, {"text": "world"})]
    path = write_srt(tmp_path / "subtitles.srt", scenes, entries)
    text = path.read_text(encoding="utf8")
    assert "00:00:00,000 --> 00:00:01,250" in text
    assert "00:00:01,250 --> 00:00:02,000" in text


def test_srt_skips_empty_narration(tmp_path):
    scenes = (Scene(1, "A", "v", "", 1),)
    media, audio = artifacts("1")
    from autovideo.models import TimelineEntry

    path = write_srt(tmp_path / "empty.srt", scenes, [TimelineEntry("1", 0, 1, 1, media, audio, None)])
    assert path.read_text(encoding="utf8") == ""
