"""Deletions that reach work the request didn't name: runs derived from a deleted upload, a video deleted mid-upload."""
import json
import types
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.models import PluginRun, TrackingData, Video
from backend.tasks import convert_video
from backend.utils.events import cancel_channel
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def alice(db, client):
    user = make_user("alice")
    client.force_login(user)
    return user


def test_runs_derived_from_a_deleted_upload_are_cancelled(client, alice, cancel_messages):
    video = make_video(alice)
    upload = TrackingData.objects.create(owner=alice, video=video, name="td", ext=".csv", file_size=10)
    convert = make_run(video, type="posdata_convert", status=PluginRun.STATUS_DONE, tracking_data=upload)
    kpi = make_run(video, type="kpi_computation", status=PluginRun.STATUS_RUNNING, tracking_data=upload)

    client.post("/plugin/run/delete", json.dumps({"plugin_list": [convert.id.hex]}), content_type="application/json")

    assert not PluginRun.objects.filter(id=kpi.id).exists()
    assert cancel_messages == [(cancel_channel("plugin_run", kpi.id.hex), "cancel")]


def test_video_deleted_while_its_upload_finishes(client, alice, monkeypatch, cancel_messages):
    """The delete lands between creating the row and storing the task id: no 500, and the quota is even."""
    def enqueue_then_delete(args, **kwargs):
        r = client.post("/video/delete", json.dumps({"id": args[0]}), content_type="application/json")
        assert r.json() == {"status": "ok"}
        return types.SimpleNamespace(id=uuid.uuid4().hex)
    monkeypatch.setattr(convert_video.convert_video_to_hls, "apply_async", enqueue_then_delete)

    r = client.post("/video/upload", {"file": SimpleUploadedFile("m.mp4", b"\x00" * 500), "title": "m"})

    assert r.json()["status"] == "ok"
    assert not Video.objects.exists()
    alice.refresh_from_db()
    assert alice.used_storage_size == 0
