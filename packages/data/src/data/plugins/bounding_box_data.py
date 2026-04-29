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
