"""Lens helpers: Gyroflow lens profiles (OpenCV fisheye model, k1..k4) 
and lenses self-calibrated from the pitch markings (angular polynomial).

Everything here works on the relative video coordinates ([0, 1] x [0, 1]) used by
calibration point correspondences and tracker outputs.

A lens is stored as an intrinsics *snapshot* (a dict, ``CalibrationAssets.lens_intrinsics``) at the
video resolution:

* ``model``: ``"opencv_fisheye"`` or ``"angular"``;
* ``width``, ``height``: the video resolution the matrices are in;
* ``camera_matrix``: K of the distorted video frame, px;
* ``camera_matrix_undistorted``: K of the ideal pinhole image the points are undistorted into, px
  (optional, defaults to ``camera_matrix``). Undistorted points are returned relative to
  ``width`` x ``height`` in that image, so they may lie outside [0, 1];
* ``opencv_fisheye``: ``distortion_coeffs`` (k1..k4), ``theta_d = theta (1 + k1 theta^2 + ... + k4 theta^8)``;
* ``content_rect_rel`` (optional): ``(x0, y0, w, h)`` of the frame region without black bars, relative to the
  frame; the lens is only defined there;
* ``angular``: ``undist_poly`` / ``dist_poly`` (descending coefficients, no constant term),
  optionally ``valid_radius`` / ``max_ray_angle``, past which the polynomial isn't one-to-one;
  ``r_u = tan(undist_poly(r_d))`` and its fitted inverse ``r_d = dist_poly(arctan(r_u))``, with radii
  normalized by ``camera_matrix`` / ``camera_matrix_undistorted`` (sskit / SoccerNet SynLoc convention).

``undistort_with_snapshot`` / ``distort_with_snapshot`` dispatch on ``model``. Points the model cannot
map (rays at or beyond 90 deg, or past the radius where the polynomial folds back) come back as NaN.
"""
import re
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

MODEL_FISHEYE = "opencv_fisheye"
MODEL_ANGULAR = "angular"

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

# how a video frame relates to the profile's calibrated frame (see ``mode_intrinsics``)
ASPECT_SAME = "same"
ASPECT_ROW_CROP = "row_crop"            # video is wider: rows of the calibrated frame cropped
ASPECT_ROW_EXTENSION = "row_extension"  # video is taller: rows beyond the calibrated frame, distortion extrapolated

# EIS crop factors accepted for a video (Gyroflow lists 0.7-0.95 for GoPro HyperSmooth modes)
MIN_CROP = 0.3
MAX_CROP = 1.0

# TODO: What about other camera/lens manufacturers? This is very specific to GoPro...
# Gyroflow identifier suffixes (``...@50000-hsboost``) of GoPro stabilisation modes
EIS_MODE_NAMES = {
    "no-eis": "no EIS",
    "hseis": "HyperSmooth On",
    "hshigh": "HyperSmooth High",
    "hsboost": "HyperSmooth Boost",
    "hsautoboost": "HyperSmooth AutoBoost",
}

# ray angles scanned for the range in which a distortion polynomial is monotonic
_THETA = np.linspace(0.0, np.pi / 2, 4000)


def parse_eis(*texts: Optional[str]) -> str:
    """Guess whether a profile was calibrated with in-camera stabilization from its free-text fields."""
    text = " ".join(t for t in texts if t).lower()
    if any(re.search(p, text) for p in _EIS_OFF_PATTERNS):
        return EIS_OFF
    if any(re.search(p, text) for p in _EIS_ON_PATTERNS):
        return EIS_ON
    return EIS_UNKNOWN


# -------------------------------------------------------------------------------------------------
# profile -> video intrinsics (recording modes)
# -------------------------------------------------------------------------------------------------

def is_compatible(calib_width: int, calib_height: int, width: int, height: int) -> bool:
    """The video has the aspect ratio the profile was calibrated at, so it can be scaled without
    assumptions. Other aspects are modelled as a centred crop (``aspect_fit``)."""
    return aspect_fit(calib_width, calib_height, width, height) == ASPECT_SAME


def aspect_fit(calib_width: int, calib_height: int, width: int, height: int) -> Optional[str]:
    """How the video frame relates to the calibrated frame at the same pixel scale across the width;
    None if a resolution is unknown."""
    if not (calib_width and calib_height and width and height):
        return None
    profile_aspect = calib_width / calib_height
    video_aspect = width / height
    if abs(video_aspect - profile_aspect) / profile_aspect <= ASPECT_TOLERANCE:
        return ASPECT_SAME
    return ASPECT_ROW_CROP if video_aspect > profile_aspect else ASPECT_ROW_EXTENSION


