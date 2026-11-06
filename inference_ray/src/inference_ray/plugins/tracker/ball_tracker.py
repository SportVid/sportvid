"""
Single-ball tracker.

Integration with SportVid:

* Frame-based parameters are given at ``REFERENCE_FPS`` (30) and scaled to the decoding rate (``scale_to_fps``).
  Below ``min_fps`` the tracker is not ``usable``; ``object_tracker`` then writes the ball candidates untracked.
* The caller passes only ball-class detections (``detections``), in frame pixels; there is no class filter here.

There is at most one ball in play, so this is not multi-object tracking: per frame the ball
detections are *candidates*, and the tracker picks at most one of them as the ball. It works on the
full candidate list of the clip (post-hoc, after the frame loop). Two ways to pick the path
(``linking``) share the stages around them:

1. **Static-object filter** (whole clip, below): decoys that never move are dropped.
2. **Linking**: ``global`` (default) -- short tracklets, then one best path through them for the
   whole clip -- or ``online`` -- a frame-by-frame Kalman track with re-acquisition.
3. **Segment refinement**: per track segment a confidence-weighted RTS smoother validates the weak
   detections, finds kick corners and fills gaps.

Defaults: global linking, pixel gates, the continuous white-noise acceleration model, a fixed ``max_gap``
for gap filling and a static filter without the co-occurrence rule (``static_cooccur`` off). Given the
camera's motion it also handles a moving camera (below).

Online linking
--------------
A constant-velocity Kalman filter (image pixels) predicts where the ball should be next. The
candidate nearest that prediction, weighted by its confidence, continues the track if it lies inside
the gate. The track restarts (after ``max_missed`` frames, or after ``switch_frames`` frames with a
confident candidate elsewhere while the gate holds only weak ones or none) at the most confident
candidate >= ``init_conf`` *only* if it is within ``reacquire_px`` of where the ball was last
genuinely seen -- a confident candidate anywhere else (including before the ball has ever been seen)
is not trusted on a single frame; it goes through the re-acquisition path below like any weak
detection, since confidence alone does not distinguish the ball from a static, clearly-lit decoy (a
cone, a spare ball).

Detection confidence is used throughout, so a weak false positive cannot hijack the track
while the real ball is unseen:

* Gate: it grows by ``gate_growth_px`` per missed frame, but only in proportion to the
  candidate's confidence (0 at ``min_conf``, full at ``init_conf``). A weak candidate is only
  accepted near the prediction (``gate_px``), however long the ball has been missing.
* Kalman update: measurement noise ``meas_px / conf`` -- a weak detection barely moves the filter.

Re-acquisition from weak detections: while the ball is unseen, candidates the active track
does not take start *provisional* tracks with their own small Kalman filter
(``tentative_gate_px``, up to ``tentative_max_missed`` unseen frames). One that collects
``confirm_frames`` consistent detections is confirmed and its detections are written back.
It must be plausible as the ball it replaces:

* starting within ``reacquire_px`` of the last known ball position: accepted (a ball at rest
  where it was lost is fine);
* starting further away: it must move (>= ``min_move_px`` over its detections -- static clutter
  such as a sign, a cone or a spare ball never confirms) and start within a radius that grows
  from ``reacquire_px`` by ``reacquire_growth_px`` per frame since the loss, up to
  ``reacquire_max_px``; once the radius is at its maximum, any moving track qualifies;
* weak candidates on the upper part of a player box (``tentative_skip_body``: head / torso
  clutter) are ignored -- the ball is at the feet or in the air, rarely in front of a torso;
* in every case its last ``confirm_frames`` detections must fit a constant-velocity line within
  ``tentative_resid_px`` RMS, and "moving" is the distance covered along the longest recent run
  that does -- hopping between static clutter spots is neither smooth nor moving;
* before the first track of the clip, any moving track qualifies.

Provisional tracks run whenever the ball is unseen -- while the active track coasts as well as
after it is lost -- and a confirmed one takes over. If it starts within ``max_gap`` frames of the
last detection it continues that segment, so the gap between them is filled; otherwise it starts
a new one. A candidate >= ``init_conf`` still (re)acquires immediately; if a provisional track
runs into it (its prediction reaches the candidate), that track's weak detections are kept as
the lead-in of the new one.

Global linking
--------------
Association is solved for the whole clip instead of greedily frame by frame, with the same pixel
gates as the online pass:

* **Tracklets**: short, unambiguous chains of candidates, each with its own constant-velocity Kalman
  filter (any number in parallel; every unclaimed candidate starts one, except weak ones on a
  player's upper body, ``tentative_skip_body``). A candidate joins a chain inside the online gate
  (``gate_px`` + ``gate_growth_px`` per unseen frame, scaled by confidence; + ``kick_vel_px`` after
  a touch), greedily by the online cost. A chain ends after ``tracklet_max_missed`` unseen frames.
  Single weak detections (fewer than ``min_tracklet_len`` and none >= ``init_conf``) are discarded.
* **One best path** through the tracklets (dynamic programming; tracklets on the path never overlap
  in time). Path score = sum of tracklet scores + link scores:

  * tracklet: ``det_reward + log LR(conf)`` per detection minus half its innovations' squared
    Mahalanobis distance; log LR(conf) = ``lr_scale * (logit(conf) - logit(init_conf))``;
  * *continuation* (same segment, gap <= ``link_max_gap``): A's forward prediction lands within
    ``gate_px + gate_growth_px * gap`` (capped at ``reacquire_max_px``) of B's backward estimate at B's
    first frame; score ``-miss_cost`` per gap frame minus half their Mahalanobis distance. A may lose
    up to ``link_trim_max`` *weak* trailing detections that overlap B (a coasting chain that picked up
    clutter before the ball's next chain starts). Into a non-eligible (short, unconfirmed) B only where
    the prediction's position sigma <= ``support_sigma_px`` -- otherwise clutter in the middle of a long
    gap would be inserted just for its detection reward;
  * *resume* (new segment, gap <= ``resume_max_gap``): B starts within ``reacquire_px`` of where A
    ended (a ball at rest where it was lost) and A has no consistent continuation into B; score
    ``-resume_cost``;
  * *restart* / path start (new segment, any gap): only for an *eligible* tracklet -- at least
    ``confirm_frames`` detections that fit a constant-velocity line within ``tentative_resid_px``
    RMS and either move (>= ``min_move_px``) or are confident (mean conf >= ``init_conf``);
    score ``-birth_cost``.

  A decoy or clutter chain only wins where it out-scores the ball, and a ball that reappears far
  away is picked up as soon as its chain is eligible (no growing re-acquisition radius).

Segment refinement
------------------
Per track segment, a confidence-weighted Kalman (RTS) smoother runs over the whole segment; gaps of
up to ``max_gap`` frames are filled from the smoothed path. With confident detections on both sides
this is the straight-line (constant-velocity) motion between them. The smoothed position std is
reported per frame as ``ball_sigma``.

Kicks (sudden changes of direction) are allowed where there is evidence for them:

* One-sided support: at every detection the path predicted from the *earlier* detections alone
  (forward filter) and from the *later* ones alone (backward filter) are compared with it. A
  kick corner lies on both -- the ball arrives along the old direction and leaves along the new
  one. Where both agree (``outlier_px``) and the arriving and leaving velocities differ by more
  than ``corner_dv_px`` -- and significantly, given both filters' velocity uncertainty, so an
  unsettled estimate after a gap or at a segment end is no corner -- the velocity is reset there
  and the path bends instead of cutting the corner.
* Players as a hint (``player_hint``): a ball within ``foot_reach`` player box widths of a
  player's foot point may be kicked. The smoother resets the velocity there; the online pass and
  the tracklets widen the gate after such a touch (``kick_vel_px`` extra, and full growth while the
  ball is unseen even for weak candidates, since a kicked ball is blurred); and at the foot the later
  side's support alone is enough to keep a weak detection (the earlier side can overshoot when
  the ball was trapped out of sight).
* A weak detection (< ``init_conf``) off the smoothed path (> ``outlier_px``) is kept only if it
  is supported: by the later side and (the earlier side or a player's foot); at the end of a
  segment (no later detection within ``max_gap``) by the earlier side. Anything else is dropped
  as a false positive and its frame treated as a gap. A supported weak detection is corroborated,
  so the final smoothing weights it as ``init_conf``; gap fills follow the smoothed path, shifted
  to meet the kept detections on both sides.

Static-object filter
--------------------
Before linking, a whole-clip pass finds clusters of ball-class candidates within
``static_radius_px`` of one spot for at least ``static_min_hits`` frames spanning at least
``static_min_span`` frames -- a cone, a spare ball, a goal-area marking, anything the detector
repeatedly calls "ball" without it ever moving. Nothing online reliably catches these: a single
confident detection (re)acquires immediately when it lands near where the ball was last seen, which
a decoy near the ball's own resting spot (kickoff, a stoppage) satisfies as well as the real ball.

A cluster is dropped only if in at least ``static_cooccur`` of its frames another candidate (not
static itself, conf >= ``static_cooccur_conf``, more than two radii away) is visible: a cone or a
spare ball coexists with the ball in play, a ball resting alone for a set piece does not, and is
kept. ``static_cooccur <= 0`` (the default) drops every static cluster. Where the detector often misses
the real ball, decoys look "alone" as well, so the rule can keep them.

Frame rate and motion model
---------------------------
Frame-based parameters are given at ``REFERENCE_FPS`` (30) and scaled to the processing rate ``fps``
(``object_tracker`` passes its decoding rate, see ``scale_to_fps``): durations in frames by fps / 30,
per-frame motion (px / frame) by 30 / fps, the acceleration by (30 / fps)^2, per-frame costs by 30 / fps.
At 30 fps nothing changes.

``motion_model``: ``"cwna"`` (default) -- continuous white-noise acceleration, Q_n = q [[n^3/3, n^2/2],
[n^2/2, n]] per axis with q = ``accel_px``^2 at 30 fps: the noise injected per second does not depend on
the frame rate, so the scaling is exact. ``"pwca"`` -- piecewise-constant acceleration per frame:
Q_1 = ``accel_px``^2 [[1/4, 1/2], [1/2, 1]], only approximately rate-free.

Camera motion
-------------
If the caller passes a camera motion (``inputs["camera_motion"]``, a ``CameraMotion`` from
``camera_motion.py``: frame-to-frame homographies; ``None`` for a fixed camera), the tracker compensates it. All tracking geometry stays in the *current frame's* pixels, so
every pixel parameter keeps its meaning however far the camera moves:

* every Kalman step (online track, provisional tracks, tracklets, the refinement's filters and
  smoother) predicts in the previous frame and maps the state into the next one: position through the
  homography, velocity and covariance through its Jacobian (the smoother uses the linearised step);
* comparisons across frames (re-acquisition near the last seen position, continuation and resume
  links, the constant-velocity checks of new chains) map the earlier position into the later frame;
* a step whose estimate failed (``CameraMotion.ok``) adds ``cam_fail_px``^2 to the position variance
  instead of trusting a guess;
* only the static-object filter needs one plane for the whole clip: frame 0's (the chained
  homographies), with ``static_radius_px`` converted per candidate by the local scale of that mapping.
  The chain drifts slowly, so a decoy seen across a long camera move may split into two clusters.


State (one dict per frame):
    {
        "frame_id": int,
        "ball_box": np.ndarray (4,) tlwh | None,
        "ball_score": float,           # detection confidence; 0 when interpolated / missing
        "ball_segment": int,           # track segment (re-acquisitions start a new one); -1 if none
        "ball_status": "detected" | "interpolated" | "none",
        "ball_sigma": float | None     # smoothed position std (px); None if no ball
    }
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .camera_motion import CameraMotion, apply_h, h_jacobian
from .tracker import Tracker

logger = logging.getLogger(__name__)

STATUS = ("none", "detected", "interpolated")
_CORNER_D2 = 4.0        # velocity change must exceed ~2 sigma of the one-sided estimates' uncertainty
_KICK_VAR = 100.0 ** 2   # velocity variance released at a kick (px/frame)^2 at 30 fps: effectively unknown vs. ball
                        #   speeds, yet small enough to keep the smoother's covariances well-conditioned
_H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)
_I2 = np.eye(2)
_I4 = np.eye(4)
_POS = np.diag([1.0, 1.0, 0.0, 0.0])

# link types on the global path
_START, _CONT, _RESUME, _RESTART = 0, 1, 2, 3

REFERENCE_FPS = 30.0      # the rate the frame-based defaults are given at

# the defaults; the backend serializer (default_kalman_ball_params) holds the same values
DEFAULTS: Dict[str, Any] = {
    "min_conf": 0.10, "init_conf": 0.40,
    "linking": "global",
    # gating (online pass, tracklets, continuation links)
    "gate_px": 60.0, "gate_growth_px": 20.0, "kick_vel_px": 30.0,
    # online pass
    "max_missed": 15, "switch_frames": 3,
    # re-acquisition / eligibility of new chains
    "confirm_frames": 4, "tentative_gate_px": 30.0, "tentative_max_missed": 2, "reacquire_px": 60.0,
    "reacquire_growth_px": 15.0, "reacquire_max_px": 400.0, "min_move_px": 20.0, "tentative_resid_px": 6.0,
    "tentative_skip_body": 0.75,
    # global linking
    "tracklet_max_missed": 5, "min_tracklet_len": 2, "link_max_gap": 60, "link_trim_max": 3, "resume_max_gap": 900,
    "det_reward": 2.0, "miss_cost": 0.2, "resume_cost": 3.0, "birth_cost": 6.0, "lr_scale": 2.0,
    "support_sigma_px": 60.0,
    # motion / measurement model
    "motion_model": "cwna", "accel_px": 4.0, "meas_px": 2.0,
    # camera motion compensation (when the pipeline passes a camera motion)
    "cam_fail_px": 20.0,
    # segment refinement
    "max_gap": 10, "outlier_px": 25.0, "corner_dv_px": 5.0, "player_hint": True, "foot_reach": 1.5,
    # static-object filter
    "static_filter": True, "static_radius_px": 12.0, "static_min_hits": 60, "static_min_span": 150,
    "static_cooccur": 0.0, "static_cooccur_conf": 0.25,
    # below this decoding rate the ball is not tracked (``usable``)
    "min_fps": 10.0,
}

# how each frame-based parameter scales with k = REFERENCE_FPS / fps
_DURATION_FRAMES = ("max_missed", "switch_frames", "tentative_max_missed", "tracklet_max_missed", "link_max_gap",
                    "resume_max_gap", "max_gap", "static_min_span")                  # / k
_EVIDENCE_HITS = ("static_min_hits",)     # / k: hits of a static object over its (scaled) span; at least 3
_PER_FRAME_PX = ("gate_px", "gate_growth_px", "kick_vel_px", "tentative_gate_px", "reacquire_growth_px",
                 "corner_dv_px", "cam_fail_px")          # * k: motion per frame
_PER_FRAME2_PX = ("accel_px",)            # * k^2: acceleration per frame^2
_PER_FRAME_COST = ("miss_cost",)          # * k: cost per frame -> constant cost per second
# not scaled: confidences, likelihood terms (lr_scale, det_reward, *_cost per event), distances that do not depend
# on the frame step (outlier_px, reacquire_px, reacquire_max_px, min_move_px, support_sigma_px, static_radius_px),
# measurement noise (meas_px, tentative_resid_px), box fractions, counts of detections (confirm_frames,
# min_tracklet_len, link_trim_max: evidence, not durations) and min_fps
# keys of the tracker config read elsewhere (Tracker base class: refiners)
_OTHER_KEYS = ("gta_link", "interpolation")


def scale_to_fps(params: Dict[str, Any], fps: float) -> Dict[str, Any]:
    """Parameters given at ``REFERENCE_FPS`` -> the same physical behaviour at ``fps``."""
    k = REFERENCE_FPS / float(fps)
    out = dict(params)
    for key in _DURATION_FRAMES:
        out[key] = max(1, int(round(params[key] / k)))
    for key in _EVIDENCE_HITS:
        out[key] = max(3, int(round(params[key] / k)))
    for key in _PER_FRAME_PX + _PER_FRAME_COST:
        out[key] = float(params[key]) * k
    for key in _PER_FRAME2_PX:
        out[key] = float(params[key]) * k ** 2
    return out


# -- small helpers ------------------------------------------------------------
def _foot_points(b: np.ndarray, box_format: str) -> np.ndarray:
    """(N, 2) bottom-centre points of (N, 4) boxes in ``tlwh`` or ``xyxy``."""
    if str(box_format).lower() == "xyxy":
        return np.stack([(b[:, 0] + b[:, 2]) * .5, b[:, 3]], axis=1)
    return np.stack([b[:, 0] + b[:, 2] * .5, b[:, 1] + b[:, 3]], axis=1)


def _maha(y: np.ndarray, S: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Squared Mahalanobis distance and log det for (..., 2) residuals and (..., 2, 2) covariances
    (closed form)."""
    a, b, c, d = S[..., 0, 0], S[..., 0, 1], S[..., 1, 0], S[..., 1, 1]
    det = np.maximum(a * d - b * c, 1e-12)
    y0, y1 = y[..., 0], y[..., 1]
    return (d * y0 * y0 - (b + c) * y0 * y1 + a * y1 * y1) / det, np.log(det)


