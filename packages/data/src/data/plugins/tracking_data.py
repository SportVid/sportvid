import logging
import zipfile

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2
from dataclasses import dataclass, field, fields
from collections.abc import Iterable


@DataManager.export("TrackingData", analyser_pb2.TRACKING_DATA)
@dataclass(kw_only=True)
class TrackingData(Data):
    type: str = field(default="TrackingData")
    filename: str = None
    ext: str = None
    
    def load(self) -> None:
        super().load()
        data = self.load_dict("tracking_data.yml")
        self.filename = data.get("filename")
        self.ext = data.get("ext")
        
    def save(self) -> None:
        super().save()
        
        self.save_dict(
            "tracking_data.yml",
            {
                "filename": self.filename,
                "ext": self.ext
            }
        )
    
    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "filename": self.filename,
            "ext": self.ext
        }
        
    def open_file(self, mode="r"):
        assert self.check_fs(), "No fs registered"
        # NOTE: creates a ZiPExtFile object returned by ZipFile.open()
        return self.fs.open_file(f"tracking_data.{self.ext}", mode)

    def load_file_from_stream(self, data_stream: Iterable) -> None:
        assert self.check_fs(), "No fs registered"
        assert self.fs.mode == "w", "Fs is not writeable"

        data_stream = iter(data_stream)
        first_pkg = next(data_stream)

        self.ext = first_pkg.ext
        self.filename = first_pkg.filename
        with self.open_file("w") as f:
            f.write(first_pkg.data_encoded)
            for x in data_stream:
                f.write(x.data_encoded)