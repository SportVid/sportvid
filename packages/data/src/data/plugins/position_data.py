import logging
from typing import List
from dataclasses import dataclass, field

import numpy.typing as npt
import numpy as np

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("PositionData", analyser_pb2.POS_DATA)
@dataclass(kw_only=True)
class PositionData(Data):
    type: str = field(default="PositionData")
    
    ref_id: str = None
    delta_time: float = field(default=None)
    
    pos: npt.NDArray = None  # np.ndarray: ["P1_x", "P1_y", "P2_x", "P2_y", ..., "PN_x", "PN_y"]
    
    def load(self) -> None:
        super().load()
        data = self.load_dict("pos_data.yml")
        
        self.ref_id = data.get("ref_id")
        self.delta_time = data.get("delta_time")
        
        with self.fs.open_file("pos.npz", "r") as f:
            self.pos = np.load(f)

    def save(self) -> None:
        super().save()

        self.save_dict(
            "pos_data.yml",
            {
                "ref_id": self.ref_id,
                "delta_time": self.delta_time,
            },
        )
        with self.fs.open_file("pos.npz", "w") as f:
            np.save(f, self.pos)

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "ref_id": self.ref_id,
            "delta_time": self.delta_time,
            "pos_data": self.pos.tolist(),
        }

    # def to_save(self) -> dict:
    #     meta = super().to_dict()
    #     return {
    #         **meta,
    #         "ref_id": self.ref_id,
    #         "pos_data": self.pos.tolist(),
    #     }


# @DataManager.export("PositionsData", analyser_pb2.POSS_DATA)
# @dataclass(kw_only=True)
# class PositionsData(Data):
#     type: str = field(default="PositionsData")
#     poss: List[PositionData] = field(default_factory=list)

#     def load(self) -> None:
#         super().load()
#         assert self.check_fs(), "No filesystem handler installed"

#         data = self.load_dict("positions_data.yml")
#         self.poss = [PositionData(**x) for x in data.get("poss")]

#         # ----
#         with self.fs.open_file("poss.npz", "r") as f:
#             poss = np.load(f)
#         if len(self.poss) != poss.shape[0]:
#             logging.error(
#                 f"Data has invalid shape {len(self.poss)} vs. {poss.shape[0]}"
#             )
#             return

#         for i in range(poss.shape[0]):
#             self.poss[i].pos = poss[i]

#     def save(self) -> None:
#         super().save()
#         assert self.check_fs(), "No filesystem handler installed"
#         assert self.fs.mode == "w", "Data packet is open read only"

#         self.save_dict(
#             "positions_data.yml",
#             {"poss": [x.to_save() for x in self.poss]},
#         )
        
#         # ----
#         with self.fs.open_file("poss.npz", "w") as f:
#             np.save(f, np.stack([x.pos for x in self.poss], axis=0))

#     def to_dict(self) -> dict:
#         return {
#             **super().to_dict(),
#             "poss": [x.to_dict() for x in self.poss],
#         }
