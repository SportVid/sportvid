from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


def generate_id() -> str:
    import uuid
    return uuid.uuid4().hex


@dataclass
class VideoAsset:
    id: str
    root_dir: Path
    manifest_filename: str = "stream.m3u8"
    media_filename: str = "media.m4s"
    manifest_text: str | None = None

    @property
    def asset_dir(self) -> Path:
        return self.root_dir / self.id

    @property
    def manifest_path(self) -> Path:
        return self.asset_dir / self.manifest_filename

    @property
    def media_path(self) -> Path:
        return self.asset_dir / self.media_filename

    def ensure_dirs(self) -> None:
        self.asset_dir.mkdir(parents=True, exist_ok=True)

    def save_manifest(self) -> None:
        if self.manifest_text is None:
            raise ValueError("manifest_text is missing")
        self.ensure_dirs()
        self.manifest_path.write_text(self.manifest_text, encoding="utf-8")

    def load_manifest(self) -> str:
        self.manifest_text = self.manifest_path.read_text(encoding="utf-8")
        return self.manifest_text


class VideoAssetManager:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or tempfile.mkdtemp())
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_asset(
        self,
        data_id: str | None = None,
        manifest_filename: str = "stream.m3u8",
        media_filename: str = "media.m4s",
    ) -> VideoAsset:
        asset = VideoAsset(
            id=data_id or generate_id(),
            root_dir=self.data_dir,
            manifest_filename=manifest_filename,
            media_filename=media_filename,
        )
        asset.ensure_dirs()
        return asset

    def load_asset(self, data_id: str) -> VideoAsset | None:
        asset_dir = self.data_dir / data_id
        if not asset_dir.exists():
            return None

        manifest_candidates = list(asset_dir.glob("*.m3u8"))
        media_candidates = list(asset_dir.glob("*.m4s")) + list(asset_dir.glob("*.mp4"))

        if not manifest_candidates or not media_candidates:
            return None

        asset = VideoAsset(
            id=data_id,
            root_dir=self.data_dir,
            manifest_filename=manifest_candidates[0].name,
            media_filename=media_candidates[0].name,
        )
        asset.load_manifest()
        return asset

    def delete_asset(self, data_id: str) -> None:
        asset_dir = self.data_dir / data_id
        if asset_dir.exists():
            shutil.rmtree(asset_dir)

    def exists(self, data_id: str) -> bool:
        asset = self.load_asset(data_id)
        return asset is not None

    def compute_media_sha1(self, data_id: str) -> str | None:
        asset = self.load_asset(data_id)
        if asset is None or not asset.media_path.exists():
            return None

        sha1 = hashlib.sha1()
        with open(asset.media_path, "rb") as f:
            while True:
                chunk = f.read(131_072)
                if not chunk:
                    break
                sha1.update(chunk)
        return sha1.hexdigest()

    def save_from_upload_stream(self, request_iterator: Iterable) -> tuple[VideoAsset, str]:
        request_iterator = iter(request_iterator)
        first = next(request_iterator, None)
        if first is None:
            raise ValueError("Empty upload stream")
        if not first.is_header:
            raise ValueError("First upload message must be header")
        if not first.id:
            raise ValueError("Video asset id is required")
        if not first.manifest_text:
            raise ValueError("manifest_text is required in header")
        if not first.manifest_filename:
            raise ValueError("manifest_filename is required in header")
        if not first.media_filename:
            raise ValueError("media_filename is required in header")

        asset = self.create_asset(
            data_id=first.id,
            manifest_filename=first.manifest_filename,
            media_filename=first.media_filename,
        )
        asset.manifest_text = first.manifest_text
        asset.save_manifest()

        sha1 = hashlib.sha1()
        with open(asset.media_path, "wb") as f:
            for req in request_iterator:
                if req.data_encoded:
                    sha1.update(req.data_encoded)
                    f.write(req.data_encoded)
                if req.eof:
                    break

        return asset, sha1.hexdigest()

    def stream_asset(self, data_id: str, chunk_size: int = 131_072) -> Iterator[dict]:
        asset = self.load_asset(data_id)
        if asset is None:
            raise FileNotFoundError(f"VideoAsset not found: {data_id}")

        media_hash = self.compute_media_sha1(data_id) or ""

        yield {
            "id": asset.id,
            "type": 23,
            "manifest_text": asset.manifest_text,
            "media_filename": asset.media_filename,
            "manifest_filename": asset.manifest_filename,
            "data_encoded": b"",
            "is_header": True,
            "eof": False,
            "hash": media_hash,
        }

        with open(asset.media_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield {
                    "id": asset.id,
                    "type": 23,
                    "manifest_text": "",
                    "media_filename": "",
                    "manifest_filename": "",
                    "data_encoded": chunk,
                    "is_header": False,
                    "eof": False,
                    "hash": media_hash,
                }

        yield {
            "id": asset.id,
            "type": 23,
            "manifest_text": "",
            "media_filename": "",
            "manifest_filename": "",
            "data_encoded": b"",
            "is_header": False,
            "eof": True,
            "hash": media_hash,
        }