import json
from pathlib import Path

from autovideo.cli import main
from autovideo.config import load_config
from autovideo.parser import parse_script
from autovideo.pipeline import plan_project
from autovideo.qa import qa_build


def test_config_examples_are_loadable():
    offline = load_config(Path("examples/config-offline.yaml"))
    comfy = load_config(Path("examples/config-comfyui.yaml"))
    assert offline["providers"]["media"]["type"] == "placeholder"
    assert comfy["providers"]["media"]["endpoint"] == "http://127.0.0.1:8188"


def test_plan_never_calls_provider():
    plan = plan_project(parse_script("# T\n## S\n- duration: 1"), {"providers": {"media": {"type": "comfyui"}, "tts": {"type": "command"}}})
    assert plan["will_call_providers"] is False
    assert plan["providers"] == {"media": "comfyui", "tts": "command"}


def test_cli_providers(capsys):
    assert main(["providers"]) == 0
    output = capsys.readouterr().out
    assert "comfyui" in output and "command" in output


def test_qa_missing_manifest_fails(tmp_path):
    report = qa_build(tmp_path)
    assert report["status"] == "FAIL"
    assert (tmp_path / "report.json").exists()


def test_cli_qa_passes_v2_build(tmp_path, monkeypatch):
    build = tmp_path / "v2-build"
    media = build / "media"
    audio = build / "audio"
    media.mkdir(parents=True)
    audio.mkdir()
    (media / "scene-001.ppm").write_bytes(b"media")
    (audio / "scene-001.wav").write_bytes(b"audio")
    (build / "video.mp4").write_bytes(b"video")
    manifest = {
        "duration": 1.0,
        "timeline": [{
            "scene_id": "1",
            "start": 0.0,
            "end": 1.0,
            "duration": 1.0,
            "media_asset": {"scene_id": "1", "asset_type": "image", "asset_path": "media/scene-001.ppm", "duration": 1.0, "provider": "placeholder", "metadata": {}},
            "audio_asset": {"scene_id": "1", "audio_path": "audio/scene-001.wav", "duration": 1.0, "provider": "mock", "metadata": {}},
            "subtitle": {"text": "hello", "start": 0.0, "end": 1.0, "duration": 1.0},
        }],
        "render": {"status": "rendered", "warnings": []},
    }
    (build / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    monkeypatch.setattr("autovideo.qa._probe_duration", lambda path: 1.0)
    assert main(["qa", str(build)]) == 0
    report = json.loads((build / "report.json").read_text(encoding="utf8"))
    assert report["status"] == "PASS"


def test_qa_invalid_timeline_returns_fail(tmp_path):
    (tmp_path / "manifest.json").write_text('{"timeline":[{"duration":"bad"}]}', encoding="utf8")
    report = qa_build(tmp_path)
    assert report["status"] == "FAIL"
    assert any("timeline" in failure for failure in report["failures"])


def test_qa_non_object_manifest_returns_fail(tmp_path):
    (tmp_path / "manifest.json").write_text("[]", encoding="utf8")
    report = qa_build(tmp_path)
    assert report["status"] == "FAIL"
    assert "manifest.json root must be an object" in report["failures"]


def test_qa_includes_renderer_warnings(tmp_path):
    (tmp_path / "manifest.json").write_text('{"timeline":[],"render":{"warnings":["source video is shorter"]}}', encoding="utf8")
    report = qa_build(tmp_path)
    assert report["status"] == "WARNING"
    assert "source video is shorter" in report["warnings"]
