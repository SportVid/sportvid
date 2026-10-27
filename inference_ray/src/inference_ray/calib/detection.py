"""Detection of the pitch markings in video frames (trak ``fitting/detection.py``): white marking pixels
found perpendicular to a guide projection of the model."""
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import map_coordinates

from .camera import CameraModel


def guide_projector(camera: CameraModel):
    """Pitch metres -> (frame px, valid) through ``camera``, stopping 3 deg short of the lens's ray-angle cutoff and
    not limited to the content region: the guide that marking detection searches around."""
    return lambda xy: camera.project_ground(xy, return_valid=True, margin_deg=3, in_content=False)


def detect_markings(frames: List[np.ndarray], project, lines: Dict[str, np.ndarray],
                    curves: Dict[str, Tuple[np.ndarray, np.ndarray, float]], rect, cfg: Dict) -> Dict[str, np.ndarray]:
    """``detect_line_points`` for the straight lines (``search_px``) and the arcs (``arc_search_m``, a metric
    window: the near-field center circle can lie far off a guide fitted to distant keypoints). ``contrast``: grey levels
    a ridge must rise above its profile's median (trak: 25)."""
    sp = float(cfg.get("search_px", 20.0))
    contrast = float(cfg.get("contrast", 25.0))
    out = detect_line_points(frames, project, lines, rect, sp, contrast=contrast, nearest=True)
    out.update(detect_line_points(frames, project, {k: v[0] for k, v in curves.items()}, rect, sp, contrast=contrast,
                                  search_m=float(cfg.get("arc_search_m", 2.0)),
                                  max_search_px=float(cfg.get("arc_max_search_px", 150.0))))
    return out


def detect_line_points(frames: List[np.ndarray], project, lines: Dict[str, np.ndarray], rect,
                       search_px: float = 20.0, contrast: float = 25.0, search_m: Optional[float] = None,
                       max_search_px: float = 150.0, nearest: bool = False, min_span_px: float = 120.0
                       ) -> Dict[str, np.ndarray]:
    """Points on the white pitch markings, found perpendicular to the projected model polylines (``project``:
    pitch metres -> (frame px, valid)). Returns ``{name: frame-px array}`` per marking, pooled over the frames; a
    marking needs >= 12 points spanning ``min_span_px``.

    The search runs ``search_px`` either side of the projection. With ``search_m``, it runs that many pitch
    metres instead, converted to px at each point and clipped to ``[search_px, max_search_px]``: wide in the
    near field, where a guide pose fitted to far-away keypoints can be tens of px off, and narrow at the
    horizon, where neighbouring markings are only a few px apart.

    ``nearest`` (implied by ``search_m``): take the strong ridge nearest the projection instead of the brightest
    one. Where several painted lines run close together (pitches carrying more than one set of markings), the
    brightest is often a neighbour."""
    x0, y0, w, h = rect
    max_hw = search_px if search_m is None else max(search_px, max_search_px)
    offsets = np.arange(-max_hw, max_hw + 0.25, 0.5)
    pooled: Dict[str, List[np.ndarray]] = {}
    for img in frames:
        W = cv2.GaussianBlur(img.min(axis=2).astype(np.float32), (3, 3), 0)       # white: bright in all channels
        for name, pts in lines.items():
            px, ok = project(pts)
            ok &= ((px[:, 0] > x0 + search_px) & (px[:, 0] < x0 + w - search_px)
                   & (px[:, 1] > y0 + search_px) & (px[:, 1] < y0 + h - search_px))
            for run in np.split(np.arange(len(px)), np.flatnonzero(~ok)):
                run = run[ok[run]]
                if len(run) < 8:
                    continue
                p = px[run]
                hw = np.full(len(p), float(search_px))
                if search_m is not None:              # px per pitch metre across the marking, at each point
                    tm = np.gradient(pts[run], axis=0)
                    nm = np.c_[-tm[:, 1], tm[:, 0]] / (np.linalg.norm(tm, axis=1, keepdims=True) + 1e-12)
                    q, q_ok = project(pts[run] + nm)
                    pxpm = np.where(q_ok, np.linalg.norm(q - p, axis=1), 0.0)
                    hw = np.clip(search_m * pxpm, search_px, max_search_px)
                found = _ridge_points(W, p, hw, offsets, contrast, nearest or search_m is not None)
                if found is not None:
                    pooled.setdefault(name, []).append(found)
    return _pooled_markings(pooled, min_span_px)


def _ridge_points(W: np.ndarray, p: np.ndarray, hw: np.ndarray, offsets: np.ndarray, contrast: float,
                  nearest: bool) -> Optional[np.ndarray]:
    """Sub-pixel white-ridge points perpendicular to the image polyline ``p`` (one unbroken run), within ``hw`` px
    of it at each point; ``None`` if fewer than 8 survive the smoothness filter."""
    t = np.gradient(p, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    n = np.c_[-t[:, 1], t[:, 0]]
    c = p[:, None, :] + offsets[None, :, None] * n[:, None, :]
    prof = map_coordinates(W, [c[..., 1].ravel(), c[..., 0].ravel()], order=1, cval=0.0).reshape(len(p), -1)
    prof[np.abs(offsets)[None, :] > hw[:, None]] = np.nan
    k = np.nanargmax(prof, axis=1)
    if nearest:
        # the strong ridge *nearest* the projection, not the brightest one (see detect_line_points)
        base = np.nanmedian(prof, axis=1, keepdims=True)
        peak = np.zeros_like(prof, dtype=bool)
        peak[:, 1:-1] = ((prof[:, 1:-1] > prof[:, :-2]) & (prof[:, 1:-1] >= prof[:, 2:])
                         & (prof[:, 1:-1] - base > contrast))
        dist = np.where(peak, np.abs(offsets)[None, :], np.inf)
        k = np.where(np.isfinite(dist.min(axis=1)), dist.argmin(axis=1), k)
    i = np.arange(len(p))
    good = ((prof[i, k] - np.nanmedian(prof, axis=1) > contrast) & (np.abs(offsets[k]) < hw - 0.25)
            & (k > 0) & (k < len(offsets) - 1))
    if good.sum() < 8:
        return None
    y_0, y_1, y_2 = prof[i, np.clip(k - 1, 0, None)], prof[i, k], prof[i, np.clip(k + 1, None, len(offsets) - 1)]
    den = y_0 - 2 * y_1 + y_2
    s = offsets[k] + 0.5 * np.divide(y_0 - y_2, den, out=np.zeros_like(den), where=np.abs(den) > 1e-6) * 0.5
    # the offset varies smoothly along a line; occlusions / other markings do not
    idx, sg = np.flatnonzero(good), s[good]
    for _ in range(2):
        if len(idx) < 8:
            break
        coef = np.polyfit(idx, sg, 2)
        keep = np.abs(np.polyval(coef, idx) - sg) < 2.0
        idx, sg = idx[keep], sg[keep]
    return p[idx] + sg[:, None] * n[idx] if len(idx) >= 8 else None


def _pooled_markings(pooled: Dict[str, List[np.ndarray]], min_span_px: float = 120.0) -> Dict[str, np.ndarray]:
    """Pool each marking's points over frames and runs; keep it with >= 12 points spanning >= ``min_span_px``."""
    out = {}
    for name, pts in pooled.items():
        q = np.concatenate(pts)
        if len(q) >= 12 and np.ptp(q, axis=0).max() >= min_span_px:
            out[name] = q
    return out
