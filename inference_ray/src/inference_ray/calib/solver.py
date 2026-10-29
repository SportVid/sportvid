"""Prior-free lens self-calibration.

The lens is an angular polynomial, ``r_u = tan(p(r_d))`` 
with ``r`` the radius from the content center divided by the content width. 
``fit_angular_lens_anchored`` fits its shape and one plane homography jointly so that every
detected marking point, undistorted, lies on its pitch marking mapped into the image 
(point-line distance for lines, Sampson distance to the conic for circles), 
with the clicks pinning the homography. Markings the pitch model puts elsewhere than they 
are painted are dropped first. The constant and linear coefficients stay fixed:
the linear one only sets the overall zoom, which the focal length absorbs.

``self_calibrate`` starts from a pinhole and alternates detecting the markings 
around the current lens's projection and refitting the lens, until the detected marking set 
stops growing. ``physical_gauge`` then moves the zoom into the lens, once a pose fit has 
measured the focal length, so the lens's angles and ``K_new`` are physical.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.optimize import least_squares

from . import detection
from .camera import CameraModel, apply_homography
from .lens import AngularLensModel, PinholeLens, even, polyval, remove_angular
from .pitch import SoccerPitch, element_geometry, marking_distance, pitch_curves, straight_lines
from .pose import fit_raw, rms

logger = logging.getLogger(__name__)

PITCH_SCALE_M = 50.0                  # pitch metres are divided by this inside the solver (conditioning)
OUT_SCALE_MAX = 2.5                   # out_scale: auto cap -- toward 90 deg a fisheye's corners run off to infinity
_AUTO_MAX_RAY_DEG = 85.0              # out_scale: auto -- a content border ray this far off-axis hits the cap


@dataclass
class AngularSolverConfig:
    poly_degree: int = 6              # 5-8 typical for strong fisheye / EIS modes
    max_iterations: int = 300
    tol: float = 1e-12
    regularization: float = 1e-5      # pull toward the round's starting polynomial (guards sparse data against a
                                      # degenerate fold-back)
    min_slope: float = 0.1            # the ray angle's slope d theta / d r_d, out to past the content corner, may not
                                      # fall below this fraction of its slope at the center. The markings rarely reach
                                      # the corners, and a free polynomial past them can fold back; 0 -> no constraint
    monotonic_weight: float = 1.0     # its penalty, in content px per unit of slope shortfall


def _unfolded(theta: np.ndarray) -> np.ndarray:
    """Mask of the samples of ``theta(r)`` (increasing ``r``) before the ray angle first stops increasing."""
    bad = np.flatnonzero(np.diff(theta) <= 0)
    keep = np.ones(len(theta), dtype=bool)
    if bad.size:
        keep[bad[0] + 1:] = False
    return keep


def _fit_inverse_polynomial(undist_poly: np.ndarray, num_samples: int = 200, r_max: float = 0.9) -> np.ndarray:
    """``dist_poly`` with ``r_d = dist_poly(arctan(r_u))`` approximating the inverse of ``undist_poly``, by
    sampling and re-fitting (the angular model has no closed-form inverse). Sampled only up to where
    ``undist_poly`` folds back (``_unfolded``): past it the forward map has no inverse, and fitting through the
    fold bends ``dist_poly`` everywhere, by 100+ px well inside the data."""
    r_d = np.linspace(0.0, r_max, num_samples)
    r_d = r_d[_unfolded(polyval(undist_poly, r_d))]
    r_u = np.tan(polyval(undist_poly, r_d))
    mask = np.isfinite(r_u) & (r_u > 0) & (r_u < 20)
    if mask.sum() < len(undist_poly):
        return undist_poly.copy()
    if undist_poly[-1] == 0.0:  # forward map through the origin: keep the inverse there too
        theta = np.arctan(r_u[mask])
        A = theta[:, None] ** np.arange(len(undist_poly) - 1, 0, -1)
        return np.r_[np.linalg.lstsq(A, r_d[mask], rcond=None)[0], 0.0]
    return np.polyfit(np.arctan(r_u[mask]), r_d[mask], len(undist_poly) - 1)


def auto_out_scale(undist_poly: np.ndarray, content_wh: Tuple[int, int], f_new: float,
                   canvas_wh: Tuple[int, int]) -> float:
    """Canvas scale (relative to ``canvas_wh``, at focal length ``f_new``) that holds the whole content frame once
    undistorted: the border of the content frame is undistorted and the canvas sized to its extent. At least 1, at
    most ``OUT_SCALE_MAX``."""
    w, h = content_wh
    c = np.array([(w - 1) / 2.0, (h - 1) / 2.0])
    t = np.linspace(0.0, 1.0, 101)[:, None]
    border = np.r_[np.c_[t * (w - 1), 0 * t], np.c_[t * (w - 1), 0 * t + (h - 1)],
                   np.c_[0 * t, t * (h - 1)], np.c_[0 * t + (w - 1), t * (h - 1)]]
    n = (border - c) / w
    theta = polyval(undist_poly, np.linalg.norm(n, axis=1))
    if not np.isfinite(theta).all() or np.degrees(theta.max()) >= _AUTO_MAX_RAY_DEG:
        return OUT_SCALE_MAX
    u = remove_angular(n, undist_poly) * f_new                          # canvas px from the center
    s = max(2.0 * np.abs(u[:, 0]).max() / canvas_wh[0], 2.0 * np.abs(u[:, 1]).max() / canvas_wh[1])
    return float(np.clip(s, 1.0, OUT_SCALE_MAX))


def poly_from_lens(lens, content_wh: Tuple[int, int], degree: int) -> np.ndarray:
    """Angular polynomial (``r_d`` -> ray angle) approximating ``lens``, sampled along the content diagonal: the
    anchored fit's start and its zoom gauge."""
    w, h = content_wh
    c = np.array([(w - 1) / 2.0, (h - 1) / 2.0])
    direction = np.array([w, h], dtype=np.float64) / np.hypot(w, h)
    r_d = np.linspace(0.0, 0.5 * np.hypot(w, h) / w, 200)
    u = (lens.undistort_points(c + np.outer(r_d * w, direction)) - lens.K_new[:2, 2]) / lens.K_new[0, 0]
    theta = np.arctan(np.linalg.norm(u, axis=1))
    ok = np.isfinite(theta)
    A = r_d[ok, None] ** np.arange(degree, 0, -1)                   # no constant term: angle 0 at the center
    return np.r_[np.linalg.lstsq(A, theta[ok], rcond=None)[0], 0.0]


