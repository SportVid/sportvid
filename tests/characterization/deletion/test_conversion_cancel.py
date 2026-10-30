"""Characterization: what convert_video_to_hls does when its video is deleted at each stage."""
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


def scheduled_plugins(enqueued_tasks):
    return [kwargs["args"][0]["plugin"] for name, args, kwargs in enqueued_tasks if name == "run_plugin"]


def delete(video):
    Video.objects.filter(id=video.id).delete()


def test_conversion_finishes_done_and_schedules_the_thumbnail(video, conversion, enqueued_tasks):
    ffmpeg, watcher = conversion

    convert_video_to_hls(video.id.hex, video.ext)

    video.refresh_from_db()
    assert video.status == Video.STATUS_DONE
    assert video.ext == ".tar.gz"
    assert os.path.isfile(archive(video.id.hex))
    assert watcher.subscribed == [("video", video.id.hex)]
    assert scheduled_plugins(enqueued_tasks) == ["thumbnail"]


def test_video_deleted_before_the_task_starts(video, conversion):
    ffmpeg, _ = conversion
    delete(video)

    with pytest.raises(Video.DoesNotExist):
        convert_video_to_hls(video.id.hex, video.ext)
    assert ffmpeg.calls == []


def test_video_deleted_before_ffmpeg_starts_still_runs_ffmpeg(video, conversion, monkeypatch):
    """The cancel message is published before the watcher subscribes, so only the DB check stops it."""
    ffmpeg, _ = conversion
    monkeypatch.setattr(convert_video, "_metadata", lambda f: delete(video) or (25.0, 10_000.0, (1920, 1080)))

    with pytest.raises(RuntimeError, match="disappeared"):
        convert_video_to_hls(video.id.hex, video.ext)
    assert len(ffmpeg.calls) == 1
    assert ffmpeg.terminated >= 1


@pytest.mark.parametrize("cancel_message", [True, False], ids=["valkey", "db_fallback"])
def test_video_deleted_while_encoding_fails_the_task(video, conversion, enqueued_tasks, cancel_message):
    ffmpeg, watcher = conversion

    def user_deletes():
        delete(video)
        if cancel_message:
            watcher.fire()
    ffmpeg.during = user_deletes

    with pytest.raises(RuntimeError, match="disappeared"):
        convert_video_to_hls(video.id.hex, video.ext)
    assert ffmpeg.terminated >= 1
    assert not os.path.exists(archive(video.id.hex))
    assert not os.path.exists(asset_dir(video.id.hex))
    assert scheduled_plugins(enqueued_tasks) == []


def test_video_deleted_while_packing_fails_the_task(video, conversion, monkeypatch, enqueued_tasks):
    monkeypatch.setattr(convert_video, "probe_media_start", lambda path: delete(video) or 0.0)

    with pytest.raises(RuntimeError, match="disappeared"):
        convert_video_to_hls(video.id.hex, video.ext)
    assert not os.path.exists(archive(video.id.hex))
    assert not os.path.exists(asset_dir(video.id.hex))
    assert scheduled_plugins(enqueued_tasks) == []
