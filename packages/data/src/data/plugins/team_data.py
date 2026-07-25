import json

from dataclasses import dataclass, field

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2


@DataManager.export("TeamsData", analyser_pb2.TEAMS_DATA)
@dataclass(kw_only=True)  # Pydantic ???
class TeamsData(Data):
    type: str = field(default="TeamsData")
    teams_data_id: str = None
    teams_data: str = None # JSON string
 
    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"
        data = self.load_dict("teams_data.yml")
        
        self.teams_data_id = data.get("teams_data_id") # type: ignore
        self.teams_data = data.get("teams_data")

    def save(self) -> None:
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is opened as 'read only'"
        self.save_dict(
            "teams_data.yml",
            {
                "teams_data_id": self.teams_data_id,
                "teams_data": self.teams_data,
            },
        )

    def to_dict(self) -> dict:
        meta = super().to_dict()
        return {
            **meta,
            "teams_data_id": self.teams_data_id,
            "teams_data": json.loads(self.teams_data)
        }
