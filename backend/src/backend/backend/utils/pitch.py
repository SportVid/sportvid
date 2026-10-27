"""Metric pitch models for the calibration templates.

The frontend templates (``frontend/src/stores/calibration_asset.js``) give every keypoint a position
relative to the playing area, drawn for one reference size (105 x 68 m for soccer). Markings of fixed
size (penalty and goal areas, penalty mark, circles) only sit at those relative positions on a pitch of
exactly that size. Here every keypoint is computed in metres from its name, for the actual pitch size.

Frame: metres, origin at the template's relative (0, 0) corner, x along the length (goal line to goal line),
y along the width, "top" at y = width; i.e. relative template coordinates times (length, width).

Sports played on standardised courts (handball 40 x 20 m, basketball 28 x 15 m) have no model: there
the relative template position times the court size is already metric.
"""
import logging
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# IFAB Laws of the Game, law 1 (the same constants as trak's SoccerPitch)
GOAL_LINE_TO_PENALTY_MARK = 11.0
PENALTY_AREA_LENGTH = 16.5
PENALTY_AREA_WIDTH = 40.32
GOAL_AREA_LENGTH = 5.5
GOAL_AREA_WIDTH = 18.32
CENTER_CIRCLE_RADIUS = 9.15
GOAL_WIDTH = 7.32                  # between the inner edges of the posts (trak's SoccerPitch.GOAL_LENGTH)

# a template point whose relative position is farther than this from the model point (both at the
# reference size) is not that keypoint
MATCH_TOLERANCE_REL = 0.02

_SPORT_ALIASES = {
    "soccer": "soccer", "football": "soccer", "fußball": "soccer", "fussball": "soccer",
    "handball": "handball",
    "basketball": "basketball",
    "climbing": "climbing", "klettern": "climbing",
}


def normalize_sport(*values: Optional[str]) -> Optional[str]:
    """Sport key of the first recognised value. Calibration assets store the frontend's display title
    (e.g. "Soccer"), videos a free-text sport."""
    for value in values:
        key = _SPORT_ALIASES.get((value or "").strip().lower())
        if key:
            return key
    return None


def soccer_keypoints(length: float, width: float) -> Dict[str, Tuple[float, float]]:
    """The soccer template's markers, in metres."""
    L, W = float(length), float(width)
    cy = W / 2.0
    pa_y, ga_y = PENALTY_AREA_WIDTH / 2.0, GOAL_AREA_WIDTH / 2.0
    # the penalty arc (radius 9.15 m around the penalty mark) meets the penalty-area line at cy +- arc_y
    arc_y = float(np.sqrt(CENTER_CIRCLE_RADIUS ** 2 - (PENALTY_AREA_LENGTH - GOAL_LINE_TO_PENALTY_MARK) ** 2))
    points = {
        "Corner-top-left": (0.0, W),
        "Corner-top-right": (L, W),
        "Corner-bottom-left": (0.0, 0.0),
        "Corner-bottom-right": (L, 0.0),
        "Midline-top": (L / 2.0, W),
        "Midline-bottom": (L / 2.0, 0.0),
        "Kick-off": (L / 2.0, cy),
        "Kick-off-circle-top": (L / 2.0, cy + CENTER_CIRCLE_RADIUS),
        "Kick-off-circle-bottom": (L / 2.0, cy - CENTER_CIRCLE_RADIUS),
    }
    for side, goal_x, inward in (("left", 0.0, 1.0), ("right", L, -1.0)):
        pa_x = goal_x + inward * PENALTY_AREA_LENGTH
        ga_x = goal_x + inward * GOAL_AREA_LENGTH
        points.update({
            f"Penalty-{side}": (goal_x + inward * GOAL_LINE_TO_PENALTY_MARK, cy),
            f"Penalty-area-{side}-corner-top": (pa_x, cy + pa_y),
            f"Penalty-area-{side}-corner-bottom": (pa_x, cy - pa_y),
            f"Goal-line-{side}-penalty-area-top": (goal_x, cy + pa_y),
            f"Goal-line-{side}-penalty-area-bottom": (goal_x, cy - pa_y),
            f"Penalty-arc-{side}-top": (pa_x, cy + arc_y),
            f"Penalty-arc-{side}-bottom": (pa_x, cy - arc_y),
            f"Goal-area-{side}-corner-top": (ga_x, cy + ga_y),
            f"Goal-area-{side}-corner-bottom": (ga_x, cy - ga_y),
            f"Goal-line-{side}-goal-area-top": (goal_x, cy + ga_y),
            f"Goal-line-{side}-goal-area-bottom": (goal_x, cy - ga_y),
            # where the posts stand on the goal line (their inner edges, as in trak's pitch model)
            f"Goal-post-{side}-top": (goal_x, cy + GOAL_WIDTH / 2.0),
            f"Goal-post-{side}-bottom": (goal_x, cy - GOAL_WIDTH / 2.0),
        })
    return points


