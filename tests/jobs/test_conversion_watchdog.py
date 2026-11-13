"""convert_video_to_hls enforces its own limits: Celery's time limits are ignored by the threads pool."""
import logging
import os
import threading
import time

import pytest

from backend.models import Video
from backend.tasks import convert_video
from backend.tasks.convert_video import ConversionTimeout, ConversionWatchdog, convert_video_to_hls
from tests.characterization.deletion.conftest import asset_dir, conversion, write_source  # noqa: F401
from tests.factories import make_user, make_video


def test_no_limit_is_exceeded_while_ffmpeg_reports_progress():
    watchdog = ConversionWatchdog(kill=lambda: None, deadline=time.monotonic() + 100, stall_timeout=60)
    assert watchdog.check() is None


def test_the_total_limit():
    start = time.monotonic()
    watchdog = ConversionWatchdog(kill=lambda: None, deadline=start + 100, stall_timeout=1000)
    assert watchdog.check(now=start + 99) is None
    assert watchdog.check(now=start + 100) == "timeout"


def test_silence_counts_from_the_last_progress_line():
    watchdog = ConversionWatchdog(kill=lambda: None, deadline=time.monotonic() + 10_000, stall_timeout=60)
    assert watchdog.check(now=time.monotonic() + 61) == "stalled"
    time.sleep(0.01)
    watchdog.touch()
    line_at = time.monotonic()
    assert watchdog.check(now=line_at + 59) is None
    assert watchdog.check(now=line_at + 61) == "stalled"


def test_the_thread_kills_once_and_records_why():
    killed = threading.Event()
    watchdog = ConversionWatchdog(kill=killed.set, deadline=time.monotonic() - 1, stall_timeout=60, interval=0.01)
    watchdog.start()
    assert killed.wait(2)
    assert watchdog.reason == "timeout"


def test_a_stopped_watchdog_kills_nothing():
    killed = threading.Event()
    watchdog = ConversionWatchdog(kill=killed.set, deadline=time.monotonic() + 0.05, stall_timeout=60, interval=0.01)
    watchdog.start()
    watchdog.stop()
    assert not killed.wait(0.2)
    assert watchdog.reason is None


def test_celery_time_limits_are_not_relied_on():
    """They would look enforced and are not (threads pool), which is how the limit went missing before."""
    assert convert_video_to_hls.time_limit is None and convert_video_to_hls.soft_time_limit is None


class _SilentFFmpeg:
    """An FFmpeg that hangs: writes nothing until it is killed, then its pipe closes."""

    def __init__(self):
        self.killed = threading.Event()
        self.stdout = self
        self.closed = False

    def readline(self):
        self.killed.wait(5)
        return ""

    def read(self):
        return ""

    def close(self):
        self.closed = True

    def poll(self):
        return -15 if self.killed.is_set() else None

    def wait(self):
        return -15


@pytest.fixture
def video(db):
    video = make_video(make_user(), status=Video.STATUS_PROCESSING, progress=0.0)
    write_source(video)
    return video


def test_a_hung_ffmpeg_is_stopped_and_the_video_ends_in_error(video, conversion, monkeypatch, settings, caplog):  # noqa: F811
    settings.HLS_STALL_TIMEOUT = 0  # any silence is too long
    proc = _SilentFFmpeg()
    monkeypatch.setattr(convert_video, "convert_to_hls", lambda *a, **k: proc)
    monkeypatch.setattr(convert_video, "terminate_process_group", lambda p: proc.killed.set())
    real = ConversionWatchdog
    monkeypatch.setattr(convert_video, "ConversionWatchdog", lambda **kw: real(interval=0.01, **kw))
    caplog.set_level(logging.INFO, logger="backend")

    with pytest.raises(ConversionTimeout):
        convert_video_to_hls(video.id.hex, video.ext)

    video.refresh_from_db()
    assert video.status == Video.STATUS_ERROR
    assert not os.path.exists(asset_dir(video.id.hex))
    [event] = [r for r in caplog.records if r.msg == "video.conversion.timeout"]
    assert event.log_fields["reason"] == "stalled"


def test_plugin_runs_wait_as_long_as_a_conversion_may_take(settings):
    from backend import plugin_manager

    assert plugin_manager.CONVERSION_MAX_RETRIES * plugin_manager.CONVERSION_POLL_SECONDS == settings.HLS_CONVERSION_TIMEOUT
