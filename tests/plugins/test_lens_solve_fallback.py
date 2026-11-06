"""calibration_lens_solve falls back to a plain DLT+RANSAC fit (pinhole, no lens correction) when it can't solve a
lens, and records why on the calibration (Calibration.lens_notice) so the user is told it is probably less precise."""
import json
from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import pytest

from backend.models import Calibration, CalibrationAssets, LensProfile, PluginRun, PointCorrespondence, Video
from backend.plugin_manager import run_plugin
from backend.utils.task import TaskFailure


@pytest.fixture
def video(db):
    from backend.models import SportVidUser

    owner = SportVidUser.objects.create_user("owner", "o@example.org", "Correct-Horse-Battery-42")
    return Video.objects.create(
        owner=owner, name="v", ext=".mp4", width=1920, height=1080, camera_motion=Video.CAMERA_MOTION_STATIC
    )


@pytest.fixture(autouse=True)
def grpc_settings(settings):
    settings.GRPC_HOST, settings.GRPC_PORT = "localhost", 1


@pytest.fixture
def lens_profile(db):
    return LensProfile.objects.create(
        key="test", name="Test lens", group="g", brand="b", model="m", calib_width=1920, calib_height=1080,
        camera_matrix=[[1000.0, 0.0, 960.0], [0.0, 1000.0, 540.0], [0.0, 0.0, 1.0]],
        distortion_coeffs=[0.01, 0.0, 0.0, 0.0], raw={},
    )


@contextmanager
def _data(**fields):
    yield SimpleNamespace(**fields)


def _asset(video):
    """An asset of 4 placed points that no pitch model resolves (so the lens solver has no keypoints)."""
    asset = CalibrationAssets.objects.create(owner=video.owner, video=video, name="cal", sport="soccer")
    for i, (vx, vy, px, py) in enumerate([(0.1, 0.2, 0.0, 0.0), (0.9, 0.2, 1.0, 0.0),
                                          (0.9, 0.8, 1.0, 1.0), (0.1, 0.8, 0.0, 1.0)]):
        PointCorrespondence.objects.create(
            calibration_asset=asset, name=f"p{i}", video_coords_rel=[{"x": vx, "y": vy}],
            comp_area_coords_rel=[{"x": px, "y": py}],
        )
    return asset


def _fake_dlt(monkeypatch, task_cls):
    """Answer the homography fit without an analyser; any other analyser call is a test failure."""
    calls = []

    def run_analyser(self, client, analyser, **kwargs):
        calls.append((analyser, kwargs))
        assert analyser == "calibration_static_dlt"
        return None, {"homography": _data(y=np.eye(3))}

    monkeypatch.setattr(task_cls, "run_analyser", run_analyser)
    return calls


def _run(video, plugin, parameters):
    run = PluginRun.objects.create(video=video, type=plugin, status=PluginRun.STATUS_QUEUED)
    run_plugin({
        "plugin": plugin, "parameters": parameters, "video": str(video.id), "user": str(video.owner.id),
        "plugin_run": str(run.id), "dry_run": False,
    })
    run.refresh_from_db()
    return run


@pytest.mark.parametrize(
    "motion, notice",
    [
        (Video.CAMERA_MOTION_STATIC, "not_enough_keypoints"),
        (Video.CAMERA_MOTION_PAN, "camera_not_static"),
        # not classified (yet): the solver isn't guessed at either
        (Video.CAMERA_MOTION_UNKNOWN, "camera_motion_unknown"),
        (None, "camera_motion_unknown"),
    ],
)
def test_unsolvable_lens_falls_back_to_a_pinhole_fit_with_a_notice(video, monkeypatch, motion, notice):
    """No lens profile and no lens the solver can find: the run still succeeds, fitted on the raw clicks, and the
    calibration says why no lens was used."""
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    video.camera_motion = motion
    video.save()
    calls = _fake_dlt(monkeypatch, CalibrationLensSolve)
    asset = _asset(video)
    run = _run(video, "calibration_lens_solve", {"calibration_id": asset.id.hex})

    assert run.status == PluginRun.STATUS_DONE
    assert run.failure_reason is None
    # the clicks reach the homography fit unchanged
    src = [p["src"] for p in json.loads(calls[0][1]["parameters"]["point_correspondences"])]
    assert {(s["x"], s["y"]) for s in src} == {(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)}

    calibration = Calibration.objects.get(calibration_asset=asset)
    assert calibration.lens_intrinsics is None
    assert calibration.lens_notice["type"] == notice
    assert calibration.to_dict()["lens_notice"] == calibration.lens_notice
    assert calibration.to_dict()["lens_model"] is None


def test_lens_profile_comes_first(video, lens_profile, monkeypatch):
    """A lens profile the user picked is used as in the plain DLT; the solver isn't run, there is no notice."""
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    video.lens_profile = lens_profile
    video.save()

    def solve_lens(self, *args):
        raise AssertionError("the solver must not run with a lens profile")

    monkeypatch.setattr(CalibrationLensSolve, "solve_lens", solve_lens)
    calls = _fake_dlt(monkeypatch, CalibrationLensSolve)
    asset = _asset(video)
    run = _run(video, "calibration_lens_solve", {"calibration_id": asset.id.hex})

    assert run.status == PluginRun.STATUS_DONE
    calibration = Calibration.objects.get(calibration_asset=asset)
    assert calibration.lens_intrinsics["model"] == "opencv_fisheye"
    assert calibration.lens_notice is None
    # fitted on undistorted clicks
    src = [p["src"] for p in json.loads(calls[0][1]["parameters"]["point_correspondences"])]
    assert {(round(s["x"], 6), round(s["y"], 6)) for s in src} != {(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)}