def mode_intrinsics(
    camera_matrix: Sequence[Sequence[float]],
    calib_width: int,
    calib_height: int,
    width: int,
    height: int,
    crop: float = 1.0,
) -> np.ndarray:
    """K of a recording mode at the video resolution, as Gyroflow and trak model GoPro modes:

    1. the video frame has the calibrated frame's pixel scale across the full width; a different
       aspect ratio crops rows (wider video) or extends them beyond the calibrated frame (taller video,
       the fisheye polynomial is extrapolated there);
    2. an EIS crop is a zoom about the frame centre (f / crop).

    The distortion coefficients are defined on the ray angle and stay unchanged.
    """
    if aspect_fit(calib_width, calib_height, width, height) is None:
        raise ValueError(f"Unknown resolution (profile {calib_width}x{calib_height}, video {width}x{height})")
    if not MIN_CROP <= crop <= MAX_CROP:
        raise ValueError(f"EIS crop {crop} outside [{MIN_CROP}, {MAX_CROP}]")
    s = width / calib_width
    K = np.asarray(camera_matrix, dtype=np.float64).copy()
    K[:2, :] *= s
    K[1, 2] -= (calib_height * s - height) / 2.0
    K[:2, :2] /= crop
    K[0, 2] = (K[0, 2] - width / 2.0) / crop + width / 2.0
    K[1, 2] = (K[1, 2] - height / 2.0) / crop + height / 2.0
    return K