def _point_scale(poly: np.ndarray, pts_norm: np.ndarray, w: int) -> np.ndarray:
    """Content px per unit of undistorted normalized coordinate at each point (geometric mean of the
    radial and tangential magnification): turns undistorted-plane distances into approximate image px."""
    r_d = np.maximum(np.linalg.norm(pts_norm, axis=1), 1e-6)
    theta = polyval(poly, r_d)
    radial = 1.0 / np.cos(theta) ** 2 * polyval(np.polyder(poly), r_d)    # d r_u / d r_d
    tangential = np.tan(theta) / r_d                                       # r_u / r_d
    return w / np.sqrt(np.abs(radial * tangential))


def _homog_delta(d: np.ndarray) -> np.ndarray:
    return np.eye(3) + np.r_[d, 0.0].reshape(3, 3)


def _least_squares(fun, x0: np.ndarray, **kw):
    return least_squares(fun, x0, loss="soft_l1", f_scale=1.0, x_scale="jac", **kw)


def fit_angular_lens_anchored(elements: List[Tuple[str, np.ndarray, np.ndarray]], content_wh: Tuple[int, int],
                              init_poly: np.ndarray, keypoints: Tuple[np.ndarray, np.ndarray],
                              canvas: Tuple[float, Tuple[int, int]], config: Optional[AngularSolverConfig] = None,
                              keypoint_weight: float = 1.0, outlier_px: float = 3.0, out_scale="auto"
                              ) -> AngularLensModel:
    """Fit the angular polynomial and one plane homography (pitch -> undistorted image) jointly, so that every
    detected marking point, undistorted, lies on its pitch marking mapped into the image.

    ``elements``: ``(name, content px (N, 2), geometry)`` per marking, geometry a homogeneous pitch line ``(3,)``
    or a circle conic ``(3, 3)`` in pitch metres (``element_geometry``). ``keypoints``: clicked ``(content px,
    pitch xy)``; they initialise the homography and enter the cost with ``keypoint_weight``. ``init_poly``
    (``poly_from_lens``) is both the start and the weak prior; its linear coefficient fixes the free zoom.
    ``canvas``: ``(f, (W, H))`` of the undistorted image, the guide lens's: the zoom is the guide's.

    A marking whose median residual exceeds ``outlier_px`` under the initial lens, with the homography fitted to
    the keypoints and all markings, is dropped first: it is painted elsewhere than the pitch model puts it, and a
    straight line in the wrong place would bend the lens to compensate.
    """
    config = config or AngularSolverConfig()
    w, h = content_wh
    c = np.array([(w - 1) / 2.0, (h - 1) / 2.0])
    T = np.diag([1.0 / PITCH_SCALE_M, 1.0 / PITCH_SCALE_M, 1.0])
    Ti = np.linalg.inv(T)
    init_poly = np.asarray(init_poly, dtype=np.float64)
    # fitted: the coefficients of r^degree .. r^2. The linear one stays at the guide's (the free zoom), the constant
    # at 0 (angle 0 at the center, else the undistortion is singular there)
    n = len(init_poly) - 2

    elems, names = [], []          # (normalized px, geometry in scaled pitch units, kind: line / arc)
    for name, pts, g in elements:
        if len(pts) < 3:
            continue
        pn = (np.asarray(pts, dtype=np.float64) - c) / w
        g = np.asarray(g, dtype=np.float64)
        elems.append((pn, Ti.T @ g if g.ndim == 1 else Ti.T @ g @ Ti, "line" if g.ndim == 1 else "arc"))
        names.append(name)
    if not elems:
        raise ValueError("no detected marking with >= 3 points")
    kp_px, kp_pitch = (np.asarray(a, dtype=np.float64) for a in keypoints)
    kp_n = (kp_px - c) / w
    kp_pitch_h = np.c_[kp_pitch[:, :2], np.ones(len(kp_pitch))] @ T.T

    H0, _ = cv2.findHomography(kp_pitch_h[:, :2], remove_angular(kp_n, init_poly), 0)
    if H0 is None:
        raise ValueError("could not initialise the homography from the keypoints")
    g0 = np.zeros(8)

    def plane(g):
        return H0 @ _homog_delta(g)

    def element_residuals(poly: np.ndarray, g: np.ndarray) -> List[np.ndarray]:
        Hi = np.linalg.inv(plane(g))
        out = []
        for pn, gn, _ in elems:
            # px scale from the current polynomial: a uniformly shrunk undistorted plane (the free zoom)
            # must not shrink the residuals with it
            scale = _point_scale(poly, pn, w)
            x = np.c_[remove_angular(pn, poly), np.ones(len(pn))]
            d, _ = marking_distance(x, gn, Hi)
            out.append(d * scale)
        return out

    def keypoint_residuals(poly: np.ndarray, g: np.ndarray) -> np.ndarray:
        q = apply_homography(plane(g), kp_pitch_h[:, :2])
        return ((remove_angular(kp_n, poly) - q) * _point_scale(poly, kp_n, w)[:, None]).ravel()

    sol = _least_squares(lambda d: np.concatenate([keypoint_residuals(init_poly, d)]
                                                  + element_residuals(init_poly, d)), g0)
    H0, g0 = plane(sol.x), np.zeros(8)        # re-base: the joint fit then starts from a zero update again
    med = [float(np.median(r)) for r in element_residuals(init_poly, g0)]
    dropped = [f"{nm} ({m:+.1f} px)" for nm, m in zip(names, med) if abs(m) > outlier_px]
    if dropped:
        logger.info("lens solver: dropped %d marking(s) not where the pitch model puts them: %s",
                    len(dropped), ", ".join(dropped))
    keep = [abs(m) <= outlier_px for m in med]
    elems, names = [e for e, k in zip(elems, keep) if k], [nm for nm, k in zip(names, keep) if k]
    if not elems:
        raise ValueError("no detected marking consistent with the pitch model")

    r_corner = 0.5 * np.hypot(w, h) / w
    # no fold-back: the slope stays above min_slope x the center's, sampled out to past the corner (where the
    # inverse dist_poly is fitted); zero, with zero gradient, for a lens that does not come near folding
    r_mono = np.linspace(0.0, 1.05 * r_corner, 64)
    slope_min = config.min_slope * init_poly[-2]

    def residuals(p: np.ndarray) -> np.ndarray:
        poly, g = np.r_[p[:n], init_poly[-2:]], p[n:]
        out = element_residuals(poly, g)
        if keypoint_weight > 0:
            out.append(keypoint_weight * keypoint_residuals(poly, g))
        out.append(np.sqrt(config.regularization) * (poly - init_poly) * w)
        if config.min_slope > 0:
            out.append(config.monotonic_weight * w * np.maximum(slope_min - polyval(np.polyder(poly), r_mono), 0.0))
        return np.concatenate(out)

    x0 = np.r_[init_poly[:n], g0]
    sol = _least_squares(residuals, x0, method="trf", max_nfev=config.max_iterations * (len(x0) + 1),
                         xtol=config.tol, ftol=config.tol)
    undist_poly = np.r_[sol.x[:n], init_poly[-2:]]
    dist_poly = _fit_inverse_polynomial(undist_poly, r_max=1.05 * r_corner)

    res = residuals(sol.x)
    sizes = [len(pn) for pn, *_ in elems]
    per = np.split(res[:sum(sizes)], np.cumsum(sizes)[:-1])

    def kind_res(kind):
        return np.concatenate([r for r, e in zip(per, elems) if e[2] == kind] or [np.empty(0)])

    # out_scale enlarges the canvas at the same focal length, i.e. shows more of the periphery
    f_new, canvas_wh = float(canvas[0]), tuple(canvas[1])
    out_scale = (auto_out_scale(undist_poly, (w, h), f_new, canvas_wh) if str(out_scale) == "auto"
                 else float(out_scale))
    w_new, h_new = even(canvas_wh[0] * out_scale), even(canvas_wh[1] * out_scale)
    zoom = f_new / w
    K = np.array([[float(w), 0.0, c[0]], [0.0, float(w), c[1]], [0.0, 0.0, 1.0]])
    K_new = np.array([[f_new, 0.0, (w_new - 1) / 2.0], [0.0, f_new, (h_new - 1) / 2.0], [0.0, 0.0, 1.0]])
    n_lines = sum(e[2] == "line" for e in elems)
    n_arcs = sum(e[2] == "arc" for e in elems)
    meta = dict(type="angular", mode="pitch-anchored", poly_degree=n + 1, n_lines=n_lines, n_arcs=n_arcs,
                markings=names, dropped_markings=dropped, n_points=sum(sizes),
                line_rms_px=rms(kind_res("line")), arc_rms_px=rms(kind_res("arc")),
                marking_median_px={nm: float(np.median(r)) for nm, r in zip(names, per)},
                marking_rms_px={nm: rms(r) for nm, r in zip(names, per)},
                marking_points={nm: s for nm, s in zip(names, sizes)},
                keypoint_weight=keypoint_weight, zoom=zoom, out_scale=out_scale, loss=float(2 * sol.cost))
    folds = r_mono[1:][np.diff(polyval(undist_poly, r_mono)) <= 0]
    if folds.size and folds[0] <= r_corner:
        meta["fold_r"] = float(folds[0])
        logger.warning("lens solver: the fitted lens folds back at r = %.3f, inside the content (corner %.3f)",
                       folds[0], r_corner)
    return AngularLensModel(undist_poly=undist_poly, dist_poly=dist_poly, K=K, size=(w, h),
                            K_new=K_new, size_new=(w_new, h_new), meta=meta)


