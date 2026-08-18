from __future__ import annotations

import copy
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from ..models import MediaArtifact, Scene
from .base import MediaProvider, ProviderError


OpenCallable = Callable[[Request, float], Any]


def _default_open(request: Request, timeout: float):
    return urlopen(request, timeout=timeout)


class ComfyUIProvider(MediaProvider):
    """ComfyUI API-format provider with retryable submit/history/download steps."""

    name = "comfyui"

    def __init__(
        self,
        endpoint: str,
        workflow: str | Path | dict[str, Any],
        *,
        node_mapping: dict[str, Any] | None = None,
        timeout: float = 30.0,
        poll_interval: float = 2.0,
        retries: int = 2,
        opener: OpenCallable = _default_open,
        sleep: Callable[[float], None] = time.sleep,
        client_id: str | None = None,
    ):
        self.endpoint = endpoint.rstrip("/") + "/"
        if not self.endpoint.startswith(("http://", "https://")):
            raise ProviderError("ComfyUI endpoint must use http:// or https://")
        self.workflow = self._load_workflow(workflow)
        self.node_mapping = node_mapping or {}
        self.timeout = max(0.1, float(timeout))
        self.poll_interval = max(0.0, float(poll_interval))
        self.retries = max(0, int(retries))
        self.opener = opener
        self.sleep = sleep
        self.client_id = client_id or str(uuid.uuid4())

    @staticmethod
    def _load_workflow(workflow: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(workflow, dict):
            return copy.deepcopy(workflow)
        path = Path(workflow)
        if not path.is_file():
            raise ProviderError(f"ComfyUI workflow not found: {path}")
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Invalid ComfyUI API workflow JSON: {path}") from exc
        if not isinstance(loaded, dict):
            raise ProviderError("ComfyUI workflow must be an API-format mapping")
        return loaded

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> bytes:
        url = urljoin(self.endpoint, path.lstrip("/"))
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, self.timeout) as response:
                    return response.read()
            except Exception as exc:  # urllib errors vary by platform and transport.
                last_error = exc
                if attempt < self.retries:
                    self.sleep(min(2.0**attempt, 5.0))
        raise ProviderError(f"ComfyUI {method} {path} failed after retries: {last_error}") from last_error

    def _json_request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            loaded = json.loads(self._request(method, path, payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"ComfyUI returned invalid JSON for {path}") from exc
        if not isinstance(loaded, dict):
            raise ProviderError(f"ComfyUI returned a non-object response for {path}")
        return loaded

    def _mapped_workflow(self, scene: Scene) -> dict[str, Any]:
        workflow = copy.deepcopy(self.workflow)
        mapping = self.node_mapping

        def set_input(node_key: str, input_key: str, value: Any) -> None:
            node_id = mapping.get(node_key)
            if node_id is None:
                return
            node = workflow.get(str(node_id))
            if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
                raise ProviderError(f"ComfyUI node mapping points to missing node: {node_id}")
            node["inputs"][input_key] = value

        set_input("prompt_node", mapping.get("prompt_input", "text"), scene.visual)
        set_input("negative_prompt_node", mapping.get("negative_prompt_input", "text"), mapping.get("negative_prompt", ""))
        if "seed" in mapping:
            set_input("seed_node", mapping.get("seed_input", "seed"), mapping["seed"])
        return workflow

    @staticmethod
    def _find_file_info(history: dict[str, Any]) -> dict[str, Any] | None:
        outputs = history.get("outputs", {})
        if not isinstance(outputs, dict):
            return None
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            # Audio is owned by TTSProvider; only return renderer-supported visuals.
            for key in ("videos", "gifs", "images"):
                values = node_output.get(key, [])
                if isinstance(values, list) and values and isinstance(values[0], dict):
                    return values[0]
        return None

    def _download(self, info: dict[str, Any], output_dir: Path, scene: Scene) -> tuple[Path, str]:
        filename = str(info.get("filename", "")).strip()
        if not filename or Path(filename).name != filename:
            raise ProviderError("ComfyUI history contained an unsafe or missing filename")
        query = urlencode({"filename": filename, "subfolder": info.get("subfolder", ""), "type": info.get("type", "output")})
        response = self._request("GET", f"/view?{query}")
        suffix = Path(filename).suffix.lower() or ".bin"
        media_type = "video" if suffix in {".mp4", ".mov", ".webm", ".mkv", ".avi", ".gif"} else "image"
        path = output_dir / f"scene-{scene.index:03d}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response)
        return path, media_type

    @staticmethod
    def _video_duration(path: Path) -> float | None:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=False)
        try:
            return float(result.stdout.strip()) if result.returncode == 0 else None
        except ValueError:
            return None

    def render_scene(self, scene: Scene, output_dir: Path) -> MediaArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        state_path = output_dir / ".comfyui-state.json"
        state: dict[str, str] = {}
        if state_path.exists():
            try:
                loaded = json.loads(state_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    state = {str(key): str(value) for key, value in loaded.items()}
            except json.JSONDecodeError:
                state = {}
        scene_id = str(scene.index)
        prompt_id = state.get(scene_id)
        if not prompt_id:
            response = self._json_request("POST", "/prompt", {"prompt": self._mapped_workflow(scene), "client_id": self.client_id})
            prompt_id = str(response.get("prompt_id", ""))
            if not prompt_id:
                raise ProviderError("ComfyUI /prompt response did not include prompt_id")
            state[scene_id] = prompt_id
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

        deadline = time.monotonic() + self.timeout
        history: dict[str, Any] | None = None
        while time.monotonic() <= deadline:
            history_response = self._json_request("GET", f"/history/{prompt_id}")
            history = history_response.get(prompt_id) if isinstance(history_response.get(prompt_id), dict) else history_response
            status = history.get("status", {}) if isinstance(history, dict) else {}
            status_string = str(status.get("status_str", "")).lower() if isinstance(status, dict) else ""
            is_failed = status_string in {"error", "failed"} or (isinstance(status, dict) and status_string and status.get("completed") is False)
            if is_failed:
                raise ProviderError(f"ComfyUI job {prompt_id} failed")
            info = self._find_file_info(history or {})
            if info:
                path, asset_type = self._download(info, output_dir, scene)
                source_duration = self._video_duration(path) if asset_type == "video" else scene.duration
                state.pop(scene_id, None)
                state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
                return MediaArtifact(scene_id, asset_type, str(path), source_duration or scene.duration, self.name, {"prompt_id": prompt_id, "filename": info.get("filename"), "source_duration_probed": source_duration is not None})
            self.sleep(self.poll_interval)
        raise ProviderError(f"ComfyUI job {prompt_id} timed out after {self.timeout:g}s")
