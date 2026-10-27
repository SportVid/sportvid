"""HLS_ENCODER picks the video encoder of the HLS conversion; "auto" uses NVENC only when it works."""
import subprocess
import types

import pytest

from utils import video_converter
from tests.config.test_settings_local import LOCAL_ENV, load_settings


@pytest.fixture
def probe(monkeypatch):
    """Fake ffmpeg for the NVENC probe; records how often it ran."""
    calls = []

    def install(returncode=0, error=None):
        def run(command, **kwargs):
            calls.append(command)
            if error:
                raise error
            return types.SimpleNamespace(returncode=returncode, stderr="Cannot load libnvidia-encode.so.1")

        monkeypatch.setattr(video_converter.subprocess, "run", run)
        return calls

    video_converter.nvenc_available.cache_clear()
    yield install
    video_converter.nvenc_available.cache_clear()


def test_auto_uses_nvenc_when_the_probe_encodes(probe):
    calls = probe(returncode=0)
    assert video_converter.resolve_hls_encoder("auto") == "nvenc"
    assert "h264_nvenc" in calls[0]


@pytest.mark.parametrize("failure", [{"returncode": 1}, {"error": FileNotFoundError("ffmpeg")},
                                     {"error": subprocess.TimeoutExpired("ffmpeg", 30)}])
def test_auto_falls_back_to_libx264(probe, failure):
    probe(**failure)
    assert video_converter.resolve_hls_encoder("auto") == "x264"


def test_the_probe_runs_once_per_process(probe):
    calls = probe(returncode=0)
    for _ in range(3):
        video_converter.resolve_hls_encoder("auto")
    assert len(calls) == 1


@pytest.mark.parametrize("setting", ["nvenc", "x264", " NVENC "])
def test_explicit_encoders_skip_the_probe(probe, setting):
    calls = probe(returncode=1)
    assert video_converter.resolve_hls_encoder(setting) == setting.strip().lower()
    assert calls == []


def test_unknown_encoder_is_rejected():
    with pytest.raises(ValueError):
        video_converter.resolve_hls_encoder("vaapi")


def test_encoder_options():
    assert video_converter.hls_encoder_args("x264") == {"vcodec": "libx264", "crf": 23}
    assert video_converter.hls_encoder_args("nvenc") == {"vcodec": "h264_nvenc", "preset": "p4", "rc": "vbr", "cq": 23}


def test_settings_default_to_auto_and_reject_unknown_values():
    probe = "\nprint(json.dumps(s.HLS_ENCODER))"
    assert load_settings(LOCAL_ENV, probe).stdout.strip().splitlines()[-1] == '"auto"'
    assert load_settings({**LOCAL_ENV, "HLS_ENCODER": "x264"}, probe).stdout.strip().splitlines()[-1] == '"x264"'
    result = load_settings({**LOCAL_ENV, "HLS_ENCODER": "vaapi"}, probe)
    assert result.returncode != 0 and "HLS_ENCODER" in result.stderr