def _round_trip_px(lens: AngularLensModel, grid: np.ndarray) -> float:
    """Largest ``|distort(undistort(p)) - p|`` (content px) over ``grid``: how well ``dist_poly`` inverts
    ``undist_poly``."""
    return float(np.max(np.linalg.norm(lens.distort_points(lens.undistort_points(grid)) - grid, axis=1)))


def physical_gauge(lens: AngularLensModel, f: float, extra_degree: int = 2, inverse_degree: int = 12,
                   samples: int = 3000, r_valid: Optional[float] = None) -> Tuple[AngularLensModel, Dict[str, float]]:
    """``lens`` rewritten so that its angles are the physical ray angles, for a pose fitted with focal length ``f``
    (px) on its undistorted canvas. Returns the new lens and ``{scale, undistort_change_px, round_trip_old_px,
    round_trip_new_px}``.

    The anchored fit fixes the zoom as a gauge: its ``tan(undist_poly(r))`` is the physical ``tan(angle)`` divided
    by ``s = K_new f / f``. This moves ``s`` into the lens (``undist_poly(r) -> arctan(s tan(undist_poly(r)))``)
    and the canvas focal becomes ``f``; every canvas pixel keeps its ray. The new ``undist_poly`` is a refit,
    ``extra_degree`` higher, weighted by ``1 / cos^2`` (canvas px per radian); ``dist_poly`` is refitted as its
    inverse with degree ``inverse_degree`` up to the content corner.

    ``r_valid`` (sportvid addition, see ``valid_region``): when the lens folds back or reaches the angle limit inside
    the frame, both fits and the statistics stop at this radius (normalised like ``r_d``), where the mapping is still
    one-to-one; past it nothing is mapped."""
    s = float(lens.K_new[0, 0]) / float(f)
    w, h = lens.size
    r_corner = 0.5 * np.hypot(w, h) / float(lens.K[0, 0])
    r_fit = 1.05 * r_corner if r_valid is None else min(1.05 * r_corner, r_valid)
    r_d = np.linspace(0.0, r_fit, samples)
    theta_old = polyval(lens.undist_poly, r_d)
    # NOTE: only where the lens is one-to-one and below 90 deg; past 90 deg tan() flips sign and the
    # refit breaks (a lens reaching ~80 deg at the content corner crosses 90 deg within the 5 % margin)
    stop = np.flatnonzero(~np.isfinite(theta_old[1:]) | (np.diff(theta_old) <= 0)
                          | (theta_old[1:] >= np.pi / 2 - 1e-3))
    if stop.size:
        r_d, theta_old = r_d[:stop[0] + 1], theta_old[:stop[0] + 1]
        r_fit = float(r_d[-1])
    theta = np.arctan(s * np.tan(theta_old))
    ok = np.isfinite(theta)
    wt = 1.0 / np.cos(theta[ok]) ** 2
    deg = len(lens.undist_poly) - 1 + extra_degree
    A = r_d[ok, None] ** np.arange(deg, 0, -1)                          # no constant term: angle 0 at the center
    undist_poly = np.r_[np.linalg.lstsq(A * wt[:, None], theta[ok] * wt, rcond=None)[0], 0.0]
    r_i = np.linspace(0.0, min(r_corner, r_fit), samples)               # the inverse, up to the content corner
    th_i = polyval(undist_poly, r_i)
    keep = (th_i > 0) & (th_i < np.radians(89.5)) & _unfolded(th_i)     # no inverse past a fold
    dist_poly = np.r_[np.linalg.lstsq(th_i[keep, None] ** np.arange(inverse_degree, 0, -1), r_i[keep],
                                      rcond=None)[0], 0.0]
    K_new = lens.K_new.copy()
    K_new[0, 0] = K_new[1, 1] = float(f)
    new = AngularLensModel(undist_poly=undist_poly, dist_poly=dist_poly, K=lens.K.copy(), size=lens.size,
                           K_new=K_new, size_new=lens.size_new,
                           meta=dict(lens.meta, gauge="physical", gauge_scale=s, zoom=float(f) / w,
                                     poly_degree=deg, inverse_degree=inverse_degree))
    xs, ys = np.meshgrid(np.linspace(0, w - 1, 97), np.linspace(0, h - 1, 73))
    grid = np.c_[xs.ravel(), ys.ravel()]
    if r_valid is not None:
        grid = grid[np.linalg.norm(grid - lens.K[:2, 2], axis=1) / float(lens.K[0, 0]) <= r_valid]
    stats = dict(scale=s,
                 undistort_change_px=float(np.max(np.linalg.norm(new.undistort_points(grid)
                                                                 - lens.undistort_points(grid), axis=1))),
                 round_trip_old_px=_round_trip_px(lens, grid), round_trip_new_px=_round_trip_px(new, grid))
    new.meta["gauge_stats"] = stats
    return new, stats


