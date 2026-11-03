"""Characterization: uploads add to used_storage_size and deletes release it."""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.models import SportVidUser, TrackingData, Video

VIDEO_BYTES = b"\x00" * 3000
CSV_BYTES = b"ts;sensor id;x;y\n1000;1;10;10\n"


@pytest.fixture
def alice(db, client):
    user = SportVidUser.objects.create_user("alice", "a@example.org", "Correct-Horse-Battery-42")
    client.force_login(user)
    return user


def used(user):
    user.refresh_from_db()
    return user.used_storage_size


def upload_video(client, name="v.mp4", data=VIDEO_BYTES):
    return client.post("/video/upload", {"file": SimpleUploadedFile(name, data), "title": "v"})


def test_video_upload_and_delete(client, alice):
    r = upload_video(client)
    assert r.json()["status"] == "ok"
    assert used(alice) == len(VIDEO_BYTES)
    video = Video.objects.get(owner=alice)
    r = client.post("/video/delete", json.dumps({"id": video.id.hex}), content_type="application/json")
    assert r.json()["status"] == "ok"
    assert used(alice) == 0


def test_tracking_data_upload_and_delete(client, alice):
    video = Video.objects.create(owner=alice, name="v", ext=".mp4", field_length=105.0, field_width=68.0)
    client.post("/tracking_data/upload", {"video_id": video.id.hex, "title": "t", "format": "kinexon",
                                          "file": SimpleUploadedFile("pos.csv", CSV_BYTES)})
    assert used(alice) == len(CSV_BYTES)
    td = TrackingData.objects.get(owner=alice)
    client.post("/tracking_data/delete", json.dumps({"id": td.id.hex}), content_type="application/json")
    assert used(alice) == 0