def _logit(c) -> np.ndarray:
    c = np.clip(np.asarray(c, dtype=np.float64), 1e-4, 1 - 1e-4)
    return np.log(c / (1.0 - c))


def _pos_sigma(P: np.ndarray) -> np.ndarray:
    """Largest position std of (..., 4, 4) state covariances."""
    return np.sqrt(np.maximum(np.linalg.eigvalsh(P[..., :2, :2])[..., -1], 0.0))


def _cv_motion(frames: np.ndarray, xy: np.ndarray, k_min: int, max_rms: float, k_max: int = 30) -> float:
    """Distance (px) covered along the longest recent run of >= ``k_min`` detections that fits a
    constant-velocity line within ``max_rms``; -1 if even the last ``k_min`` do not."""
    for k in range(min(len(frames), k_max), k_min - 1, -1):
        t = np.asarray(frames[-k:], dtype=np.float64)
        A = np.c_[t - t[0], np.ones(len(t))]
        coef, *_ = np.linalg.lstsq(A, xy[-k:], rcond=None)        # rows: velocity, offset
        if np.sqrt(np.mean(np.sum((A @ coef - xy[-k:]) ** 2, axis=1))) <= max_rms:
            return float(np.linalg.norm(coef[0]) * abs(t[-1] - t[0]))
    return -1.0