def test_lens_profile_that_leaves_too_few_points_fails(video, lens_profile, monkeypatch):
    """The picked profile is not dropped silently for a pinhole fit: the run fails as the plain DLT does."""
    from backend.tasks import calibration_static_dlt
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    video.lens_profile = lens_profile
    video.save()
    monkeypatch.setattr(
        calibration_static_dlt, "undistort_with_snapshot", lambda points, lens: [[np.nan, np.nan]] * len(points)
    )
    _fake_dlt(monkeypatch, CalibrationLensSolve)
    asset = _asset(video)
    run = _run(video, "calibration_lens_solve", {"calibration_id": asset.id.hex})

    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason["type"] == "not_enough_points_after_undistortion"
    assert not Calibration.objects.filter(calibration_asset=asset).exists()


def test_plain_dlt_has_no_notice(video, monkeypatch):
    from backend.tasks.calibration_static_dlt import CalibrationStaticDlt

    _fake_dlt(monkeypatch, CalibrationStaticDlt)
    asset = _asset(video)
    assert _run(video, "calibration_static_dlt", {"calibration_id": asset.id.hex}).status == PluginRun.STATUS_DONE
    assert Calibration.objects.get(calibration_asset=asset).lens_notice is None


def _solver_with_result(monkeypatch, solver_result):
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    task = CalibrationLensSolve()
    task.solver_parameters = {}
    monkeypatch.setattr(task, "upload_video", lambda client, video: "video-id")
    monkeypatch.setattr(
        task, "run_analyser",
        lambda client, analyser, **kwargs: (None, {"lens": _data(text=json.dumps(solver_result))}),
    )
    return task


KEYPOINTS = [{"name": f"keypoint_{i}", "video": [0.1 * i, 0.5], "pitch": [10.0 * i, 34.0]} for i in range(6)]


def test_solver_failure_is_the_notice(video, monkeypatch):
    """The Ray plugin reports a lens it couldn't fit as a result carrying "failure"; its reason is kept."""
    task = _solver_with_result(monkeypatch, {
        "failure": {"type": "lens_solver_failed", "message": "no pitch markings found around the clicked keypoints"}
    })
    with pytest.raises(TaskFailure) as failure:
        task.solve_lens(None, video, KEYPOINTS, 105.0, 68.0, "soccer", None)
    assert failure.value.type == "lens_solver_failed"
    assert failure.value.details == {"reason": "no pitch markings found around the clicked keypoints"}

    assert task.lens_intrinsics(None, video, KEYPOINTS, 105.0, 68.0, "soccer", None) is None
    assert task.lens_notice["details"]["reason"] == "no pitch markings found around the clicked keypoints"


def test_failed_analyser_call_resumes_the_run(video):
    """A crashed or timed-out solver call marked the run ERROR with its reason; the fallback carries the run on,
    so it goes back to RUNNING and the reason moves to the calibration's notice."""
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    timeout = {"type": "analyser_timeout", "message": "...", "details": {"timeout_seconds": 5}}
    run = PluginRun.objects.create(
        video=video, type="calibration_lens_solve", status=PluginRun.STATUS_ERROR, failure_reason=timeout
    )
    notice = CalibrationLensSolve().lens_unusable(TaskFailure("lens_solver_failed", "..."), video, run)
    assert notice == timeout
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_RUNNING
    assert run.failure_reason is None


def test_deleted_run_does_not_fall_back(video):
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    run = PluginRun.objects.create(video=video, type="calibration_lens_solve", status=PluginRun.STATUS_RUNNING)
    PluginRun.objects.filter(id=run.id).delete()
    with pytest.raises(TaskFailure):
        CalibrationLensSolve().lens_unusable(TaskFailure("lens_solver_failed", "..."), video, run)


def test_solved_lens_that_leaves_too_few_points_falls_back(video, monkeypatch):
    """A lens whose valid range excludes the clicks: the lens solver fits without it (the plain DLT, whose lens is
    a profile the user picked, still fails then)."""
    from backend.tasks import calibration_static_dlt
    from backend.tasks.calibration_lens_solve import CalibrationLensSolve

    monkeypatch.setattr(CalibrationLensSolve, "solve_lens", lambda self, *args: {"model": "angular"})
    monkeypatch.setattr(
        calibration_static_dlt, "undistort_with_snapshot", lambda points, lens: [[np.nan, np.nan]] * len(points)
    )
    _fake_dlt(monkeypatch, CalibrationLensSolve)
    asset = _asset(video)
    run = _run(video, "calibration_lens_solve", {"calibration_id": asset.id.hex})

    assert run.status == PluginRun.STATUS_DONE
    calibration = Calibration.objects.get(calibration_asset=asset)
    assert calibration.lens_intrinsics is None
    assert calibration.lens_notice["type"] == "not_enough_points_after_undistortion"
