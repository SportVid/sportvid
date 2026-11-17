"""Small fixes: boolean query flags, files of deleted videos, tracking uploads that cannot be converted."""
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.models import PluginRun, TrackingData, Video
from backend.utils import media_dir_to_file, media_path_to_file
from tests.characterization.authz.conftest import as_user, world  # noqa: F401
from tests.factories import make_user, make_video

CSV_BYTES = b"ts;sensor id;x;y\n1000;1;10;10\n"


def _results(client, **params):
    return {e["id"]: e for e in client.get("/plugin/run/result/list", params).json()["entries"]}


@pytest.mark.parametrize("value", ["false", "False", "0"])
def test_add_results_false_lists_results_without_their_data(as_user, world, value):  # noqa: F811
    """axios sends the boolean false as the string "false", which used to count as true."""
    entries = _results(as_user("alice"), video_id=world.video.id.hex, add_results=value)
    assert "data" not in entries[world.result.id.hex]


@pytest.mark.parametrize("params", [{}, {"add_results": "true"}])
def test_results_come_with_data_by_default_and_on_request(as_user, world, params):  # noqa: F811
    entries = _results(as_user("alice"), video_id=world.video.id.hex, **params)
    assert "data" in entries[world.result.id.hex]


@pytest.mark.parametrize("url", ["/plugin/run/list", "/plugin/list"])
def test_run_listings_read_the_flag_as_a_boolean(as_user, world, url, monkeypatch):  # noqa: F811
    from backend.plugin_manager import PluginManager

    monkeypatch.setattr(PluginManager, "get_results", lambda self, run: {"r": 1})
    client = as_user("alice")
    without = client.get(url, {"video_id": world.video.id.hex, "add_results": "false"}).json()["entries"]
    with_results = client.get(url, {"video_id": world.video.id.hex, "add_results": "true"}).json()["entries"]
    assert all("results" not in e for e in without)
    assert all(e["results"] == {"r": 1} for e in with_results)


def _write(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00")
    return path


def test_deleting_a_video_row_removes_everything_it_owned(db):
    """Also for deletes that don't go through video/delete: a deleted user, the admin, the shell."""
    owner = make_user()
    video = make_video(owner, ext=".tar.gz")
    files = [_write(media_path_to_file(video.id.hex, ext)) for ext in (".tar.gz", ".mp4", ".tar.gz.partial")]
    folder = media_dir_to_file(video.id.hex) + video.id.hex
    _write(os.path.join(folder, "init.mp4"))

    owner.delete()  # cascades to the video

    assert not any(os.path.exists(path) for path in files + [folder])


def test_deleting_one_video_leaves_the_files_of_others(db):
    owner = make_user()
    video, other = make_video(owner, ext=".tar.gz"), make_video(owner, ext=".tar.gz")
    _write(media_path_to_file(video.id.hex, ".tar.gz"))
    kept = _write(media_path_to_file(other.id.hex, ".tar.gz"))
    kept_folder = media_dir_to_file(other.id.hex) + other.id.hex
    _write(os.path.join(kept_folder, "init.mp4"))

    Video.objects.filter(id=video.id).delete()

    assert os.path.exists(kept) and os.path.isdir(kept_folder)


def test_a_video_without_an_extension_does_not_take_its_folder_for_a_file(db):
    video = make_video(make_user(), ext="")
    Video.objects.filter(id=video.id).delete()  # must not raise (os.remove on the HLS folder)


@pytest.fixture
def alice(db, client):
    user = make_user()
    client.force_login(user)
    return user


def _csv_files(root):
    return {os.path.join(d, f) for d, _, names in os.walk(root) for f in names if f.endswith(".csv")}


def test_tracking_upload_whose_conversion_cannot_start_leaves_nothing_behind(client, alice, settings):
    """kinexon needs the pitch size; without it posdata_convert rejects its parameters."""
    video = Video.objects.create(owner=alice, name="v", ext=".mp4")  # no field_length/field_width
    before = _csv_files(settings.MEDIA_ROOT)

    r = client.post("/tracking_data/upload", {"video_id": video.id.hex, "title": "t", "format": "kinexon",
                                              "file": SimpleUploadedFile("pos.csv", CSV_BYTES)})

    assert (r.status_code, r.json()["type"]) == (400, "validation_error")
    assert not TrackingData.objects.filter(owner=alice).exists()
    assert not PluginRun.objects.filter(video=video).exists()
    alice.refresh_from_db()
    assert alice.used_storage_size == 0
    assert _csv_files(settings.MEDIA_ROOT) == before


def test_plugin_upload_that_is_too_large_leaves_no_temp_folder(client, alice, settings, tmp_path):
    from backend.plugin_uploads import plugin_upload_root

    settings.DATA_CACHE_ROOT = f"{tmp_path}/cache/"
    video = Video.objects.create(owner=alice, name="v", ext=".mp4")
    alice.max_file_size = 10
    alice.save()

    r = client.post("/plugin/run/new", {"plugin": "object_tracker", "video_id": video.id.hex, "parameters": "{}",
                                        "file_extra": SimpleUploadedFile("big.bin", b"x" * 11)})

    assert r.status_code == 413
    assert os.listdir(plugin_upload_root()) == []
