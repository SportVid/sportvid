import logging
from pathlib import Path

from ..manager import DataManager
from ..data import Data
from interface import analyser_pb2
from dataclasses import dataclass, field
from collections.abc import Iterable
from utils import VideoDecoder


@DataManager.export("VideoAssetData", analyser_pb2.VIDEO_ASSET_DATA)
@dataclass(kw_only=True)
class VideoAssetData(Data):
    type: str = field(default="VideoAssetData")
    manifest_filename: str = field(default="stream.m3u8")
    media_filename: str = field(default="media.m4s")
    manifest_text: str | None = field(default=None)

    def manifest_path(self) -> Path:
        return self.file_path(self.manifest_filename)

    def media_path(self) -> Path:
        return self.file_path(self.media_filename)

    def load(self) -> None:
        super().load()
        meta = self.load_dict("video_asset_data.yml")
        self.manifest_filename = meta.get("manifest_filename", self.manifest_filename)
        self.media_filename = meta.get("media_filename", self.media_filename)

        manifest_path = self.manifest_path()
        if manifest_path.exists():
            self.manifest_text = manifest_path.read_text(encoding="utf-8")

    def save(self) -> None:
        super().save()
        self.save_dict(
            "video_asset_data.yml",
            {
                "manifest_filename": self.manifest_filename,
                "media_filename": self.media_filename,
            },
        )
        if self.manifest_text is not None:
            self.manifest_path().write_text(self.manifest_text, encoding="utf-8")

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "manifest_filename": self.manifest_filename,
            "media_filename": self.media_filename,
            "manifest_text": self.manifest_text,
        }

    def open_manifest(self, mode="r"):
        if "b" in mode:
            return open(self.manifest_path(), mode)
        return open(self.manifest_path(), mode, encoding="utf-8")

    def open_media(self, mode="rb"):
        return open(self.media_path(), mode)

    def load_file_from_stream(self, data_stream: Iterable) -> None:
        data_stream = iter(data_stream)
        first_pkg = next(data_stream)

        if not first_pkg.is_header:
            raise ValueError("First package must be a header")

        self.manifest_filename = first_pkg.manifest_filename or "stream.m3u8"
        self.media_filename = first_pkg.media_filename or "media.m4s"
        self.manifest_text = first_pkg.manifest_text or ""

        self.data_path().mkdir(parents=True, exist_ok=True)
        self.save()

        with self.open_media("wb") as f:
            for x in data_stream:
                if getattr(x, "data_encoded", None):
                    f.write(x.data_encoded)
                if getattr(x, "eof", False):
                    break

    @property
    def ext(self) -> str:
        return self.media_path().suffix.lstrip(".")

    @property
    def filename(self) -> str:
        return self.media_filename

    def __call__(self, fps: float = None, **kwargs) -> "VideoAssetIterator":
        return VideoAssetIterator(self, fps=fps)


class VideoAssetIterator:
    def __init__(self, data: VideoAssetData, fps: float = None):
        self.data = data
        self.fps = fps
        self.video_file = None
        self.video_decoder = None

    def __enter__(self):
        self.video_file = self.data.open_media("rb")
        self.video_decoder = VideoDecoder(
            self.video_file,
            fps=self.fps,
            extension=self.data.media_path().suffix,
        )
        return self.video_decoder

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.video_file is not None:
            self.video_file.close()