# -- motion / measurement model ------------------------------------------------
def _warp_states(W: np.ndarray, X: np.ndarray, P: np.ndarray):
    """States (N, 4) and covariances (N, 4, 4) through the homography ``W`` (one frame's pixels -> the next
    one's): position mapped, velocity and covariance through its Jacobian at the position. Returns X, P and
    the Jacobians A (N, 4, 4) of the state map."""
    J = h_jacobian(W, X[:, :2])
    A = np.zeros((len(X), 4, 4))
    A[:, :2, :2] = J
    A[:, 2:, 2:] = J
    Xw = np.empty_like(X)
    Xw[:, :2] = apply_h(W, X[:, :2])
    Xw[:, 2:] = np.einsum("nij,nj->ni", J, X[:, 2:])
    return Xw, A @ P @ np.swapaxes(A, 1, 2), A


class _Motion:
    """Constant-velocity model on the ball centre, state [x, y, vx, vy], one step per frame.

    ``accel_px`` is already scaled to the processing rate (``scale_to_fps``: * k^2, k = 30 / fps).
    CWNA: Q_n = q [[n^3/3, n^2/2], [n^2/2, n]] per axis with q = accel_ref^2 * k^3 = accel_px^2 / k, so the
    noise injected per second does not depend on fps. PWCA: Q_1 = accel_px^2 [[1/4, 1/2], [1/2, 1]] per
    axis, Q_n by composing n steps. Measurement noise: (``meas_px`` / conf)^2. ``vel_scale`` k also scales
    the velocity priors (initial and kick variance, given in px / frame at 30 fps)."""

    def __init__(self, kind: str, accel_px: float, meas_px: float, vel_scale: float = 1.0):
        if kind not in ("cwna", "pwca"):
            raise ValueError(f"ball_tracker: motion_model must be 'cwna' or 'pwca', got {kind!r}")
        k = float(vel_scale)
        self.kind = kind
        self.q = accel_px ** 2 / k
        self.Q1_axis = accel_px ** 2 * np.array([[0.25, 0.5], [0.5, 1.0]])
        self.meas_px = float(meas_px)
        self.v0 = (30.0 * k) ** 2                                    # unknown initial velocity
        kv = _KICK_VAR * k ** 2
        self.Q_kick = np.diag([0.0, 0.0, kv, kv])
        self._cache: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        self._Fa = self._Qa = None

    def FQ(self, n: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Transition and process noise over ``n`` >= 1 frames."""
        n = int(n)
        if n not in self._cache:
            F = np.eye(4)
            F[0, 2] = F[1, 3] = n
            if self.kind == "cwna":
                a = self.q * np.array([[n ** 3 / 3.0, n ** 2 / 2.0], [n ** 2 / 2.0, float(n)]])
            else:
                a = np.zeros((2, 2))
                for i in range(n):
                    Fi = np.array([[1.0, i], [0.0, 1.0]])
                    a += Fi @ self.Q1_axis @ Fi.T
            self._cache[n] = (F, np.kron(a, _I2))
        return self._cache[n]

    def FQ_stack(self, ns: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """``FQ`` for an array of step counts: (len, 4, 4) each."""
        nmax = int(ns.max())
        if self._Fa is None or len(self._Fa) <= nmax:
            size = max(nmax + 1, 2 * (0 if self._Fa is None else len(self._Fa)))
            fq = [self.FQ(max(k, 1)) for k in range(size)]
            self._Fa = np.stack([f for f, _ in fq])
            self._Qa = np.stack([q for _, q in fq])
        return self._Fa[ns], self._Qa[ns]

    def r2(self, conf) -> np.ndarray:
        """Measurement variance per axis for confidence(s) ``conf``."""
        return (self.meas_px / np.maximum(np.asarray(conf, dtype=np.float64), 0.05)) ** 2

    def init(self, xy, conf: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """State at a first detection: position variance of a conf=1 detection, or of ``conf``."""
        r2 = self.meas_px ** 2 if conf is None else float(self.r2(conf))
        return np.array([xy[0], xy[1], 0.0, 0.0], dtype=np.float64), np.diag([r2, r2, self.v0, self.v0])

    def predict(self, x, P, kick: bool = False, W: Optional[np.ndarray] = None, cam_var: float = 0.0):
        """One step. ``kick``: the velocity is reset before this step (a touch / kick at the current
        frame), so the next position already moves with the new, unknown velocity. ``W``: the camera's
        homography into the next frame (the state is mapped there); ``cam_var``: extra position variance
        (a failed camera estimate). Returns x, P and the linearised transition (for the smoother)."""
        F, Q = self.FQ(1)
        if kick:
            P = P + self.Q_kick
        x, P, Fe = F @ x, F @ P @ F.T + Q, F
        if W is not None:
            X, Pw, A = _warp_states(W, x[None], P[None])
            x, P, Fe = X[0], Pw[0], A[0] @ F
        if cam_var > 0:
            P = P + cam_var * _POS
        return x, P, Fe

    def update(self, x, P, z, conf: float):
        """Joseph-form update. Returns x, P."""
        r2 = float(self.r2(conf))
        S = P[:2, :2] + r2 * _I2
        K = np.linalg.solve(S, P[:2, :]).T                         # P H^T S^-1 (S symmetric)
        x = x + K @ (np.asarray(z, dtype=np.float64) - x[:2])
        IKH = _I4 - K @ _H
        return x, IKH @ P @ IKH.T + r2 * (K @ K.T)


class _CVKalman:
    """A running filter on ``_Motion`` (online pass and provisional tracks)."""

    def __init__(self, xy, m: _Motion):
        self.m = m
        self.x, self.P = m.init(xy)

    def predict(self, kick: bool = False, W: Optional[np.ndarray] = None, cam_var: float = 0.0) -> np.ndarray:
        self.x, self.P, _ = self.m.predict(self.x, self.P, kick, W, cam_var)
        return self.x[:2]

    def update(self, xy, conf: float = 1.0) -> None:
        self.x, self.P = self.m.update(self.x, self.P, xy, conf)


def _filter(z: np.ndarray, conf: np.ndarray, kick_into: np.ndarray, m: _Motion,
            warps: Optional[Sequence] = None, cam_var: Optional[np.ndarray] = None):
    """Forward Kalman pass over consecutive frames.

    ``z``: (T, 2) centres (each in its own frame's pixels), NaN where there is no detection (the first
    row must be one); ``conf``: (T,) confidences; ``kick_into[t]``: the velocity may jump in the step into
    frame t; ``warps[t]`` / ``cam_var[t]``: the camera's homography into frame t and the extra position
    variance of that step (``None``: fixed camera). Returns predicted (``xp``, ``Pp``: before the update at
    t, i.e. from earlier frames only) and filtered (``xf``, ``Pf``) states, and the linearised transitions
    ``Fe`` into each frame."""
    T = len(z)
    xp, Pp = np.zeros((T, 4)), np.zeros((T, 4, 4))
    xf, Pf = np.zeros((T, 4)), np.zeros((T, 4, 4))
    Fe = np.zeros((T, 4, 4))
    x, P = m.init(z[0])
    xp[0], Pp[0], xf[0], Pf[0], Fe[0] = x, P, x, P, _I4
    for t in range(1, T):
        x, P, Fe[t] = m.predict(x, P, bool(kick_into[t]), None if warps is None else warps[t],
                                0.0 if cam_var is None else float(cam_var[t]))
        xp[t], Pp[t] = x, P
        if np.isfinite(z[t]).all():
            x, P = m.update(x, P, z[t], conf[t])
        xf[t], Pf[t] = x, P
    return xp, Pp, xf, Pf, Fe


def _smooth(xp, Pp, xf, Pf, Fe) -> Tuple[np.ndarray, np.ndarray]:
    """RTS backward pass over a ``_filter`` run (linearised transitions ``Fe``). Returns smoothed states
    (T, 4) and covariances."""
    xs, Ps = xf.copy(), Pf.copy()
    for t in range(len(xf) - 2, -1, -1):
        C = np.linalg.solve(Pp[t + 1], Fe[t + 1] @ Pf[t]).T         # Pf Fe^T Pp^-1 (Pp symmetric)
        xs[t] = xf[t] + C @ (xs[t + 1] - xp[t + 1])
        Ps[t] = Pf[t] + C @ (Ps[t + 1] - Pp[t + 1]) @ C.T
    return xs, Ps


class _Tentative:
    """A provisional track started from a weak candidate (online pass)."""

    def __init__(self, i: int, row: np.ndarray, xy: np.ndarray, m: _Motion):
        self.kf = _CVKalman(xy, m)
        self.kf.update(xy, row[4])
        self.picks = [(i, row.copy())]          # (frame, [x, y, w, h, conf])
        self.xy = [np.asarray(xy, dtype=np.float64)]
        self.misses = 0

    def hit(self, i: int, row: np.ndarray, xy: np.ndarray) -> None:
        self.kf.update(xy, row[4])
        self.picks.append((i, row.copy()))
        self.xy.append(np.asarray(xy, dtype=np.float64))
        self.misses = 0

    @property
    def mean_conf(self) -> float:
        return float(np.mean([r[4] for _, r in self.picks]))


class _Tracklet:
    """A short chain of candidates (global linking). Keeps the forward-filtered state at every detection."""
    __slots__ = ("x", "P", "frames", "rows", "xy", "foot", "d2", "misses", "xf", "Pf")

    def __init__(self, m: _Motion, i: int, row: np.ndarray, xy: np.ndarray, foot: bool):
        self.x, self.P = m.init(xy, row[4])
        self.frames, self.rows, self.xy, self.foot, self.d2 = [i], [row.copy()], [xy.copy()], [foot], [0.0]
        self.xf, self.Pf = [self.x], [self.P]
        self.misses = 0

    def hit(self, m: _Motion, i: int, row: np.ndarray, xy: np.ndarray, foot: bool, d2: float) -> None:
        self.x, self.P = m.update(self.x, self.P, xy, row[4])
        self.frames.append(i)
        self.rows.append(row.copy())
        self.xy.append(xy.copy())
        self.foot.append(foot)
        self.d2.append(float(d2))
        self.xf.append(self.x)
        self.Pf.append(self.P)
        self.misses = 0


class BallTracker(Tracker):

    def __init__(self, tracker_params: Dict[str, Any], fps: float = REFERENCE_FPS, device: str = "cpu", **kwargs):
        super().__init__(tracker_params, device, **kwargs)
        p = self.tracker_params
        unknown = sorted(k for k in p if k not in DEFAULTS and k not in _OTHER_KEYS)
        if unknown:
            logger.warning("ball_tracker: unknown tracker_params key(s) ignored: %s", ", ".join(unknown))
        self.fps = float(fps)
        self.vel_scale = REFERENCE_FPS / self.fps
        c = scale_to_fps({**DEFAULTS, **{k: v for k, v in p.items() if k in DEFAULTS and v is not None}}, self.fps)
        self.params = c
        for key, default in DEFAULTS.items():
            setattr(self, key, type(default)(c[key]))
        self.linking, self.motion_model = self.linking.lower(), self.motion_model.lower()
        if self.linking not in ("online", "global"):
            raise ValueError(f"ball_tracker: linking must be 'online' or 'global', got {self.linking!r}")
        self.model = _Motion(self.motion_model, self.accel_px, self.meas_px, self.vel_scale)
        self.camera_motion: Optional[CameraMotion] = None    # of the last track() call
        self._cm: Optional[CameraMotion] = None
        self._failcum = None
        self._logit_ref = float(_logit(self.init_conf))
        if self.fps != REFERENCE_FPS:
            logger.info("ball_tracker: frame-based parameters scaled from %.0f to %.2f fps", REFERENCE_FPS, self.fps)

    @property
    def usable(self) -> bool:
        """Below ``min_fps`` the ball moves too far between frames to associate it; the caller then writes
        the candidates untracked."""
        return self.fps >= self.min_fps

    # -- pipeline interface ---------------------------------------------------
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> List[np.ndarray]:
        """Per frame ``(N, 5)`` candidates ``[x, y, w, h (tlwh), conf]``; ``detections`` holds ball-class
        detector dicts only, in frame pixels."""
        cands = []
        for dets in inputs.get("detections") or []:
            rows = [(*np.asarray(d["xyxy"], dtype=np.float64)[:4], float(d["conf"])) for d in (dets or [])
                    if float(d["conf"]) >= self.min_conf]
            a = np.asarray(rows, dtype=np.float64).reshape(-1, 5)
            a[:, 2:4] -= a[:, 0:2]              # xyxy -> tlwh
            cands.append(a)
        return cands

    def _filter_static(self, candidates: List[np.ndarray]) -> List[np.ndarray]:
        """Drop decoys (see the module docstring): clusters (radius ``static_radius_px``) with >=
        ``static_min_hits`` hits spanning >= ``static_min_span`` frames, in >= ``static_cooccur`` of whose
        frames another candidate (not static, conf >= ``static_cooccur_conf``, > 2 radii away) is visible.
        Clusters are grown densest first from 3x3 grid neighbourhoods and re-centred on their median, so a
        spot on a grid-cell edge is found as one. With camera motion, positions are in frame 0's plane and
        distances are converted back to each candidate's own frame pixels (local scale ``sc``)."""
        if not self.static_filter or sum(len(c) for c in candidates) < self.static_min_hits:
            return candidates
        fr = np.concatenate([np.full(len(c), i) for i, c in enumerate(candidates)]).astype(np.int64)
        idx = np.concatenate([np.arange(len(c)) for c in candidates]).astype(np.int64)
        xy = np.concatenate([c[:, :2] + c[:, 2:4] / 2.0 for c in candidates])
        conf = np.concatenate([c[:, 4] for c in candidates])
        sc = np.ones(len(xy))                                 # plane px per frame px
        if self._cm is not None:
            Hm = self._cm.to_mosaic(fr)
            sc = np.sqrt(np.abs(np.linalg.det(h_jacobian(Hm, xy))))
            xy = apply_h(Hm, xy)
        rad = max(self.static_radius_px, 1e-6)
        cell = np.floor(xy / (rad * float(np.median(sc)))).astype(np.int64)
        keys = cell[:, 0] * 1_000_003 + cell[:, 1]
        by_cell: Dict[int, List[int]] = {}
        for p, kk in enumerate(keys):
            by_cell.setdefault(int(kk), []).append(p)
        cell_xy = {int(kk): (int(cx), int(cy)) for kk, cx, cy in zip(keys, cell[:, 0], cell[:, 1])}

        def neighbourhood(cx, cy):
            out = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    out.extend(by_cell.get((cx + dx) * 1_000_003 + (cy + dy), ()))
            return out

        dens = sorted(((len(neighbourhood(*cell_xy[kk])), kk) for kk in by_cell), reverse=True)
        assigned = np.zeros(len(xy), dtype=bool)
        clusters = []
        for cnt, kk in dens:
            if cnt < self.static_min_hits:
                break
            pts = np.array([p for p in neighbourhood(*cell_xy[kk]) if not assigned[p]], dtype=np.int64)
            if pts.size < self.static_min_hits:
                continue
            centre = np.median(xy[pts], axis=0)
            member = pts
            for _ in range(2):                                # re-centre on the points in range
                member = pts[np.linalg.norm(xy[pts] - centre, axis=1) / sc[pts] <= rad]
                if not member.size:
                    break
                centre = np.median(xy[member], axis=0)
            frames = np.unique(fr[member]) if member.size else np.zeros(0, dtype=np.int64)
            if frames.size < self.static_min_hits or frames[-1] - frames[0] < self.static_min_span:
                continue
            assigned[member] = True
            clusters.append((member, centre, frames))
        if not clusters:
            return candidates

        partner = ~assigned & (conf >= self.static_cooccur_conf)
        drop = np.zeros(len(xy), dtype=bool)
        n_drop_loc = n_keep_loc = 0
        for member, centre, frames in clusters:
            if self.static_cooccur <= 0:
                frac = 1.0
            else:
                ok = partner & np.isin(fr, frames) & (np.linalg.norm(xy - centre, axis=1) / sc > 2.0 * rad)
                frac = np.unique(fr[ok]).size / frames.size
            if frac >= self.static_cooccur:
                drop[member] = True
                n_drop_loc += 1
            else:
                n_keep_loc += 1
        if not drop.any():
            logger.info("ball_tracker: static-object filter kept %d static location(s) seen alone (ball at rest)",
                        n_keep_loc)
            return candidates
        dropped: Dict[int, set] = {}
        for p in np.flatnonzero(drop):
            dropped.setdefault(int(fr[p]), set()).add(int(idx[p]))
        out = []
        for i, c in enumerate(candidates):
            if i in dropped:
                c = c[[j for j in range(len(c)) if j not in dropped[i]]]
            out.append(c)
        logger.info("ball_tracker: static-object filter dropped %d candidate(s) at %d decoy location(s) (never moving "
                    "ball-class detections, e.g. a cone or a spare ball), kept %d static location(s) seen alone "
                    "(ball at rest)", int(drop.sum()), n_drop_loc, n_keep_loc)
        return out

    def process(self, inputs: Dict[Any, Any], **kwargs) -> List[Dict[str, Any]]:
        """``inputs``: ``detections`` (per-frame detector output), optionally ``players`` (per-frame player
        track boxes), ``box_format`` of those boxes (default tlwh) and ``camera_motion`` (a ``CameraMotion``;
        given, the tracker compensates it)."""
        feet = self._player_feet(inputs.get("players"), inputs.get("box_format", "tlwh"))
        return self.track(self.preprocess(inputs, **kwargs), player_feet=feet,
                          camera_motion=inputs.get("camera_motion"))

    # -- camera motion helpers (identity without compensation) -----------------
    def _fail_var(self, t: int) -> float:
        """Extra position variance of the camera step into frame ``t`` (a failed estimate)."""
        return 0.0 if self._cm is None or t <= 0 or self._cm.ok[t] else self.cam_fail_px ** 2

    def _cam_step(self, t: int) -> Tuple[Optional[np.ndarray], float]:
        """The camera's homography into frame ``t`` and that step's extra position variance."""
        if self._cm is None or t <= 0:
            return None, 0.0
        return self._cm.step(t), self._fail_var(t)

    def _map(self, xy, a: int, b: int) -> np.ndarray:
        """Point(s) from frame ``a``'s pixels to frame ``b``'s."""
        if self._cm is None or a == b:
            return np.asarray(xy, dtype=np.float64)
        return apply_h(self._cm.between(int(a), int(b)), xy).reshape(np.shape(xy))

    def _common_xy(self, frames: Sequence[int], xy: np.ndarray, ref: int) -> np.ndarray:
        """Positions (N, 2), each in its own frame, in frame ``ref``'s pixels."""
        xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
        if self._cm is None:
            return xy
        return np.vstack([self._map(p, f, ref) for f, p in zip(frames, xy)])

    def _span_warps(self, a0: int, T: int):
        """Camera steps for a span of ``T`` frames from ``a0``: forward (into local frame t) and backward
        (reversed index r: from frame a0+T-r into a0+T-1-r) homographies and extra variances."""
        if self._cm is None:
            return None, None, None, None
        fw = [None] + [self._cm.step(a0 + t) for t in range(1, T)]
        fv = np.array([0.0] + [self._fail_var(a0 + t) for t in range(1, T)])
        bw = [None] + [self._cm.rel[a0 + T - r] for r in range(1, T)]
        bv = np.array([0.0] + [self._fail_var(a0 + T - r) for r in range(1, T)])
        return fw, fv, bw, bv

    def _player_feet(self, players, box_format: str) -> Optional[List[np.ndarray]]:
        """Per frame ``(N, 4)`` player foot points and box sizes ``[fx, fy, w, h]``."""
        if not self.player_hint or players is None:
            return None
        out = []
        for boxes in players:
            b = np.asarray(boxes if boxes is not None else [], dtype=np.float64).reshape(-1, 4)
            wh = b[:, 2:4] - b[:, 0:2] if str(box_format).lower() == "xyxy" else b[:, 2:4]
            out.append(np.c_[_foot_points(b, box_format), wh] if len(b) else np.zeros((0, 4)))
        return out

    def _near_foot(self, feet: Optional[List[np.ndarray]], i: int, xy) -> bool:
        """Ball centre ``xy`` within ``foot_reach`` box widths of a player's foot point in frame ``i``."""
        if feet is None or i >= len(feet) or not len(feet[i]) or not np.isfinite(xy).all():
            return False
        f = feet[i]
        return bool((np.linalg.norm(f[:, :2] - np.asarray(xy)[None], axis=1) <= self.foot_reach * f[:, 2]).any())

    def _on_body(self, feet: Optional[List[np.ndarray]], i: int, centres: np.ndarray) -> np.ndarray:
        """Candidates on the upper ``tentative_skip_body`` of a player box (torso / head clutter)."""
        out = np.zeros(len(centres), dtype=bool)
        if feet is None or self.tentative_skip_body <= 0 or i >= len(feet) or not len(feet[i]) or not len(centres):
            return out
        f = feet[i]
        dx = np.abs(centres[:, None, 0] - f[None, :, 0]) <= f[None, :, 2] / 2.0
        top = f[None, :, 1] - f[None, :, 3]
        dy = (centres[:, None, 1] >= top) & (centres[:, None, 1] <= top + self.tentative_skip_body * f[None, :, 3])
        return (dx & dy).any(axis=1)

    def _gate(self, missed, conf: np.ndarray, at_foot) -> np.ndarray:
        """Gate radius for a track / tracklet: the growth while the ball is unseen scales with confidence,
        unless the ball was last seen at a player's foot (a kicked ball is blurred -> weak). Broadcasts
        ``missed`` / ``at_foot`` against ``conf``."""
        w = np.clip((conf - self.min_conf) / max(self.init_conf - self.min_conf, 1e-6), 0.0, 1.0)
        grow = self.gate_growth_px * np.asarray(missed, dtype=np.float64)
        return np.where(at_foot, self.gate_px + self.kick_vel_px + grow * np.ones_like(w), self.gate_px + grow * w)

    def _log_lr(self, conf) -> np.ndarray:
        """log p(conf | ball) / p(conf | clutter), neutral at ``init_conf``."""
        return self.lr_scale * (_logit(conf) - self._logit_ref)

    # -- tracking -------------------------------------------------------------
    def track(self, candidates: List[np.ndarray], player_feet: Optional[List[np.ndarray]] = None,
              camera_motion: Optional[CameraMotion] = None, **kwargs) -> List[Dict[str, Any]]:
        """``candidates``: per frame (N, 5) ``[x, y, w, h, conf]`` (``preprocess``); ``camera_motion``: the
        camera's frame-to-frame homographies (``None``: fixed camera)."""
        self.reset_state()
        n = len(candidates)
        if camera_motion is not None and len(camera_motion) != n:
            raise ValueError(f"ball_tracker: camera motion for {len(camera_motion)} frames, {n} frames of candidates")
        self.camera_motion = self._cm = camera_motion
        if camera_motion is not None:
            fv = np.array([self._fail_var(t) for t in range(n)])
            self._failcum = np.cumsum(fv)                     # sum of the failed steps' variance into frame t
        cands = self._filter_static([np.asarray(c, dtype=np.float64).reshape(-1, 5) for c in candidates])
        link = self._link_global if self.linking == "global" else self._link_online
        box, score, seg, n_seg, info = link(cands, player_feet)

        status = np.where(seg >= 0, 1, 0)
        sigma = np.full(n, np.nan)
        stats = np.zeros(2, dtype=int)                       # dropped outliers, kept kick corners
        for s in range(n_seg):
            stats += self._refine_segment(box, score, seg, status, sigma, s, player_feet)
        self.state = [{"frame_id": i,
                       "ball_box": None if status[i] == 0 else box[i].copy(),
                       "ball_score": float(score[i]),
                       "ball_segment": int(seg[i]),
                       "ball_status": STATUS[status[i]],
                       "ball_sigma": None if status[i] == 0 or not np.isfinite(sigma[i]) else float(sigma[i])}
                      for i in range(n)]
        self.frame_id = n
        n_det, n_int = int((status == 1).sum()), int((status == 2).sum())
        logger.info("ball_tracker (%s linking): ball in %d/%d frames (%d detected, %d interpolated), %d segment(s), "
                    "%s; %d weak detection(s) dropped as outliers, %d kick corner(s)%s%s.", self.linking, n_det + n_int,
                    n, n_det, n_int, n_seg, info, stats[0], stats[1],
                    "" if player_feet is not None else " (no player hint)",
                    "" if camera_motion is None else " (camera compensated)")
        return self.state

    # -- online linking -------------------------------------------------------
    def _link_online(self, candidates: List[np.ndarray], player_feet: Optional[List[np.ndarray]]):
        """Frame-by-frame pass. Returns per-frame box, score, segment, the number of segments and a log note."""
        n = len(candidates)
        box = np.full((n, 4), np.nan)
        score = np.zeros(n)
        seg = np.full(n, -1, dtype=np.int64)

        kf, missed, far_hits, segment = None, 0, 0, -1
        at_foot = False                 # last seen at a player's foot -> may have been kicked since
        last_seen = None                # (frame, centre) of the last detection of a confirmed track
        tentatives: List[_Tentative] = []
        n_confirmed = n_lead_in = 0
        for i, c in enumerate(candidates):
            centres = c[:, :2] + c[:, 2:4] / 2.0 if len(c) else np.zeros((0, 2))
            W, cv = self._cam_step(i)                       # camera motion into this frame
            pick = None
            if kf is not None:
                pred = kf.predict(at_foot and missed == 0, W, cv)  # the velocity jumps once, at the touch
                gate = self._gate(missed, c[:, 4], at_foot) if len(c) else np.zeros(0)
                d = np.linalg.norm(centres - pred, axis=1) if len(c) else np.zeros(0)
                inside = np.flatnonzero(d <= gate)
                # a confident candidate outside the gate while the track has only weak ones inside (or
                # none): after switch_frames such frames the track is on clutter / the ball went elsewhere
                strong_out = bool(len(c)) and bool((c[d > gate, 4] >= self.init_conf).any())
                weak_in = not (c[inside, 4] >= self.init_conf).any() if inside.size else True
                far_hits = far_hits + 1 if (strong_out and weak_in) else 0
                if far_hits >= self.switch_frames:
                    kf, inside = None, np.zeros(0, int)       # re-acquire below
                elif inside.size:
                    # nearest to the prediction, confident candidates preferred
                    pick = int(inside[np.argmin(d[inside] / gate[inside] - 0.5 * c[inside, 4])])
                    kf.update(centres[pick], c[pick, 4])
                    missed = 0
                else:
                    missed += 1
                    if missed > self.max_missed:
                        kf = None           # lost -> re-acquire below
            if kf is None:
                strong = np.flatnonzero(c[:, 4] >= self.init_conf) if len(c) else np.zeros(0, int)
                # an *immediate* re-acquire: only for a confident candidate near where the ball was
                # last genuinely seen (a ball at rest where it was lost reappearing there, say). Any
                # other confident candidate -- far away, or before the ball has ever been seen -- must
                # instead earn it via the tentative/_plausible path below, same as a weak detection:
                # otherwise a static, confidently-detected decoy (a cone, a spare ball) far from the
                # last known position would be trusted on a single frame with no check it ever moves.
                near = (strong[np.linalg.norm(centres[strong] - self._map(last_seen[1], last_seen[0], i), axis=1)
                               <= self.reacquire_px]
                        if strong.size and last_seen is not None else np.zeros(0, dtype=int))
                if near.size:
                    pick = int(near[np.argmax(c[near, 4])])
                    segment += 1
                    missed, far_hits = 0, 0
                    lead = self._lead_in(tentatives, centres[pick], W, cv)
                    if lead is not None:        # a provisional track runs into it: keep its detections
                        for j, row in lead.picks:
                            box[j], score[j], seg[j] = row[:4], row[4], segment
                        kf = lead.kf
                        kf.update(centres[pick], c[pick, 4])
                        n_lead_in += len(lead.picks)
                    else:
                        kf = _CVKalman(centres[pick], self.model)
            if pick is not None:
                box[i], score[i], seg[i] = c[pick, :4], c[pick, 4], segment
                at_foot = self._near_foot(player_feet, i, centres[pick])
                last_seen = (i, centres[pick])
                tentatives = []
                continue
            # the ball is unseen (track coasting or lost): look for it among the weak candidates
            ok = ~self._on_body(player_feet, i, centres)
            tr = self._step_tentatives(tentatives, i, c[ok], centres[ok], last_seen, W, cv)
            if tr is not None:              # confirmed: take it over and write its detections back
                first = tr.picks[0][0]
                join = last_seen is not None and first - last_seen[0] <= self.max_gap + 1
                segment += 0 if join else 1
                for j, row in tr.picks:
                    box[j], score[j], seg[j] = row[:4], row[4], segment
                kf, missed, far_hits, tentatives = tr.kf, 0, 0, []
                at_foot = self._near_foot(player_feet, tr.picks[-1][0], tr.xy[-1])
                last_seen = (tr.picks[-1][0], tr.xy[-1])
                n_confirmed += 1
        info = f"{n_confirmed} re-acquired from weak detections, {n_lead_in} weak lead-in detection(s)"
        return box, score, seg, segment + 1, info

    def _step_tentatives(self, tentatives: List[_Tentative], i: int, c: np.ndarray, centres: np.ndarray,
                         last_seen, W: Optional[np.ndarray] = None, cv: float = 0.0) -> Optional[_Tentative]:
        """Advance the provisional tracks by frame ``i`` (in place; ``W``, ``cv``: the camera step into it)
        and return one that is now confirmed, if any."""
        used = set()
        for tr in sorted(tentatives, key=lambda t: -len(t.picks)):   # longer tracks choose first
            pred = tr.kf.predict(False, W, cv)
            gate = self.tentative_gate_px + self.gate_growth_px * tr.misses
            d = np.linalg.norm(centres - pred, axis=1) if len(c) else np.zeros(0)
            free = [j for j in np.argsort(d) if j not in used and d[j] <= gate]
            if free:
                tr.hit(i, c[free[0]], centres[free[0]])
                used.add(free[0])
            else:
                tr.misses += 1
        tentatives[:] = [t for t in tentatives if t.misses <= self.tentative_max_missed]
        for j in range(len(c)):                                        # unclaimed candidates start new ones
            if j not in used:
                tentatives.append(_Tentative(i, c[j], centres[j], self.model))
        ready = [t for t in tentatives if t.misses == 0 and len(t.picks) >= self.confirm_frames
                 and self._plausible(t, last_seen)]
        return max(ready, key=lambda t: (len(t.picks), t.mean_conf)) if ready else None

    def _lead_in(self, tentatives: List[_Tentative], xy: np.ndarray, W: Optional[np.ndarray] = None,
                 cv: float = 0.0) -> Optional[_Tentative]:
        """The provisional track (>= 2 detections) whose prediction for this frame reaches ``xy``,
        i.e. the weak detections of the ball just before a confident one; longest first."""
        for tr in sorted(tentatives, key=lambda t: -len(t.picks)):
            if len(tr.picks) < 2:
                continue
            pred = tr.kf.predict(False, W, cv)
            if np.linalg.norm(pred - xy) <= self.tentative_gate_px + self.gate_growth_px * tr.misses:
                return tr
        return None

    def _plausible(self, tr: _Tentative, last_seen) -> bool:
        """Could this provisional track be the ball that was lost at ``last_seen``? Its recent
        detections must lie on a smooth (constant-velocity) path; "moving" means covering at least
        ``min_move_px`` along it -- hopping between static clutter spots is neither."""
        frames = [i for i, _ in tr.picks[-30:]]               # _cv_motion looks at the last 30 at most
        xy = self._common_xy(frames, tr.xy[-30:], frames[-1])
        covered = _cv_motion(np.asarray(frames), xy, self.confirm_frames, self.tentative_resid_px)
        if covered < 0:
            return False
        moving = covered >= self.min_move_px
        if last_seen is None:
            return moving
        f0 = tr.picks[0][0]
        dist = float(np.linalg.norm(tr.xy[0] - self._map(last_seen[1], last_seen[0], f0)))
        if dist <= self.reacquire_px:
            return True
        radius = self.reacquire_px + self.reacquire_growth_px * (tr.picks[0][0] - last_seen[0])
        return moving and (dist <= radius or radius >= self.reacquire_max_px)

    # -- global linking: tracklets --------------------------------------------
    def _link_global(self, candidates: List[np.ndarray], player_feet: Optional[List[np.ndarray]]):
        """Tracklets, then the best path through them. Same outputs as ``_link_online``."""
        n = len(candidates)
        tracklets = self._build_tracklets(candidates, player_feet)
        path = self._best_path(tracklets)
        box = np.full((n, 4), np.nan)
        score = np.zeros(n)
        seg = np.full(n, -1, dtype=np.int64)
        segment, n_links, n_trimmed = -1, np.zeros(4, dtype=int), 0
        for t_idx, etype, keep in path:
            tr = tracklets[t_idx]
            n_links[etype] += 1
            n_trimmed += len(tr["frames"]) - keep
            if etype != _CONT:
                segment += 1
            f = tr["frames"][:keep]
            box[f], score[f], seg[f] = tr["rows"][:keep, :4], tr["rows"][:keep, 4], segment
        info = (f"{len(path)} of {len(tracklets)} tracklet(s) on the path ({n_links[_CONT]} continued, "
                f"{n_links[_RESUME]} resumed, {n_links[_RESTART] + n_links[_START]} started; {n_trimmed} weak tail "
                f"detection(s) trimmed)")
        return box, score, seg, segment + 1, info

    def _build_tracklets(self, candidates: List[np.ndarray], feet: Optional[List[np.ndarray]]) -> List[Dict[str, Any]]:
        m = self.model
        F1, Q1 = m.FQ(1)
        active: List[_Tracklet] = []
        done: List[_Tracklet] = []
        for i, c in enumerate(candidates):
            ctr = c[:, :2] + c[:, 2:4] / 2.0
            used = np.zeros(len(c), dtype=bool)
            if active:                                         # batched predict
                X = np.stack([tr.x for tr in active])
                P = np.stack([tr.P for tr in active])
                kicked = np.array([tr.foot[-1] for tr in active])
                misses = np.array([tr.misses for tr in active], dtype=np.float64)
                P = P + np.where((kicked & (misses == 0))[:, None, None], m.Q_kick[None], 0.0)  # jumps once, at the touch
                X = X @ F1.T
                P = F1 @ P @ F1.T + Q1
                Wc, cv = self._cam_step(i)                     # camera motion into this frame
                if Wc is not None:
                    X, P, _ = _warp_states(Wc, X, P)
                if cv > 0:
                    P = P + cv * _POS
                for a, tr in enumerate(active):
                    tr.x, tr.P = X[a], P[a]
                taken = np.zeros(len(active), dtype=bool)
                if len(c):
                    y = ctr[None, :, :] - X[:, None, :2]
                    d2 = _maha(y, P[:, None, :2, :2] + m.r2(c[:, 4])[None, :, None, None] * _I2)[0]
                    d = np.linalg.norm(y, axis=2)
                    gate = self._gate(misses[:, None], c[None, :, 4], kicked[:, None])
                    cost = d / gate - 0.5 * c[None, :, 4]
                    aa, jj = np.nonzero(d <= gate)
                    for k in np.argsort(cost[aa, jj], kind="stable"):   # greedy by cost (one ball: few candidates)
                        a, j = aa[k], jj[k]
                        if taken[a] or used[j]:
                            continue
                        active[a].hit(m, i, c[j], ctr[j], self._near_foot(feet, i, ctr[j]), d2[a, j])
                        taken[a] = used[j] = True
                for a in np.flatnonzero(~taken):
                    active[a].misses += 1
            keep = []
            for tr in active:
                (keep if tr.misses <= self.tracklet_max_missed else done).append(tr)
            active = keep
            if len(c):
                body = self._on_body(feet, i, ctr) & (c[:, 4] < self.init_conf)   # weak torso / head clutter
                for j in np.flatnonzero(~used & ~body):
                    active.append(_Tracklet(m, i, c[j], ctr[j], self._near_foot(feet, i, ctr[j])))
        done.extend(active)

        out = []
        for tr in done:
            conf = np.array([r[4] for r in tr.rows])
            if len(tr.frames) < self.min_tracklet_len and conf.max() < self.init_conf:
                continue
            out.append(self._summarise(tr, conf))
        out.sort(key=lambda t: (t["start"], t["end"]))
        return out

    def _summarise(self, tr: _Tracklet, conf: np.ndarray) -> Dict[str, Any]:
        """Start state (backward filter over the tracklet; the forward states were kept while building),
        eligibility and score."""
        frames = np.asarray(tr.frames, dtype=np.int64)
        xy = np.asarray(tr.xy)
        a0, a1 = frames[0], frames[-1]
        if len(frames) == 1:
            xs0, Ps0 = tr.xf[0], tr.Pf[0]
        else:
            z = np.full((a1 - a0 + 1, 2), np.nan)
            z[frames - a0] = xy
            cspan = np.zeros(a1 - a0 + 1)
            cspan[frames - a0] = conf
            kick = np.zeros(a1 - a0 + 1, dtype=bool)
            kick[frames[np.asarray(tr.foot, dtype=bool)] - a0] = True
            _, _, bw, bv = self._span_warps(int(a0), len(z))
            bf, bPf = _filter(z[::-1], cspan[::-1], kick[::-1], self.model, bw, bv)[2:4]   # reversed: t+1 -> t
            flip = np.diag([1.0, 1.0, -1.0, -1.0])                                # reversed time -> forward velocity
            xs0, Ps0 = bf[-1] @ flip, flip @ bPf[-1] @ flip
        covered = -1.0
        if len(frames) >= self.confirm_frames:                # a CV-consistent run at either end (a tail or
            xyc = self._common_xy(frames, xy, int(a1))        # head may hold clutter), in one frame's pixels
            covered = max(_cv_motion(frames, xyc, self.confirm_frames, self.tentative_resid_px),
                          _cv_motion(frames[::-1], xyc[::-1], self.confirm_frames, self.tentative_resid_px))
        eligible = covered >= 0 and (covered >= self.min_move_px or conf.mean() >= self.init_conf)
        d2 = np.asarray(tr.d2)
        d2[0] = 0.0
        dscore = self.det_reward + self._log_lr(conf) - 0.5 * d2
        return {"frames": frames, "rows": np.asarray(tr.rows), "xy": xy, "foot": np.asarray(tr.foot, dtype=bool),
                "start": int(a0), "end": int(a1), "xs": xs0, "Ps": Ps0,
                "xfd": np.asarray(tr.xf), "Pfd": np.asarray(tr.Pf), "dscore": dscore, "weak": conf < self.init_conf,
                "eligible": bool(eligible), "node": float(dscore.sum())}

    # -- global linking: best path --------------------------------------------
    def _continuations(self, b: Dict[str, Any], s: int, xe: np.ndarray, Pe: np.ndarray, fe: np.ndarray,
                       ee: np.ndarray, base: np.ndarray) -> np.ndarray:
        """Continuation scores into tracklet ``b`` (starting at ``s``) from predecessor end states ``xe``,
        ``Pe`` (at frames ``ee``, kicked if ``fe``) with path scores ``base``; -inf where inadmissible."""
        m = self.model
        g = (s - ee).astype(np.int64)                        # >= 1 steps
        _, Q = m.FQ_stack(g)
        P = Pe + np.where(fe[:, None, None], m.Q_kick[None], 0.0)
        gg = g[:, None].astype(np.float64)
        xp = xe[:, :2] + gg * xe[:, 2:]                      # constant velocity over g frames
        gq = g[:, None, None].astype(np.float64)
        Ppos = P[:, :2, :2] + gq * (P[:, :2, 2:] + P[:, 2:, :2]) + gq ** 2 * P[:, 2:, 2:] + Q[:, :2, :2]
        if self._cm is not None:                             # predicted in the predecessor's frame -> frame s
            for j in range(len(g)):
                H = self._cm.between(int(ee[j]), int(s))
                J = h_jacobian(H, xp[j][None])[0]
                xp[j] = apply_h(H, xp[j][None])[0]
                Ppos[j] = J @ Ppos[j] @ J.T + (self._failcum[s] - self._failcum[ee[j]]) * _I2
        y = xp - b["xs"][None, :2]
        d2, _ = _maha(y, Ppos + b["Ps"][None, :2, :2])
        ok = np.linalg.norm(y, axis=1) <= np.minimum(self.gate_px + self.gate_growth_px * g, self.reacquire_max_px)
        if not b["eligible"]:
            # a short / unconfirmed chain is only evidence where the prediction into it is precise; across a
            # long gap it would be inserted just for its detection reward (clutter mid-gap)
            ok &= np.sqrt(np.linalg.eigvalsh(Ppos)[:, -1]) <= self.support_sigma_px
        sc = base - self.miss_cost * (g - 1) - 0.5 * d2
        sc[~ok] = -np.inf
        return sc

    def _best_path(self, T: List[Dict[str, Any]]) -> List[Tuple[int, int, int]]:
        """Best non-overlapping chain of tracklets. Returns [(tracklet index, link type into it, number of its
        detections kept)]. A continuation may trim up to ``link_trim_max`` *weak* trailing detections off its
        predecessor (a coasting tracklet that picked up clutter before the ball's next tracklet starts)."""
        N = len(T)
        if not N:
            return []
        start = np.array([t["start"] for t in T])
        end = np.array([t["end"] for t in T])
        first = np.array([t["xy"][0] for t in T])
        last = np.array([t["xy"][-1] for t in T])
        xe = np.array([t["xfd"][-1] for t in T])
        Pe = np.array([t["Pfd"][-1] for t in T])
        fe = np.array([t["foot"][-1] for t in T])
        best = np.full(N, -np.inf)
        pred = np.full(N, -1, dtype=np.int64)
        pred_keep = np.full(N, -1, dtype=np.int64)          # detections of pred kept (-1: all)
        etype = np.zeros(N, dtype=np.int64)

        by_end = np.argsort(end, kind="stable")
        end_sorted = end[by_end]
        W = max(self.link_max_gap + 1, self.resume_max_gap)
        ptr, run_best, run_arg = 0, 0.0, -1                  # best path ending before the current start (0 = empty)
        for b in range(N):                                   # T is sorted by start
            s = start[b]
            while ptr < N and end_sorted[ptr] < s:
                a = by_end[ptr]
                if best[a] > run_best:
                    run_best, run_arg = best[a], a
                ptr += 1
            opts = []                                        # (score, pred, type, keep)
            if T[b]["eligible"]:
                opts.append((run_best - self.birth_cost, run_arg, _START if run_arg < 0 else _RESTART, -1))
            # predecessors that ended in [s - W, s - 1]: a contiguous run of by_end[:ptr]
            lo = np.searchsorted(end_sorted[:ptr], s - W, side="left")
            cand = by_end[lo:ptr]
            cand = cand[np.isfinite(best[cand])]
            cont_ok = np.zeros(cand.size, dtype=bool)
            if cand.size:
                cm = np.flatnonzero(s - end[cand] <= self.link_max_gap + 1)
                if cm.size:
                    ca = cand[cm]
                    sc = self._continuations(T[b], s, xe[ca], Pe[ca], fe[ca], end[ca], best[ca])
                    cont_ok[cm] = np.isfinite(sc)
                    if cont_ok.any():
                        k = int(np.argmax(sc))
                        opts.append((float(sc[k]), int(ca[k]), _CONT, -1))
            # trimmed continuations: predecessors still running at s whose detections from s on are all weak
            if self.link_trim_max > 0 and b:
                ov = np.flatnonzero((end[:b] >= s) & (start[:b] < s) & np.isfinite(best[:b]))
                rows = []
                for a in ov:
                    fa = T[a]["frames"]
                    keep = int(np.searchsorted(fa, s))       # detections before s
                    if (keep < 1 or len(fa) - keep > self.link_trim_max or not T[a]["weak"][keep:].all()
                            or s - fa[keep - 1] > self.link_max_gap + 1):
                        continue
                    rows.append((a, keep, best[a] - float(T[a]["dscore"][keep:].sum())))
                if rows:
                    ta = np.array([r[0] for r in rows])
                    tk = np.array([r[1] for r in rows])
                    xs_ = np.stack([T[a]["xfd"][k - 1] for a, k in zip(ta, tk)])
                    Ps_ = np.stack([T[a]["Pfd"][k - 1] for a, k in zip(ta, tk)])
                    fs_ = np.array([T[a]["foot"][k - 1] for a, k in zip(ta, tk)])
                    es_ = np.array([T[a]["frames"][k - 1] for a, k in zip(ta, tk)])
                    sc = self._continuations(T[b], s, xs_, Ps_, fs_, es_, np.array([r[2] for r in rows]))
                    if np.isfinite(sc).any():
                        k = int(np.argmax(sc))
                        opts.append((float(sc[k]), int(ta[k]), _CONT, int(tk[k])))
            # resume (ball at rest where it was lost): only from a predecessor that has no consistent
            # continuation into B -- a continuation carries strictly more information (same segment, filled)
            if cand.size:
                last_s = (last[cand] if self._cm is None else
                          np.array([self._map(last[a], end[a], s) for a in cand]).reshape(-1, 2))
                rs = cand[~cont_ok & (s - end[cand] <= self.resume_max_gap) &
                          (np.linalg.norm(last_s - first[b], axis=1) <= self.reacquire_px)]
                if rs.size:
                    a = rs[np.argmax(best[rs])]
                    opts.append((best[a] - self.resume_cost, int(a), _RESUME, -1))
            if opts:
                sc, p, ty, keep = max(opts, key=lambda o: o[0])
                best[b], pred[b], etype[b], pred_keep[b] = T[b]["node"] + sc, p, ty, keep
        if not np.isfinite(best).any() or best.max() <= 0:
            return []
        b = int(np.argmax(best))
        path, keep = [], len(T[b]["frames"])
        while b >= 0:
            path.append((b, int(etype[b]), keep))
            keep = int(pred_keep[b]) if pred_keep[b] >= 0 else (len(T[pred[b]]["frames"]) if pred[b] >= 0 else 0)
            b = int(pred[b])
        path.reverse()
        return path

    # -- segment refinement ---------------------------------------------------
    def _paths(self, z: np.ndarray, conf: np.ndarray, kick: np.ndarray, a0: int):
        """Smoothed path and covariances plus the one-sided predictions (position, velocity) at every
        frame of a span starting at frame ``a0`` (each in its own frame's pixels): ``fwd`` from frames < t
        only, ``bwd`` from frames > t only. ``kick[t]``: the velocity may change between t and t + 1."""
        fw, fv, bw, bv = self._span_warps(int(a0), len(z))
        kick_into = np.r_[False, kick[:-1]]                  # forward: step t -> t+1 enters t+1
        xp, Pp, xf, Pf, Fe = _filter(z, conf, kick_into, self.model, fw, fv)
        bp, bPp = _filter(z[::-1], conf[::-1], kick[::-1], self.model, bw, bv)[:2]   # reversed: t+1 -> t enters t
        bp, bPp = bp[::-1].copy(), bPp[::-1]
        bp[:, 2:] *= -1.0                                    # reversed time -> forward velocity
        xs, Ps = _smooth(xp, Pp, xf, Pf, Fe)
        return xs[:, :2], Ps, (xp, Pp), (bp, bPp)

    def _refine_segment(self, box: np.ndarray, score: np.ndarray, seg: np.ndarray, status: np.ndarray,
                        sigma: np.ndarray, s: int, player_feet: Optional[List[np.ndarray]]) -> np.ndarray:
        """Validate the weak detections of segment ``s`` against the smoothed / one-sided paths,
        then fill its gaps of <= ``max_gap`` frames from the smoothed path and write the smoothed
        position std to ``sigma`` (in place). Returns ``[n dropped, n kick corners]``."""
        det = np.flatnonzero((seg == s) & (status == 1))
        if det.size == 0:
            return np.zeros(2, dtype=int)
        if det.size == 1:
            sigma[det] = np.sqrt(self.model.r2(score[det]))
            return np.zeros(2, dtype=int)
        centres = box[:, :2] + box[:, 2:4] / 2.0
        at_foot = {int(t): self._near_foot(player_feet, int(t), centres[t]) for t in det}
        corners: set = set()
        n_drop = 0
        while True:
            a0, a1 = det[0], det[-1]                          # weak detections at the ends shrink the span
            z = np.full((a1 - a0 + 1, 2), np.nan)
            z[det - a0] = centres[det]
            kick = np.zeros(a1 - a0 + 1, dtype=bool)
            kick[np.array([t - a0 for t in det if at_foot[int(t)] or int(t) in corners], dtype=int)] = True
            path, Ps, (fwd, fP), (bwd, bP) = self._paths(z, score[a0:a1 + 1], kick, a0)
            fwd, fP, bwd, bP = fwd[det - a0], fP[det - a0], bwd[det - a0], bP[det - a0]

            nxt = np.r_[det[1:], np.iinfo(np.int64).max]
            weak = score[det] < self.init_conf
            resid = np.linalg.norm(centres[det] - path[det - a0], axis=1)
            fwd_ok = np.linalg.norm(centres[det] - fwd[:, :2], axis=1) <= self.outlier_px
            bwd_ok = np.linalg.norm(centres[det] - bwd[:, :2], axis=1) <= self.outlier_px
            foot = np.array([at_foot[int(t)] for t in det])
            has_later = (nxt - det) <= self.max_gap + 1
            supported = np.where(has_later, bwd_ok & (fwd_ok | foot), fwd_ok)

            # corner: supported from the later side, and the ball arrives and leaves at different velocities
            dv = fwd[:, 2:] - bwd[:, 2:]
            d2 = _maha(dv, fP[:, 2:, 2:] + bP[:, 2:, 2:])[0]
            turn = (np.linalg.norm(dv, axis=1) > self.corner_dv_px) & (d2 > _CORNER_D2)
            new_corners = {int(t) for t in det[has_later & supported & turn]} - corners
            if new_corners:                                   # let the path bend there, re-check
                corners |= new_corners
                continue
            bad = weak & (resid > self.outlier_px) & ~supported
            if not bad.any():
                # corroborated weak detections count as confident for the final path
                conf = score[a0:a1 + 1].copy()
                ok = det[weak & supported] - a0
                conf[ok] = np.maximum(conf[ok], self.init_conf)
                path, Ps = self._paths(z, conf, kick, a0)[:2]
                break
            worst = det[bad][np.argmax(resid[bad])]          # drop one at a time, then re-check
            box[worst], score[worst], seg[worst], status[worst] = np.nan, 0.0, -1, 0
            det = det[det != worst]
            corners.discard(int(worst))
            n_drop += 1
            if det.size < 2:
                sigma[det] = np.sqrt(self.model.r2(score[det]))
                return np.array([n_drop, len(corners)])
        sig = _pos_sigma(Ps)
        sigma[det] = sig[det - a0]
        for a, b in zip(det[:-1], det[1:]):
            gap = b - a - 1
            if 0 < gap <= self.max_gap:
                t = (np.arange(1, gap + 1) / (gap + 1))[:, None]
                wh = (1 - t) * box[a, 2:4] + t * box[b, 2:4]  # box size: linear between the two sides
                # smoothed shape, shifted to meet the kept detections on both sides (no jumps)
                pin = (1 - t) * (centres[a] - path[a - a0]) + t * (centres[b] - path[b - a0])
                box[a + 1:b] = np.c_[path[a + 1 - a0:b - a0] + pin - wh / 2.0, wh]
                seg[a + 1:b], status[a + 1:b], sigma[a + 1:b] = s, 2, sig[a + 1 - a0:b - a0]
        return np.array([n_drop, len(corners)])

    # -- helpers --------------------------------------------------------------
    def reset_state(self):
        self.state = []
        self.frame_id = 0
