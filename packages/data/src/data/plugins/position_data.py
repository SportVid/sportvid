import json

from dataclasses import dataclass, field

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("PositionData", analyser_pb2.POS_DATA)
@dataclass(kw_only=True)  # Pydantic ???
class PositionData(Data):
    type: str = field(default="PositionData")
    ref_id: str = None
    delta_time: float = field(default=None) # type: ignore
    pos: str = None  # uses JSON representation for the output data
 
    def load(self) -> None:
        super().load()
        data = self.load_dict("pos_data.yml")
        
        self.ref_id = data.get("ref_id") # type: ignore
        self.delta_time = data.get("delta_time") # type: ignore
        self.pos = data.get("pos") # type: ignore
        
        # with self.fs.open_file("pos.npz", "r") as f: # type: ignore
        #     self.pos = np.load(f)

    def save(self) -> None:
        super().save()

        self.save_dict(
            "pos_data.yml",
            {
                "ref_id": self.ref_id,
                "delta_time": self.delta_time,
                "pos_data": self.pos
            },
        )
        # with self.fs.open_file("pos.npz", "w") as f:
        #     np.save(f, self.pos)

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "ref_id": self.ref_id,
            "delta_time": self.delta_time,
            "pos_data": json.loads(self.pos)  # parse as dict()
        }
