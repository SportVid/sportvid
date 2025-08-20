import json

from dataclasses import dataclass, field

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("PositionData", analyser_pb2.POS_DATA)
@dataclass(kw_only=True)  # Pydantic ???
class PositionData(Data):
    type: str = field(default="PositionData")
    tracking_data_id: str = None
    meta_data: str = None  # JSON string
    pos: str = None  # JSON string
 
    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"
        data = self.load_dict("pos_data.yml")
        
        self.tracking_data_id = data.get("tracking_data_id") # type: ignore
        self.meta_data = data.get("meta_data")
        self.pos = data.get("pos")
        
        # ----
        # with self.fs.open_file("pos.json", "r") as f: # type: ignore
        #     self.pos = json.dumps(json.load(f))
        # with self.fs.open_file("pos.npz", "r") as f: # type: ignore
        #     self.pos = np.load(f)

    def save(self) -> None:
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is opened as 'read only'"
        self.save_dict(
            "pos_data.yml",
            {
                "tracking_data_id": self.tracking_data_id,
                "meta_data": self.meta_data,
                "pos": self.pos
            },
        )
        
        # ----
        # with self.fs.open_file("pos.json", "w") as f:
        #     json.dump(self.pos, f)
        # with self.fs.open_file("pos.npz", "w") as f:
        #     np.save(f, self.pos)

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "tracking_data_id": self.tracking_data_id,
            "meta_data": json.loads(self.meta_data),
            "pos_data": json.loads(self.pos)
        }
