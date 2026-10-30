"""The API side of a plugin run: plugin/run/new creates and enqueues it, plugin/run/delete cancels it.

Assertions stay on what callers observe (response body, rows, the enqueued task payload,
cancel messages), so they hold when the handlers move into a service layer (T8).
"""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from backend.models import PluginRun, TrackingData
from backend.utils.events import cancel_channel
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def alice(db, client):
    user = make_user("alice")
    client.force_login(user)
    return user


@pytest.fixture
def video(alice):
    return make_video(alice)


def new_run(client, plugin, video, parameters=None):
    body = {"plugin": plugin, "video_id": video.id.hex, "parameters": parameters or {}}
    return client.post("/plugin/run/new", json.dumps(body), content_type="application/json")


def enqueued_runs(enqueued_tasks):
    return [kwargs["args"][0] for name, _, kwargs in enqueued_tasks if name == "run_plugin"]


# plugin/run/new

def test_new_run_is_queued_and_enqueued(client, video, enqueued_tasks):
    r = new_run(client, "thumbnail", video)

    assert r.status_code == 200
    body = r.json()
    run = PluginRun.objects.get(id=body["plugin_run_id"])
    assert (run.video, run.type, run.status) == (video, "thumbnail", PluginRun.STATUS_QUEUED)
    assert body["entry"]["id"] == run.id.hex

    [payload] = enqueued_runs(enqueued_tasks)
    assert payload["plugin"] == "thumbnail"
    assert payload["plugin_run"] == str(run.id)
    assert payload["video"] == str(video.id)
    assert payload["dry_run"] is False
    # the Celery task id is kept so plugin/run/delete can revoke the queued task
    assert run.task_id


def test_new_run_stores_the_validated_parameters(client, video, enqueued_tasks):
    """Serializer defaults are filled in and recorded on the run (provenance, T15)."""
    r = new_run(client, "team_clustering", video, {"K": 3})

    run = PluginRun.objects.get(id=r.json()["plugin_run_id"])
    assert run.parameters["K"] == 3
    assert run.parameters["clustering_algo"] == "KMEANS"
    [payload] = enqueued_runs(enqueued_tasks)
    assert payload["parameters"]["K"] == 3


def test_new_run_with_an_uploaded_file(client, video, enqueued_tasks):
    r = client.post("/plugin/run/new", {
        "plugin": "thumbnail",
        "video_id": video.id.hex,
        "parameters": "{}",
        "file_positions": SimpleUploadedFile("positions.csv", b"ts;x;y\n"),
    })

    run = PluginRun.objects.get(id=r.json()["plugin_run_id"])
    # the run records the original name only; the worker gets the temporary path
    assert run.parameters["_files"] == {"positions": "positions.csv"}
    [payload] = enqueued_runs(enqueued_tasks)
    assert payload["parameters"]["_files"]["positions"]["value"] == "positions.csv"
    assert payload["parameters"]["_files"]["positions"]["path"]


def test_new_run_rejects_a_file_over_the_limit(client, alice, video, enqueued_tasks):
    alice.max_file_size = 4
    alice.save()
    r = client.post("/plugin/run/new", {
        "plugin": "thumbnail", "video_id": video.id.hex, "parameters": "{}",
        "file_positions": SimpleUploadedFile("positions.csv", b"too large"),
    })

    assert r.status_code == 413
    assert r.json()["type"] == "file_too_large"
    assert not PluginRun.objects.exists()
    assert enqueued_runs(enqueued_tasks) == []


@pytest.mark.parametrize("plugin, parameters, field", [
    ("no_such_plugin", {}, "plugin"),
    ("thumbnail", [1, 2], "parameters"),
    ("team_clustering", {"K": 1}, "K"),
])
def test_new_run_rejects_invalid_input(client, video, enqueued_tasks, plugin, parameters, field):
    r = new_run(client, plugin, video, parameters)

    assert r.status_code == 400
    assert r.json()["type"] == "validation_error"
    assert field in r.json()["errors"]
    assert not PluginRun.objects.exists()
    assert enqueued_runs(enqueued_tasks) == []


def test_new_run_rejects_a_malformed_body(client, video):
    r = client.post("/plugin/run/new", "{not json", content_type="application/json")
    assert r.status_code == 400
    assert r.json()["type"] == "wrong_request_body"


# plugin/run/delete

def delete_runs(client, ids):
    return client.post("/plugin/run/delete", json.dumps({"plugin_list": ids}), content_type="application/json")


def revoked(enqueued_tasks):
    return {args[0] for name, args, kwargs in enqueued_tasks if name == "revoke" and kwargs == {"terminate": False}}


