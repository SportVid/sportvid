"""What convert_video_to_hls does when its video is deleted at each stage.

A deleted video is a cancellation, not a failure: the task removes what it wrote, logs
video.conversion.cancelled with the stage that noticed it, and logs nothing at ERROR.
"""
import logging
import os

import pytest

from backend.models import Video
from backend.tasks import convert_video
from backend.tasks.convert_video import convert_video_to_hls
from tests.characterization.deletion.conftest import archive, asset_dir, write_source
from tests.factories import make_user, make_video


@pytest.fixture
def video(db):
    video = make_video(make_user(), status=Video.STATUS_PROCESSING, progress=0.0)
    write_source(video)
    os.makedirs(asset_dir(video.id.hex), exist_ok=True)
    return video


@pytest.fixture
def log(caplog):
    caplog.set_level(logging.DEBUG, logger="backend")
    return caplog


def scheduled_plugins(enqueued_tasks):
    return [kwargs["args"][0]["plugin"] for name, args, kwargs in enqueued_tasks if name == "run_plugin"]


def cancelled_sources(log):
    return [r.log_fields["source"] for r in log.records if r.msg == "video.conversion.cancelled"]


def errors(log):
    return [r for r in log.records if r.levelno >= logging.ERROR]


def delete(video):
    Video.objects.filter(id=video.id).delete()


def assert_cleaned_up(video, enqueued_tasks):
    assert not os.path.exists(archive(video.id.hex))
    assert not os.path.exists(asset_dir(video.id.hex))
    assert scheduled_plugins(enqueued_tasks) == []


def test_conversion_finishes_done_and_schedules_the_thumbnail(video, conversion, enqueued_tasks, log):
    ffmpeg, watcher = conversion

    convert_video_to_hls(video.id.hex, video.ext)

    video.refresh_from_db()
    assert video.status == Video.STATUS_DONE
    assert video.ext == ".tar.gz"
    assert os.path.isfile(archive(video.id.hex))
    assert watcher.subscribed == [("video", video.id.hex)]
    assert scheduled_plugins(enqueued_tasks) == ["thumbnail", "camera_motion_classification"]
    assert cancelled_sources(log) == []


def test_conversion_lines_carry_the_video_id(video, conversion, log_lines):
    delete(video)
    convert_video_to_hls(video.id.hex, video.ext)

    assert f"INFO video.conversion.cancelled video_id={video.id.hex} source=deleted_before_start" in log_lines()


def test_video_deleted_before_the_task_starts(video, conversion, enqueued_tasks, log):
    ffmpeg, _ = conversion
    delete(video)

    assert convert_video_to_hls(video.id.hex, video.ext) is None
    assert ffmpeg.calls == []
    assert cancelled_sources(log) == ["deleted_before_start"]
    assert errors(log) == []


def test_cancel_before_ffmpeg_starts_stops_it_at_once(video, conversion, monkeypatch, enqueued_tasks, log):
    """The watcher subscribes first, so a cancel while reading the metadata is kept for the FFmpeg that follows."""
    ffmpeg, watcher = conversion

    def user_deletes(file_in):
        delete(video)
        watcher.fire()  # on_cancel finds no process yet
        return 25.0, 10_000.0, (1920, 1080)
    monkeypatch.setattr(convert_video, "_metadata", user_deletes)

    assert convert_video_to_hls(video.id.hex, video.ext) is None
    assert ffmpeg.terminated_at[0] == 0  # right after it started, not by the existence check
    assert cancelled_sources(log) == ["valkey"]
    assert errors(log) == []
    assert_cleaned_up(video, enqueued_tasks)


@pytest.mark.parametrize("cancel_message, killed_after", [(True, 0), (False, 2)], ids=["valkey", "db_fallback"])
def test_video_deleted_while_encoding(video, conversion, enqueued_tasks, log, cancel_message, killed_after):
    """The cancel message kills FFmpeg at once; without it the existence check on `progress=` does."""
    ffmpeg, watcher = conversion

    def user_deletes():
        delete(video)
        if cancel_message:
            watcher.fire()
    ffmpeg.during = user_deletes

    assert convert_video_to_hls(video.id.hex, video.ext) is None
    assert ffmpeg.terminated_at[0] == killed_after
    assert cancelled_sources(log) == ["valkey" if cancel_message else "db_fallback"]
    assert errors(log) == []
    assert_cleaned_up(video, enqueued_tasks)


def test_video_deleted_while_packing(video, conversion, monkeypatch, enqueued_tasks, log):
    monkeypatch.setattr(convert_video, "probe_media_start", lambda path: delete(video) or 0.0)

    assert convert_video_to_hls(video.id.hex, video.ext) is None
    assert cancelled_sources(log) == ["deleted_while_packing"]
    assert errors(log) == []
    assert_cleaned_up(video, enqueued_tasks)


def test_files_removed_under_the_task_count_as_cancelled(video, conversion, monkeypatch, enqueued_tasks, log):
    """video/delete removes the files while the task reads them; the task's error is the deletion's doing."""
    def files_gone(path):
        delete(video)
        raise FileNotFoundError(path)
    monkeypatch.setattr(convert_video, "probe_media_start", files_gone)

    assert convert_video_to_hls(video.id.hex, video.ext) is None
    assert cancelled_sources(log) == ["deleted"]
    assert errors(log) == []
    assert_cleaned_up(video, enqueued_tasks)


def test_a_real_failure_still_fails(video, conversion, monkeypatch, log):
    monkeypatch.setattr(convert_video, "probe_media_start", lambda path: 5.0)

    with pytest.raises(RuntimeError, match="out of sync"):
        convert_video_to_hls(video.id.hex, video.ext)
    video.refresh_from_db()
    assert video.status == Video.STATUS_ERROR
    assert [r.getMessage() for r in errors(log)] == [f"Video conversion failed: {video.id.hex}"]
