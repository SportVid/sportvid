import logging
import zipfile
from typing import List, Dict, Union, Any
from dataclasses import dataclass, field
from ..manager import DataManager
from ..data import Data
from ..fs_handler import LocalFSHandler
from interface import analyser_pb2


@DataManager.export("DictData", analyser_pb2.DICT_DATA)
@dataclass(kw_only=True)
class DictData(Data):
    type: str = field(default="DictData")
    data: Dict[Any, Any] = field(default_factory=dict)
    index: List[Union[str, int]] = field(default_factory=list)
    
    def load(self) -> None:
        super().load()
        if not self.check_fs():
            raise Exception("No filesystem handler installed")

        data = self.load_dict("list_data.yml")
        self.index = data.get("index")
        self.data = data.get("data")

    def save(self) -> None:
        super().save()
        if not self.check_fs():
            raise Exception("No filesystem handler installed.")
        if not self.fs.mode == "w":
            raise Exception("Data packet is open read only.")

        self.save_dict("list_data.yml", {"index": self.index, "data": self.data})

    def create_data(self, data_type: str, index: str = None) -> Data:
        if not self.fs.mode == "w":
            raise Exception("Data packet is open read only.")
        if not data_type in DataManager._data_name_lut:
            raise Exception(f"Unknown data type {data_type}.")

        data = DataManager._data_name_lut[data_type]()
        data._register_fs_handler(LocalFSHandler(self.fs, data.id))

        self.data.append(data.id)
        if index is None:
            index = len(self.index)
        self.index.append(index)

        return data

    def add_data(self, data: Data, index: str = None) -> None:
        with data:
            local_fs = LocalFSHandler(self.fs, data.id)

            for file in data.fs.list_files():
                with data.fs.open_file(file) as f_in, local_fs.open_file(file, "w") as f_out:
                    while True:
                        chunk = f_in.read(1024)
                        if not chunk:
                            break
                        f_out.write(chunk)

        self.data.append(data.id)
        if index is None:
            index = len(self.index)
        self.index.append(index)

    def __len__(self):
        return len(self.index)

    def __iter__(self):
        if len(self.index) != len(self.data):
            raise ValueError(
                f"Length mismatch: index={len(self.index)} data={len(self.data)}"
            )

        for i, data_id in zip(self.index, self.data):
            probe = Data()
            probe._register_fs_handler(LocalFSHandler(self.fs, data_id))

            with probe:
                data_type = probe.type

            if data_type not in DataManager._data_name_lut:
                raise ValueError(f"Unknown data type {data_type}")

            typed = DataManager._data_name_lut[data_type]()
            typed._register_fs_handler(LocalFSHandler(self.fs, data_id))
            yield i, typed

    def archive_all(self, data_manager: DataManager) -> None:
        for _, data in self:
            with data:
                output_path = data_manager._create_data_path(data.id)
                with zipfile.ZipFile(output_path, "w") as z:
                    for file in data.fs.list_files():
                        logging.info(f"Archiving {file}.")
                        with data.fs.open_file(file) as f_in, z.open(file, "w") as f_out:
                            while True:
                                chunk = f_in.read(1024)
                                if not chunk:
                                    break
                                f_out.write(chunk)

    def to_dict(self) -> dict:
        result = {**super().to_dict(), "data": [], "index": []}
        for i, data in self:
            with data:
                result["index"].append(i)
                result["data"].append(data.to_dict())

        return result
