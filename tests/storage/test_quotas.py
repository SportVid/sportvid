"""Uploads respect max_storage_size; plugin uploads respect max_file_size; usage can be recomputed."""
import json
from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from backend.models import SportVidUser, TrackingData, Video
from tests.characterization.storage.test_storage_accounting import (  # noqa: F401
    CSV_BYTES, VIDEO_BYTES, alice, upload_video, used,
)


def limit(user, max_storage=None, max_file=None):
    if max_storage is not None:
        user.max_storage_size = max_storage
    if max_file is not None:
        user.max_file_size = max_file
    user.save()


def test_video_upload_over_quota_is_rejected_before_writing(client, alice, settings, tmp_path):
    limit(alice, max_storage=len(VIDEO_BYTES) - 1)
    r = upload_video(client)
    assert (r.status_code, r.json()) == (413, {"status": "error", "type": "quota_exceeded"})
    assert not Video.objects.filter(owner=alice).exists()
    assert used(alice) == 0


def test_video_upload_up_to_the_quota_is_accepted(client, alice):
    limit(alice, max_storage=len(VIDEO_BYTES))
    assert upload_video(client).json()["status"] == "ok"
    assert upload_video(client, "w.mp4").status_code == 413  # the second one no longer fits


def test_tracking_upload_over_quota_is_rejected(client, alice):
    video = Video.objects.create(owner=alice, name="v", ext=".mp4", field_length=105.0, field_width=68.0)
    limit(alice, max_storage=len(CSV_BYTES) - 1)
    r = client.post("/tracking_data/upload", {"video_id": video.id.hex, "title": "t", "format": "kinexon",
                                              "file": SimpleUploadedFile("pos.csv", CSV_BYTES)})
    assert r.status_code == 413
    assert not TrackingData.objects.filter(owner=alice).exists()


def test_plugin_upload_is_capped_at_max_file_size(client, alice, enqueued_tasks):
    video = Video.objects.create(owner=alice, name="v", ext=".mp4")
    limit(alice, max_file=10)
    r = client.post("/plugin/run/new", {"plugin": "object_tracker", "video_id": video.id.hex, "parameters": "{}",
                                        "file_extra": SimpleUploadedFile("big.bin", b"x" * 11)})
    assert (r.status_code, r.json()["type"]) == (413, "file_too_large")
    assert enqueued_tasks == []


def test_recompute_storage_usage_dry_run_and_apply(alice):
    Video.objects.create(owner=alice, name="v", ext=".mp4", file_size=500)
    TrackingData.objects.create(owner=alice, name="t", ext=".csv", file_size=20, meta_file_size=5)
    out = StringIO()
    call_command("recompute_storage_usage", stdout=out)
    assert "alice: 0 -> 525 bytes" in out.getvalue() and used(alice) == 0
    call_command("recompute_storage_usage", apply=True, stdout=StringIO())
    assert used(alice) == 525