def soccer_fits(length: float, width: float) -> bool:
    """The fixed-size markings fit on the pitch without overlapping (penalty areas inside the width, the
    penalty arcs short of the centre circle). Smaller youth pitches use other markings."""
    reach = GOAL_LINE_TO_PENALTY_MARK + CENTER_CIRCLE_RADIUS        # penalty arc's tip from the goal line
    return width > PENALTY_AREA_WIDTH and length / 2.0 > reach + CENTER_CIRCLE_RADIUS


# sport -> (keypoints in metres for a (length, width), whether that size can carry the markings, reference size
# the frontend templates are drawn for)
PITCH_MODELS: Dict[str, Tuple[Callable, Callable, Tuple[float, float]]] = {
    "soccer": (soccer_keypoints, soccer_fits, (105.0, 68.0)),
}


def resolve_keypoint(
    sport: Optional[str], name: str, template_rel: Sequence[float], length: float, width: float
) -> Optional[Tuple[str, Tuple[float, float]]]:
    """``(keypoint, (x, y) in metres)`` of a template marker on a ``length`` x ``width`` pitch, or None if the
    sport has no model, the pitch can't carry its markings, or no keypoint matches.

    The name decides; the template position must agree with it at the reference size. A name that doesn't
    (unknown, or a template typo) is matched by its template position alone.
    """
    if sport not in PITCH_MODELS:
        return None
    keypoints, fits, (ref_length, ref_width) = PITCH_MODELS[sport]
    if not fits(length, width):
        return None
    reference = {k: np.asarray(v) / [ref_length, ref_width] for k, v in keypoints(ref_length, ref_width).items()}
    rel = np.asarray(template_rel, dtype=np.float64)[:2]

    def distance(key: str) -> float:
        return float(np.linalg.norm(reference[key] - rel))

    by_name = {k.lower(): k for k in reference}.get((name or "").strip().lower())
    if by_name is not None and distance(by_name) <= MATCH_TOLERANCE_REL:
        key = by_name
    else:
        key = min(reference, key=distance)
        if distance(key) > MATCH_TOLERANCE_REL:
            return None
        logger.warning(f"Calibration keypoint '{name}' at {rel.tolist()} matched to '{key}' by its position")
    return key, keypoints(length, width)[key]


def object_pitch_positions(
    sport: Optional[str], object_type: Optional[str], name: str, template_rel: Sequence[Dict], length: float,
    width: float,
) -> Tuple[Optional[str], List[Tuple[float, float]]]:
    """Where a calibration object (``PointCorrespondence``) lies on the pitch, in relative pitch coordinates: a marker
    the sport's model knows by its metric position on this pitch (``resolve_keypoint``), anything else at its template
    position. Returns the model keypoint's name (None if not resolved) and one point per template point."""
    points = [(float(p["x"]), float(p["y"])) for p in template_rel if p.get("x") is not None and p.get("y") is not None]
    if object_type == "marker" and points:
        keypoint = resolve_keypoint(sport, name, points[0], length, width)
        if keypoint is not None:
            return keypoint[0], [(keypoint[1][0] / length, keypoint[1][1] / width)]
    return None, points


