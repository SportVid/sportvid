"""B2: object IDs from a request are resolved through the owner (backend/permissions.py).

For every endpoint that takes an object ID, a request against alice's objects by
another user, by an anonymous client, or (for writes) by a researcher must change
nothing and must not reveal any of alice's object IDs.
"""
import json

import pytest

from backend.models import PluginRun
from tests.characterization.authz.conftest import db_fingerprint
from tests.characterization.authz.endpoints import ENDPOINTS


def _assert_denied(endpoint, client, world):
    before = db_fingerprint()
    response, request_data = endpoint.call(client, world)
    assert db_fingerprint() == before, f"{endpoint.path} changed the database"

    body = response.content.decode(errors="replace")
    requested = json.dumps(request_data)
    leaked = {i for i in world.alice_ids if i in body and i not in requested}
    assert not leaked, f"{endpoint.path} leaked {leaked}"
    return response


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: e.id)
def test_other_user_is_denied(endpoint, as_user, world):
    _assert_denied(endpoint, as_user("bob"), world)


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: e.id)
def test_anonymous_is_denied(endpoint, as_user, world):
    _assert_denied(endpoint, as_user(None), world)


@pytest.mark.parametrize("endpoint", [e for e in ENDPOINTS if e.kind == "write"], ids=lambda e: e.id)
def test_researcher_cannot_write_other_users_objects(endpoint, as_user, world):
    client = as_user("rita")  # log in first: force_login itself updates last_login
    before = db_fingerprint()
    endpoint.call(client, world)
    assert db_fingerprint() == before, f"{endpoint.path} changed the database"


def test_plugin_list_without_video_lists_only_own_runs(as_user, world):
    response = as_user("bob").get("/plugin/list")
    assert response.json()["status"] == "ok"
    assert world.plugin_run.id.hex not in response.content.decode()


def test_plugin_run_result_list_without_filter_lists_only_own_results(as_user, world):
    response = as_user("bob").get("/plugin/run/result/list")
    assert world.result.id.hex not in response.content.decode()


def test_timeline_list_without_video_lists_only_own_timelines(as_user, world):
    response = as_user("bob").get("/timeline/list")
    assert world.timeline.id.hex not in response.content.decode()


# ---------- IDs inside plugin parameters
def _run(client, video, plugin, parameters):
    return client.post(
        "/plugin/run/new",
        json.dumps({"plugin": plugin, "video_id": video.id.hex, "parameters": parameters}),
        content_type="application/json",
    )


@pytest.mark.parametrize("plugin, parameters", [
    ("kpi_computation", lambda w: {"format": "dfl", "tracking_data_id": w.tracking_data.id.hex}),
    ("posdata_convert", lambda w: {"tracking_data_id": w.tracking_data.id.hex}),
    ("osnet_reid", lambda w: {"object_tracker_id": w.plugin_run.id.hex}),
    ("team_clustering", lambda w: {"object_tracker_id": w.plugin_run.id.hex}),
    ("calibration_static_dlt", lambda w: {"calibration_id": w.calibration.id.hex}),
    ("invert_scalar", lambda w: {"scalar_timeline_id": w.timeline.id.hex}),
])
def test_plugin_parameters_cannot_reference_other_users_objects(as_user, world, enqueued_tasks, plugin, parameters):
    runs_before = PluginRun.objects.count()
    response = _run(as_user("bob"), world.bob_video, plugin, parameters(world))
    assert response.json()["status"] == "error"
    assert PluginRun.objects.count() == runs_before
    assert enqueued_tasks == []


def test_plugin_parameters_may_reference_own_objects(as_user, world, enqueued_tasks):
    response = _run(as_user("alice"), world.video, "kpi_computation", {"format": "dfl", "tracking_data_id": world.tracking_data.id.hex})
    assert response.json()["status"] == "ok"
    assert [name for name, *_ in enqueued_tasks] == ["run_plugin"]


# ---------- uploads that attach to a video
def test_tracking_data_upload_cannot_attach_to_other_users_video(as_user, world):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = as_user("bob")
    before = db_fingerprint()
    client.post("/tracking_data/upload", {
        "video_id": world.video.id.hex, "title": "x", "format": "kinexon",
        "file": SimpleUploadedFile("pos.csv", b"a;b\n1;2\n"),
    })
    assert db_fingerprint() == before
