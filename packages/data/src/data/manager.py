from __future__ import annotations

import time
import os
import logging
import tempfile
import hashlib
import shutil
from typing import Iterator, List
from collections.abc import Iterable
from pathlib import Path

from .data import Data
from .fs_handler import ZipFSHandler
from .utils import create_data_path, generate_id
from utils.cache import Cache
from interface import analyser_pb2


class DataManager:
    _data_name_lut = {}
    _data_enum_lut = {}
    _data_minetype_lut = {}

    VIDEO_ASSET_ENUM = analyser_pb2.VIDEO_ASSET_DATA

    def __init__(self, data_dir=None, cache: Cache = None):
        self.cache = cache
        if not data_dir:
            data_dir = tempfile.mkdtemp()
        self.data_dir = data_dir
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

    @classmethod
    def export(cls, name: str, enum_value: int, minetype: List[str] = None):
        def export_helper(data):
            cls._data_name_lut[name] = data
            cls._data_enum_lut[enum_value] = data
            if minetype:
                for x in minetype:
                    cls._data_minetype_lut[x] = data
            return data
        return export_helper

    def _is_video_asset_type(self, data_type) -> bool:
        if isinstance(data_type, str):
            cls_ = self._data_name_lut.get(data_type)
            if cls_ is None:
                return False
            return cls_ in [self._data_enum_lut.get(self.VIDEO_ASSET_ENUM)]
        return data_type == self.VIDEO_ASSET_ENUM

    def _create_data_path(self, data_id) -> str:
        return self._create_file_path(data_id, "zip")

    def _create_file_path(self, data_id, extension) -> str:
        return create_data_path(self.data_dir, data_id, extension)

    def _create_asset_dir(self, data_id: str) -> str:
        path = Path(self.data_dir) / data_id
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _load_zip_data(self, data_id: str):
        data_path = create_data_path(self.data_dir, data_id, "zip")

        if not os.path.exists(data_path):
            logging.error(f"Data not found with data_id {data_id}")
            return None

        data = Data()
        data._register_fs_handler(ZipFSHandler(data_path, mode="r"))
        with data:
            data_type = data.type
            data_id = data.id

        assert data_type in self._data_name_lut, f"Unknown data type {data_type}"

        data = self._data_name_lut[data_type](id=data_id)
        data._register_fs_handler(ZipFSHandler(data_path, mode="r"))
        return data

    def _load_video_asset_data(self, data_id: str):
        asset_dir = Path(self.data_dir) / data_id
        if not asset_dir.exists():
            logging.error(f"Video asset not found with data_id {data_id}")
            return None

        data_cls = self._data_enum_lut[self.VIDEO_ASSET_ENUM]
        data = data_cls(id=data_id)
        data._register_data_dir(self.data_dir)
        data.load()
        return data

    def create_data(self, data_type: str, data_id: str = None):
        assert data_type in self._data_name_lut, f"Unknown data type {data_type}"

        if data_id is not None:
            data = self._data_name_lut[data_type](id=data_id)
        else:
            data = self._data_name_lut[data_type]()

        if self._is_video_asset_type(data_type):
            data.data_dir = self.data_dir
            self._create_asset_dir(data.id)
            return data

        data_path = create_data_path(self.data_dir, data.id, "zip")
        data._register_fs_handler(ZipFSHandler(data_path, mode="w"))
        return data

    def load(self, data_id: str):
        zip_path = create_data_path(self.data_dir, data_id, "zip")
        asset_dir = Path(self.data_dir) / data_id

        if os.path.exists(zip_path):
            return self._load_zip_data(data_id)

        if asset_dir.exists():
            return self._load_video_asset_data(data_id)

        logging.error(f"Data not found with data_id {data_id}")
        return None

    def delete(self, data_id: str):
        zip_path = create_data_path(self.data_dir, data_id, "zip")
        asset_dir = Path(self.data_dir) / data_id

        if self.cache and hasattr(self.cache, "delete_by_value_field"):
            try:
                deleted = self.cache.delete_by_value_field("data_id", data_id)
                if deleted:
                    logging.info("Deleted %d cache entries for data_id %s", deleted, data_id)
            except Exception:
                logging.exception("Failed cache invalidation for data_id %s", data_id)

        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except FileNotFoundError:
                pass

        if asset_dir.exists():
            try:
                shutil.rmtree(asset_dir)
            except FileNotFoundError:
                pass

    def load_file_from_stream(self, data_stream: Iterable) -> tuple[Data, str]:
        data_stream = iter(data_stream)
        first_pkg = next(data_stream)

        hash_stream = hashlib.sha1()

        if first_pkg.type not in self._data_enum_lut:
            logging.error(f"No data class register with index {first_pkg.type}")
            return None

        data_type = first_pkg.type

        if first_pkg.id is not None and len(first_pkg.id) > 0:
            data_id = first_pkg.id
            if os.path.exists(create_data_path(self.data_dir, data_id, "zip")) or (Path(self.data_dir) / data_id).exists():
                logging.error(f"Data with id already exists {data_id}")
                return None
            data = self._data_enum_lut[data_type](id=data_id)
        else:
            data = self._data_enum_lut[data_type]()

        assert hasattr(data, "load_file_from_stream"), f"Data {data.type} has no function load_file_from_stream"

        if self._is_video_asset_type(data_type):
            data.data_dir = self.data_dir

            def data_generator():
                yield first_pkg
                if getattr(first_pkg, "data_encoded", None):
                    hash_stream.update(first_pkg.data_encoded)
                for x in data_stream:
                    if getattr(x, "data_encoded", None):
                        hash_stream.update(x.data_encoded)
                    yield x

            data.load_file_from_stream(data_generator())
        else:
            data_path = create_data_path(self.data_dir, data.id, "zip")
            data._register_fs_handler(ZipFSHandler(data_path, mode="w"))

            def data_generator():
                yield first_pkg
                hash_stream.update(first_pkg.data_encoded)
                for x in data_stream:
                    hash_stream.update(x.data_encoded)
                    yield x

            with data as d:
                d.load_file_from_stream(data_generator())

        file_hash = hash_stream.hexdigest()

        if self.cache:
            logging.info(f"Check file cache for {file_hash}")
            cached_data_info = self.cache.get(file_hash)
            cached_data = None
            if cached_data_info is not None:
                logging.info(f"Found data for file upload in cache {cached_data_info}")
                cached_data = self.load(cached_data_info.get("data_id"))
                logging.info(f"Found data for file upload in cache {cached_data}")
                if cached_data is not None:
                    self.delete(data.id)
                    data = cached_data

            self.cache.set(file_hash, {"data_id": data.id, "time": time.time(), "type": "file"})

        return data, file_hash

    def load_data_from_stream(self, data_stream: Iterable) -> tuple[Data, str]:
        data_stream = iter(data_stream)
        first_pkg = next(data_stream)

        data_id = first_pkg.id
        hash_stream = hashlib.sha1()
        output_path = create_data_path(self.data_dir, data_id, "zip")

        def data_generator():
            yield first_pkg.data_encoded
            hash_stream.update(first_pkg.data_encoded)
            for x in data_stream:
                hash_stream.update(x.data_encoded)
                yield x.data_encoded

        if os.path.exists(output_path):
            logging.warning(f"Data with id already exists {data_id}")
            for _ in data_generator():
                pass
            return self.load(data_id), hash_stream.hexdigest()

        with open(output_path, "wb") as f_out:
            for x in data_generator():
                f_out.write(x)

        return self.load(data_id), hash_stream.hexdigest()

    def dump_to_stream(self, data_id: str, chunk_size: int = 131_072) -> Iterator[dict]:
        data = self.load(data_id)
        if data is None:
            logging.error(f"Data not found with id {data_id}")
            return None

        if hasattr(data, "manifest_filename") and hasattr(data, "media_filename") and hasattr(data, "manifest_text"):
            yield {
                "id": data.id,
                "type": self.VIDEO_ASSET_ENUM,
                "manifest_text": data.manifest_text or "",
                "manifest_filename": data.manifest_filename,
                "media_filename": data.media_filename,
                "data_encoded": b"",
                "is_header": True,
                "eof": False,
            }

            with open(data.media_path(), "rb") as bytestream:
                while True:
                    chunk = bytestream.read(chunk_size)
                    if not chunk:
                        break
                    yield {
                        "id": data.id,
                        "type": self.VIDEO_ASSET_ENUM,
                        "manifest_text": "",
                        "manifest_filename": "",
                        "media_filename": "",
                        "data_encoded": chunk,
                        "is_header": False,
                        "eof": False,
                    }

            yield {
                "id": data.id,
                "type": self.VIDEO_ASSET_ENUM,
                "manifest_text": "",
                "manifest_filename": "",
                "media_filename": "",
                "data_encoded": b"",
                "is_header": False,
                "eof": True,
            }
            return

        data_path = create_data_path(self.data_dir, data_id, "zip")
        if not os.path.exists(data_path):
            logging.error(f"Zip data not found with id {data_id}")
            return None

        with open(data_path, "rb") as bytestream:
            while True:
                chunk = bytestream.read(chunk_size)
                if not chunk:
                    break
                yield {"id": data_id, "data_encoded": chunk}