import sys
import wave
from pathlib import Path

import pytest

from autovideo.models import Scene
from autovideo.providers.base import ProviderError
from autovideo.providers.tts import CommandTTSProvider, MockTTSProvider


def test_mock_tts_uses_scene_duration(tmp_path):
    scene = Scene(1, "One", "visual", "hello", 0.15)
    artifact = MockTTSProvider().synthesize_scene(scene, tmp_path)
    assert artifact.provider == "mock"
    assert artifact.duration == pytest.approx(0.15, abs=0.001)
    assert Path(artifact.audio_path).exists()


def test_command_tts_probes_real_wav_duration(tmp_path):
    code = "import sys,wave; p=sys.argv[1]; w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\\0\\0'*800); w.close()"
    command = [sys.executable, "-c", code, "{output}"]
    artifact = CommandTTSProvider(command).synthesize_scene(Scene(1, "One", "v", "hello", 3), tmp_path)
    assert artifact.duration == pytest.approx(0.1, abs=0.01)


def test_command_tts_requires_output(tmp_path):
    with pytest.raises(ProviderError, match="output"):
        CommandTTSProvider([sys.executable, "-c", "pass", "{output}"]).synthesize_scene(Scene(1, "One", "v", "hello"), tmp_path)


def test_command_tts_template_receives_text(tmp_path):
    marker = tmp_path / "text.txt"
    code = "import sys; open(sys.argv[2],'w',encoding='utf8').write(sys.argv[1]); import wave; w=wave.open(sys.argv[3],'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\\0\\0'*80); w.close()"
    command = [sys.executable, "-c", code, "{text}", str(marker), "{output}"]
    CommandTTSProvider(command).synthesize_scene(Scene(1, "One", "v", "hello world"), tmp_path)
    assert marker.read_text(encoding="utf8") == "hello world"
