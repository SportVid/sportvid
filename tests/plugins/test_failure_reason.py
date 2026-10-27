"""A failed plugin run carries why it failed (PluginRun.failure_reason), for the frontend to show."""
import pytest

from backend.models import CalibrationAssets, PluginRun, SportVidUser, Video
from backend.plugin_manager import PluginManager, run_plugin
from backend.utils.task import TaskFailure


@pytest.fixture
def video(db):
    owner = SportVidUser.objects.create_user("owner", "o@example.org", "Correct-Horse-Battery-42")
    return Video.objects.create(owner=owner, name="v", ext=".mp4", width=1920, height=1080)


@pytest.fixture
def grpc_settings(settings):
    # read by the calibration tasks' __init__; the tests fail before any analyser call
    settings.GRPC_HOST, settings.GRPC_PORT = "localhost", 1


def _run(video, plugin, parameters=None):
    run = PluginRun.objects.create(video=video, type=plugin, status=PluginRun.STATUS_QUEUED)
    run_plugin({
        "plugin": plugin,
        "parameters": parameters or {},
        "video": str(video.id),
        "user": str(video.owner.id),
        "plugin_run": str(run.id),
        "dry_run": False,
    })
    run.refresh_from_db()
    return run


def _register(monkeypatch, name, call):
    monkeypatch.setitem(PluginManager._plugins, name, type(name, (), {"__call__": call}))


def test_task_failure_is_stored_and_published(video, monkeypatch, published_events):
    def call(self, **kwargs):
        raise TaskFailure("not_enough_keypoints", "needs 6, got 2", count=2, required=6)

    _register(monkeypatch, "failing", call)
    run = _run(video, "failing")
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason == {
        "type": "not_enough_keypoints", "message": "needs 6, got 2", "details": {"count": 2, "required": 6}
    }
    assert any(
        p["type"] == "plugin_run.update" and p["entry"]["failure_reason"] == run.failure_reason
        for _, p in published_events
    )


def test_unexpected_error_text_is_not_exposed(video, monkeypatch):
    def call(self, **kwargs):
        raise RuntimeError("/mnt/data/secret/path exploded")

    _register(monkeypatch, "crashing", call)
    run = _run(video, "crashing")
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason == {"type": "internal_error"}


def test_reason_recorded_earlier_in_the_run_is_kept(video, monkeypatch):
    def call(self, plugin_run=None, **kwargs):
        # as the analyser timeout in analyser_client.py does, then the task gives up
        plugin_run.failure_reason = {"type": "analyser_timeout", "message": "...", "details": {}}
        raise TaskFailure("lens_solver_failed", "The lens solver could not fit a lens to this video")

    _register(monkeypatch, "timing_out", call)
    assert _run(video, "timing_out").failure_reason["type"] == "analyser_timeout"


def test_unknown_plugin(video):
    run = _run(video, "no_such_plugin")
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason["type"] == "unknown_plugin"


def test_failed_dependency(video):
    tracker = PluginRun.objects.create(video=video, type="object_tracker", status=PluginRun.STATUS_ERROR)
    run = _run(video, "team_clustering", {"object_tracker_id": tracker.id.hex})
    assert run.failure_reason["type"] == "dependency_failed"
    assert run.failure_reason["details"] == {"plugin_run_id": tracker.id.hex, "plugin": "object_tracker"}


def test_successful_run_has_no_reason(video, monkeypatch):
    _register(monkeypatch, "fine", lambda self, **kwargs: {})
    run = _run(video, "fine")
    assert run.status == PluginRun.STATUS_DONE
    assert run.failure_reason is None
    assert run.to_dict()["failure_reason"] is None


def test_calibration_with_too_few_points(video, grpc_settings):
    asset = CalibrationAssets.objects.create(owner=video.owner, video=video, name="cal", sport="soccer")
    run = _run(video, "calibration_static_dlt", {"calibration_id": asset.id.hex})
    assert run.failure_reason["type"] == "not_enough_point_correspondences"
    assert run.failure_reason["details"] == {"count": 0, "required": 4}


@pytest.mark.parametrize("motion", [Video.CAMERA_MOTION_PAN, Video.CAMERA_MOTION_ZOOM, Video.CAMERA_MOTION_PAN_ZOOM])
def test_lens_solver_rejects_a_moving_camera(video, motion, grpc_settings):
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    video.camera_motion = motion
    with pytest.raises(TaskFailure) as failure:
        CalibrationLensSolve().lens_intrinsics(None, video, [], 105.0, 68.0, "soccer", None)
    assert failure.value.type == "camera_not_static"
    assert failure.value.details == {"camera_motion": motion}


def test_lens_solver_needs_enough_keypoints(video, grpc_settings):
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    video.camera_motion = Video.CAMERA_MOTION_STATIC
    with pytest.raises(TaskFailure) as failure:
        CalibrationLensSolve().lens_intrinsics(None, video, [{}] * 5, 105.0, 68.0, "soccer", None)
    assert failure.value.type == "not_enough_keypoints"
    assert failure.value.details == {"count": 5, "required": 6}


def test_analyser_timeout_records_its_reason(video, settings, monkeypatch):
    import types
    from contextlib import nullcontext

    from backend.utils import analyser_client
    from interface import analyser_pb2

    run = PluginRun.objects.create(video=video, type="calibration_lens_solve", status=PluginRun.STATUS_RUNNING)
    monkeypatch.setattr(analyser_client, "cancellation_watcher", lambda *a, **k: nullcontext(None))
    settings.PLUGIN_RUN_TIMEOUT = 0.2
    client = analyser_client.TaskAnalyserClient(host="localhost", port=1, plugin_run_db=run)
    running = types.SimpleNamespace(status=analyser_pb2.GetPluginStatusResponse.RUNNING, progress=0.1)
    monkeypatch.setattr(client, "get_plugin_status", lambda job_id: running)
    monkeypatch.setattr(client, "abort_plugin", lambda job_id: None)

    assert client.get_plugin_results("job-1") is None
    assert run.failure_reason["type"] == "analyser_timeout"
    run.refresh_from_db()
    assert run.failure_reason["type"] == "analyser_timeout"
