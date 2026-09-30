"""Lens helpers for Gyroflow lens profiles (OpenCV fisheye model, k1..k4).

Everything here works on the relative video coordinates ([0, 1] x [0, 1]) used by
calibration point correspondences and tracker outputs, and is numpy-only so the
backend doesn't need OpenCV.
"""
import re
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

EIS_ON = "on"
EIS_OFF = "off"
EIS_UNKNOWN = "unknown"

# checked in order; "off" first so "NO-EIS" doesn't match the generic "EIS" pattern
_EIS_OFF_PATTERNS = [
    r"\bno[-_ ]?eis\b", r"\bnon[-_ ]?eis\b", r"\beis[-_ ]?(off|n|no)\b",
    r"\bno[-_ ]?stab", r"\bstab(ilization|ilisation)?[-_ ]?off\b",
    r"\b(hs|hypersmooth|rs|rocksteady)[-_ ]?off\b", r"\bwithout (eis|stabili[sz]ation)\b",
]
_EIS_ON_PATTERNS = [
    r"\beis\b", r"\beis[-_ ]?(on|y|yes)\b", r"\bstab(ilization|ilisation)?[-_ ]?on\b",
    r"\bhs\b", r"hypersmooth", r"rocksteady", r"horizon[-_ ]?(lock|leveling|levelling)",
]

# relative tolerance when comparing aspect ratios of video and profile
ASPECT_TOLERANCE = 0.01


def parse_eis(*texts: Optional[str]) -> str:
    """Guess whether a profile was calibrated with in-camera stabilization from its free-text fields."""
    text = " ".join(t for t in texts if t).lower()
    if any(re.search(p, text) for p in _EIS_OFF_PATTERNS):
        return EIS_OFF
    if any(re.search(p, text) for p in _EIS_ON_PATTERNS):
        return EIS_ON
    return EIS_UNKNOWN


def is_compatible(calib_width: int, calib_height: int, width: int, height: int) -> bool:
    """A profile can be scaled to a video if both share the aspect ratio (Gyroflow treats
    differing aspect ratios as a sensor crop, which we don't support)."""
    if not (calib_width and calib_height and width and height):
        return False
    profile_aspect = calib_width / calib_height
    video_aspect = width / height
    return abs(video_aspect - profile_aspect) / profile_aspect <= ASPECT_TOLERANCE


