import json
import numpy as np
from dataclasses import dataclass, field
from ..manager import DataManager
from ..data import Data
from .ndarray_data import NDArrayData
from interface import analyser_pb2


@DataManager.export("ReIDData", analyser_pb2.REID_DATA)
@dataclass(kw_only=True)
class ReIDData(Data):
    type: str = field(default="ReIDData")
    reid_data_id: str | None = None
    frames: dict[str, dict[str, NDArrayData]] = field(default_factory=dict)
    mapping: str = None  # JSON representation

    def add_array(self, frame_id: str, name: str, arr: np.ndarray) -> None:
        if frame_id not in self.frames:
            self.frames[frame_id] = {}
        self.frames[frame_id][name] = NDArrayData.from_array(name, arr)

    def get_array(self, frame_id: str, name: str) -> np.ndarray:
        try:
            return self.frames[frame_id][name].to_array()
        except KeyError as exc:
            raise KeyError(f"Array '{name}' not found in frame '{frame_id}'") from exc

    def has_array(self, frame_id: str, name: str) -> bool:
        return frame_id in self.frames and name in self.frames[frame_id]

    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"
        data = self.load_dict("reid_data.yml")

        self.reid_data_id = data.get("reid_data_id")
        self.mapping = data.get("mapping")
        
        with self.fs.open_file("frames.json", "r") as f:
            raw_frames = json.loads(f.read().decode("utf-8"))
        
        self.frames = {
            frame_id: {
                name: NDArrayData(
                    name=item["name"],
                    shape=item["shape"],
                    dtype=item["dtype"],
                    data=bytes.fromhex(item["data_hex"]),
                )
                for name, item in frame_payloads.items()
            }
            for frame_id, frame_payloads in raw_frames.items()
        }

    def save(self) -> None:
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is opened as 'read only'"

        self.save_dict(
            "reid_data.yml",
            {
                "reid_data_id": self.reid_data_id,
                "mapping": self.mapping
            },
        )

        raw_frames = {
            frame_id: {
                name: {
                    "name": item.name,
                    "shape": item.shape,
                    "dtype": item.dtype,
                    "data_hex": item.data.hex(),
                }
                for name, item in frame_payloads.items()
            }
            for frame_id, frame_payloads in self.frames.items()
        }

        payload = json.dumps(raw_frames).encode("utf-8")
        with self.fs.open_file("frames.json", "w") as f:
            f.write(payload)

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "reid_data_id": self.reid_data_id,
            "mapping": self.mapping,
            "frames": {
                frame_id: {
                    name: {
                        "shape": item.shape,
                        "dtype": item.dtype,
                        "data_len": len(item.data),
                    }
                    for name, item in frame_payloads.items()
                }
                for frame_id, frame_payloads in self.frames.items()
            },
        }