def valid_region(lens: AngularLensModel, max_ray_deg: float = _AUTO_MAX_RAY_DEG) -> Dict:
    """Where ``lens`` maps image radius to ray angle one-to-one: up to the first radius at which the angle stops
    growing or reaches ``max_ray_deg``. With markings only in part of the image, the polynomial is extrapolated
    elsewhere and can fold back or run towards 90 deg inside the frame, typically in the corners; points past this
    radius can't be mapped.

    Returns ``radius`` (normalised like ``r_d``, by ``K``'s focal length), ``ray_angle`` there (rad), ``fraction`` of
    the content frame inside it and ``complete`` (the whole frame is valid), plus ``reason`` and ``kind`` (``fold`` /
    ``steep``) if not."""
    w, h = lens.size
    f = float(lens.K[0, 0])
    r_corner = 0.5 * np.hypot(w, h) / f
    r = np.linspace(0.0, r_corner, 4000)
    theta = polyval(lens.undist_poly, r)
    folds = ~np.isfinite(theta[1:]) | (np.diff(theta) <= 0)
    steep = theta[1:] >= np.radians(max_ray_deg)
    bad = np.flatnonzero(folds | steep)
    if not bad.size:
        return dict(radius=float(r_corner), ray_angle=float(theta[-1]), fraction=1.0, complete=True)
    k = bad[0]
    xs, ys = np.meshgrid(np.linspace(0, w - 1, 193), np.linspace(0, h - 1, 145))
    fraction = float(np.mean(np.hypot(xs - (w - 1) / 2.0, ys - (h - 1) / 2.0) / f <= r[k]))
    reason = (f"the ray angle stops growing at {100 * r[k] / r_corner:.0f} % of the corner radius" if folds[k]
              else f"rays reach {max_ray_deg:g} deg off-axis at {100 * r[k] / r_corner:.0f} % of the corner radius")
    return dict(radius=float(r[k]), ray_angle=float(theta[k]), fraction=fraction, complete=False, reason=reason,
                kind="fold" if folds[k] else "steep")


