"""A plugin run records the parameters it was started with and the Ray plugin versions."""
import json
import types

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from backend.models import PluginRun, SportVidUser, Video
from backend.serializers.object_tracker import DETECTOR_DEFAULTS


@pytest.fixture
def alice(db, client):
    user = SportVidUser.objects.create_user("alice", "a@example.org", "Correct-Horse-Battery-42")
    client.force_login(user)
    return user


@pytest.fixture
def video(alice):
    return Video.objects.create(owner=alice, name="v", ext=".mp4")


def test_run_records_the_validated_parameters(client, video, enqueued_tasks):
    r = client.post("/plugin/run/new", json.dumps({"plugin": "object_tracker", "video_id": video.id.hex,
                                                   "parameters": {"detector": "yolo11"}}), content_type="application/json")
    run = PluginRun.objects.get(id=r.json()["plugin_run_id"])
    assert run.parameters["detector"] == "yolo11"
    assert run.parameters["detector_params"]["checkpoint"] == DETECTOR_DEFAULTS["yolo11"]["checkpoint"]
    assert r.json()["entry"]["parameters"] == run.parameters  # exposed in the API


def test_uploaded_files_are_recorded_by_name_only(client, video, enqueued_tasks):
    # whisper has no parameter serializer, so _files reaches the task (serializers drop it)
    r = client.post("/plugin/run/new", {"plugin": "whisper", "video_id": video.id.hex, "parameters": "{}",
                                        "file_extra": SimpleUploadedFile("calib.json", b"{}")})
    run = PluginRun.objects.get(id=r.json()["plugin_run_id"])
    assert run.parameters["_files"] == {"extra": "calib.json"}


def test_each_analyser_job_appends_the_ray_plugin_version(video, deployed_ray_plugins):
    from backend.utils.task import Task

    run = PluginRun.objects.create(video=video, type="whisper", status=PluginRun.STATUS_RUNNING)
    deployed_ray_plugins.update({"video_to_audio": "0.1", "whisper": "0.3"})
    client = types.SimpleNamespace(
        plugin_run_db=run,
        run_plugin=lambda *a, **k: "job",
        get_plugin_results=lambda **k: types.SimpleNamespace(outputs=[]),
    )
    Task().run_analyser(client, "video_to_audio")
    Task().run_analyser(client, "whisper")
    run.refresh_from_db()
    assert run.provenance == [{"ray_plugin": "video_to_audio", "version": "0.1"},
                              {"ray_plugin": "whisper", "version": "0.3"}]


def test_failed_analyser_job_records_nothing(video):
    from backend.utils.task import Task

    run = PluginRun.objects.create(video=video, type="whisper", status=PluginRun.STATUS_RUNNING)
    client = types.SimpleNamespace(plugin_run_db=run, run_plugin=lambda *a, **k: "job",
                                   get_plugin_results=lambda **k: None)
    assert Task().run_analyser(client, "whisper") is None
    run.refresh_from_db()
    assert run.provenance is None


def test_models_and_migrations_are_in_sync(db):
    """Fails when a model change comes without its migration."""
    call_command("makemigrations", "backend", "--check", "--dry-run", verbosity=0)
