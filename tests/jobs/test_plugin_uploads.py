"""Files uploaded with a plugin run reach its task and are removed when the run is over.

plugin/run/new used to write them to the backend container's /tmp, a tmpfs the Celery worker
cannot see, with a Path object in the JSON task payload, and nothing removed them.
"""
import json
import os
import time

import pytest
from celery.exceptions import Retry
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.cleanup import cleanup_upload_orphans, find_upload_orphans
from backend.models import PluginRun, SportVidUser, Video
from backend.plugin_manager import PluginManager, run_plugin
from backend.plugin_uploads import plugin_upload_root, remove_uploaded_files, uploaded_file_path
from tests.factories import make_run


@pytest.fixture
def uploads(settings, tmp_path):
    settings.DATA_CACHE_ROOT = f"{tmp_path}/cache/"
    return plugin_upload_root()


@pytest.fixture
def alice(db, client):
    user = SportVidUser.objects.create_user("alice", "a@example.org", "Correct-Horse-Battery-42")
    client.force_login(user)
    return user


@pytest.fixture
def video(alice):
    return Video.objects.create(owner=alice, name="v", ext=".mp4")


def submit(client, video, plugin="whisper", parameters=None, **files):
    # whisper has no parameter serializer, so _files reaches the task as the view built it
    return client.post("/plugin/run/new", {"plugin": plugin, "video_id": video.id.hex,
                                           "parameters": json.dumps(parameters or {}), **files})


def payload_of(enqueued_tasks):
    [args] = [kwargs["args"] for name, _, kwargs in enqueued_tasks if name == "run_plugin"]
    return args[0]


def folders(root):
    return sorted(os.listdir(root)) if os.path.isdir(root) else []


def test_the_upload_is_stored_where_the_worker_can_read_it(client, video, uploads, enqueued_tasks):
    r = submit(client, video, file_query_images=SimpleUploadedFile("me.jpg", b"jpeg bytes"))
    assert r.status_code == 200

    payload = payload_of(enqueued_tasks)
    json.dumps(payload)  # Celery's serializer gets plain JSON, no Path objects
    path = uploaded_file_path(payload["parameters"], "query_images")
    assert path.startswith(os.path.realpath(uploads))  # the shared data volume, not /tmp
    with open(path, "rb") as f:
        assert f.read() == b"jpeg bytes"
    assert PluginRun.objects.get(id=r.json()["plugin_run_id"]).parameters["_files"] == {"query_images": "me.jpg"}


def test_a_client_cannot_point_a_run_at_a_file_of_its_choice(client, video, uploads, enqueued_tasks):
    submit(client, video, parameters={"_files": {"query_images": {"value": "x", "path": "/etc/passwd"}},
                                      "query_images": "/etc/passwd"})

    parameters = payload_of(enqueued_tasks)["parameters"]
    assert parameters["_files"] == {}  # set by the view, never taken from the request
    assert uploaded_file_path(parameters, "query_images") is None


def test_paths_outside_the_upload_folder_are_neither_read_nor_removed(uploads, tmp_path):
    outside = tmp_path / "elsewhere" / "file.jpg"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    parameters = {"_files": {"q": {"value": "file.jpg", "path": str(outside)}}}

    assert uploaded_file_path(parameters, "q") is None
    remove_uploaded_files(parameters)
    assert outside.exists()


def test_a_run_that_cannot_start_removes_its_upload(client, video, uploads, enqueued_tasks, monkeypatch):
    monkeypatch.setattr(PluginManager, "__call__", lambda self, *a, **k: None)

    r = submit(client, video, file_query_images=SimpleUploadedFile("me.jpg", b"x"))

    assert r.status_code == 500
    assert folders(uploads) == []


def test_an_upload_that_is_too_large_leaves_nothing(client, alice, video, uploads, enqueued_tasks):
    alice.max_file_size = 10
    alice.save()

    r = submit(client, video, file_extra=SimpleUploadedFile("big.bin", b"x" * 11))

    assert r.status_code == 413
    assert folders(uploads) == []


def _run_with_upload(client, video, enqueued_tasks):
    submit(client, video, file_query_images=SimpleUploadedFile("me.jpg", b"jpeg bytes"))
    payload = payload_of(enqueued_tasks)
    return payload, PluginRun.objects.get(id=payload["plugin_run"])


def test_the_task_reads_the_upload_and_the_folder_goes_when_it_is_done(
        client, video, uploads, enqueued_tasks, register_plugin):
    read = []

    def call(self, parameters=None, **kwargs):
        with open(uploaded_file_path(parameters, "query_images"), "rb") as f:
            read.append(f.read())
        return {}
    register_plugin("whisper", call)
    payload, run = _run_with_upload(client, video, enqueued_tasks)

    run_plugin(payload)

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_DONE and read == [b"jpeg bytes"]
    assert folders(uploads) == []


def test_the_folder_goes_when_the_run_fails(client, video, uploads, enqueued_tasks, register_plugin):
    def call(self, **kwargs):
        raise RuntimeError("model crashed")
    register_plugin("whisper", call)
    payload, run = _run_with_upload(client, video, enqueued_tasks)

    run_plugin(payload)

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    assert folders(uploads) == []


def test_the_folder_stays_while_the_task_waits_to_retry(client, video, uploads, enqueued_tasks, register_plugin):
    """Waiting for a dependency (or the conversion) retries the same task with the same files."""
    register_plugin("whisper", lambda self, **kwargs: {})
    payload, run = _run_with_upload(client, video, enqueued_tasks)
    tracker = make_run(video, type="object_tracker", status=PluginRun.STATUS_RUNNING)
    payload["parameters"]["object_tracker_id"] = tracker.id.hex

    with pytest.raises(Retry):
        run_plugin(payload)
    assert len(folders(uploads)) == 1

    PluginRun.objects.filter(id=tracker.id).update(status=PluginRun.STATUS_DONE)
    run_plugin(payload)
    assert folders(uploads) == []


def test_leftovers_of_a_crashed_worker_are_swept(uploads, settings):
    settings.ORPHAN_CLEANUP_DELETE = True
    settings.PLUGIN_RUN_TIMEOUT = 12 * 3600
    settings.ORPHAN_CLEANUP_MIN_AGE = 24 * 3600
    os.makedirs(uploads)
    old, young = os.path.join(uploads, "run-old"), os.path.join(uploads, "run-young")
    for folder in (old, young):
        os.makedirs(folder)
        with open(os.path.join(folder, "f.jpg"), "wb") as f:
            f.write(b"\x00" * 10)
    then = time.time() - 2 * 24 * 3600
    os.utime(old, (then, then))

    assert [str(p) for p, _ in find_upload_orphans()] == [old]
    assert cleanup_upload_orphans() == (1, 10)
    assert folders(uploads) == ["run-young"]


def test_uploads_are_kept_at_least_as_long_as_a_run_may_take(uploads, settings):
    settings.PLUGIN_RUN_TIMEOUT = 12 * 3600
    os.makedirs(os.path.join(uploads, "run-a"))
    then = time.time() - 11 * 3600
    os.utime(os.path.join(uploads, "run-a"), (then, then))

    assert find_upload_orphans(min_age_seconds=60) == []