def _region_problem(region: Dict, min_fraction: float) -> Optional[str]:
    """Why a lens with this ``valid_region`` can't be used, if at all. A lens running to the angle limit inside the
    frame is implausible (the good fits on the test clips stay at 41-72 deg in the corners, the broken ones reach
    87-123 deg); one folding back in the outer corners is kept if it still maps ``min_fraction`` of the frame."""
    if region["complete"]:
        return None
    if region["kind"] == "steep":
        return region["reason"]
    if region["fraction"] < min_fraction:
        return f"it maps only {100 * region['fraction']:.0f} % of the frame: {region['reason']}"
    return None


def measure_content_rect(frames: List[np.ndarray], thr: float = 12.0) -> Tuple[int, int, int, int]:
    """Black-bar-free region ``(x0, y0, w, h)`` of the frame, from the column / row brightness of the frames."""
    m = np.mean([f.mean(axis=2) for f in frames], axis=0)
    cols, rows = np.flatnonzero(m.mean(axis=0) > thr), np.flatnonzero(m.mean(axis=1) > thr)
    fh, fw = m.shape
    if not cols.size or not rows.size:
        return 0, 0, fw, fh
    w, h = int(cols[-1] - cols[0] + 1), int(rows[-1] - rows[0] + 1)
    w, h = (fw, h) if fw - w <= 4 else (w, h)                # codec bleed: snap to the full size
    w, h = (w, fh) if fh - h <= 4 else (w, h)
    w, h = w + (w % 2), h + (h % 2)
    return (fw - w) // 2, (fh - h) // 2, w, h