def scale_intrinsics(
    camera_matrix: Sequence[Sequence[float]],
    calib_width: int,
    calib_height: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Scale a camera matrix calibrated at calib_width x calib_height to the video resolution."""
    if not is_compatible(calib_width, calib_height, width, height):
        raise ValueError(
            f"Lens profile ({calib_width}x{calib_height}) doesn't match the video aspect ratio ({width}x{height})"
        )
    K = np.asarray(camera_matrix, dtype=np.float64).copy()
    K[0, :] *= width / calib_width
    K[1, :] *= height / calib_height
    return K


def undistort_points_rel(
    points_rel: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    distortion_coeffs: Sequence[float],
    width: int,
    height: int,
    iterations: int = 20,
) -> np.ndarray:
    """Undistort relative video coordinates with the OpenCV fisheye model.

    Equivalent to cv2.fisheye.undistortPoints(pts, K, D, P=K) on pixel coordinates, i.e.
    the result lives in an ideal pinhole image with the same K, again as relative coordinates.
    Points beyond the model's valid range (theta >= 90 deg) come back as NaN.
    """
    K = np.asarray(camera_matrix, dtype=np.float64)
    k1, k2, k3, k4 = (list(distortion_coeffs) + [0.0] * 4)[:4]
    pts = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2) * [width, height]

    y_d = (pts[:, 1] - K[1, 2]) / K[1, 1]
    x_d = (pts[:, 0] - K[0, 2] - K[0, 1] * y_d) / K[0, 0]
    theta_d = np.hypot(x_d, y_d)

    # Newton iterations on theta_d = theta * (1 + k1 theta^2 + k2 theta^4 + k3 theta^6 + k4 theta^8)
    theta = theta_d.copy()
    for _ in range(iterations):
        t2 = theta * theta
        f = theta * (1 + t2 * (k1 + t2 * (k2 + t2 * (k3 + t2 * k4)))) - theta_d
        df = 1 + t2 * (3 * k1 + t2 * (5 * k2 + t2 * (7 * k3 + t2 * 9 * k4)))
        theta = theta - f / df

    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(theta_d > 1e-12, np.tan(theta) / theta_d, 1.0)
    scale[(theta < 0) | (theta >= np.pi / 2)] = np.nan

    x_u, y_u = x_d * scale, y_d * scale
    u = K[0, 0] * x_u + K[0, 1] * y_u + K[0, 2]
    v = K[1, 1] * y_u + K[1, 2]
    return np.stack([u / width, v / height], axis=1)


def lens_intrinsics_snapshot(lens_profile, width: int, height: int) -> Dict:
    """Intrinsics of a LensProfile scaled to a video, stored alongside results computed with them."""
    K = scale_intrinsics(
        lens_profile.camera_matrix, lens_profile.calib_width, lens_profile.calib_height, width, height
    )
    return {
        "lens_profile_id": lens_profile.id.hex,
        "lens_profile_name": lens_profile.name,
        "model": "opencv_fisheye",
        "width": width,
        "height": height,
        "camera_matrix": K.tolist(),
        "distortion_coeffs": list(lens_profile.distortion_coeffs),
    }


def undistort_with_snapshot(points_rel: Sequence[Sequence[float]], snapshot: Optional[Dict]) -> np.ndarray:
    """Undistort relative points with a stored intrinsics snapshot; identity if there is none."""
    points = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2)
    if not snapshot:
        return points
    return undistort_points_rel(
        points,
        snapshot["camera_matrix"],
        snapshot["distortion_coeffs"],
        snapshot["width"],
        snapshot["height"],
    )


def camera_pose_from_homography(
    homography: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    width: int,
    height: int,
    field_length: float,
    field_width: float,
) -> Dict:
    """Recover the camera pose from an (undistorted) image -> pitch homography and known intrinsics.

    `homography` maps relative (undistorted) video coordinates to relative pitch coordinates,
    as stored on CalibrationAssets. The pitch frame is x along the length and y along the width
    (both in metres, origin at relative (0, 0)), z is the pitch normal.
    """
    H = np.asarray(homography, dtype=np.float64)
    K = np.asarray(camera_matrix, dtype=np.float64)
    image_scale = np.diag([width, height, 1.0])
    pitch_scale = np.diag([field_length, field_width, 1.0])

    # pitch metres -> undistorted pixels, which is K [r1 r2 t] up to scale
    G = image_scale @ np.linalg.inv(H) @ np.linalg.inv(pitch_scale)
    M = np.linalg.inv(K) @ G
    n1, n2 = np.linalg.norm(M[:, 0]), np.linalg.norm(M[:, 1])
    M = M * (2.0 / (n1 + n2))
    if M[2, 2] < 0:  # the pitch has to be in front of the camera
        M = -M

    r1, r2, t = M[:, 0], M[:, 1], M[:, 2]
    U, _, Vt = np.linalg.svd(np.stack([r1, r2, np.cross(r1, r2)], axis=1))
    R = U @ Vt
    center = -R.T @ t
    optical_axis = R.T @ np.array([0.0, 0.0, 1.0])

    pose = {
        "position": {"x": float(center[0]), "y": float(center[1])},
        "height": float(abs(center[2])),
        # angle of the optical axis below the pitch plane (90 = looking straight down)
        "tilt_deg": float(np.degrees(np.arcsin(min(abs(optical_axis[2]), 1.0)))),
        # direction of the optical axis projected onto the pitch, in the pitch frame
        "heading_deg": float(np.degrees(np.arctan2(optical_axis[1], optical_axis[0]))),
        "horizontal_fov_deg": float(np.degrees(2 * np.arctan(width / (2 * K[0, 0])))),
        "rotation": R.tolist(),
        "translation": t.tolist(),
        # a homography consistent with K has equally long, orthogonal first two columns in
        # K^-1 H; large deviations mean a wrong lens profile or bad point correspondences
        "consistency": {
            "norm_ratio": float(n1 / n2),
            "orthogonality": float(abs(np.dot(r1, r2)) / (np.linalg.norm(r1) * np.linalg.norm(r2))),
        },
    }
    return pose


def reprojection_rmse(
    homography: Sequence[Sequence[float]],
    src_points_rel: Sequence[Sequence[float]],
    dst_points_rel: Sequence[Sequence[float]],
    field_length: float,
    field_width: float,
) -> float:
    """RMS distance in metres between the pitch points and the video points mapped by the homography."""
    src = np.asarray(src_points_rel, dtype=np.float64).reshape(-1, 2)
    dst = np.asarray(dst_points_rel, dtype=np.float64).reshape(-1, 2)
    error_m = (apply_homography(homography, src) - dst) * [field_length, field_width]
    return float(np.sqrt(np.mean(np.sum(error_m**2, axis=1))))


def apply_homography(homography: Sequence[Sequence[float]], points: Sequence[Sequence[float]]) -> np.ndarray:
    H = np.asarray(homography, dtype=np.float64)
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    projected = np.concatenate([pts, np.ones((len(pts), 1))], axis=1) @ H.T
    return projected[:, :2] / projected[:, 2:3]


def unsupported_reason(profile_json: Dict) -> Optional[str]:
    """Why a raw Gyroflow profile can't be applied with the plain OpenCV fisheye model, if at all."""
    if (profile_json.get("distortion_model") or "opencv_fisheye") != "opencv_fisheye":
        return f"distortion model '{profile_json.get('distortion_model')}'"
    if profile_json.get("digital_lens"):
        return f"digital lens '{profile_json.get('digital_lens')}'"
    if profile_json.get("asymmetrical"):
        return "asymmetrical lens"
    if (profile_json.get("input_horizontal_stretch") or 1.0) != 1.0 or (
        profile_json.get("input_vertical_stretch") or 1.0
    ) != 1.0:
        return "anamorphic input stretch"
    if profile_json.get("interpolations"):
        return "interpolated (zoom) profile"
    params = profile_json.get("fisheye_params") or {}
    if len(params.get("camera_matrix") or []) != 3 or len(params.get("distortion_coeffs") or []) != 4:
        return "missing camera matrix or distortion coefficients"
    return None
