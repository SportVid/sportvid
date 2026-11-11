"""Kalman ball tracker (inference_ray plugins/tracker/ball_tracker.py): linking, camera motion, static filter,
frame-rate gate, and its backend parameters; the camera motion estimate it compensates (tracker/camera_motion.py)."""
import numpy as np
import pytest

from backend.serializers.object_tracker import (
    ObjectTrackerSerializer,
    default_camera_motion_params,
    default_kalman_ball_params,
)
from inference_ray.plugins.tracker.ball_tracker import DEFAULTS, BallTracker
from inference_ray.plugins.tracker.camera_motion import CameraMotion, CameraMotionEstimator, apply_h


def det(xy, conf=0.8, r=6.0):
    return {"xyxy": [xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], "conf": conf}


def centres(state):
    return np.array([s["ball_box"][:2] + s["ball_box"][2:] / 2 if s["ball_box"] is not None else [np.nan] * 2
                     for s in state])


def straight_clip(n=120, gap=range(50, 56), pan=0.0):
    """A ball rolling at 5 px / frame, missing in ``gap``; ``pan``: the camera pans by this many px / frame
    (image content shifts left), so the ball's image position is its world position minus the pan."""
    world = np.c_[200 + 5.0 * np.arange(n), np.full(n, 500.0)]
    image = world - np.c_[pan * np.arange(n), np.zeros(n)]
    dets = [[] if i in gap else [det(image[i])] for i in range(n)]
    return dets, image


@pytest.mark.parametrize("linking", ["global", "online"])
def test_tracks_and_fills_a_gap(linking):
    dets, truth = straight_clip()
    state = BallTracker({"linking": linking}).process({"detections": dets})
    assert [s["ball_status"] for s in state[50:56]] == ["interpolated"] * 6
    assert np.abs(centres(state) - truth).max() < 1.0
    assert all(s["ball_sigma"] > 0 for s in state)


def test_detections_are_taken_as_routed_without_a_class_filter():
    dets, _ = straight_clip(gap=())
    for frame in dets:
        frame[0]["cls_id"] = 37          # any class: the caller already routed the ball candidates
    state = BallTracker({}).process({"detections": dets})
    assert all(s["ball_status"] == "detected" for s in state)


def test_camera_pan_is_compensated():
    pan = 8.0
    dets, truth = straight_clip(pan=pan)
    rel = np.tile(np.eye(3), (len(dets), 1, 1))
    rel[1:, 0, 2] = pan                  # frame t -> frame t-1: content was pan px further right
    tracker = BallTracker({})
    state = tracker.process({"detections": dets, "camera_motion": CameraMotion(rel)})
    assert [s["ball_status"] for s in state[50:56]] == ["interpolated"] * 6
    assert np.abs(centres(state) - truth).max() < 1.0


def test_identity_camera_motion_changes_nothing():
    dets, _ = straight_clip()
    a = BallTracker({}).process({"detections": dets})
    b = BallTracker({}).process({"detections": dets, "camera_motion": CameraMotion.identity(len(dets))})
    assert np.allclose(centres(a), centres(b))


def test_static_decoy_is_dropped_when_the_filter_is_on():
    assert DEFAULTS["static_filter"] is False   # off by default, kept as an option for fixed cameras
    dets, _ = straight_clip(n=300, gap=())
    for frame in dets:
        frame.append(det((1500.0, 300.0), conf=0.9))
    state = BallTracker({"static_filter": True}).process({"detections": dets})
    assert np.linalg.norm(centres(state) - [1500.0, 300.0], axis=1).min() > 50


def test_min_fps_gate():
    assert BallTracker({}, fps=10).usable
    assert not BallTracker({}, fps=5).usable
    assert BallTracker({"min_fps": 5}, fps=5).usable


def test_backend_defaults_match_the_plugin():
    assert default_kalman_ball_params == DEFAULTS


def test_backend_validates_the_linking_and_motion_model():
    ok = ObjectTrackerSerializer(data={"detector": "rfdetr",
                                       "ball_tracker_params": {"linking": "online", "motion_model": "pwca"}})
    assert ok.is_valid(), ok.errors
    for bad in ({"linking": "greedy"}, {"motion_model": "cv"}, {"static_cooccur": 1.5}):
        s = ObjectTrackerSerializer(data={"detector": "rfdetr", "ball_tracker_params": bad})
        assert not s.is_valid() and "ball_tracker_params" in s.errors


