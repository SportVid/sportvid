"""Focal length and pose of a static camera from clicked pitch keypoints.
Initialized from a homography of the undistorted points with a plane decomposition, then a robust fit of f,
rotation and camera center from several start focal lengths; 
``fit_raw`` refines it in raw frame px through any lens.
"""
from typing import Dict, Optional

import cv2
import numpy as np
from scipy.optimize import least_squares

from .camera import CameraModel, intrinsics, is_physical, pack_pose, pinhole_project, unpack_pose

F_MULTI_START = (0.6, 0.8, 1.0, 1.25, 1.6)      # initial f relative to the lens's canvas f
ROBUST_PX = 3.0                                 # soft-L1 scale of the pixel loss


def decompose(H_pitch2img: np.ndarray, K: np.ndarray, pts_pitch: np.ndarray):
    """World(pitch) --> camera rotation and camera center (pitch frame) of a plane homography.

    The overall sign of the decomposition is ambiguous; it is chosen so that the given
    ground points lie in front of the camera (the pitch origin itself may be behind it).
    """
    A0 = np.linalg.inv(K) @ H_pitch2img
    A0 = A0 / np.linalg.norm(A0[:, 0])
    X = np.c_[pts_pitch, np.zeros(len(pts_pitch))]
    best = None
    for sign in (1.0, -1.0):
        r1, r2, t = (sign * A0).T
        U, _, Vt = np.linalg.svd(np.stack([r1, r2, np.cross(r1, r2)], 1))
        R = U @ Vt
        depth = float(np.mean(X @ R[2] + t[2])) # mean z_cam of the points
        if best is None or depth > best[0]:
            best = (depth, R, -R.T @ t)
    return best[1], best[2]


def fit(img, pit, pp, R0, C0, f0) -> Dict:
    """Robust undistorted-pixel fit of f, rotation and camera center; raises ValueError if non-physical."""
    X = np.c_[pit, np.zeros(len(pit))]

    def resid(p):
        f, R, C = unpack_pose(p)
        return (pinhole_project(R, C, f, pp, X)[0] - img).ravel()

    sol = least_squares(resid, pack_pose(f0, R0, C0), loss="soft_l1", f_scale=ROBUST_PX, x_scale="jac")
    f, R, C = unpack_pose(sol.x)
    if not is_physical(R, C, X):
        raise ValueError("non-physical solution")
    res = np.linalg.norm((pinhole_project(R, C, f, pp, X)[0] - img), axis=1)
    cost = float(np.sum(2 * ROBUST_PX ** 2 * (np.sqrt(1 + (res / ROBUST_PX) ** 2) - 1)))
    return dict(f=float(f), R=R, C=C, res=res, cost=cost)


def rms(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x ** 2))) if x.size else float("nan")


def fit_multistart(img, pit, pp, R0, C0, f0: float) -> Optional[Dict]:
    """``fit`` from each ``F_MULTI_START`` multiple of ``f0``; the lowest-cost physical solution (None if none)."""
    fits = []
    for m in F_MULTI_START:
        try:
            fits.append(fit(img, pit, pp, R0, C0, f0 * m))
        except ValueError:
            pass
    return min(fits, key=lambda s: s["cost"]) if fits else None


def fit_raw(lens, off, raw, pit, x0=None) -> Optional[Dict]:
    """f + pose minimizing the robust reprojection error in *raw* frame px through ``lens`` (content offset ``off``);
    ``x`` is ``pack_pose(f, R, C)``. Starts from ``x0`` or a multi-start fit on the undistorted points. 
    None if non-physical.
    """
    X = np.c_[pit, np.zeros(len(pit))]
    pp, f_new = lens.K_new[:2, 2], float(lens.K_new[0, 0])
    if x0 is None:
        und = lens.undistort_points(raw - off)
        if not np.isfinite(und).all():
            return None
        H, _ = cv2.findHomography(pit, und, 0)
        if H is None:
            return None
        R0, C0 = decompose(H, intrinsics(f_new, pp), pit)
        s = fit_multistart(und, pit, pp, R0, C0, f_new)
        if s is None:
            return None
        x0 = pack_pose(s["f"], s["R"], s["C"])
    try:
        sol = least_squares(lambda p: (CameraModel.from_params(lens, p, off).pixels(X) - raw).ravel(), x0,
                            loss="soft_l1", f_scale=ROBUST_PX, x_scale="jac")
    except ValueError:
        return None
    f, R, C = unpack_pose(sol.x)
    if f <= 0 or not is_physical(R, C, X):
        return None
    return dict(x=sol.x, f=float(f), R=R, C=C,
                res=np.linalg.norm(CameraModel.from_params(lens, sol.x, off).pixels(X) - raw, axis=1))