def scale_intrinsics(
    camera_matrix: Sequence[Sequence[float]],
    calib_width: int,
    calib_height: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Scale a camera matrix calibrated at calib_width x calib_height to a video of the same aspect ratio."""
    if not is_compatible(calib_width, calib_height, width, height):
        raise ValueError(
            f"Lens profile ({calib_width}x{calib_height}) doesn't match the video aspect ratio ({width}x{height})"
        )
    return mode_intrinsics(camera_matrix, calib_width, calib_height, width, height)


def _mode_suffix(identifier: str) -> str:
    """``gopro-hero11black-wide-3840x3360@25000-hseis`` -> ``hseis``."""
    tail = identifier.rsplit("@", 1)[-1]
    return tail.split("-", 1)[1] if "-" in tail else ""


def recording_modes(raw: Dict, width: int, height: int) -> List[Dict]:
    """The EIS crops a video may have been recorded with under a Gyroflow profile, from its
    ``compatible_settings``: ``{"crop", "label", "listed", "sizes"}`` per distinct crop.

    ``listed``: the calibration or an entry of the video's aspect ratio has this crop; otherwise it is
    borrowed from another aspect ratio, or from a digital-lens entry (e.g. GoPro HyperView, whose
    stretch can't be modelled, but whose EIS crop is the same stabilisation). Crop 1.0 (as calibrated)
    is always included.
    """
    calib = raw.get("calib_dimension") or {}
    modes = {1.0: {"crop": 1.0, "label": "as calibrated", "listed": False, "sizes": set()}}
    if calib.get("w") and calib.get("h"):
        modes[1.0]["sizes"].add(f"{calib['w']}x{calib['h']}")
        modes[1.0]["listed"] = aspect_fit(calib["w"], calib["h"], width, height) == ASPECT_SAME
    for entry in raw.get("compatible_settings") or []:
        if not entry.get("width") or not entry.get("height"):
            continue
        crop = round(float(entry.get("crop") or 1.0), 4)
        if not MIN_CROP <= crop <= MAX_CROP:
            continue
        suffix = _mode_suffix(entry.get("identifier") or "")
        listed = not entry.get("digital_lens") and aspect_fit(entry["width"], entry["height"], width, height) == ASPECT_SAME
        mode = modes.setdefault(crop, {"crop": crop, "label": None, "listed": False, "sizes": set()})
        if mode["label"] in (None, "as calibrated") and suffix in EIS_MODE_NAMES:
            mode["label"] = EIS_MODE_NAMES[suffix]
        mode["listed"] = mode["listed"] or listed
        mode["sizes"].add(f"{entry['width']}x{entry['height']}")
    result = []
    for mode in modes.values():
        mode["label"] = mode["label"] or f"crop {mode['crop']:g}"
        mode["sizes"] = sorted(mode["sizes"])
        result.append(mode)
    return sorted(result, key=lambda m: (not m["listed"], -m["crop"]))


def lens_intrinsics_snapshot(lens_profile, width: int, height: int, crop: float = 1.0) -> Dict:
    """Intrinsics of a LensProfile for a video recorded with EIS ``crop``, stored alongside results computed with them."""
    K = mode_intrinsics(
        lens_profile.camera_matrix, lens_profile.calib_width, lens_profile.calib_height, width, height, crop
    )
    return {
        "lens_profile_id": lens_profile.id.hex,
        "lens_profile_name": lens_profile.name,
        "model": MODEL_FISHEYE,
        "width": width,
        "height": height,
        "crop": crop,
        "aspect_fit": aspect_fit(lens_profile.calib_width, lens_profile.calib_height, width, height),
        "camera_matrix": K.tolist(),
        "distortion_coeffs": list(lens_profile.distortion_coeffs),
    }


def angular_snapshot(solver_result: Dict, width: int, height: int) -> Dict:
    """Intrinsics snapshot of a lens self-calibrated by the ``calibration_lens_solve`` plugin, at the video resolution.

    The solver works on the decoded frame's content region (no black bars) with pixel centres at integers and
    centres its undistorted canvas on a larger image. Here both matrices are moved to whole-frame pixels with the
    frame edge at 0 (as relative video coordinates times the resolution), and the undistorted image is centred on
    the content centre, so undistorted relative coordinates stay close to the video frame.
    """
    lens = solver_result["lens"]
    frame_w, frame_h = solver_result["frame_size"]
    x0, y0, content_w, content_h = lens["meta"].get("content_rect") or [0, 0, frame_w, frame_h]
    K = np.asarray(lens["K"], dtype=np.float64).copy()
    K[0, 2] += x0 + 0.5
    K[1, 2] += y0 + 0.5
    K_new = np.asarray(lens["K_new"], dtype=np.float64).copy()
    K_new[:2, 2] = K[:2, 2]
    scale = np.diag([width / frame_w, height / frame_h, 1.0])
    pose = solver_result.get("pose") or {}
    return {
        "model": MODEL_ANGULAR,
        "source": "calibration_lens_solve",
        "width": width,
        "height": height,
        "camera_matrix": (scale @ K).tolist(),
        "camera_matrix_undistorted": (scale @ K_new).tolist(),
        "undist_poly": list(lens["undist_poly"]),
        "dist_poly": list(lens["dist_poly"]),
        # past this radius (normalised by camera_matrix's focal length) / ray angle the lens isn't one-to-one
        "valid_radius": (solver_result.get("valid_region") or {}).get("radius"),
        "max_ray_angle": (solver_result.get("valid_region") or {}).get("ray_angle"),
        # the region without black bars, where the lens is defined: (x0, y0, w, h) relative to the frame
        "content_rect_rel": [x0 / frame_w, y0 / frame_h, content_w / frame_w, content_h / frame_h],
        "solver": {
            "rounds": solver_result.get("rounds"),
            "markings": lens["meta"].get("markings"),
            "dropped_markings": lens["meta"].get("dropped_markings"),
            "line_rms_px": lens["meta"].get("line_rms_px"),
            "arc_rms_px": lens["meta"].get("arc_rms_px"),
            "pose_rmse_px": pose.get("rmse_px"),
            "horizontal_fov_deg": pose.get("horizontal_fov_deg"),
            "gauge": solver_result.get("gauge"),
            "valid_fraction": (solver_result.get("valid_region") or {}).get("fraction"),
            "frame_times_ms": solver_result.get("frame_times_ms"),
            "keypoints": solver_result.get("keypoints"),
        },
    }


# -------------------------------------------------------------------------------------------------
# point mapping
# -------------------------------------------------------------------------------------------------

def _polyval(poly: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Horner's method; ``poly`` in descending order."""
    result = np.full_like(x, poly[0], dtype=np.float64)
    for c in poly[1:]:
        result = x * result + c
    return result


def _monotonic_limit(values: np.ndarray, grid: np.ndarray) -> float:
    """First grid value after which ``values`` (sampled on ``grid``) stops increasing; else the grid's end."""
    bad = np.flatnonzero(np.diff(values) <= 0)
    return float(grid[bad[0]]) if bad.size else float(grid[-1])


def _fisheye_theta_d(theta: np.ndarray, D: Sequence[float]) -> np.ndarray:
    k1, k2, k3, k4 = (list(D) + [0.0] * 4)[:4]
    t2 = theta * theta
    return theta * (1 + t2 * (k1 + t2 * (k2 + t2 * (k3 + t2 * k4))))


def _to_normalized(points_rel, K: np.ndarray, width: int, height: int) -> np.ndarray:
    pts = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2) * [width, height]
    y = (pts[:, 1] - K[1, 2]) / K[1, 1]
    x = (pts[:, 0] - K[0, 2] - K[0, 1] * y) / K[0, 0]
    return np.stack([x, y], axis=1)


def _from_normalized(n: np.ndarray, K: np.ndarray, width: int, height: int) -> np.ndarray:
    u = K[0, 0] * n[:, 0] + K[0, 1] * n[:, 1] + K[0, 2]
    v = K[1, 1] * n[:, 1] + K[1, 2]
    return np.stack([u / width, v / height], axis=1)


def _rescale(n: np.ndarray, r_from: np.ndarray, r_to: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Move each normalized point from radius ``r_from`` to ``r_to``; NaN where not ``valid``."""
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(r_from > 1e-12, r_to / r_from, 1.0)
    scale[~valid] = np.nan
    return n * scale[:, None]


def undistort_points_rel(
    points_rel: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    distortion_coeffs: Sequence[float],
    width: int,
    height: int,
    iterations: int = 20,
    new_camera_matrix: Optional[Sequence[Sequence[float]]] = None,
) -> np.ndarray:
    """Undistort relative video coordinates with the OpenCV fisheye model.

    Equivalent to cv2.fisheye.undistortPoints(pts, K, D, P=new_camera_matrix or K) on pixel coordinates,
    i.e. the result lives in an ideal pinhole image, again as relative coordinates. Points beyond the
    model's valid range (theta >= 90 deg, or past the angle where the polynomial folds back) are NaN.
    """
    K = np.asarray(camera_matrix, dtype=np.float64)
    P = K if new_camera_matrix is None else np.asarray(new_camera_matrix, dtype=np.float64)
    n = _to_normalized(points_rel, K, width, height)
    theta_d = np.hypot(n[:, 0], n[:, 1])
    theta_max = _monotonic_limit(_fisheye_theta_d(_THETA, distortion_coeffs), _THETA)

    # Newton iterations on theta_d = theta * (1 + k1 theta^2 + k2 theta^4 + k3 theta^6 + k4 theta^8)
    k1, k2, k3, k4 = (list(distortion_coeffs) + [0.0] * 4)[:4]
    theta = theta_d.copy()
    for _ in range(iterations):
        t2 = theta * theta
        f = _fisheye_theta_d(theta, distortion_coeffs) - theta_d
        df = 1 + t2 * (3 * k1 + t2 * (5 * k2 + t2 * (7 * k3 + t2 * 9 * k4)))
        theta = theta - f / df

    valid = (theta >= 0) & (theta < min(theta_max, np.pi / 2 - 1e-9))
    with np.errstate(invalid="ignore"):
        r_u = np.tan(np.where(valid, theta, 0.0))
    return _from_normalized(_rescale(n, theta_d, r_u, valid), P, width, height)


def distort_points_rel(
    points_rel: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    distortion_coeffs: Sequence[float],
    width: int,
    height: int,
    new_camera_matrix: Optional[Sequence[Sequence[float]]] = None,
) -> np.ndarray:
    """Inverse of ``undistort_points_rel``: relative coordinates in the pinhole image -> distorted video."""
    K = np.asarray(camera_matrix, dtype=np.float64)
    P = K if new_camera_matrix is None else np.asarray(new_camera_matrix, dtype=np.float64)
    n = _to_normalized(points_rel, P, width, height)
    r_u = np.hypot(n[:, 0], n[:, 1])
    theta = np.arctan(r_u)
    theta_max = _monotonic_limit(_fisheye_theta_d(_THETA, distortion_coeffs), _THETA)
    return _from_normalized(_rescale(n, r_u, _fisheye_theta_d(theta, distortion_coeffs), theta < theta_max),
                            K, width, height)


def undistort_points_angular_rel(
    points_rel: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    new_camera_matrix: Sequence[Sequence[float]],
    undist_poly: Sequence[float],
    width: int,
    height: int,
    valid_radius: Optional[float] = None,
) -> np.ndarray:
    """Undistort relative video coordinates with an angular polynomial lens: ``r_u = tan(undist_poly(r_d))``."""
    K = np.asarray(camera_matrix, dtype=np.float64)
    poly = np.asarray(undist_poly, dtype=np.float64)
    n = _to_normalized(points_rel, K, width, height)
    r_d = np.hypot(n[:, 0], n[:, 1])
    grid = np.linspace(0.0, max(float(np.nanmax(r_d, initial=0.0)), 1e-6) * 1.01, 4000)
    r_max = _monotonic_limit(_polyval(poly, grid), grid)
    angle = _polyval(poly, r_d)
    valid = (angle >= 0) & (angle < np.pi / 2 - 1e-9) & (r_d <= r_max)
    if valid_radius is not None:
        valid &= r_d <= valid_radius
    with np.errstate(invalid="ignore"):
        r_u = np.tan(np.where(valid, angle, 0.0))
    return _from_normalized(_rescale(n, r_d, r_u, valid), np.asarray(new_camera_matrix, dtype=np.float64),
                            width, height)


def distort_points_angular_rel(
    points_rel: Sequence[Sequence[float]],
    camera_matrix: Sequence[Sequence[float]],
    new_camera_matrix: Sequence[Sequence[float]],
    dist_poly: Sequence[float],
    width: int,
    height: int,
    max_ray_angle: Optional[float] = None,
) -> np.ndarray:
    """Inverse of ``undistort_points_angular_rel``: ``r_d = dist_poly(arctan(r_u))``."""
    poly = np.asarray(dist_poly, dtype=np.float64)
    n = _to_normalized(points_rel, np.asarray(new_camera_matrix, dtype=np.float64), width, height)
    r_u = np.hypot(n[:, 0], n[:, 1])
    theta = np.arctan(r_u)
    theta_max = _monotonic_limit(_polyval(poly, _THETA), _THETA)
    if max_ray_angle is not None:
        theta_max = min(theta_max, max_ray_angle)
    return _from_normalized(_rescale(n, r_u, _polyval(poly, theta), theta < theta_max),
                            np.asarray(camera_matrix, dtype=np.float64), width, height)


def undistorted_camera_matrix(snapshot: Dict) -> List[List[float]]:
    """K of the pinhole image a snapshot undistorts into (what a homography on undistorted points sees)."""
    return snapshot.get("camera_matrix_undistorted") or snapshot["camera_matrix"]


def undistort_with_snapshot(points_rel: Sequence[Sequence[float]], snapshot: Optional[Dict]) -> np.ndarray:
    """Undistort relative points with a stored intrinsics snapshot; identity if there is none."""
    points = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2)
    if not snapshot:
        return points
    model = snapshot.get("model", MODEL_FISHEYE)
    if model == MODEL_FISHEYE:
        return undistort_points_rel(
            points, snapshot["camera_matrix"], snapshot["distortion_coeffs"], snapshot["width"], snapshot["height"],
            new_camera_matrix=snapshot.get("camera_matrix_undistorted"),
        )
    if model == MODEL_ANGULAR:
        return undistort_points_angular_rel(
            points, snapshot["camera_matrix"], undistorted_camera_matrix(snapshot), snapshot["undist_poly"],
            snapshot["width"], snapshot["height"], valid_radius=snapshot.get("valid_radius"),
        )
    raise ValueError(f"Unknown lens model '{model}'")


def distort_with_snapshot(points_rel: Sequence[Sequence[float]], snapshot: Optional[Dict]) -> np.ndarray:
    """Map relative points of the undistorted image back into the video; identity if there is no snapshot."""
    points = np.asarray(points_rel, dtype=np.float64).reshape(-1, 2)
    if not snapshot:
        return points
    model = snapshot.get("model", MODEL_FISHEYE)
    if model == MODEL_FISHEYE:
        return distort_points_rel(
            points, snapshot["camera_matrix"], snapshot["distortion_coeffs"], snapshot["width"], snapshot["height"],
            new_camera_matrix=snapshot.get("camera_matrix_undistorted"),
        )
    if model == MODEL_ANGULAR:
        return distort_points_angular_rel(
            points, snapshot["camera_matrix"], undistorted_camera_matrix(snapshot), snapshot["dist_poly"],
            snapshot["width"], snapshot["height"], max_ray_angle=snapshot.get("max_ray_angle"),
        )
    raise ValueError(f"Unknown lens model '{model}'")


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