DEFAULT_PARAMETERS = {
    "rounds": 5,                      # maximum rounds; stops earlier once the markings stop growing (<= 1 %)
    "first_round_outlier_px": 15.0,   # "painted elsewhere" threshold in round 1 (pinhole guide)
    "outlier_px": 3.0,                # the same from round 2 on, under the current lens
    "poly_degree": 6,
    "keypoint_weight": 1.0,
    "regularization": 1e-5,
    "min_slope": 0.1,                 # no fold-back: see AngularSolverConfig
    "monotonic_weight": 1.0,
    "search_px": 20.0,                # line search window either side of the projection
    "arc_search_m": 2.0,              # circle search window in pitch metres ...
    "arc_max_search_px": 150.0,       # ... clipped in px
    "contrast": 25.0,                 # grey levels a marking ridge must rise above its surroundings (trak). 12 recovered
                                      # faint lines on one re-encoded clip but hurt on three others
    "out_scale": "auto",
    "physical_max_px": 0.05,          # physical gauge: warn if the refit moves the undistortion by more ...
    "physical_fail_px": 1.0,          # ... and fail beyond this
    "min_valid_fraction": 0.95,       # share of the frame the lens must map (see valid_region)
    "collapse_ratio": 0.9,            # a round finding fewer than this share of the previous round's points ends the rounds
}


