"""video/upload stores the file, creates a PROCESSING Video and enqueues the HLS conversion (T9, T17)."""
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.models import Video
from backend.utils import media_path_to_file
from tests.factories import make_user

VIDEO_BYTES = b"\x00" * 1000


@pytest.fixture
def alice(db, client):
    user = make_user("alice")
    client.force_login(user)
    return user


def upload(client, name="match.mp4", **fields):
    return client.post("/video/upload", {"file": SimpleUploadedFile(name, VIDEO_BYTES), "title": "match", **fields})


def conversions(enqueued_tasks):
    return [args[0] for name, args, _ in enqueued_tasks if name == "convert_video_to_hls"]


def test_upload_enqueues_the_hls_conversion(client, alice, enqueued_tasks):
    r = upload(client)

    assert r.json()["status"] == "ok"
    video = Video.objects.get()
    assert (video.owner, video.name, video.ext, video.status) == (alice, "match", ".mp4", Video.STATUS_PROCESSING)
    assert video.file_size == len(VIDEO_BYTES)
    assert video.task_id
    assert r.json()["entries"][0]["id"] == video.id.hex

    with open(media_path_to_file(video.id.hex, video.ext), "rb") as f:
        assert f.read() == VIDEO_BYTES
    assert conversions(enqueued_tasks) == [(video.id.hex, ".mp4", [])]


def test_upload_passes_the_requested_analysers_on(client, alice, enqueued_tasks):
    upload(client, analyser="shotdetection,thumbnail")
    [(_, _, analysers)] = conversions(enqueued_tasks)
    assert analysers == ["shotdetection", "thumbnail"]


@pytest.mark.parametrize("fields, expected", [
    ({"sport": "handball"}, (40.0, 20.0)),
    ({"sport": "unknown"}, (105.0, 68.0)),
    ({"sport": "soccer", "fieldLength": "100,5", "fieldWidth": "64"}, (100.5, 64.0)),
    ({"sport": "basketball", "fieldLength": "", "fieldWidth": "not a number"}, (28.0, 15.0)),
])
def test_field_size_defaults_to_the_sport(client, alice, fields, expected):
    upload(client, **fields)
    video = Video.objects.get()
    assert (video.field_length, video.field_width) == expected


def test_upload_rejects_other_file_types(client, alice, enqueued_tasks):
    r = upload(client, name="match.avi")

    assert r.json()["type"] == "wrong_file_extension"
    assert not Video.objects.exists()
    assert conversions(enqueued_tasks) == []
    alice.refresh_from_db()
    assert alice.used_storage_size == 0
