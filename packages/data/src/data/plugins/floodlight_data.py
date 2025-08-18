import json
import numpy.typing as npt
import numpy as np

from dataclasses import dataclass, field

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("FloodlightData", analyser_pb2.FL_DATA)
@dataclass(kw_only=True)  # Pydantic ???
class FloodlightData(Data):
    type: str = field(default="FloodlightData")
    tracking_data_id: str = None
    meta_data: int = None  # TODO
    xy_pos: npt.NDArray = None  # TODO
 
    def load(self) -> None:
        super().load()
        data = self.load_dict("pos_data.yml")
        
        self.tracking_data_id = data.get("tracking_data_id") # type: ignore

        with self.fs.open_file("xy_pos.npz", "r") as f: # type: ignore
            self.xy_pos = np.load(f)

    def save(self) -> None:
        super().save()

        self.save_dict(
            "fl_data.yml",
            {
                "tracking_data_id": self.tracking_data_id,
            },
        )

        with self.fs.open_file("pos.npz", "w") as f:
            np.save(f, self.pos)

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "tracking_data_id": self.tracking_data_id,
            "xy_pos": self.xy_pos.tolist(),
        }