def _round_score(meta: Dict, max_rms_px: float) -> Tuple[int, float]:
    """How well a round's lens explains the painted markings, comparable across rounds (whose detected sets and
    outlier thresholds differ): the points on the markings it fits within ``max_rms_px`` RMS, then their
    point-weighted RMS (lower is better). A round that drops markings, or keeps them only loosely, scores lower."""
    good = [(meta["marking_points"][nm], r) for nm, r in meta["marking_rms_px"].items() if r <= max_rms_px]
    n = sum(p for p, _ in good)
    return n, -float(np.sqrt(sum(p * r * r for p, r in good) / n)) if n else float("-inf")


def self_calibrate(frames: List[np.ndarray], raw: np.ndarray, pitch_xy: np.ndarray, pitch: SoccerPitch,
                   rect: Tuple[int, int, int, int], params: Optional[Dict] = None, progress=None
                   ) -> Tuple[AngularLensModel, List[Dict]]:
    """A lens from the clicks ``raw`` (frame px) of the keypoints ``pitch_xy`` (pitch frame), the pitch model and
    the markings painted in ``frames`` (static camera, content region ``rect``). Returns the lens and one log entry
    per round.

    Round 1 starts from a pinhole (f = half the content width). Each round fits f + pose under the current lens,
    detects the markings around that projection and refits the lens; the next round searches around the new lens.
    A pinhole guide misses the curved outer lines and makes them look misplaced, so round 1 keeps markings up to
    ``first_round_outlier_px`` off and later rounds apply ``outlier_px`` under the current lens. Stops after
    ``rounds`` or once the detected marking points stop growing, and returns the round whose lens fits the most
    marking points within ``outlier_px`` (``_round_score``), not necessarily the last: a round can lose markings
    the previous one fitted."""
    params = {**DEFAULT_PARAMETERS, **(params or {})}
    off, content = np.array(rect[:2], dtype=np.float64), tuple(int(v) for v in rect[2:])
    lines, curves = straight_lines(pitch), pitch_curves(pitch)
    geometry = element_geometry(lines, curves)
    config = AngularSolverConfig(poly_degree=int(params["poly_degree"]), regularization=float(params["regularization"]),
                                 min_slope=float(params["min_slope"]),
                                 monotonic_weight=float(params["monotonic_weight"]))
    rounds = max(1, int(params["rounds"]))

    guide_lens = PinholeLens(content)
    canvas = (float(guide_lens.K_new[0, 0]), tuple(guide_lens.size_new))     # fixed across rounds: same zoom
    init = poly_from_lens(guide_lens, content, config.poly_degree)
    lens, prev_points, log, best = None, -1, [], None
    for k in range(rounds):
        guide = fit_raw(guide_lens, off, raw, pitch_xy)
        if guide is None:
            raise ValueError(f"no physical camera pose from the clicks under the round-{k + 1} lens")
        project = detection.guide_projector(CameraModel.from_params(guide_lens, guide["x"], off))
        detected = detection.detect_markings(frames, project, lines, curves, rect, params)
        if not detected:
            raise ValueError(f"no pitch markings found around the clicked keypoints (round {k + 1})")
        elements = [(name, pts - off, geometry[name]) for name, pts in detected.items()]
        n_points = sum(len(p) for p in detected.values())
        outlier = float(params["first_round_outlier_px"]) if k == 0 else float(params["outlier_px"])
        lens = fit_angular_lens_anchored(elements, content, init, (raw - off, pitch_xy), canvas, config,
                                         keypoint_weight=float(params["keypoint_weight"]), outlier_px=outlier,
                                         out_scale=params["out_scale"])
        m = lens.meta
        log.append(dict(round=k + 1, markings_detected=len(detected), points=n_points, lines=m["n_lines"],
                        arcs=m["n_arcs"], line_rms_px=m["line_rms_px"], arc_rms_px=m["arc_rms_px"],
                        dropped=m["dropped_markings"], guide_rmse_px=rms(guide["res"])))
        logger.info("lens solver: round %d/%d (%s guide): %d marking(s), %d point(s) | fitted %d line(s) + %d arc(s), "
                    "RMS %.2f px lines, %.2f px arcs%s", k + 1, rounds, "pinhole" if k == 0 else "previous round's",
                    len(detected), n_points, m["n_lines"], m["n_arcs"], m["line_rms_px"], m["arc_rms_px"],
                    f" | dropped {', '.join(m['dropped_markings'])}" if m["dropped_markings"] else "")
        if progress is not None:
            progress((k + 1) / rounds)
        score = _round_score(m, float(params["outlier_px"]))
        if best is None or score > best[0]:
            best = (score, lens, k)
        if k > 0 and n_points < prev_points * float(params["collapse_ratio"]):
            # sportvid addition: the previous round's lens finds far fewer markings than its own guide did (it bends
            # where there are no markings); no later round would recover them
            logger.info("lens solver: round %d found %d point(s) after %d, stopping", k + 1, n_points, prev_points)
            break
        if k > 0 and n_points <= prev_points * 1.01:
            break                                    # nothing new found with the better lens: converged
        prev_points = n_points
        guide_lens, init = lens, lens.undist_poly
    (n_good, _), lens, k_best = best
    for entry in log:
        entry["kept"] = entry["round"] == k_best + 1
    logger.info("lens solver: keeping round %d of %d: %d point(s) on markings it fits within %.1f px RMS",
                k_best + 1, len(log), n_good, float(params["outlier_px"]))
    lens.meta.update(content_rect=[int(v) for v in rect], rounds=len(log), best_round=k_best + 1)
    return lens, log


