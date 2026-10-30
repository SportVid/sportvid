"""A stand-in FFmpeg for convert_video_to_hls: no encoder, no media, only the files and progress lines it would produce."""
import io
import os
import threading
import types
from contextlib import contextmanager

import pytest

from backend.tasks import convert_video
from backend.utils import media_dir_to_file, media_path_to_file

PROGRESS = "out_time_us=5000000\nprogress=continue\nout_time_us=10000000\nprogress=end\n"


class _Progress(io.StringIO):
    """FFmpeg's -progress pipe; calls `during` before the first line, i.e. while the task watches it encode."""

    def __init__(self, ffmpeg):
        super().__init__(PROGRESS)
        self.ffmpeg = ffmpeg

    def readline(self, *args):
        if self.ffmpeg.during is not None:
            during, self.ffmpeg.during = self.ffmpeg.during, None
            during()
        line = super().readline(*args)
        if line:
            self.ffmpeg.lines_read += 1
        return line


class FakeFFmpeg:
    """Writes a single-file fMP4 playlist like the real conversion; `during` runs while it "encodes".

    terminated_at lists how many progress lines the task had read at each kill: 0 means it was
    stopped at once, 2 means only the existence check on the first `progress=` line caught it.
    """

    def __init__(self, rc=0, during=None):
        self.rc = rc
        self.during = during
        self.calls = []
        self.lines_read = 0
        self.terminated_at = []

    def __call__(self, file_in, manifest, asynchronous=True, **args):
        self.calls.append((file_in, manifest))
        asset_dir = os.path.dirname(manifest)
        media = os.path.basename(manifest).replace(".m3u8", ".mp4")
        with open(manifest, "w") as f:
            f.write(f'#EXTM3U\n#EXT-X-MAP:URI="{media}"\n#EXTINF:5.0,\n{media}\n#EXT-X-ENDLIST\n')
        with open(os.path.join(asset_dir, media), "wb") as f:
            f.write(b"\x00" * 100)
        return types.SimpleNamespace(stdout=_Progress(self), poll=lambda: self.rc, wait=lambda: self.rc)


class FakeWatcher:
    """cancellation_watcher without Valkey: `fire()` delivers the cancel message."""

    def __init__(self):
        self.subscribed = []
        self.event = None
        self.on_cancel = None

    @contextmanager
    def __call__(self, kind, resource_id, on_cancel=None):
        self.subscribed.append((kind, resource_id))
        self.event, self.on_cancel = threading.Event(), on_cancel
        yield self.event

    def fire(self):
        self.event.set()
        if self.on_cancel is not None:
            self.on_cancel()


@pytest.fixture
def conversion(monkeypatch):
    """Patch the conversion's outside world; returns (ffmpeg, watcher) to steer it."""
    ffmpeg, watcher = FakeFFmpeg(), FakeWatcher()
    monkeypatch.setattr(convert_video, "convert_to_hls", ffmpeg)
    monkeypatch.setattr(convert_video, "cancellation_watcher", watcher)
    monkeypatch.setattr(convert_video, "_metadata", lambda file_in: (25.0, 10_000.0, (1920, 1080)))
    monkeypatch.setattr(convert_video, "resolve_hls_encoder", lambda setting: "x264")
    monkeypatch.setattr(convert_video, "probe_media_start", lambda path: 0.0)

    def terminate(proc):
        ffmpeg.terminated_at.append(ffmpeg.lines_read)
    monkeypatch.setattr(convert_video, "terminate_process_group", terminate)
    return ffmpeg, watcher


def write_source(video):
    """The uploaded original, where video/upload puts it."""
    path = media_path_to_file(video.id.hex, video.ext)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00" * 100)
    return path


def asset_dir(video_id_hex):
    return os.path.join(media_dir_to_file(video_id_hex), video_id_hex)


def archive(video_id_hex):
    return media_path_to_file(video_id_hex, ".tar.gz")
