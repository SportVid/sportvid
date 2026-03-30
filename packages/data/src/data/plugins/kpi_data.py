import json

from dataclasses import dataclass, field

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("KpiData", analyser_pb2.KPI_DATA)
@dataclass(kw_only=True)
class KpiData(Data):
    type: str = field(default="KpiData")
    tracking_data_id: str = None
    meta_data: str = None  # JSON string: {format, kpi_names, player_ids, teams, segments, framerate}
    kpis: str = None       # JSON string: {frame_idx: [[player_id, dist, vel, metpow], ...], ...}

    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"
        data = self.load_dict("kpi_data.yml")
        self.tracking_data_id = data.get("tracking_data_id")
        self.meta_data = data.get("meta_data")
        self.kpis = data.get("kpis")

    def save(self) -> None:
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is opened as 'read only'"
        self.save_dict(
            "kpi_data.yml",
            {
                "tracking_data_id": self.tracking_data_id,
                "meta_data": self.meta_data,
                "kpis": self.kpis,
            },
        )

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "tracking_data_id": self.tracking_data_id,
            "meta_data": json.loads(self.meta_data) if self.meta_data else None,
            "kpis": json.loads(self.kpis) if self.kpis else None,
        }
