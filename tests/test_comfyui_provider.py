import json
from pathlib import Path

import pytest

from autovideo.models import Scene
from autovideo.providers.comfyui import ComfyUIProvider
from autovideo.providers.base import ProviderError


class Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def scene():
    return Scene(1, "One", "a prompt", "say this", 0.2, "#112233")


def provider(tmp_path, opener, **kwargs):
    workflow = {"6": {"inputs": {"text": "old"}}, "7": {"inputs": {"text": "old negative"}}, "3": {"inputs": {"seed": 1}}}
    return ComfyUIProvider("http://127.0.0.1:8188", workflow, node_mapping={"prompt_node": "6", "negative_prompt_node": "7", "seed_node": "3", "seed": 42}, opener=opener, poll_interval=0, **kwargs)


def test_comfyui_submit_poll_and_download(tmp_path):
    calls = []

    def opener(request, timeout):
        calls.append((request.method, request.full_url, json.loads(request.data) if request.data else None))
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-1"}')
        if "/history/job-1" in request.full_url:
            return Response(b'{"job-1":{"status":{"status_str":"success"},"outputs":{"9":{"images":[{"filename":"result.png","subfolder":"","type":"output"}]}}}}')
        return Response(b"PNG")

    artifact = provider(tmp_path, opener).render_scene(scene(), tmp_path / "media")
    assert artifact.asset_type == "image"
    assert Path(artifact.asset_path).read_bytes() == b"PNG"
    assert calls[0][0] == "POST"
    assert calls[0][2]["prompt"]["6"]["inputs"]["text"] == "a prompt"


def test_comfyui_video_output_is_normalized(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-2"}')
        if "/history/job-2" in request.full_url:
            return Response(b'{"job-2":{"outputs":{"9":{"videos":[{"filename":"clip.mp4"}]}}}}')
        return Response(b"MP4")

    artifact = provider(tmp_path, opener).render_scene(scene(), tmp_path / "media")
    assert artifact.asset_type == "video"
    assert artifact.asset_path.endswith(".mp4")


def test_comfyui_skips_audio_before_visual_output(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-mixed"}')
        if "/history/job-mixed" in request.full_url:
            return Response(b'{"job-mixed":{"outputs":{"9":{"audio":[{"filename":"voice.wav"}],"images":[{"filename":"visual.png"}]}}}}')
        return Response(b"PNG")

    artifact = provider(tmp_path, opener).render_scene(scene(), tmp_path / "media")
    assert artifact.asset_type == "image"
    assert artifact.metadata["filename"] == "visual.png"


def test_comfyui_audio_only_output_is_treated_as_missing(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-audio"}')
        return Response(b'{"job-audio":{"outputs":{"9":{"audio":[{"filename":"voice.wav"}]}}}}')

    with pytest.raises(ProviderError, match="timed out"):
        provider(tmp_path, opener, timeout=0.01).render_scene(scene(), tmp_path / "media")


def test_comfyui_retries_transient_transport_error(tmp_path):
    attempts = {"count": 0}

    def opener(request, timeout):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("temporary")
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-3"}')
        if "/history/job-3" in request.full_url:
            return Response(b'{"job-3":{"outputs":{"9":{"images":[{"filename":"ok.png"}]}}}}')
        return Response(b"OK")

    artifact = provider(tmp_path, opener, retries=1).render_scene(scene(), tmp_path / "media")
    assert artifact.provider == "comfyui"
    assert attempts["count"] >= 2


def test_comfyui_failure_status_is_reported(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-fail"}')
        return Response(b'{"job-fail":{"status":{"status_str":"error"}}}')

    with pytest.raises(ProviderError, match="failed"):
        provider(tmp_path, opener).render_scene(scene(), tmp_path / "media")


def test_comfyui_missing_output_times_out(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-empty"}')
        return Response(b'{"job-empty":{"status":{"status_str":"success"},"outputs":{}}}')

    with pytest.raises(ProviderError, match="timed out"):
        provider(tmp_path, opener, timeout=0.01).render_scene(scene(), tmp_path / "media")


def test_comfyui_resume_uses_saved_prompt_id(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / ".comfyui-state.json").write_text('{"1":"saved-job"}', encoding="utf-8")
    calls = []

    def opener(request, timeout):
        calls.append(request.method + " " + request.full_url)
        if "/history/saved-job" in request.full_url:
            return Response(b'{"saved-job":{"outputs":{"9":{"images":[{"filename":"resume.png"}]}}}}')
        return Response(b"RESUMED")

    artifact = provider(tmp_path, opener).render_scene(scene(), media_dir)
    assert artifact.asset_path.endswith("scene-001.png")
    assert artifact.metadata["filename"] == "resume.png"
    assert not any(item.endswith("/prompt") for item in calls)


def test_comfyui_rejects_unsafe_filename(tmp_path):
    def opener(request, timeout):
        if request.full_url.endswith("/prompt"):
            return Response(b'{"prompt_id":"job-safe"}')
        if "/history/job-safe" in request.full_url:
            return Response(b'{"job-safe":{"outputs":{"9":{"images":[{"filename":"../secret.png"}]}}}}')
        return Response(b"bad")

    with pytest.raises(ProviderError, match="unsafe"):
        provider(tmp_path, opener).render_scene(scene(), tmp_path / "media")
