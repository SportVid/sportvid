"""Lens models on the content frame: 
the angular polynomial the solver fits and the pinhole it starts from. 
Both share ``K``, ``K_new``, ``size``, ``size_new``, ``meta``,
``undistort_points``, ``distort_points`` and ``max_ray_angle``.
``K_new`` / ``size_new`` describe the undistorted pinhole canvas.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

_THETA = np.linspace(0.0, np.pi / 2, 4000)  # ray angles scanned by ``max_ray_angle``


def _monotonic_limit(r: np.ndarray) -> float:
    """First ray angle in ``_THETA`` after which the image radius ``r(theta)`` stops increasing (else 90 deg)."""
    bad = np.flatnonzero(np.diff(r) <= 0)
    return float(_THETA[bad[0]]) if bad.size else float(np.pi / 2)


def even(x: float) -> int:
    """``x`` rounded to the nearest even integer (canvas sizes)."""
    return int(round(x / 2.0)) * 2


def polyval(poly: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Horner's method; ``poly`` in descending order: ``poly[0] x^n + ... + poly[n]``."""
    result = np.full_like(x, poly[0], dtype=np.float64)
    for c in poly[1:]:
        result = x * result + c
    return result


def remove_angular(points: np.ndarray, undist_poly: np.ndarray) -> np.ndarray:
    """centerd, width-normalized distorted points -> undistorted. ``r_u = tan(poly(r_d))``."""
    r_d = np.linalg.norm(points, axis=-1, keepdims=True)
    r_u = np.tan(polyval(undist_poly, r_d))
    scale = np.divide(r_u, r_d, out=np.ones_like(r_d), where=r_d > 1e-10)
    return scale * points


def apply_angular(points: np.ndarray, dist_poly: np.ndarray) -> np.ndarray:
    """centerd, width-normalized undistorted points -> distorted. ``r_d = poly(arctan(r_u))``."""
    r_u = np.linalg.norm(points, axis=-1, keepdims=True)
    r_d = polyval(dist_poly, np.arctan(r_u))
    scale = np.divide(r_d, r_u, out=np.ones_like(r_u), where=r_u > 1e-10)
    return scale * points


@dataclass
class AngularLensModel:
    undist_poly: np.ndarray             # (poly_degree + 1,) descending; r_u = tan(poly(r_d))
    dist_poly: np.ndarray               # its re-fit inverse;            r_d = poly(arctan(r_u))
    K: np.ndarray                       # (3, 3) source (distorted) intrinsics, content px (fx=fy=width)
    size: Tuple[int, int]               # (W, H) of the content frame
    K_new: np.ndarray                   # (3, 3) intrinsics of the undistorted pinhole image
    size_new: Tuple[int, int]           # (W, H) of the undistorted image
    meta: Dict[str, Any] = field(default_factory=dict)

    def undistort_points(self, pts: np.ndarray) -> np.ndarray:
        """Distorted content px -> undistorted pinhole px (``K_new`` frame)."""
        p = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        n = (p - self.K[:2, 2]) / self.K[0, 0]
        u = remove_angular(n, self.undist_poly)
        return u * self.K_new[0, 0] + self.K_new[:2, 2]

    def distort_points(self, pts: np.ndarray) -> np.ndarray:
        """Undistorted pinhole px (``K_new`` frame) -> distorted content px."""
        p = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        n = (p - self.K_new[:2, 2]) / self.K_new[0, 0]
        d = apply_angular(n, self.dist_poly)
        return d * self.K[0, 0] + self.K[:2, 2]

    def max_ray_angle(self) -> float:
        """Largest ray angle (rad) up to which ``dist_poly`` is monotonic: beyond it the model folds rays back
        towards the image center, so projections there must be rejected."""
        return _monotonic_limit(polyval(self.dist_poly, _THETA))

    def to_dict(self) -> Dict[str, Any]:
        return dict(type="angular", undist_poly=self.undist_poly.tolist(), dist_poly=self.dist_poly.tolist(),
                    K=self.K.tolist(), size=list(self.size), K_new=self.K_new.tolist(),
                    size_new=list(self.size_new), meta=self.meta)


class PinholeLens:
    """No distortion at all; same interface as ``AngularLensModel``. f = half the content width."""

    def __init__(self, size: Tuple[int, int]):
        w, h = size
        self.size = self.size_new = (int(w), int(h))
        self.K = self.K_new = np.array([[0.5 * w, 0, (w - 1) / 2.0], [0, 0.5 * w, (h - 1) / 2.0], [0, 0, 1.0]])
        self.meta = dict(pinhole=True)

    def undistort_points(self, pts):
        return np.asarray(pts, dtype=np.float64).reshape(-1, 2)

    distort_points = undistort_points

    @staticmethod
    def max_ray_angle() -> float:
        return np.pi / 2
