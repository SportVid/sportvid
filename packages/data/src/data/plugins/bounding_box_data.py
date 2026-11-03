import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass, field

import numpy.typing as npt
import numpy as np

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2

# TODO: insightface_detector & ocr both use BBoxData and the previous BBoxesData types!
@dataclass(kw_only=True)
class BboxData(Data):
    image_id: int = None
    ref_id: str = None
    team_id: str = None
    time: float = None
    x: int = None
    y: int = None
    w: int = None
    h: int = None
    top_x: int = None
    top_y: int = None
    det_score: float = 1.0

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "top_x": self.top_x,
            "top_y": self.top_y,
            "det_score": self.det_score,
            "time": self.time,
            "ref_id": self.ref_id,
            "team_id": self.team_id,
            "image_id": self.image_id,
        }


def compute_bboxes_meta(bboxes: Dict) -> Dict:
    """
    Entity meta data of a ``BboxesData.bboxes`` dict ({frame_time: [[entity_id, team_id, ...], ...]}).
    - Entity scheme: team_id 0=ball, 1=inactive, 2=refs, ≥3=teams.
    - Each kind has its own id namespace stored under player_ids / ref_ids / ball_ids.
    - team_id=1 entries (inactive) stay inside player_ids since they were tracked as person-detections.
    Shared by the bbox edit views (backend) and object_tracker (inference_ray).
    """
    BALL_TID, REF_TID = 0, 2
    # collect (entity_id, team_id) per kind
    players_by_team = {}  # team_id -> set(entity_id) for teams (incl. inactive=0)
    ball_ids = set()
    ref_ids = set()
    for frame_bboxes in bboxes.values():
        for bbox in frame_bboxes:
            if len(bbox) <= 1:
                continue
            pid, tid = bbox[0], bbox[1]
            if tid == BALL_TID:
                ball_ids.add(pid)
            elif tid == REF_TID:
                ref_ids.add(pid)
            else:
                players_by_team.setdefault(tid, set()).add(pid)

    team_id_meta = {}
    if ball_ids: team_id_meta[BALL_TID] = {"id": BALL_TID, "name": "Ball"}
    if ref_ids: team_id_meta[REF_TID] = {"id": REF_TID, "name": "Referees"}
    # active teams (team_id ≥ 3) sorted by player count desc, then by id for stability
    active_teams = sorted(
        ((tid, pids) for tid, pids in players_by_team.items() if tid >= 3),
        key=lambda x: (-len(x[1]), x[0]),
    )
    for letter_idx, (tid, _) in enumerate(active_teams):
        name = f"Team {chr(ord('A') + letter_idx)}" if letter_idx < 26 else f"Team {tid}"
        team_id_meta[tid] = {"id": tid, "name": name}

    player_id_meta = {}
    for tid, pids in players_by_team.items():
        for pid in sorted(pids):
            player_id_meta[pid] = {"id": pid, "name": str(pid), "number": pid, "team_id": tid}
    ref_id_meta = {pid: {"id": pid, "name": str(pid)} for pid in sorted(ref_ids)}
    ball_id_meta = {pid: {"id": pid} for pid in sorted(ball_ids)}

    return {
        "team_ids": team_id_meta,
        "player_ids": player_id_meta,
        "ref_ids": ref_id_meta,
        "ball_ids": ball_id_meta,
    }


@DataManager.export("BboxesData", analyser_pb2.BBOXES_DATA)
@dataclass(kw_only=True)
class BboxesData(Data):
    type: str = field(default="BboxesData")
    # bboxes: List[BboxData] = field(default_factory=list)
    # bboxes: Dict[int, List[BboxesData]] = field(default_factory=dict)
    bboxes: str = None  # JSON str representation
    meta_data: str = None  # JSON str representation

    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"
        data = self.load_dict("bboxes_data.yml")
        # self.bboxes = [BboxData(**x) for x in data.get("bboxes")]
        self.bboxes = data.get("bboxes")
        self.meta_data = data.get("meta_data")

    def save(self) -> None:
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is opened as 'read only'"

        self.save_dict(
            "bboxes_data.yml",
            {
                # "bboxes": [box.to_dict() for box in self.bboxes]
                "bboxes": self.bboxes,
                "meta_data": self.meta_data,
            },
        )

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            # "bboxes": [box.to_dict() for box in self.bboxes]
            "bboxes": self.bboxes,
            "meta_data": self.meta_data,
        }
