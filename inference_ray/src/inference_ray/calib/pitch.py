"""Soccer pitch model and its ground markings.
Metres, origin at the center mark, x along the pitch (goal to goal), y down in the schematic. 
The goal frames are left out: the homography solver only uses the ground plane.
"""
from typing import Dict, Tuple

import numpy as np


class SoccerPitch:
    """Static class variables that are specified by the rules of the game (the same as sportvid's
    ``backend/utils/pitch.py``)."""
    GOAL_LINE_TO_PENALTY_MARK = 11.0
    PENALTY_AREA_WIDTH = 40.32
    PENALTY_AREA_LENGTH = 16.5
    GOAL_AREA_WIDTH = 18.32
    GOAL_AREA_LENGTH = 5.5
    CENTER_CIRCLE_RADIUS = 9.15

    # marking -> (start keypoint, end keypoint); the arcs run between their intersections with the 16 m line
    LINES = {
        "Big rect. left bottom": ("L_PENALTY_AREA_BL_CORNER", "L_PENALTY_AREA_BR_CORNER"),
        "Big rect. left top": ("L_PENALTY_AREA_TL_CORNER", "L_PENALTY_AREA_TR_CORNER"),
        "Big rect. left main": ("L_PENALTY_AREA_TR_CORNER", "L_PENALTY_AREA_BR_CORNER"),
        "Big rect. right bottom": ("R_PENALTY_AREA_BL_CORNER", "R_PENALTY_AREA_BR_CORNER"),
        "Big rect. right top": ("R_PENALTY_AREA_TL_CORNER", "R_PENALTY_AREA_TR_CORNER"),
        "Big rect. right main": ("R_PENALTY_AREA_TL_CORNER", "R_PENALTY_AREA_BL_CORNER"),
        "Small rect. left bottom": ("L_GOAL_AREA_BL_CORNER", "L_GOAL_AREA_BR_CORNER"),
        "Small rect. left top": ("L_GOAL_AREA_TL_CORNER", "L_GOAL_AREA_TR_CORNER"),
        "Small rect. left main": ("L_GOAL_AREA_TR_CORNER", "L_GOAL_AREA_BR_CORNER"),
        "Small rect. right bottom": ("R_GOAL_AREA_BL_CORNER", "R_GOAL_AREA_BR_CORNER"),
        "Small rect. right top": ("R_GOAL_AREA_TL_CORNER", "R_GOAL_AREA_TR_CORNER"),
        "Small rect. right main": ("R_GOAL_AREA_TL_CORNER", "R_GOAL_AREA_BL_CORNER"),
        "Side line top": ("TL_PITCH_CORNER", "TR_PITCH_CORNER"),
        "Side line bottom": ("BL_PITCH_CORNER", "BR_PITCH_CORNER"),
        "Side line left": ("TL_PITCH_CORNER", "BL_PITCH_CORNER"),
        "Side line right": ("TR_PITCH_CORNER", "BR_PITCH_CORNER"),
        "Middle line": ("T_TOUCH_AND_HALFWAY_LINES_INTERSECTION", "B_TOUCH_AND_HALFWAY_LINES_INTERSECTION"),
        "Circle right": ("TR_16M_LINE_AND_PENALTY_ARC_INTERSECTION", "BR_16M_LINE_AND_PENALTY_ARC_INTERSECTION"),
        "Circle left": ("TL_16M_LINE_AND_PENALTY_ARC_INTERSECTION", "BL_16M_LINE_AND_PENALTY_ARC_INTERSECTION"),
    }

    def __init__(self, pitch_length=105., pitch_width=68.):
        self.PITCH_LENGTH = pitch_length
        self.PITCH_WIDTH = pitch_width

        hl, hw = pitch_length / 2.0, pitch_width / 2.0
        pa_l, pa_w = SoccerPitch.PENALTY_AREA_LENGTH, SoccerPitch.PENALTY_AREA_WIDTH / 2.0
        ga_l, ga_w = SoccerPitch.GOAL_AREA_LENGTH, SoccerPitch.GOAL_AREA_WIDTH / 2.0
        r, pm = SoccerPitch.CENTER_CIRCLE_RADIUS, SoccerPitch.GOAL_LINE_TO_PENALTY_MARK
        dx = pa_l - pm
        arc_y = np.sqrt(r * r - dx * dx)        # penalty arc meets the 16 m line at y = +-arc_y

        points = {
            "CENTER_MARK": (0, 0, 0),
            "L_PENALTY_MARK": (-hl + pm, 0, 0),
            "R_PENALTY_MARK": (hl - pm, 0, 0),
            "TL_PITCH_CORNER": (-hl, -hw, 0),
            "BL_PITCH_CORNER": (-hl, hw, 0),
            "TR_PITCH_CORNER": (hl, -hw, 0),
            "BR_PITCH_CORNER": (hl, hw, 0),
            "L_PENALTY_AREA_TL_CORNER": (-hl, -pa_w, 0),
            "L_PENALTY_AREA_TR_CORNER": (-hl + pa_l, -pa_w, 0),
            "L_PENALTY_AREA_BL_CORNER": (-hl, pa_w, 0),
            "L_PENALTY_AREA_BR_CORNER": (-hl + pa_l, pa_w, 0),
            "R_PENALTY_AREA_TL_CORNER": (hl - pa_l, -pa_w, 0),
            "R_PENALTY_AREA_TR_CORNER": (hl, -pa_w, 0),
            "R_PENALTY_AREA_BL_CORNER": (hl - pa_l, pa_w, 0),
            "R_PENALTY_AREA_BR_CORNER": (hl, pa_w, 0),
            "L_GOAL_AREA_TL_CORNER": (-hl, -ga_w, 0),
            "L_GOAL_AREA_TR_CORNER": (-hl + ga_l, -ga_w, 0),
            "L_GOAL_AREA_BL_CORNER": (-hl, ga_w, 0),
            "L_GOAL_AREA_BR_CORNER": (-hl + ga_l, ga_w, 0),
            "R_GOAL_AREA_TL_CORNER": (hl - ga_l, -ga_w, 0),
            "R_GOAL_AREA_TR_CORNER": (hl, -ga_w, 0),
            "R_GOAL_AREA_BL_CORNER": (hl - ga_l, ga_w, 0),
            "R_GOAL_AREA_BR_CORNER": (hl, ga_w, 0),
            "T_TOUCH_AND_HALFWAY_LINES_INTERSECTION": (0, -hw, 0),
            "B_TOUCH_AND_HALFWAY_LINES_INTERSECTION": (0, hw, 0),
            "TL_16M_LINE_AND_PENALTY_ARC_INTERSECTION": (-hl + pa_l, -arc_y, 0),
            "BL_16M_LINE_AND_PENALTY_ARC_INTERSECTION": (-hl + pa_l, arc_y, 0),
            "TR_16M_LINE_AND_PENALTY_ARC_INTERSECTION": (hl - pa_l, -arc_y, 0),
            "BR_16M_LINE_AND_PENALTY_ARC_INTERSECTION": (hl - pa_l, arc_y, 0),
        }
        self.point_dict = {k: np.array(v, dtype="float") for k, v in points.items()}
        self.line_extremities = {k: (self.point_dict[a], self.point_dict[b]) for k, (a, b) in self.LINES.items()}

    def _circle(self, center, from_angle, to_angle, dist, close: bool):
        """Points every ``dist`` m along a circle of the center-circle radius; ``close``: append the end angle."""
        r = SoccerPitch.CENTER_CIRCLE_RADIUS
        nb_pts = int(r * (to_angle - from_angle) / dist)
        dangle = dist / r
        angles = [from_angle] + [from_angle + i * dangle for i in range(1, nb_pts + (1 if close else 0))]
        if close:
            angles.append(to_angle)
        return [np.array((center[0] + np.cos(a) * r, center[1] + np.sin(a) * r, 0.)) for a in angles]

    def sample_field_points(self, dist=0.1, dist_circles=0.2):
        """``{marking: [points]}``, each marking sampled every ``dist`` m (circles: ``dist_circles``)."""
        polylines = {"Circle central": self._circle(self.point_dict["CENTER_MARK"], 0., 2 * np.pi, dist_circles,
                                                    close=False)}
        for key, (start, end) in self.line_extremities.items():
            if key in ("Circle left", "Circle right"):
                side = key[7]                                               # "l" / "r"
                center = self.point_dict["L_PENALTY_MARK" if side == "l" else "R_PENALTY_MARK"]
                a_start = np.arctan2(start[1] - center[1], start[0] - center[0]) + 2 * np.pi
                a_end = np.arctan2(end[1] - center[1], end[0] - center[0]) + 2 * np.pi
                from_angle, to_angle = (a_start, a_end) if side == "l" else (a_end, a_start)
                if to_angle < from_angle:
                    to_angle += 2 * np.pi
                polylines[key] = self._circle(center, from_angle, to_angle, dist_circles, close=True)
            else:
                polyline = [start]
                nb_pts = int(np.sqrt(np.sum(np.square(start - end))) / dist - 1)
                v = end - start
                v /= np.linalg.norm(v)
                prev_pt = start
                for _ in range(nb_pts):
                    prev_pt = prev_pt + dist * v
                    polyline.append(prev_pt)
                polyline.append(end)
                polylines[key] = polyline
        return polylines


