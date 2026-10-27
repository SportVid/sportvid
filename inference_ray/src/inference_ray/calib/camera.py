"""A pinhole camera behind a lens, in the pitch frame.
ground (pitch metres) --pinhole--> undistorted px --distort--> content px --offset--> frame px
``f`` / ``pp`` are the focal length and principal point of the *undistorted* image, 
``R`` / ``C`` the world(pitch) --> camera rotation and the camera center in the pitch frame.
"""
from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np


def intrinsics(f: float, pp) -> np.ndarray:
    return np.array([[f, 0.0, pp[0]], [0.0, f, pp[1]], [0.0, 0.0, 1.0]])


def ground_homography(f: float, pp, R, C) -> np.ndarray:
    """Ground plane (pitch metres, z = 0) -> pinhole px homography of a camera with pose ``R`` / ``C``."""
    return intrinsics(f, pp) @ np.stack([R[:, 0], R[:, 1], -R @ C], axis=1)


def pack_pose(f: float, R, C) -> np.ndarray:
    """``(f, R, C)`` -> the 7-vector ``[f, Rodrigues(R), C]`` the pose solvers optimise."""
    return np.r_[f, cv2.Rodrigues(np.asarray(R))[0].ravel(), C]


def unpack_pose(p) -> Tuple[float, np.ndarray, np.ndarray]:
    return p[0], cv2.Rodrigues(p[1:4])[0], p[4:7]


def pinhole_project(R, C, f: float, pp, X) -> Tuple[np.ndarray, np.ndarray]:
    """Pitch-frame points ``X`` (N, 3) -> pinhole px (N, 2) and camera-frame coordinates (N, 3)."""
    Xc = (np.asarray(X, dtype=np.float64) - C) @ R.T
    z = np.where(np.abs(Xc[:, 2]) < 1e-9, 1e-9, Xc[:, 2])
    return np.stack([f * Xc[:, 0] / z + pp[0], f * Xc[:, 1] / z + pp[1]], axis=1), Xc


def is_physical(R, C, X) -> bool:
    """Every point of ``X`` (N, 3) in front of the camera ``R`` / ``C``, and the camera above the ground (z <= 0)."""
    return not (((X - C) @ R.T)[:, 2].min() <= 0 or C[2] > 0)


def apply_homography(H: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    q = np.c_[pts, np.ones(len(pts))] @ np.asarray(H, dtype=np.float64).T
    return q[:, :2] / np.where(np.abs(q[:, 2:3]) < 1e-12, 1e-12, q[:, 2:3])


@dataclass
class CameraModel:
    lens: object
    f: float
    pp: np.ndarray
    R: np.ndarray
    C: np.ndarray
    offset: np.ndarray  # top-left of the content region (no black bars) in the video frame, px

    @classmethod
    def from_params(cls, lens, p, offset) -> "CameraModel":
        """Camera from a solver vector ``pack_pose(f, R, C)``; principal point at the lens's ``K_new``."""
        f, R, C = unpack_pose(np.asarray(p, dtype=np.float64))
        return cls(lens, f, lens.K_new[:2, 2], R, C, np.asarray(offset, dtype=np.float64))

    def pixels(self, xyz) -> np.ndarray:
        """Pitch-frame points (N, 3) -> frame px, without validity (for solvers' residuals)."""
        return self.lens.distort_points(pinhole_project(self.R, self.C, self.f, self.pp, xyz)[0]) + self.offset

    def project(self, xyz, margin_deg: float = 0.0, in_content: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """Pitch-frame points (N, 3) -> ``(frame px, valid)``. ``valid``: in front of the camera, within the lens
        model's monotonic range less ``margin_deg`` and (``in_content``) inside the content region."""
        u, Xc = pinhole_project(self.R, self.C, self.f, self.pp, xyz)
        theta = np.arctan2(np.hypot(Xc[:, 0], Xc[:, 1]), Xc[:, 2])
        q = self.lens.distort_points(u)
        w, h = self.lens.size
        cutoff = self.lens.max_ray_angle() - np.radians(margin_deg)
        valid = (Xc[:, 2] > 1e-6) & (theta < cutoff)
        if in_content:
            valid &= (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
        return q + self.offset, valid

    def project_ground(self, xy, return_valid: bool = False, margin_deg: float = 0.0, in_content: bool = True):
        """Ground-plane pitch metres (N, 2) -> frame px. See ``project`` for ``margin_deg`` / ``in_content``."""
        xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
        px, valid = self.project(np.c_[xy, np.zeros(len(xy))], margin_deg=margin_deg, in_content=in_content)
        return (px, valid) if return_valid else px
