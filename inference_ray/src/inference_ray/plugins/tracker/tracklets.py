"""The ``BboxesData`` tracklet format shared by object_tracker (writer), osnet_reid and team_clustering (readers).

``bboxes``: JSON ``{frame_time_ms: [row, ...]}``, one row per box, coordinates normalised by the frame size:

    [entity_id, team_id, game_section, x_center, y_bottom, x, y, w, h, score]

``x, y`` is the top-left corner, ``x_center, y_bottom`` the foot point. ``team_id`` follows ``TeamId``.

``meta_data``: JSON with ``team_ids``, ``player_ids`` / ``ref_ids`` / ``ball_ids`` (the entity scheme of
``data.compute_bboxes_meta``) and ``video: {fps, h, w}``, the decoding rate and the frame size the boxes are
normalised by.
"""

from enum import IntEnum
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import numpy as np


class TeamId(IntEnum):
    UNKNOWN = (-1, "Unknown")
    BALL = (0, "Ball")
    BYSTANDER = (1, "Bystander")
    REFEREE = (2, "Referee")
    TEAM_LEFT = (3, "Team A")
    TEAM_RIGHT = (4, "Team B")

    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj


# NOTE: every team object_tracker offers, present or not, so the editor can move players to a team before
# team_clustering ran; edits rebuild them from the boxes (backend views/bounding_boxes.py).
DEFAULT_TEAM_META = {
    TeamId.UNKNOWN: {"name": "Unknown"},
    TeamId.BYSTANDER: {"name": "Bystander"},
    TeamId.BALL: {"name": "Ball"},
    TeamId.REFEREE: {"name": "Referee"},
    TeamId.TEAM_LEFT: {"name": "Team A"},
    TeamId.TEAM_RIGHT: {"name": "Team B"},
}


def frame_time_ms(frame_id: int, fps: float) -> int:
    """ Key of a decoded frame in ``bboxes`` (frames are decoded at ``fps``). """
    return round((frame_id / fps) * 1000.)


def tracklet_row(entity_id: int, team_id: int, tlwh, frame_w: int, frame_h: int, score: float) -> List:
    """ One ``bboxes`` row from a tlwh box in image pixels. """
    x, y, w, h = (float(v) for v in tlwh)
    x_n, y_n, w_n, h_n = x / frame_w, y / frame_h, w / frame_w, h / frame_h
    return [
        int(entity_id), int(team_id), 0,
        float(x_n + w_n / 2), float(y_n + h_n),
        float(x_n), float(y_n), float(w_n), float(h_n),
        float(score),
    ]


def center_to_tlwh(xywh) -> np.ndarray:
    """ Detector ``xywh`` (box centre, width, height) -> tlwh. """
    cx, cy, w, h = (float(v) for v in xywh)
    return np.array([cx - w / 2, cy - h / 2, w, h], dtype=np.float64)


def video_meta(meta_data: Mapping[str, Any], default_fps: float = 30,
               default_size: Tuple[int, int] = (1080, 1920)) -> Tuple[float, int, int]:
    """ (fps, frame_h, frame_w) from a tracklets ``meta_data`` dict.

    object_tracker writes ``video.h`` / ``video.w``. ``detector_h`` / ``detector_w`` are read as a fallback:
    the readers used to look for them, which object_tracker never wrote, so they always fell back to 1080p.
    """
    video = (meta_data or {}).get("video", {}) or {}
    h = video.get("h", video.get("detector_h", default_size[0]))
    w = video.get("w", video.get("detector_w", default_size[1]))
    return video.get("fps", default_fps), int(h), int(w)


def denormalize_rows(rows: Iterable, frame_w: int, frame_h: int) -> np.ndarray:
    """ ``bboxes`` rows as an (N, 10) float array with the tlwh columns (5:9) in image pixels. """
    arr = np.array(list(rows), dtype=np.float64).reshape(-1, 10)
    arr[:, [5, 7]] *= frame_w
    arr[:, [6, 8]] *= frame_h
    return arr


def entity_class_ids(output_class_mapping: Mapping[Any, Mapping[str, Any]], entity_type: str) -> set:
    """ Detector class ids whose ``output_class_mapping`` entry has this ``entity_type`` (keys may be str). """
    return {int(cls_id) for cls_id, entry in (output_class_mapping or {}).items()
            if (entry or {}).get("entity_type") == entity_type}


def split_detections(detections: List[List[Dict[str, Any]]], cls_ids: set):
    """ Per-frame detections -> (others, selected): ``selected`` holds the detections of ``cls_ids``. """
    others, selected = [], []
    for frame_dets in detections:
        others.append([d for d in frame_dets if int(d['cls_id']) not in cls_ids])
        selected.append([d for d in frame_dets if int(d['cls_id']) in cls_ids])
    return others, selected
