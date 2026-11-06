"""Projection between the video and the pitch through a calibration: its homography (relative undistorted video
coordinates -> relative pitch coordinates, ``CalibrationAssets.homography_matrix``) and lens
(``CalibrationAssets.lens_intrinsics``, see ``utils/lens.py``). The frontend renders the results and does no
geometry of its own.

Points that can't be mapped come back as NaN: beyond the lens's valid range, behind the camera or beyond the
horizon (pitch -> video), or outside the frame's content region, where the lens isn't defined.
"""
from typing import Dict, List, Optional, Sequence

import numpy as np

from backend.utils.lens import distort_with_snapshot, undistort_with_snapshot

IDENTITY = np.eye(3)

# pitch -> video: undistorted points farther than this (relative to the frame) from its centre lie towards the
# horizon, where the projection runs off to infinity
MAX_UNDISTORTED_OFFSET = 3.0


def is_calibrated(homography) -> bool:
    """A calibration asset has a homography once a DLT run set it; until then it holds the identity."""
    return homography is not None and not np.allclose(np.asarray(homography, dtype=np.float64), IDENTITY)


def _apply(H: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Homogeneous ``H [x, y, 1]`` per point, (N, 3)."""
    return np.c_[points, np.ones(len(points))] @ H.T


def video_to_pitch(points_rel: Sequence[Sequence[float]], homography, lens: Optional[Dict]) -> np.ndarray:
    """Relative video coordinates -> relative pitch coordinates."""
    pts = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2)
    q = _apply(np.asarray(homography, dtype=np.float64), undistort_with_snapshot(pts, lens))
    with np.errstate(divide="ignore", invalid="ignore"):
        return q[:, :2] / q[:, 2:3]


def _front_sign(homography: np.ndarray, lens: Optional[Dict], in_front: Optional[np.ndarray]) -> float:
    """Sign of ``(H [u, 1])_w`` for ground points in front of the camera (seen at ``u``): the same for all of them.
    Taken from ``in_front`` (e.g. the clicked keypoints), else the frame centre."""
    pts = in_front if in_front is not None and len(in_front) else np.array([[0.5, 0.5]])
    w = _apply(homography, undistort_with_snapshot(pts, lens))[:, 2]
    w = w[np.isfinite(w)]
    return 1.0 if not w.size or np.sum(np.sign(w)) >= 0 else -1.0


def _in_content(points_rel: np.ndarray, lens: Optional[Dict], margin: float = 0.002) -> np.ndarray:
    x0, y0, w, h = (lens or {}).get("content_rect_rel") or (0.0, 0.0, 1.0, 1.0)
    x, y = points_rel[:, 0], points_rel[:, 1]
    return (x >= x0 - margin) & (x <= x0 + w + margin) & (y >= y0 - margin) & (y <= y0 + h + margin)


def pitch_to_video(points_rel: Sequence[Sequence[float]], homography, lens: Optional[Dict],
                   in_front: Optional[Sequence[Sequence[float]]] = None) -> np.ndarray:
    """Relative pitch coordinates -> relative video coordinates, NaN where the camera can't see the point.
    ``in_front``: relative video points known to show the ground (the clicked keypoints), which fix which side of
    the camera is the front."""
    H = np.asarray(homography, dtype=np.float64)
    pts = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2)
    front = _front_sign(H, lens, None if in_front is None else np.asarray(in_front, dtype=np.float64).reshape(-1, 2))
    q = _apply(np.linalg.inv(H), pts)
    # H^-1 [p, 1] = [u, 1] / s, with s of the front sign for points in front of the camera
    visible = (np.sign(q[:, 2]) == front) & (np.abs(q[:, 2]) > 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        u = q[:, :2] / q[:, 2:3]
    visible &= np.all(np.abs(u - 0.5) <= MAX_UNDISTORTED_OFFSET, axis=1)
    u[~visible] = np.nan
    v = distort_with_snapshot(u, lens)
    v[~_in_content(v, lens)] = np.nan
    return v


def project_polylines(polylines: Dict[str, np.ndarray], homography, lens: Optional[Dict],
                      in_front: Optional[Sequence[Sequence[float]]] = None) -> List[Dict]:
    """Pitch polylines (relative pitch coordinates) projected into the video: ``[{"name", "points": [[x, y], ...]}]``,
    each split into the pieces the camera can see."""
    out = []
    for name, pts in polylines.items():
        v = pitch_to_video(pts, homography, lens, in_front)
        ok = np.isfinite(v).all(axis=1)
        for run in np.split(np.arange(len(v)), np.flatnonzero(~ok)):
            run = run[ok[run]]
            if len(run) > 1:
                out.append({"name": name, "points": np.round(v[run], 6).tolist()})
    return out


def to_json_points(points: np.ndarray, digits: int = 6) -> List[Optional[List[float]]]:
    """(N, 2) -> ``[[x, y] | None]``: None for points that couldn't be mapped."""
    return [None if not np.isfinite(p).all() else [round(float(p[0]), digits), round(float(p[1]), digits)]
            for p in np.asarray(points, dtype=np.float64).reshape(-1, 2)]
