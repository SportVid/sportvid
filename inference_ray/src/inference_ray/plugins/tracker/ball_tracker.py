"""
Single-ball tracker.

Integration with SportVid:

* Frame-based parameters are given at ``REFERENCE_FPS`` (30) and scaled to the
  decoding rate (``scale_to_fps``): durations in frames by fps / 30, per-frame motion by 30 / fps,
  accelerations by (30 / fps)^2. At 30 fps nothing changes.
* The caller passes only ball-class detections (``detections``), in frame pixels; there is no class filter here.

There is at most one ball in play, so this is not multi-object tracking: per frame the ball
detections are *candidates*, and a constant-velocity Kalman filter (image pixels) predicts
where the ball should be next. The candidate nearest that prediction, weighted by its
confidence, continues the track if it lies inside the gate. The track restarts (after
``max_missed`` frames, or after ``switch_frames`` frames with a confident candidate elsewhere
while the gate holds only weak ones or none) at the most confident candidate >= ``init_conf``
*only* if it is within ``reacquire_px`` of where the ball was last genuinely seen -- a confident
candidate anywhere else (including before the ball has ever been seen) is not trusted on a single
frame; it goes through the re-acquisition path below like any weak detection, since confidence
alone does not distinguish the ball from a static, clearly-lit decoy (a cone, a spare ball).

Detection confidence is used throughout, so a weak false positive cannot hijack the track
while the real ball is unseen:

* Gate: it grows by ``gate_growth_px`` per missed frame, but only in proportion to the
  candidate's confidence (0 at ``min_conf``, full at ``init_conf``). A weak candidate is only
  accepted near the prediction (``gate_px``), however long the ball has been missing.
* Kalman update: measurement noise ``meas_px / conf`` -- a weak detection barely moves the filter.
* Post-hoc, per track segment, a confidence-weighted Kalman (RTS) smoother runs over the whole
  segment; gaps of up to ``max_gap`` frames are filled from the smoothed path. With confident
  detections on both sides this is the straight-line (constant-velocity) motion between them.

Kicks (sudden changes of direction) are allowed where there is evidence for them:

* One-sided support: at every detection the path predicted from the *earlier* detections alone
  (forward filter) and from the *later* ones alone (backward filter) are compared with it. A
  kick corner lies on both -- the ball arrives along the old direction and leaves along the new
  one. Where both agree (``outlier_px``) and the arriving and leaving velocities differ by more
  than ``corner_dv_px`` -- and significantly, given both filters' velocity uncertainty, so an
  unsettled estimate after a gap or at a segment end is no corner -- the velocity is reset there
  and the path bends instead of cutting the corner.
* Players as a hint (``player_hint``): a ball within ``foot_reach`` player box widths of a
  player's foot point may be kicked. The smoother resets the velocity there; the live pass
  widens the gate after such a touch (``kick_vel_px`` extra, and full growth while the ball is
  unseen even for weak candidates, since a kicked ball is blurred); and at the foot the later
  side's support alone is enough to keep a weak detection (the earlier side can overshoot when
  the ball was trapped out of sight).
* A weak detection (< ``init_conf``) off the smoothed path (> ``outlier_px``) is kept only if it
  is supported: by the later side and (the earlier side or a player's foot); at the end of a
  segment (no later detection within ``max_gap``) by the earlier side. Anything else is dropped
  as a false positive and its frame treated as a gap. A supported weak detection is corroborated,
  so the final smoothing weights it as ``init_conf``; gap fills follow the smoothed path, shifted
  to meet the kept detections on both sides.

Static-object filter: before any of the above, a whole-clip pass (this tracker already works on
the full candidate list of the clip, not a true online stream) drops ball-class candidates that
sit within ``static_radius_px`` of the same spot for at least ``static_min_hits`` frames spanning
more than ``static_min_span`` frames -- a cone, a spare ball, a goal-area marking, anything the
detector confidently and repeatedly calls "ball" without it ever moving. This exists because
nothing *online* reliably catches it: a single confident detection (re)acquires immediately when
it lands near where the ball was last genuinely seen (below), which a static decoy near the
ball's own resting spot (kickoff, a stoppage) satisfies just as well as the real ball would.

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


State (one dict per frame):
    {
        "frame_id": int,
        "ball_box": np.ndarray (4,) tlwh | None,
        "ball_score": float,           # detection confidence; 0 when interpolated / missing
        "ball_segment": int,           # track segment (re-acquisitions start a new one); -1 if none
        "ball_status": "detected" | "interpolated" | "none"
    }
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .tracker import Tracker

logger = logging.getLogger(__name__)

STATUS = ("none", "detected", "interpolated")
_CORNER_D2 = 4.0        # velocity change must exceed ~2 sigma of the one-sided estimates' uncertainty
_KICK_VAR = 100.0 ** 2   # velocity variance released at a kick (px/frame)^2: effectively unknown vs. ball speeds,
                        #   yet small enough to keep the smoother's covariances well-conditioned
_F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64)
_H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)


def _foot_points(b: np.ndarray, box_format: str) -> np.ndarray:
    """(N, 2) bottom-centre points of (N, 4) boxes in ``tlwh`` or ``xyxy``."""
    if str(box_format).lower() == "xyxy":
        return np.stack([(b[:, 0] + b[:, 2]) * .5, b[:, 3]], axis=1)
    return np.stack([b[:, 0] + b[:, 2] * .5, b[:, 1] + b[:, 3]], axis=1)


class _CVKalman:
    """Constant-velocity Kalman filter on the ball centre, one step per frame. Measurement noise
    scales with 1 / confidence, so weak detections move the state little. ``vel_scale`` (30 / fps)
    scales the velocity constants, which are given in px / frame at 30 fps."""

    def __init__(self, xy, accel_px: float, meas_px: float, vel_scale: float = 1.0):
        self.x = np.array([xy[0], xy[1], 0.0, 0.0])
        v0 = (30.0 * vel_scale) ** 2                                          # unknown initial velocity
        self.P = np.diag([meas_px ** 2, meas_px ** 2, v0, v0])
        g = np.array([[0.5, 0], [0, 0.5], [1, 0], [0, 1]])
        self.Q = (accel_px ** 2) * g @ g.T
        kick_var = _KICK_VAR * vel_scale ** 2
        self.Q_kick = np.diag([0.0, 0.0, kick_var, kick_var])
        self.meas_px = meas_px

    def predict(self, kick: bool = False) -> np.ndarray:
        """``kick``: the velocity is reset before this step (a touch / kick at the current frame),
        so the next position already moves with the new, unknown velocity."""
        P = self.P + self.Q_kick if kick else self.P
        self.x = _F @ self.x
        self.P = _F @ P @ _F.T + self.Q
        return self.x[:2]

    def update(self, xy, conf: float = 1.0) -> None:
        R = (self.meas_px / max(conf, 0.05)) ** 2 * np.eye(2)
        S = _H @ self.P @ _H.T + R
        K = self.P @ _H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (np.asarray(xy, dtype=np.float64) - _H @ self.x)
        self.P = (np.eye(4) - K @ _H) @ self.P


def _filter(z: np.ndarray, conf: np.ndarray, kick_into: np.ndarray, accel_px: float, meas_px: float,
            vel_scale: float = 1.0):
    """Forward Kalman pass over consecutive frames.

    ``z``: (T, 2) centres, NaN where there is no detection (the first row must be one);
    ``conf``: (T,) confidences; ``kick_into[t]``: the velocity may jump in the step into frame t.
    Returns predicted (``xp``, ``Pp``: before the update at t, i.e. from earlier frames only)
    and filtered (``xf``, ``Pf``) states."""
    T = len(z)
    kf = _CVKalman(z[0], accel_px, meas_px, vel_scale)
    xp, Pp = np.zeros((T, 4)), np.zeros((T, 4, 4))
    xf, Pf = np.zeros((T, 4)), np.zeros((T, 4, 4))
    xp[0], Pp[0] = kf.x, kf.P
    xf[0], Pf[0] = kf.x, kf.P
    for t in range(1, T):
        kf.predict(bool(kick_into[t]))
        xp[t], Pp[t] = kf.x, kf.P
        if np.isfinite(z[t]).all():
            kf.update(z[t], conf[t])
        xf[t], Pf[t] = kf.x, kf.P
    return xp, Pp, xf, Pf


def _smooth(xp, Pp, xf, Pf) -> np.ndarray:
    """RTS backward pass over a ``_filter`` run. Returns the smoothed (T, 2) centres."""
    xs = xf.copy()
    for t in range(len(xf) - 2, -1, -1):
        C = Pf[t] @ _F.T @ np.linalg.inv(Pp[t + 1])
        xs[t] = xf[t] + C @ (xs[t + 1] - xp[t + 1])
    return xs[:, :2]


class _Tentative:
    """A provisional track started from a weak candidate."""

    def __init__(self, i: int, row: np.ndarray, xy: np.ndarray, accel_px: float, meas_px: float,
                 vel_scale: float = 1.0):
        self.kf = _CVKalman(xy, accel_px, meas_px, vel_scale)
        self.kf.update(xy, row[4])
        self.picks = [(i, row.copy())]          # (frame, [x, y, w, h, conf])
        self.xy = [np.asarray(xy, dtype=np.float64)]
        self.misses = 0

    def hit(self, i: int, row: np.ndarray, xy: np.ndarray) -> None:
        self.kf.update(xy, row[4])
        self.picks.append((i, row.copy()))
        self.xy.append(np.asarray(xy, dtype=np.float64))
        self.misses = 0

    def recent_motion(self, k_min: int, max_rms: float, k_max: int = 30) -> float:
        """Distance (px) covered along the longest recent run of >= ``k_min`` detections that fits
        a constant-velocity line within ``max_rms``; -1 if even the last ``k_min`` do not."""
        for k in range(min(len(self.picks), k_max), k_min - 1, -1):
            t = np.array([i for i, _ in self.picks[-k:]], dtype=np.float64)
            xy = np.array(self.xy[-k:])
            A = np.c_[t - t[0], np.ones(len(t))]
            coef, *_ = np.linalg.lstsq(A, xy, rcond=None)      # rows: velocity, offset
            if np.sqrt(np.mean(np.sum((A @ coef - xy) ** 2, axis=1))) <= max_rms:
                return float(np.linalg.norm(coef[0]) * (t[-1] - t[0]))
        return -1.0

    @property
    def mean_conf(self) -> float:
        return float(np.mean([r[4] for _, r in self.picks]))


REFERENCE_FPS = 30.0      # the rate the frame-based defaults are given at

# the defaults; the backend serializer holds the same values
DEFAULTS = {
    "min_conf": 0.10, "init_conf": 0.40, "gate_px": 60.0, "gate_growth_px": 20.0, "max_missed": 15,
    "switch_frames": 3, "max_gap": 10, "outlier_px": 25.0, "corner_dv_px": 5.0, "kick_vel_px": 30.0,
    "player_hint": True, "foot_reach": 1.5, "confirm_frames": 4, "tentative_gate_px": 30.0,
    "tentative_max_missed": 2, "reacquire_px": 60.0, "reacquire_growth_px": 15.0, "reacquire_max_px": 400.0,
    "min_move_px": 20.0, "tentative_resid_px": 6.0, "tentative_skip_body": 0.75, "accel_px": 4.0, "meas_px": 2.0,
    "static_filter": True, "static_radius_px": 12.0, "static_min_hits": 60, "static_min_span": 150,
    "min_fps": 10.0,
}

# how each frame-based parameter scales with k = REFERENCE_FPS / fps
_DURATION_FRAMES = ("max_missed", "switch_frames", "max_gap", "tentative_max_missed", "static_min_span")  # / k
_EVIDENCE_HITS = ("static_min_hits",)       # / k: hits of a static object over its (scaled) span; at least 3
_PER_FRAME_PX = ("gate_px", "gate_growth_px", "kick_vel_px", "corner_dv_px", "tentative_gate_px",
                 "reacquire_growth_px")      # * k: motion per frame
_PER_FRAME2_PX = ("accel_px",)               # * k^2: acceleration per frame^2
# not scaled: confidences, distances that do not depend on the frame step (reacquire_px, reacquire_max_px,
# min_move_px, outlier_px, static_radius_px), measurement noise (meas_px, tentative_resid_px), box fractions,
# and confirm_frames (a number of detections: evidence, not a duration)


def scale_to_fps(params: Dict[str, Any], fps: float) -> Dict[str, Any]:
    """ Parameters given at ``REFERENCE_FPS`` -> the same physical behaviour at ``fps``. """
    k = REFERENCE_FPS / float(fps)
    out = dict(params)
    for key in _DURATION_FRAMES:
        out[key] = max(1, int(round(params[key] / k)))
    for key in _EVIDENCE_HITS:
        out[key] = max(3, int(round(params[key] / k)))
    for key in _PER_FRAME_PX:
        out[key] = float(params[key]) * k
    for key in _PER_FRAME2_PX:
        out[key] = float(params[key]) * k ** 2
    return out


class BallTracker(Tracker):

    def __init__(self, tracker_params: Dict[str, Any], fps: float = REFERENCE_FPS, device: str = "cpu", **kwargs):
        super().__init__(tracker_params, device, **kwargs)
        self.fps = float(fps)
        self.vel_scale = REFERENCE_FPS / self.fps
        c = scale_to_fps({**DEFAULTS, **{k: v for k, v in self.tracker_params.items() if v is not None}}, self.fps)
        self.params = c
        self.min_conf = float(c["min_conf"])
        self.init_conf = float(c["init_conf"])
        self.gate_px = float(c["gate_px"])
        self.gate_growth_px = float(c["gate_growth_px"])
        self.max_missed = int(c["max_missed"])
        self.switch_frames = int(c["switch_frames"])
        self.max_gap = int(c["max_gap"])
        self.accel_px = float(c["accel_px"])
        self.meas_px = float(c["meas_px"])
        self.outlier_px = float(c["outlier_px"])
        self.kick_vel_px = float(c["kick_vel_px"])
        self.player_hint = bool(c["player_hint"])
        self.foot_reach = float(c["foot_reach"])
        self.corner_dv_px = float(c["corner_dv_px"])
        self.confirm_frames = int(c["confirm_frames"])
        self.tentative_gate_px = float(c["tentative_gate_px"])
        self.tentative_max_missed = int(c["tentative_max_missed"])
        self.reacquire_px = float(c["reacquire_px"])
        self.reacquire_growth_px = float(c["reacquire_growth_px"])
        self.reacquire_max_px = float(c["reacquire_max_px"])
        self.min_move_px = float(c["min_move_px"])
        self.tentative_resid_px = float(c["tentative_resid_px"])
        self.tentative_skip_body = float(c["tentative_skip_body"])
        self.static_filter = bool(c["static_filter"])
        self.static_radius_px = float(c["static_radius_px"])
        self.static_min_hits = int(c["static_min_hits"])
        self.static_min_span = int(c["static_min_span"])
        self.min_fps = float(c["min_fps"])

    @property
    def usable(self) -> bool:
        """ Below ``min_fps`` the ball moves too far between frames to associate it; the caller then writes
        the candidates untracked. """
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
        return self._filter_static(cands)

    def _filter_static(self, candidates: List[np.ndarray]) -> List[np.ndarray]:
        """Drop candidates that sit within ``static_radius_px`` of the same spot for at least
        ``static_min_hits`` frames spanning more than ``static_min_span`` frames (see the module
        docstring). A whole-clip pass: cheap grid-bucket by position, not true clustering -- a
        static object's repeated detections land in the same bucket almost every time; occasional
        jitter across a bucket edge just needs one more hit to still clear ``static_min_hits``."""
        if not self.static_filter:
            return candidates
        cell = max(self.static_radius_px, 1e-6)
        buckets: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        for i, c in enumerate(candidates):
            if not len(c):
                continue
            for j, xy in enumerate(c[:, :2] + c[:, 2:4] / 2.0):
                buckets.setdefault((int(xy[0] // cell), int(xy[1] // cell)), []).append((i, j))

        drop: Dict[int, set] = {}
        n_locations = 0
        for hits in buckets.values():
            if len(hits) < self.static_min_hits:
                continue
            frames = [i for i, _ in hits]
            if max(frames) - min(frames) < self.static_min_span:
                continue
            pts = np.array([candidates[i][j, :2] + candidates[i][j, 2:4] / 2.0 for i, j in hits])
            if np.linalg.norm(pts - pts.mean(axis=0), axis=1).max() > self.static_radius_px:
                continue          # spread too wide for one fixed point -> probably the ball passing through
            n_locations += 1
            for i, j in hits:
                drop.setdefault(i, set()).add(j)
        if not drop:
            return candidates

        out, n_dropped = [], 0
        for i, c in enumerate(candidates):
            if i in drop and len(c):
                keep = [j for j in range(len(c)) if j not in drop[i]]
                n_dropped += len(c) - len(keep)
                c = c[keep] if keep else np.zeros((0, 5))
            out.append(c)
        logger.info("ball_tracker: static-object filter dropped %d candidate(s) at %d fixed location(s) "
                   "(never moving ball-class detections, e.g. a cone or a spare ball)", n_dropped, n_locations)
        return out

    def process(self, inputs: Dict[Any, Any], **kwargs) -> List[Dict[str, Any]]:
        """``inputs``: ``detections`` (per-frame detector output), optionally ``players``
        (per-frame player track boxes) and ``box_format`` of those boxes (default tlwh)."""
        feet = self._player_feet(inputs.get("players"), inputs.get("box_format", "tlwh"))
        return self.track(self.preprocess(inputs, **kwargs), player_feet=feet)

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

    # -- tracking -------------------------------------------------------------
    def track(self, candidates: List[np.ndarray], player_feet: Optional[List[np.ndarray]] = None,
              **kwargs) -> List[Dict[str, Any]]:
        self.reset_state()
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
            pick = None
            if kf is not None:
                pred = kf.predict(kick=at_foot and missed == 0)   # the velocity jumps once, at the touch
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
                near = (strong[np.linalg.norm(centres[strong] - last_seen[1], axis=1) <= self.reacquire_px]
                       if strong.size and last_seen is not None else np.zeros(0, dtype=int))
                if near.size:
                    pick = int(near[np.argmax(c[near, 4])])
                    segment += 1
                    missed, far_hits = 0, 0
                    lead = self._lead_in(tentatives, centres[pick])
                    if lead is not None:        # a provisional track runs into it: keep its detections
                        for j, row in lead.picks:
                            box[j], score[j], seg[j] = row[:4], row[4], segment
                        kf = lead.kf
                        kf.update(centres[pick], c[pick, 4])
                        n_lead_in += len(lead.picks)
                    else:
                        kf = _CVKalman(centres[pick], self.accel_px, self.meas_px, self.vel_scale)
            if pick is not None:
                box[i], score[i], seg[i] = c[pick, :4], c[pick, 4], segment
                at_foot = self._near_foot(player_feet, i, centres[pick])
                last_seen = (i, centres[pick])
                tentatives = []
                continue
            # the ball is unseen (track coasting or lost): look for it among the weak candidates
            ok = ~self._on_body(player_feet, i, centres)
            tr = self._step_tentatives(tentatives, i, c[ok], centres[ok], last_seen)
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

        status = np.where(seg >= 0, 1, 0)
        stats = np.zeros(2, dtype=int)                       # dropped outliers, kept kick corners
        for s in range(segment + 1):
            stats += self._refine_segment(box, score, seg, status, s, player_feet)
        self.state = [{"frame_id": i,
                       "ball_box": None if status[i] == 0 else box[i].copy(),
                       "ball_score": float(score[i]),
                       "ball_segment": int(seg[i]),
                       "ball_status": STATUS[status[i]]} for i in range(n)]
        self.frame_id = n
        n_det, n_int = int((status == 1).sum()), int((status == 2).sum())
        logger.info("ball_tracker: ball in %d/%d frames (%d detected, %d interpolated), %d segment(s), "
                    "%d re-acquired from weak detections, %d weak lead-in detection(s); %d weak detection(s) "
                    "dropped as outliers, %d kick corner(s)%s.", n_det + n_int, n, n_det, n_int, segment + 1,
                    n_confirmed, n_lead_in, stats[0], stats[1],
                    "" if player_feet is not None else " (no player hint)")
        return self.state

    def _step_tentatives(self, tentatives: List[_Tentative], i: int, c: np.ndarray, centres: np.ndarray,
                         last_seen) -> Optional[_Tentative]:
        """Advance the provisional tracks by frame ``i`` (in place) and return one that is now
        confirmed, if any."""
        used = set()
        for tr in sorted(tentatives, key=lambda t: -len(t.picks)):   # longer tracks choose first
            pred = tr.kf.predict()
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
                tentatives.append(_Tentative(i, c[j], centres[j], self.accel_px, self.meas_px, self.vel_scale))
        ready = [t for t in tentatives if t.misses == 0 and len(t.picks) >= self.confirm_frames
                 and self._plausible(t, last_seen)]
        return max(ready, key=lambda t: (len(t.picks), t.mean_conf)) if ready else None

    def _lead_in(self, tentatives: List[_Tentative], xy: np.ndarray) -> Optional[_Tentative]:
        """The provisional track (>= 2 detections) whose prediction for this frame reaches ``xy``,
        i.e. the weak detections of the ball just before a confident one; longest first."""
        for tr in sorted(tentatives, key=lambda t: -len(t.picks)):
            if len(tr.picks) < 2:
                continue
            pred = tr.kf.predict()
            if np.linalg.norm(pred - xy) <= self.tentative_gate_px + self.gate_growth_px * tr.misses:
                return tr
        return None

    def _plausible(self, tr: _Tentative, last_seen) -> bool:
        """Could this provisional track be the ball that was lost at ``last_seen``? Its recent
        detections must lie on a smooth (constant-velocity) path; "moving" means covering at least
        ``min_move_px`` along it -- hopping between static clutter spots is neither."""
        covered = tr.recent_motion(self.confirm_frames, self.tentative_resid_px)
        if covered < 0:
            return False
        moving = covered >= self.min_move_px
        if last_seen is None:
            return moving
        dist = float(np.linalg.norm(tr.xy[0] - last_seen[1]))
        if dist <= self.reacquire_px:
            return True
        radius = self.reacquire_px + self.reacquire_growth_px * (tr.picks[0][0] - last_seen[0])
        return moving and (dist <= radius or radius >= self.reacquire_max_px)

    def _gate(self, missed: int, conf: np.ndarray, at_foot: bool = False) -> np.ndarray:
        """Per-candidate gate radius: the growth while the ball is unseen scales with confidence,
        unless the ball was last seen at a player's foot (a kicked ball is blurred -> weak)."""
        w = np.clip((conf - self.min_conf) / max(self.init_conf - self.min_conf, 1e-6), 0.0, 1.0)
        if at_foot:
            return self.gate_px + self.kick_vel_px + self.gate_growth_px * missed * np.ones_like(w)
        return self.gate_px + self.gate_growth_px * missed * w

    def _paths(self, z: np.ndarray, conf: np.ndarray, kick: np.ndarray):
        """Smoothed path plus the one-sided predictions (position, velocity) at every frame of a
        span: ``fwd`` from frames < t only, ``bwd`` from frames > t only.
        ``kick[t]``: the velocity may change between t and t + 1."""
        args = (self.accel_px, self.meas_px, self.vel_scale)
        kick_into = np.r_[False, kick[:-1]]                  # forward: step t -> t+1 enters t+1
        xp, Pp, xf, Pf = _filter(z, conf, kick_into, *args)
        bp, bPp = _filter(z[::-1], conf[::-1], kick[::-1], *args)[:2]   # reversed: step t+1 -> t enters t
        bp, bPp = bp[::-1].copy(), bPp[::-1]
        bp[:, 2:] *= -1.0                                    # reversed time -> forward velocity
        return _smooth(xp, Pp, xf, Pf), (xp, Pp), (bp, bPp)

    def _refine_segment(self, box: np.ndarray, score: np.ndarray, seg: np.ndarray, status: np.ndarray,
                        s: int, player_feet: Optional[List[np.ndarray]]) -> np.ndarray:
        """Validate the weak detections of segment ``s`` against the smoothed / one-sided paths,
        then fill its gaps of <= ``max_gap`` frames from the smoothed path (in place).
        Returns ``[n dropped, n kick corners]``."""
        det = np.flatnonzero((seg == s) & (status == 1))
        if det.size < 2:
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
            path, (fwd, fP), (bwd, bP) = self._paths(z, score[a0:a1 + 1], kick)
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
            cov = fP[:, 2:, 2:] + bP[:, 2:, 2:]
            d2 = np.einsum("ni,nij,nj->n", dv, np.linalg.inv(cov), dv)
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
                path = self._paths(z, conf, kick)[0]
                break
            worst = det[bad][np.argmax(resid[bad])]          # drop one at a time, then re-check
            box[worst], score[worst], seg[worst], status[worst] = np.nan, 0.0, -1, 0
            det = det[det != worst]
            corners.discard(int(worst))
            n_drop += 1
        for a, b in zip(det[:-1], det[1:]):
            gap = b - a - 1
            if 0 < gap <= self.max_gap:
                t = (np.arange(1, gap + 1) / (gap + 1))[:, None]
                wh = (1 - t) * box[a, 2:4] + t * box[b, 2:4]  # box size: linear between the two sides
                # smoothed shape, shifted to meet the kept detections on both sides (no jumps)
                pin = (1 - t) * (centres[a] - path[a - a0]) + t * (centres[b] - path[b - a0])
                box[a + 1:b] = np.c_[path[a + 1 - a0:b - a0] + pin - wh / 2.0, wh]
                seg[a + 1:b], status[a + 1:b] = s, 2
        return np.array([n_drop, len(corners)])

    # -- helpers --------------------------------------------------------------
    def reset_state(self):
        self.state = []
        self.frame_id = 0
