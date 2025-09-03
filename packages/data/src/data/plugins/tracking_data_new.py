import base64
import logging
import os

from ..manager import DataManager
from ..data import Data
from ..fs_handler import LocalFSHandler, ZipFSHandler
from interface import analyser_pb2
from dataclasses import dataclass, field, fields
from collections.abc import Iterable


@DataManager.export("TrackingData", analyser_pb2.TRACKING_DATA)
@dataclass(kw_only=True)
class TrackingData(Data):
    type: str = field(default="TrackingData")
    filename: str = None
    ext: str = None
    content: bytes = b''
    
    # NOTE: data.load() is called via FSHandler.open(data            
    def load(self) -> None:
        super().load()
        assert self.check_fs(), "No filesystem handler installed"

        data = self.load_dict("tracking_data.yml")
        
        self.filename = data.get("filename")
        self.ext = data.get("ext")
        
        # handle bytes content; decode from base64 if it was encoded
        content_data = data.get("content")
        if isinstance(content_data, str):
            # if content was stored as base64 string, decode it
            self.content = base64.b64decode(content_data.encode('utf-8'))
        elif isinstance(content_data, bytes):
            self.content = content_data
        else:
            self.content = None  
        
    def save(self) -> None:
        """ save tracking data to YAML file, encoding bytes content as base64. """
        super().save()
        assert self.check_fs(), "No filesystem handler installed"
        assert self.fs.mode == "w", "Data package is open read only"
        
        # encode bytes content as base64 for YAML storage
        content_to_save = None
        if self.content is not None:
            content_to_save = base64.b64encode(self.content).decode('utf-8')
        
        self.save_dict(
            "tracking_data.yml",
            {
                "filename": self.filename,
                "ext": self.ext,
                "content": content_to_save
            }
        )

    def save_bytes_chunked(self, data: bytes, filename: str, chunk_size: int = 8192):
        with open(filename, 'wb') as f:
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                f.write(chunk)
        
    def to_dict(self) -> dict:
        # encode bytes content as base64 for serialization
        content_to_export = None
        if self.content is not None:
            content_to_export = base64.b64encode(self.content).decode('utf-8')
    
        return {
            **super().to_dict(),
            "filename": self.filename,
            "ext": self.ext,
            "content": content_to_export
        }

    # NOTE: this overwrites create_data() in manager.py
    def create_data(self, data_type: str, index: str = None) -> Data:
        assert self.fs.mode == "w", "Data packet is open read only"
        assert data_type in DataManager._data_name_lut, f"Unknown data type {data_type}"
        
        data = DataManager._data_name_lut[data_type]()
        data._register_fs_handler(LocalFSHandler(self.fs, data.id))

        return data
 
    def load_file_as_bytes(self, fp: str, ext: str) -> None:
        """Load file content as bytes.
        """
        with open(fp, 'rb') as f:
            self.content = f.read()
        self.ext = ext
        self.filename = os.path.basename(fp)

    def get_content_as_string(self, encoding: str = 'utf-8') -> str:
        """Get content as string.
        """
        if self.content is b'': return None
        return self.content.decode(encoding)

    def set_content_from_string(self, content: str, encoding: str = 'utf-8') -> None:
        """Set content from string.
        """
        self.content = content.encode(encoding)

    # def extract_all(self, data_manager: DataManager) -> None:
    #     td_id = self.id
    #     # td_ext = self.ext or 'bin'
    #     # output_path = data_manager._create_file_path(td_id, td_ext) # (self.data_dir, data_id, ext)
        
    #     output_path = data_manager._create_data_path(td_id) # (self.data_dir, data_id, "zip")
    #     with zipfile.ZipFile(output_path, "w") as z:
    #         with self.fs.open_file(file) as f_in, z.open(file, "w") as f_out
    #             chunk = f_in.read(1024)
    #             if not chunk: break
    #             f_out.write(chunk)
    
    def open_file(self, mode="r"):
        assert self.check_fs(), "No fs registered"
        return self.fs.open_file(f"tracking_data.{self.ext}", mode)

    def load_file_from_stream(self, data_stream: Iterable) -> None:
        assert self.check_fs(), "No fs registered"
        assert self.fs.mode == "w", "Fs is not writeable"

        data_stream = iter(data_stream)
        try:
            first_pkg = next(data_stream)
        except StopIteration:
            logging.warning("empty data stream...")
            return

        self.ext = getattr(first_pkg, 'ext', None)
        self.filename = getattr(first_pkg, 'filename', None)
        
        chunks = [first_pkg.data_encoded]
        for chunk in data_stream:
            chunks.append(chunk.data_encoded)
        
        self.content = b''.join(chunks)
        
        # self.ext = first_pkg
        # self.filename = filename

        # with self.open_file("w") as f:
        #     f.write(first_pkg.data_encoded)
        #     for x in data_stream:
        #         f.write(x.data_encoded)
