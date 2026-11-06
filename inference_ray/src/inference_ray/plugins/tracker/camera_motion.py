"""
Camera motion between consecutive frames, estimated from the video and consumed by trackers.

Per frame t a homography ``rel[t]`` maps frame t pixels to frame t-1 pixels (``rel[0]`` = identity); ``ok[t]``
says whether that step was estimated or is a guess (a failed estimate, e.g. at a scene cut). Trackers warp their
state step by step (``step``) and map positions between two frames only across a short gap (``between``), so
estimation errors do not pile up in one global plane. Only a whole-clip pass such as the ball tracker's
static-object filter needs a common plane (``to_mosaic``: frame 0).

Estimation (``StepEstimator``, one frame at a time; ``CameraMotionEstimator`` wraps it for the object tracker):

* **Point pairs** from the background of the two frames. ``features``: ``klt`` (default) tracks Shi-Tomasi corners
  of frame t-1 into frame t with pyramidal Lucas-Kanade optical flow and keeps a corner only if tracking it back
  lands within ``fb_px`` of where it started; ``orb`` matches ORB descriptors with Lowe's ratio test. The
  detections of each frame (grown by ``box_margin``) are masked out, since players and the ball move on their own.
* **Model**, fitted with RANSAC. ``model="auto"`` (default) fits a similarity (pan, tilt, zoom, roll) and a
  homography and keeps the homography only if it explains clearly more pairs (``auto_margin``). ``homography``,
  ``affine`` and ``similarity`` force one model (the first two fall back to a similarity). For a planar scene (the
  pitch) or a camera that only rotates and zooms, one homography is exact for the whole image.
* **Plausibility.** A step is accepted only with enough inliers (``min_inliers`` and ``min_inlier_share`` of the
  pairs), the image corners moving by at most ``max_step`` of the image diagonal, a scale change of at most
  ``max_scale_step`` and no fold.
* **Failures.** If no model is accepted, the previous step is repeated once (a pan continues), else identity.
  These steps are flagged (``ok`` False) so a tracker can widen its position uncertainty there.
* **Fixed or moving.** ``mode``: ``auto`` (default) passes the motion on only if at least ``moving_share`` of the
  steps move the image corners by more than ``static_px``, so a fixed camera gives the same result as no
  estimation; ``on`` always passes it; ``off`` skips the estimation.

Per-frame limits (``static_px``, ``max_step``, ``max_scale_step``) are given at 30 fps and scaled to the decoding
rate. Known limits: on-screen overlays (score bug, logos) that are numerous enough pull a step towards identity; a
non-planar background (stands) seen from a translating camera is only approximated by a homography.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

logger = logging.getLogger(__name__)

REFERENCE_FPS = 30.0      # per-frame limits (static_px, max_step, max_scale_step) are given at this rate

# kind of each step
HOMOGRAPHY, SIMILARITY, HELD, IDENTITY, AFFINE = 0, 1, 2, 3, 4


def apply_h(H: np.ndarray, xy: np.ndarray) -> np.ndarray:
    """Points (N, 2) through one homography (3, 3), or through per-point homographies (N, 3, 3)."""
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    p = np.c_[xy, np.ones(len(xy))]
    q = p @ H.T if H.ndim == 2 else np.einsum("nij,nj->ni", H, p)
    return q[:, :2] / q[:, 2:3]


def h_jacobian(H: np.ndarray, xy: np.ndarray) -> np.ndarray:
    """(N, 2, 2) Jacobians of the homography (3, 3) (or per-point (N, 3, 3)) at the points (N, 2)."""
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    Hn = np.broadcast_to(H, (len(xy), 3, 3))
    p = np.c_[xy, np.ones(len(xy))]
    w = np.einsum("nj,nj->n", Hn[:, 2, :], p)
    q = np.stack([np.einsum("nj,nj->n", Hn[:, 0, :], p) / w, np.einsum("nj,nj->n", Hn[:, 1, :], p) / w], axis=1)
    return (Hn[:, :2, :2] - q[:, :, None] * Hn[:, None, 2, :2]) / w[:, None, None]


def _norm(H: np.ndarray) -> np.ndarray:
    return H / H[2, 2] if abs(H[2, 2]) > 1e-12 else H


class CameraMotion:
    """Per-frame homographies ``rel[t]``: frame t -> frame t-1, whether each step was estimated (``ok``) and how
    (``kind``: HOMOGRAPHY, SIMILARITY, AFFINE, or HELD / IDENTITY for a failed step)."""

    def __init__(self, rel: np.ndarray, ok: Optional[np.ndarray] = None, kind: Optional[np.ndarray] = None):
        self.rel = np.asarray(rel, dtype=np.float64).reshape(-1, 3, 3).copy()
        self.rel[0] = np.eye(3)
        n = len(self.rel)
        self.ok = np.ones(n, dtype=bool) if ok is None else np.asarray(ok, dtype=bool).copy()
        self.ok[0] = True
        self.kind = np.zeros(n, dtype=np.int8) if kind is None else np.asarray(kind, dtype=np.int8).copy()
        self._step = np.stack([_norm(np.linalg.inv(R)) for R in self.rel])        # frame t-1 -> frame t
        C = np.empty_like(self.rel)                                                # frame t -> frame 0
        C[0] = np.eye(3)
        for t in range(1, n):
            C[t] = _norm(C[t - 1] @ self.rel[t])
        self._C = C
        self._Cinv = np.stack([_norm(np.linalg.inv(c)) for c in C])

    def __len__(self) -> int:
        return len(self.rel)

    @classmethod
    def identity(cls, n: int) -> "CameraMotion":
        return cls(np.tile(np.eye(3), (n, 1, 1)))

    def step(self, t: int) -> np.ndarray:
        """Frame t-1 -> frame t."""
        return self._step[t]

    def between(self, a: int, b: int) -> np.ndarray:
        """Frame a -> frame b."""
        return np.eye(3) if a == b else _norm(self._Cinv[b] @ self._C[a])

    def to_mosaic(self, frames: np.ndarray) -> np.ndarray:
        """(N, 3, 3) frame -> frame 0 for the given frame indices."""
        return self._C[np.asarray(frames, dtype=np.int64)]

    def motion_px(self, shape) -> np.ndarray:
        """Per step, the mean displacement (px) of the image corners (0 for frame 0)."""
        h, w = shape[:2]
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float64)
        return np.array([np.linalg.norm(apply_h(R, corners) - corners, axis=1).mean() for R in self.rel])


class StepEstimator:
    """Streaming estimation, one frame at a time (``add``), of the steps of a ``CameraMotion`` (``result``).
    ``features``: klt | orb; ``scale``: image scale the points are found and matched at; ``model``: auto |
    homography | affine | similarity; ``max_step``: the largest plausible corner motion per frame, as a fraction of
    the image diagonal; ``max_scale_step``: the largest plausible zoom per frame (relative); ``box_margin``: masked
    boxes grow by this share of their size. KLT: ``max_corners``, ``min_distance`` (px at ``scale``), ``fb_px``
    (forward-backward limit, px at ``scale``), ``win`` and ``levels`` of the Lucas-Kanade pyramid. ORB:
    ``max_features``, ``ratio`` (Lowe's ratio test)."""

    def __init__(self, features: str = "klt", model: str = "auto", scale: float = 1.0, max_corners: int = 2000,
                 min_distance: float = 8.0, fb_px: float = 1.0, win: int = 21, levels: int = 4,
                 max_features: int = 3000, ratio: float = 0.75, ransac_px: float = 3.0, min_inliers: int = 30,
                 min_inlier_share: float = 0.25, max_step: float = 0.1, max_scale_step: float = 0.05,
                 box_margin: float = 0.15, auto_margin: float = 0.1):
        import cv2  # only needed here

        if features not in ("klt", "orb"):
            raise ValueError(f"camera motion: features must be klt or orb, got {features!r}")
        if model not in ("auto", "homography", "affine", "similarity"):
            raise ValueError(f"camera motion: model must be auto, homography, affine or similarity, got {model!r}")
        self.cv2 = cv2
        self.features = features
        self.model, self.scale, self.ratio, self.ransac_px = model, float(scale), float(ratio), float(ransac_px)
        self.max_corners, self.min_distance, self.fb_px = int(max_corners), float(min_distance), float(fb_px)
        self.lk = dict(winSize=(int(win), int(win)), maxLevel=int(levels),
                       criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        self.min_inliers, self.min_inlier_share = int(min_inliers), float(min_inlier_share)
        self.max_step, self.max_scale_step = float(max_step), float(max_scale_step)
        self.box_margin, self.auto_margin = float(box_margin), float(auto_margin)
        if features == "orb":
            self.orb = cv2.ORB_create(nfeatures=int(max_features))
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.S = np.diag([self.scale, self.scale, 1.0])
        self.S_inv = np.linalg.inv(self.S)
        self.rel: List[np.ndarray] = []
        self.ok: List[bool] = []
        self.kind: List[int] = []
        self.shape = None
        self._prev = None               # klt: (scaled image, corners (K, 1, 2)); orb: (keypoints (K, 2), descriptors)
        self._last_good = None          # last accepted step (repeated once on failure)

    def __len__(self) -> int:
        return len(self.rel)

    def add(self, frame: np.ndarray, boxes_xyxy: Optional[np.ndarray] = None) -> None:
        """The next frame ((H, W, 3) RGB or (H, W) grey, uint8) and the boxes (N, 4) xyxy in its pixels to mask
        out."""
        cv2 = self.cv2
        img = _grey(frame)
        self.shape = img.shape
        small = img if self.scale == 1.0 else cv2.resize(img, None, fx=self.scale, fy=self.scale,
                                                         interpolation=cv2.INTER_AREA)
        mask = np.full(small.shape, 255, dtype=np.uint8)
        if boxes_xyxy is not None and len(boxes_xyxy):
            b = np.asarray(boxes_xyxy, dtype=np.float64).reshape(-1, 4).copy()
            m = (b[:, 2:4] - b[:, 0:2]) * self.box_margin
            b[:, 0:2] -= m
            b[:, 2:4] += m
            for x0, y0, x1, y1 in (b * self.scale).astype(int):
                mask[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = 0
        cur = self._features(small, mask)
        if not self.rel:
            self.rel.append(np.eye(3)), self.ok.append(True), self.kind.append(HOMOGRAPHY)
            self._prev = cur
            return
        pairs = self._pairs(cur, self._prev)
        R, k = self._select(*pairs) if pairs is not None else (None, IDENTITY)
        ok = R is not None
        if not ok:
            if self._last_good is not None and self.ok[-1]:
                R, k = self._last_good, HELD
            else:
                R, k = np.eye(3), IDENTITY
        else:
            self._last_good = R
        self.rel.append(R), self.ok.append(ok), self.kind.append(k)
        self._prev = cur

    def result(self) -> CameraMotion:
        cm = CameraMotion(np.stack(self.rel) if self.rel else np.eye(3)[None], np.array(self.ok, dtype=bool),
                          np.array(self.kind, dtype=np.int8))
        if len(cm) > 1:
            kind = cm.kind[1:]
            mot = cm.motion_px(self.shape)[1:]
            logger.info("camera motion (%s, %s): %d step(s), %d homography, %d similarity, %d affine, %d failed "
                        "(%d held, %d identity); corner motion median %.2f px / frame, p95 %.2f", self.features,
                        self.model, len(kind), int((kind == HOMOGRAPHY).sum()), int((kind == SIMILARITY).sum()),
                        int((kind == AFFINE).sum()), int((~cm.ok).sum()), int((kind == HELD).sum()),
                        int((kind == IDENTITY).sum()), float(np.median(mot)), float(np.percentile(mot, 95)))
        return cm

    def _features(self, small, mask):
        """klt: the image and its corners outside the mask (tracked into the next frame); orb: keypoints (in
        full-resolution px) and descriptors outside the mask."""
        if self.features == "klt":
            p = self.cv2.goodFeaturesToTrack(small, maxCorners=self.max_corners, qualityLevel=0.01,
                                             minDistance=self.min_distance, blockSize=7, mask=mask)
            return small, (np.zeros((0, 1, 2), np.float32) if p is None else p)
        kp, des = self.orb.detectAndCompute(small, mask)
        return (np.float64([k.pt for k in kp]) / self.scale if kp else np.zeros((0, 2))), des

    def _pairs(self, cur, prev):
        """Point pairs (src in the current frame, dst in the previous one), in px at ``scale``, or None."""
        cv2 = self.cv2
        if self.features == "klt":
            (ic, _), (ip, pp) = cur, prev
            if len(pp) < 8:
                return None
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(ip, ic, pp, None, **self.lk)
            back, st2, _ = cv2.calcOpticalFlowPyrLK(ic, ip, nxt, None, **self.lk)
            good = (st.reshape(-1).astype(bool) & st2.reshape(-1).astype(bool)
                    & (np.linalg.norm((back - pp).reshape(-1, 2), axis=1) < self.fb_px))
            if good.sum() < 8:
                return None
            return nxt.reshape(-1, 2)[good].astype(np.float64), pp.reshape(-1, 2)[good].astype(np.float64)
        (pc, dc), (pp, dp) = cur, prev
        if dc is None or dp is None or len(pc) < 8 or len(pp) < 8:
            return None
        good = [a for a, b in (m for m in self.matcher.knnMatch(dc, dp, k=2) if len(m) == 2)
                if a.distance < self.ratio * b.distance]
        if len(good) < 8:
            return None
        return pc[[g.queryIdx for g in good]] * self.scale, pp[[g.trainIdx for g in good]] * self.scale

    def _plausible(self, H, n_in, n_match) -> bool:
        if H is None or n_in < self.min_inliers or n_in < self.min_inlier_share * n_match:
            return False
        h, w = self.shape
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float64)
        if np.linalg.norm(apply_h(H, corners) - corners, axis=1).max() > self.max_step * np.hypot(h, w):
            return False
        det = np.linalg.det(h_jacobian(H, np.vstack([corners, [[w / 2, h / 2]]])))
        return bool((det > 0).all() and np.abs(np.log(det) / 2.0).max() <= np.log1p(self.max_scale_step))

    def _fit(self, kind, src, dst):
        """One model on the pairs (px at ``scale``): the full-resolution transform if plausible, else None; and
        its inliers among all pairs at the threshold (comparable across models)."""
        cv2 = self.cv2
        thr = self.ransac_px * self.scale
        if kind == "homography":
            M, _ = cv2.findHomography(src, dst, cv2.RANSAC, thr)
        else:
            f = cv2.estimateAffine2D if kind == "affine" else cv2.estimateAffinePartial2D
            M, _ = f(src, dst, method=cv2.RANSAC, ransacReprojThreshold=thr)
            M = None if M is None else np.vstack([M, [0.0, 0.0, 1.0]])
        if M is None or not np.isfinite(M).all():
            return None, 0
        n_in = int((np.linalg.norm(apply_h(M, src) - dst, axis=1) <= thr).sum())
        Mf = _norm(self.S_inv @ M @ self.S)
        return (Mf if self._plausible(Mf, n_in, len(src)) else None), n_in

    def _select(self, src, dst):
        codes = {"homography": HOMOGRAPHY, "similarity": SIMILARITY, "affine": AFFINE}
        if self.model == "auto":
            Hm, nH = self._fit("homography", src, dst)
            Sm, nS = self._fit("similarity", src, dst)
            if Sm is not None and (Hm is None or nH < (1.0 + self.auto_margin) * nS):
                return Sm, SIMILARITY
            return (Hm, HOMOGRAPHY) if Hm is not None else (None, IDENTITY)
        M, _ = self._fit(self.model, src, dst)
        if M is None and self.model != "similarity":
            M, _ = self._fit("similarity", src, dst)
            return (M, SIMILARITY) if M is not None else (None, IDENTITY)
        return (M, codes[self.model]) if M is not None else (None, IDENTITY)


def _grey(frame) -> np.ndarray:
    import cv2
    a = np.asarray(frame)
    if a.ndim == 3:                                                    # (H, W, 3) RGB, as the video decoder gives
        return cv2.cvtColor(np.ascontiguousarray(a), cv2.COLOR_RGB2GRAY)
    return a


class CameraMotionEstimator:
    """Camera motion for the object tracker: ``add`` each decoded frame with its detections, ``finalize`` after the
    last one. ``motion`` is what trackers get: the ``CameraMotion``, or None for a fixed camera (``mode`` auto) or
    ``mode`` off. ``params``: ``mode``, ``static_px``, ``moving_share`` and those of ``StepEstimator``; missing
    keys take ``DEFAULTS``. Per-frame limits are given at 30 fps and scaled to ``fps``."""

    # the backend serializer's default_camera_motion_params holds the same values
    DEFAULTS: Dict[str, Any] = {
        "mode": "auto",            # auto: pass the motion on only if the camera moves | on: always | off: skip
        "static_px": 0.5,          # auto: a step "moves" if the image corners shift by more than this (px) ...
        "moving_share": 0.02,      # ... and the camera moves if at least this share of the steps does
        "features": "klt",         # klt: corners tracked by optical flow | orb: descriptor matching
        "model": "auto",           # auto: similarity, or a homography where it explains clearly more pairs
        "auto_margin": 0.1,        # auto: the homography needs this many more inliers (relative)
        "scale": 1.0,              # image scale for the points
        "max_corners": 2000,       # klt
        "min_distance": 8.0,       # klt: px at scale, between corners
        "fb_px": 1.0,              # klt: forward-backward limit (px at scale)
        "win": 21,                 # klt: Lucas-Kanade window (px)
        "levels": 4,               # klt: Lucas-Kanade pyramid levels
        "max_features": 3000,      # orb
        "ratio": 0.75,             # orb: Lowe's ratio test
        "ransac_px": 3.0,          # RANSAC reprojection threshold (full-resolution px)
        "min_inliers": 30,
        "min_inlier_share": 0.25,
        "max_step": 0.1,           # largest plausible corner motion per frame, as a fraction of the image diagonal
        "max_scale_step": 0.05,    # largest plausible zoom per frame (relative)
        "box_margin": 0.15,        # masked detection boxes grow by this share of their size
    }

    def __init__(self, params: Optional[Mapping[str, Any]] = None, fps: float = REFERENCE_FPS):
        params = dict(params or {})
        unknown = sorted(set(params) - set(self.DEFAULTS))
        if unknown:
            logger.warning("camera motion: ignoring unknown parameter(s) %s", unknown)
        cfg = {k: params.get(k, v) for k, v in self.DEFAULTS.items()}
        self.mode = str(cfg.pop("mode")).lower()
        if self.mode not in ("auto", "on", "off"):
            raise ValueError(f"camera motion: mode must be auto, on or off, got {self.mode!r}")
        k = REFERENCE_FPS / float(fps)                    # per-frame limits scale with the frame step
        self.static_px = float(cfg.pop("static_px")) * k
        self.moving_share = float(cfg.pop("moving_share"))
        cfg["max_step"] = float(cfg["max_step"]) * k
        cfg["max_scale_step"] = float(cfg["max_scale_step"]) * k
        self._est = StepEstimator(**cfg) if self.mode != "off" else None
        self.estimate: Optional[CameraMotion] = None     # the full estimate, also for a fixed camera
        self.moving: Optional[bool] = None
        self.motion: Optional[CameraMotion] = None

    def add(self, frame: np.ndarray, boxes_xyxy: Optional[np.ndarray] = None) -> None:
        if self._est is not None:
            self._est.add(frame, boxes_xyxy)

    def finalize(self) -> Optional[CameraMotion]:
        if self._est is None:
            return None
        self.estimate, shape = self._est.result(), self._est.shape
        self._est = None
        if len(self.estimate) < 2:
            self.moving = False
            return None
        share = float((self.estimate.motion_px(shape)[1:] > self.static_px).mean())
        self.moving = share >= self.moving_share
        self.motion = self.estimate if (self.mode == "on" or self.moving) else None
        logger.info("camera motion: %.1f %% of the steps move more than %.2f px -> %s camera (mode %s); trackers %s "
                    "camera motion", 100 * share, self.static_px, "moving" if self.moving else "fixed", self.mode,
                    "get the" if self.motion is not None else "get no")
        return self.motion