def test_delete_cancels_active_runs(client, video, enqueued_tasks, cancel_messages):
    queued = make_run(video, status=PluginRun.STATUS_QUEUED, task_id="t-queued")
    running = make_run(video, status=PluginRun.STATUS_RUNNING, task_id="t-running")
    running_untracked = make_run(video, status=PluginRun.STATUS_RUNNING)
    done = make_run(video, status=PluginRun.STATUS_DONE, task_id="t-done")
    failed = make_run(video, status=PluginRun.STATUS_ERROR, task_id="t-failed")
    runs = [queued, running, running_untracked, done, failed]

    r = delete_runs(client, [run.id.hex for run in runs])

    assert r.json()["status"] == "ok"
    assert not PluginRun.objects.exists()
    # queued Celery tasks are revoked; running analyser jobs are told to abort
    assert revoked(enqueued_tasks) == {"t-queued", "t-running"}
    assert {channel for channel, _ in cancel_messages} == {
        cancel_channel("plugin_run", run.id.hex) for run in (queued, running, running_untracked)
    }


def test_delete_all_only_touches_own_runs(client, video, cancel_messages):
    bob_run = make_run(make_video(make_user("bob")), status=PluginRun.STATUS_RUNNING, task_id="t-bob")
    make_run(video, status=PluginRun.STATUS_DONE)

    delete_runs(client, ["all"])

    assert list(PluginRun.objects.all()) == [bob_run]
    assert cancel_messages == []


def test_delete_ignores_other_users_runs(client, video, enqueued_tasks, cancel_messages):
    bob_run = make_run(make_video(make_user("bob")), status=PluginRun.STATUS_RUNNING, task_id="t-bob")

    delete_runs(client, [bob_run.id.hex])

    assert PluginRun.objects.filter(id=bob_run.id).exists()
    assert revoked(enqueued_tasks) == set()
    assert cancel_messages == []


def test_deleting_a_conversion_removes_its_tracking_data(client, alice, video, cancel_messages):
    """posdata_convert owns the uploaded file: deleting the run deletes it, its derived runs, and frees the storage."""
    alice.used_storage_size = 1000
    alice.save()
    upload = TrackingData.objects.create(owner=alice, video=video, name="td", ext=".csv", file_size=300)
    convert = make_run(video, type="posdata_convert", status=PluginRun.STATUS_DONE, tracking_data=upload)
    kpi = make_run(video, type="kpi_computation", status=PluginRun.STATUS_DONE, tracking_data=upload)

    delete_runs(client, [convert.id.hex])

    assert not TrackingData.objects.filter(id=upload.id).exists()
    assert not PluginRun.objects.filter(id=kpi.id).exists()
    alice.refresh_from_db()
    assert alice.used_storage_size == 700


def test_uploaded_files_reach_plugins_with_a_serializer(client, video, enqueued_tasks):
    """The serializer used to drop _files, so serializer plugins never got their uploads."""
    r = client.post("/plugin/run/new", {
        "plugin": "team_clustering", "video_id": video.id.hex, "parameters": '{"K": 3}',
        "file_extra": SimpleUploadedFile("extra.csv", b"ts;x;y\n"),
    })

    run = PluginRun.objects.get(id=r.json()["plugin_run_id"])
    assert run.parameters["_files"] == {"extra": "extra.csv"}
    [payload] = enqueued_runs(enqueued_tasks)
    assert payload["parameters"]["K"] == 3
    assert payload["parameters"]["_files"]["extra"]["path"]


# admins and other users' runs (decided 2026-10-30)

def test_admin_deletes_another_users_run(client, video, enqueued_tasks, cancel_messages):
    run = make_run(video, status=PluginRun.STATUS_RUNNING, task_id="t-alice")
    client.force_login(make_user("adam", role="admin"))

    r = delete_runs(client, [run.id.hex])

    assert r.json()["status"] == "ok"
    assert not PluginRun.objects.filter(id=run.id).exists()
    assert revoked(enqueued_tasks) == {"t-alice"}
    assert cancel_messages == [(cancel_channel("plugin_run", run.id.hex), "cancel")]


def test_admin_delete_all_still_means_own_runs(client, video, cancel_messages):
    run = make_run(video, status=PluginRun.STATUS_DONE)
    client.force_login(make_user("adam", role="admin"))

    delete_runs(client, ["all"])

    assert PluginRun.objects.filter(id=run.id).exists()


def test_researcher_cannot_delete_another_users_run(client, video, cancel_messages):
    run = make_run(video, status=PluginRun.STATUS_DONE)
    client.force_login(make_user("rita", role="researcher"))

    delete_runs(client, [run.id.hex])

    assert PluginRun.objects.filter(id=run.id).exists()


def test_admin_deleting_a_conversion_frees_the_owners_storage(client, alice, video, cancel_messages):
    alice.used_storage_size = 1000
    alice.save()
    adam = make_user("adam", role="admin", used_storage_size=500)
    upload = TrackingData.objects.create(owner=alice, video=video, name="td", ext=".csv", file_size=300)
    convert = make_run(video, type="posdata_convert", status=PluginRun.STATUS_DONE, tracking_data=upload)
    client.force_login(adam)

    delete_runs(client, [convert.id.hex])

    alice.refresh_from_db()
    adam.refresh_from_db()
    assert (alice.used_storage_size, adam.used_storage_size) == (700, 500)