def corner_to_pitch(xy, length: float, width: float) -> np.ndarray:
    """sportvid / Kinexon metres (origin at the lower-left corner, y up) -> the pitch frame."""
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    return np.stack([xy[:, 0] - length / 2.0, width / 2.0 - xy[:, 1]], axis=1)


def pitch_polylines(pitch: SoccerPitch, dist: float = 0.3, dist_circles: float = 0.2) -> Dict[str, np.ndarray]:
    """Ground-plane pitch elements as ``{name: (N, 2) array}`` in metres."""
    return {name: np.asarray(pts, dtype=np.float64)[:, :2]
            for name, pts in pitch.sample_field_points(dist=dist, dist_circles=dist_circles).items()}


def marking_distance(x: np.ndarray, geometry: np.ndarray, Hi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Signed distance of homogeneous image points ``x`` (N, 3) from a pitch-plane marking, and the unit image
    normal at each point. ``geometry``: a line ``(3,)`` or a circle conic ``(3, 3)`` in pitch coordinates (see
    ``element_geometry``); ``Hi``: image -> pitch homography. Circles use the Sampson (first-order) distance."""
    if np.ndim(geometry) == 1:
        l = Hi.T @ geometry
        nrm = np.hypot(l[0], l[1])
        return (x @ l) / nrm, np.broadcast_to(l[:2] / nrm, (len(x), 2))
    Cx = x @ (Hi.T @ geometry @ Hi)
    den = 2.0 * np.hypot(Cx[:, 0], Cx[:, 1]) + 1e-12          # |gradient of x^T C x| (+ eps)
    return np.sum(Cx * x, axis=1) / den, 2.0 * Cx[:, :2] / den[:, None]


def straight_lines(pitch: SoccerPitch, dist: float = 0.25) -> Dict[str, np.ndarray]:
    """The straight ground lines of the pitch model, sampled every ``dist`` metres."""
    out = {}
    for name, pts in pitch_polylines(pitch, dist=dist).items():
        if len(pts) < 3 or np.ptp(pts, axis=0).max() < 1.0:
            continue
        d = pts[-1] - pts[0]
        normal = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        if np.abs((pts - pts[0]) @ normal).max() < 1e-3:
            out[name] = pts
    return out


def pitch_curves(pitch: SoccerPitch, dist: float = 0.25) -> Dict[str, Tuple[np.ndarray, np.ndarray, float]]:
    """The circular ground markings (center circle, penalty arcs): ``{name: (arc samples, center, radius)}``."""
    centers = {"Circle central": np.zeros(2), "Circle left": pitch.point_dict["L_PENALTY_MARK"][:2],
               "Circle right": pitch.point_dict["R_PENALTY_MARK"][:2]}
    polys = pitch_polylines(pitch, dist=dist, dist_circles=dist)
    return {name: (polys[name], np.asarray(c, dtype=np.float64), SoccerPitch.CENTER_CIRCLE_RADIUS)
            for name, c in centers.items() if name in polys}


def element_geometry(lines: Dict[str, np.ndarray], curves: Dict[str, Tuple[np.ndarray, np.ndarray, float]]
                     ) -> Dict[str, np.ndarray]:
    """Homogeneous pitch-plane geometry per marking: a line ``(3,)`` or a circle as a conic ``(3, 3)``."""
    out = {name: np.cross(np.r_[pts[0], 1.0], np.r_[pts[-1], 1.0]) for name, pts in lines.items()}
    for name, (_, (cx, cy), r) in curves.items():
        out[name] = np.array([[1.0, 0.0, -cx], [0.0, 1.0, -cy], [-cx, -cy, cx * cx + cy * cy - r * r]])
    return out
