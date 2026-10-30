"""video/delete deletes the row, then stops the conversion and the plugin runs, removes the files and frees the storage."""
import json
import logging
import os
import types

import pytest

from backend.models import PluginRun, Video
from backend.utils.events import cancel_channel
from tests.characterization.deletion.conftest import asset_dir, write_source
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def alice(db, client):
    user = make_user("alice", used_storage_size=1000)
    client.force_login(user)
    return user


def delete_video(client, video):
    return client.post("/video/delete", json.dumps({"id": video.id.hex}), content_type="application/json")


def revoked(enqueued_tasks):
    return [args[0] for name, args, kwargs in enqueued_tasks if name == "revoke" and kwargs == {"terminate": False}]


def test_deleting_a_converting_video_revokes_and_cancels_the_conversion(client, alice, enqueued_tasks, cancel_messages):
    video = make_video(alice, status=Video.STATUS_PROCESSING, task_id="t-conv", file_size=300)
    source = write_source(video)
    os.makedirs(asset_dir(video.id.hex))

    r = delete_video(client, video)

    assert r.json() == {"status": "ok"}
    assert not Video.objects.filter(id=video.id).exists()
    assert revoked(enqueued_tasks) == ["t-conv"]
    assert cancel_messages == [(cancel_channel("video", video.id.hex), "cancel")]
    assert not os.path.exists(source)
    assert not os.path.exists(asset_dir(video.id.hex))
    alice.refresh_from_db()
    assert alice.used_storage_size == 700


def test_deleting_a_converted_video_leaves_its_finished_task_alone(client, alice, enqueued_tasks, cancel_messages):
    """Only a PROCESSING video has a conversion to stop; revoking a finished task id only fills the workers' revoke list."""
    video = make_video(alice, status=Video.STATUS_DONE, task_id="t-done")

    delete_video(client, video)

    assert not Video.objects.filter(id=video.id).exists()
    assert revoked(enqueued_tasks) == []
    assert cancel_messages == []


@pytest.mark.parametrize("status", [PluginRun.STATUS_QUEUED, PluginRun.STATUS_WAITING, PluginRun.STATUS_RUNNING])
def test_deleting_a_video_cancels_its_active_plugin_runs(client, alice, enqueued_tasks, cancel_messages, status):
    """The runs cascade away with the video; their Celery tasks and analyser jobs are stopped too."""
    video = make_video(alice)
    run = make_run(video, status=status, task_id="t-run")
    done = make_run(video, status=PluginRun.STATUS_DONE, task_id="t-done")

    delete_video(client, video)

    assert not PluginRun.objects.filter(id__in=[run.id, done.id]).exists()
    assert revoked(enqueued_tasks) == ["t-run"]
    assert cancel_messages == [(cancel_channel("plugin_run", run.id.hex), "cancel")]


def test_the_row_is_gone_before_the_cancel_goes_out(client, alice, monkeypatch):
    """A task that subscribes after the cancel was published must find its video missing."""
    from backend.utils import events

    video = make_video(alice, status=Video.STATUS_PROCESSING, task_id="t-conv")
    run = make_run(video, status=PluginRun.STATUS_RUNNING)
    seen = []

    def publish(channel, message):
        seen.append((channel, Video.objects.filter(id=video.id).exists(), PluginRun.objects.filter(id=run.id).exists()))
    monkeypatch.setattr(events, "get_client", lambda: types.SimpleNamespace(publish=publish))

    delete_video(client, video)

    assert seen == [(cancel_channel("video", video.id.hex), False, False),
                    (cancel_channel("plugin_run", run.id.hex), False, False)]


def test_video_delete_logs_what_it_cancelled(client, alice, caplog, cancel_messages):
    video = make_video(alice, status=Video.STATUS_PROCESSING, task_id="t-conv", file_size=300)

    with caplog.at_level(logging.INFO, logger="backend"):
        delete_video(client, video)

    events = {r.msg: r.log_fields for r in caplog.records if hasattr(r, "log_fields")}
    assert events["video.conversion.cancel"] == {
        "video_id": video.id.hex, "task_id": "t-conv", "stage": "processing",
        "revoked": "true", "cancel_sent": "true", "reason": "video_delete",
    }
    assert events["video.delete"] == {"video_id": video.id.hex, "storage_released": 300, "files_removed": "true"}


def test_deleting_another_users_video_changes_nothing(client, alice, enqueued_tasks, cancel_messages):
    video = make_video(make_user("bob"), task_id="t-bob")

    r = delete_video(client, video)

    assert r.json()["type"] == "not_exist"
    assert Video.objects.filter(id=video.id).exists()
    assert revoked(enqueued_tasks) == []
    assert cancel_messages == []