def _segment(a, b, step: float) -> np.ndarray:
    n = max(2, int(np.ceil(np.hypot(b[0] - a[0], b[1] - a[1]) / step)) + 1)
    return np.linspace(a, b, n)


def _arc(centre, radius: float, from_angle: float, to_angle: float, step: float) -> np.ndarray:
    n = max(2, int(np.ceil(radius * abs(to_angle - from_angle) / step)) + 1)
    t = np.linspace(from_angle, to_angle, n)
    return np.stack([centre[0] + radius * np.cos(t), centre[1] + radius * np.sin(t)], axis=1)


def soccer_markings(length: float, width: float, step: float = 0.5) -> Dict[str, np.ndarray]:
    """The painted lines and circles of a soccer pitch as polylines in metres, sampled every ``step`` m (dense
    enough to curve once projected through a distorting lens)."""
    L, W = float(length), float(width)
    cy = W / 2.0
    pa_y, ga_y = PENALTY_AREA_WIDTH / 2.0, GOAL_AREA_WIDTH / 2.0
    arc_half = float(np.arccos((PENALTY_AREA_LENGTH - GOAL_LINE_TO_PENALTY_MARK) / CENTER_CIRCLE_RADIUS))
    out = {
        "Touchline bottom": _segment((0.0, 0.0), (L, 0.0), step),
        "Touchline top": _segment((0.0, W), (L, W), step),
        "Goal line left": _segment((0.0, 0.0), (0.0, W), step),
        "Goal line right": _segment((L, 0.0), (L, W), step),
        "Halfway line": _segment((L / 2.0, 0.0), (L / 2.0, W), step),
        "Centre circle": _arc((L / 2.0, cy), CENTER_CIRCLE_RADIUS, 0.0, 2 * np.pi, step / 2.0),
    }
    for side, goal_x, inward in (("left", 0.0, 1.0), ("right", L, -1.0)):
        pa_x = goal_x + inward * PENALTY_AREA_LENGTH
        ga_x = goal_x + inward * GOAL_AREA_LENGTH
        mark_x = goal_x + inward * GOAL_LINE_TO_PENALTY_MARK
        facing = 0.0 if inward > 0 else np.pi                     # the arc lies on the pitch side of the area
        out.update({
            f"Penalty area {side} top": _segment((goal_x, cy + pa_y), (pa_x, cy + pa_y), step),
            f"Penalty area {side} bottom": _segment((goal_x, cy - pa_y), (pa_x, cy - pa_y), step),
            f"Penalty area {side} front": _segment((pa_x, cy - pa_y), (pa_x, cy + pa_y), step),
            f"Goal area {side} top": _segment((goal_x, cy + ga_y), (ga_x, cy + ga_y), step),
            f"Goal area {side} bottom": _segment((goal_x, cy - ga_y), (ga_x, cy - ga_y), step),
            f"Goal area {side} front": _segment((ga_x, cy - ga_y), (ga_x, cy + ga_y), step),
            f"Penalty arc {side}": _arc((mark_x, cy), CENTER_CIRCLE_RADIUS, facing - arc_half, facing + arc_half,
                                        step / 2.0),
        })
    return out


def pitch_markings(sport: Optional[str], length: float, width: float, step: float = 0.5) -> Dict[str, np.ndarray]:
    """Polylines of the markings to draw over the video, in relative pitch coordinates (metres / (length, width)):
    every marking of the sport's model if it has one and the pitch can carry it, else the boundary and the
    halfway line, which are at the same relative position on any pitch."""
    if sport in PITCH_MODELS and PITCH_MODELS[sport][1](length, width):
        markings = {"soccer": soccer_markings}[sport](length, width, step)
    else:
        L, W = float(length), float(width)
        markings = {
            "Boundary": np.concatenate([_segment(a, b, step) for a, b in
                                        (((0, 0), (L, 0)), ((L, 0), (L, W)), ((L, W), (0, W)), ((0, W), (0, 0)))]),
            "Halfway line": _segment((L / 2.0, 0.0), (L / 2.0, W), step),
        }
    return {name: pts / [length, width] for name, pts in markings.items()}
