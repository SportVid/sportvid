"""Characterization: video/delete cancels the conversion, deletes the row and files, and frees the storage."""
import json
import os

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


def test_deleting_a_converted_video_still_revokes_its_finished_task(client, alice, enqueued_tasks, cancel_messages):
    video = make_video(alice, status=Video.STATUS_DONE, task_id="t-done")

    delete_video(client, video)

    assert revoked(enqueued_tasks) == ["t-done"]
    assert cancel_messages == [(cancel_channel("video", video.id.hex), "cancel")]


def test_deleting_a_video_does_not_cancel_its_plugin_runs(client, alice, enqueued_tasks, cancel_messages):
    """The runs cascade away, but their Celery tasks and analyser jobs are left running."""
    video = make_video(alice)
    run = make_run(video, status=PluginRun.STATUS_RUNNING, task_id="t-run")

    delete_video(client, video)

    assert not PluginRun.objects.filter(id=run.id).exists()
    assert "t-run" not in revoked(enqueued_tasks)
    assert cancel_channel("plugin_run", run.id.hex) not in {channel for channel, _ in cancel_messages}


def test_deleting_another_users_video_changes_nothing(client, alice, enqueued_tasks, cancel_messages):
    video = make_video(make_user("bob"), task_id="t-bob")

    r = delete_video(client, video)

    assert r.json()["type"] == "not_exist"
    assert Video.objects.filter(id=video.id).exists()
    assert revoked(enqueued_tasks) == []
    assert cancel_messages == []
