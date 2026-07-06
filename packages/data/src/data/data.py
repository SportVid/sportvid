import logging
import yaml
from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from typing import Optional, Dict
from pathlib import Path
import uuid
import shutil
import tempfile

from .fs_handler import FSHandler


def generate_id():
    return uuid.uuid4().hex


@dataclass(kw_only=True)
class Data:
    id: str = field(default_factory=generate_id)
    version: str = field(default="1.0")
    type: str = field(default="PluginData")
    name: Optional[str] = None
    ref_id: Optional[str] = None

    def _register_fs_handler(self, fs: FSHandler) -> None:
        self.fs = fs

    def _register_data_dir(self, data_dir: str) -> None:
        self.data_dir = data_dir

    def __enter__(self):
        if hasattr(self, "fs") and self.fs:
            self.fs.open(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "fs") and self.fs:
            self.fs.close(self)

    def check_fs(self):
        return hasattr(self, "fs") and self.fs is not None

    def check_data_dir(self):
        return hasattr(self, "data_dir") and self.data_dir is not None

    def data_path(self) -> Path:
        assert self.check_data_dir(), "No data_dir registered"
        return Path(self.data_dir) / self.id

    def file_path(self, filename: str) -> Path:
        return self.data_path() / filename

    def load(self) -> None:
        data = self.load_dict("meta.yml")
        for x in fields(Data):
            default_value = x.default if x.default is not None else None
            setattr(self, x.name, data.get(x.name, default_value))

    def load_dict(self, filename: str) -> Dict:
        if self.check_fs():
            with self.fs.open_file(filename, "r") as f:
                decoded_data = f.read().decode("utf-8")
                return yaml.safe_load(decoded_data) or {}

        if self.check_data_dir():
            path = self.file_path(filename)
            if not path.exists():
                logging.warning(f"Metadata file not found: {path}")
                return {}
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        raise AssertionError("No filesystem handler or data_dir registered")

    def save(self) -> None:
        data_dict = {}
        for x in fields(Data):
            data_dict[x.name] = getattr(self, x.name)
        self.save_dict("meta.yml", data_dict)

    def save_dict(self, filename: str, data: Dict) -> None:
        if self.check_fs():
            assert self.fs.mode == "w", "Data package is open read only"
            with self.fs.open_file(filename, "w") as f:
                f.write(yaml.safe_dump(data).encode())
            return

        if self.check_data_dir():
            self.data_path().mkdir(parents=True, exist_ok=True)
            self.file_path(filename).write_text(
                yaml.safe_dump(data),
                encoding="utf-8",
            )
            return

        raise AssertionError("No filesystem handler or data_dir registered")

    def open_file(self, filename: str, mode: str = "rb", encoding: str | None = None):
        if self.check_fs():
            return self.fs.open_file(filename, mode)

        if self.check_data_dir():
            self.data_path().mkdir(parents=True, exist_ok=True)
            return open(self.file_path(filename), mode, encoding=encoding)

        raise AssertionError("No filesystem handler or data_dir registered")

    def to_dict(self) -> dict:
        data_dict = {}
        for x in fields(Data):
            data_dict[x.name] = getattr(self, x.name)
        return data_dict
    
    # NOTE: idea is to get the local file path so we can run ffmpeg on the file.
    @contextmanager
    def get_local_file_path(self, filename: str):
        if self.check_data_dir():
            path = self.file_path(filename)
            if not path.exists():
                raise FileNotFoundError(f"Local file not found: {path}")
            yield path
            return

        if self.check_fs():
            suffix = Path(filename).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
                with self.fs.open_file(filename, "r") as src:
                    shutil.copyfileobj(src, tmp)
                tmp.flush()
                yield Path(tmp.name)
            return

        raise AssertionError("No filesystem handler or data_dir registered")