# -- camera motion estimate --------------------------------------------------------------------------------------
cv2 = pytest.importorskip("cv2")
W, H = 640, 360


def scene(seed=0, h=H + 200, w=W + 400):
    """A textured background (RGB uint8)."""
    rng = np.random.default_rng(seed)
    grey = cv2.GaussianBlur(rng.uniform(0, 255, (h, w)).astype(np.float32), (0, 0), 2.0)
    grey = cv2.normalize(grey, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return np.repeat(grey[:, :, None], 3, axis=2)


def panning_view(n, pan_x, pan_y=0.0, seed=0):
    """Frames of a view panning over the scene by (pan_x, pan_y) px / frame; a frame-t pixel lies
    (pan_x, pan_y) further right / down in frame t-1, so the true step is a translation by +pan."""
    bg = scene(seed, H + 100 + int(abs(pan_y) * n), W + 100 + int(abs(pan_x) * n))   # the view never leaves it
    frames = []
    for t in range(n):
        M = np.float32([[1, 0, -(50 + pan_x * t)], [0, 1, -(50 + pan_y * t)]])
        frames.append(cv2.warpAffine(bg, M, (W, H), flags=cv2.INTER_LINEAR))
    return frames


@pytest.mark.parametrize("features", ["klt", "orb"])
def test_estimate_recovers_a_pan(features):
    est = CameraMotionEstimator({"features": features}, fps=30)
    for f in panning_view(12, 3.0, 1.5):
        est.add(f)
    cm = est.finalize()
    assert cm is not None and est.moving and cm.ok.all()
    corners = np.array([[0, 0], [W, 0], [W, H], [0, H]], dtype=np.float64)
    for t in range(1, len(cm)):
        assert np.abs(apply_h(cm.rel[t], corners) - (corners + [3.0, 1.5])).max() < 0.5


def test_fixed_camera_passes_no_motion_unless_mode_on():
    frames = panning_view(10, 0.0)
    auto = CameraMotionEstimator({}, fps=10)
    on = CameraMotionEstimator({"mode": "on"}, fps=10)
    for f in frames:
        auto.add(f), on.add(f)
    assert auto.finalize() is None and auto.moving is False
    assert on.finalize() is not None
    off = CameraMotionEstimator({"mode": "off"}, fps=10)
    off.add(frames[0])
    assert off.finalize() is None


def test_masked_boxes_are_ignored():
    """A patch moving against the pan inside a masked box does not bias the estimate."""
    frames = panning_view(8, 4.0)
    boxes = []
    for t, f in enumerate(frames):
        x = 100 + 12 * t
        f[100:220, x:x + 120] = np.roll(scene(1)[:120, :120], 5 * t, axis=1)
        boxes.append(np.array([[x, 100, x + 120, 220]], dtype=np.float64))
    est = CameraMotionEstimator({"mode": "on"}, fps=30)
    for f, b in zip(frames, boxes):
        est.add(f, b)
    cm = est.finalize()
    assert np.abs(cm.rel[1:, 0, 2] - 4.0).max() < 0.3


def test_estimated_motion_feeds_the_ball_tracker():
    pan = 6.0
    frames = panning_view(len(straight_clip()[0]), pan)
    est = CameraMotionEstimator({}, fps=30)
    for f in frames:
        est.add(f)
    cm = est.finalize()
    exact = np.tile(np.eye(3), (len(frames), 1, 1))
    exact[1:, 0, 2] = pan
    dets, truth = straight_clip(pan=pan)
    state = BallTracker({}).process({"detections": dets, "camera_motion": cm})
    ref = BallTracker({}).process({"detections": dets, "camera_motion": CameraMotion(exact)})
    assert cm is not None and np.abs(cm.rel - exact).max() < 0.05
    assert [s["ball_status"] for s in state] == [s["ball_status"] for s in ref]
    assert np.abs(centres(state) - centres(ref)).max() < 0.5
    assert np.abs(centres(state) - truth).max() < 1.0


def test_camera_motion_backend_defaults_match_the_plugin():
    assert default_camera_motion_params == CameraMotionEstimator.DEFAULTS