def calibrate(frames: List[np.ndarray], raw: np.ndarray, pitch_xy: np.ndarray, pitch: SoccerPitch,
              rect: Optional[Tuple[int, int, int, int]] = None, params: Optional[Dict] = None, progress=None
              ) -> Dict:
    """``self_calibrate`` + a pose fit under the fitted lens + ``physical_gauge``: the lens in physical units, with
    the rounds, the pose fit and the gauge statistics."""
    params = {**DEFAULT_PARAMETERS, **(params or {})}
    rect = tuple(rect) if rect is not None else measure_content_rect(frames)
    lens, log = self_calibrate(frames, raw, pitch_xy, pitch, rect, params, progress)
    min_fraction = float(params["min_valid_fraction"])

    def unusable(problem: str) -> ValueError:
        return ValueError(f"the fitted lens is not usable ({problem}); the markings found "
                          f"({', '.join(lens.meta['markings'])}) constrain it too weakly: click more keypoints spread "
                          f"over the image, near the edges in particular")

    region = valid_region(lens)
    problem = _region_problem(region, min_fraction)
    if problem:
        raise unusable(problem)
    off = np.array(rect[:2], dtype=np.float64)
    pose = fit_raw(lens, off, raw, pitch_xy)
    if pose is None:
        raise ValueError("no physical camera pose from the clicks under the fitted lens")
    lens, gauge = physical_gauge(lens, pose["f"], r_valid=None if region["complete"] else region["radius"])
    region = valid_region(lens)
    problem = _region_problem(region, min_fraction)
    if problem:
        raise unusable(f"in physical units {problem}")
    if gauge["undistort_change_px"] > float(params["physical_fail_px"]):
        raise unusable(f"converting it to physical units moves it by {gauge['undistort_change_px']:.3g} px")
    if not region["complete"]:
        logger.warning("lens solver: the lens maps %.1f %% of the frame (%s)", 100 * region["fraction"],
                       region["reason"])
    lens.meta["valid_region"] = region
    if gauge["undistort_change_px"] > float(params["physical_max_px"]):
        logger.warning("lens solver: the physical gauge moves the undistortion by %.3f px (> %.3f px)",
                       gauge["undistort_change_px"], float(params["physical_max_px"]))
    pose = fit_raw(lens, off, raw, pitch_xy, x0=pose["x"])
    if pose is None:
        raise ValueError("no physical camera pose from the clicks under the physical lens")
    # horizontal field of view along the principal row, from the physical lens
    edge = np.array([[0.0, (lens.size[1] - 1) / 2.0], [lens.size[0] - 1.0, (lens.size[1] - 1) / 2.0]])
    u = (lens.undistort_points(edge) - lens.K_new[:2, 2]) / lens.K_new[0, 0]
    hfov = float(np.degrees(np.arctan(-u[0, 0]) + np.arctan(u[1, 0])))
    return dict(
        lens=lens.to_dict(),
        rounds=log,
        pose=dict(f=pose["f"], rmse_px=rms(pose["res"]), max_px=float(np.max(pose["res"])),
                  camera_position=pose["C"].tolist(), horizontal_fov_deg=hfov),
        gauge=gauge,
        valid_region=region,
    )
