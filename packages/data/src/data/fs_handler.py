import zipfile, tarfile
import logging
import yaml
import os
import io

from dataclasses import dataclass, field, fields, asdict
from typing import Callable, Optional, Dict

import uuid


class FSHandler:
    pass


class ArchiveFileWrapper:
    """Wrapper to handle both regular files and nested tar archives"""
    
    def __init__(self, file_data, filename):
        """
        Docstring for __init__
        
        :param self: Wrapper object
        :param file_data: bytes object
        :param filename: ...
        """
        
        self.filename = filename
        self.tar_obj = None
        
        # Create BytesIO from the data
        self.file_obj = io.BytesIO(file_data)
        
        # Use tarfile's built-in check
        try:
            if tarfile.is_tarfile(self.file_obj):
                self.file_obj.seek(0)
                self.tar_obj = tarfile.open(fileobj=self.file_obj, mode='r:*')
            else:
                self.file_obj.seek(0)
        except Exception:
            self.file_obj.seek(0)
    
    def is_archive(self):
        return self.tar_obj is not None
    
    def list_files(self):
        """List files in the tar archive"""
        if self.tar_obj:
            return self.tar_obj.getnames()
        return []
    
    def open_nested(self, member_name, mode='r'):
        """Open a file from within the tar archive"""
        if self.tar_obj:
            return self.tar_obj.extractfile(member_name)
        return None
    
    def read(self, *args, **kwargs):
        """Direct read if not an archive"""
        return self.file_obj.read(*args, **kwargs)
    
    def tell(self):
        """Tell support"""
        return self.file_obj.tell()
    
    def close(self):
        if self.tar_obj:
            self.tar_obj.close()
        if self.file_obj:
            self.file_obj.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class ZipFSHandler(FSHandler):
    def __init__(self, path: str, mode: str = "r") -> None:
        if mode is None:
            mode = "w"
        assert mode == "w" or mode == "r", "No valid mode for ZipData"

        self.path = path
        self.zipfile = None
        self.mode = mode

    def open(self, data) -> None:
        logging.debug(f"open {self.path}")
        self.zipfile = zipfile.ZipFile(self.path, self.mode)
        if self.mode == "r":
            data.load()

    def list_files(self) -> None:
        if self.zipfile is None:
            raise Exception()
        yield from self.zipfile.namelist()

    def close(self, data) -> None:
        logging.debug(f"close {self.path}")
        if self.zipfile is None:
            return

        if self.mode == "r":
            self.zipfile.close()
            self.zipfile = None
            return

        data.save()

        self.zipfile.close()
        self.zipfile = None

    def open_file(self, filename: str, mode: str = "r"):
        logging.debug(f"{self.__class__.__name__} open_file {self.path} {filename}")
        if self.zipfile is None:
            logging.error("")
            return None

        if mode == "w" and self.mode == "r":
            raise ValueError
        
        if "w" in mode or "a" in mode:
            return self.zipfile.open(filename, mode=mode, force_zip64=True)
        
        # return self.zipfile.open(filename, mode=mode, force_zip64=True)
        # NOTE: uses context manager to ensure handle is closed immediately
        with self.zipfile.open(filename, mode=mode, force_zip64=True) as zip_file_obj:
            file_data = zip_file_obj.read()

        # Return wrapper that manages handles lazily
        return ArchiveFileWrapper(file_data, filename)


class LocalFSHandler(FSHandler):
    def __init__(self, fs: FSHandler, path: str) -> None:
        self.fs = fs
        self.path = path

    def open(self, data) -> None:
        logging.debug(f"open {self.path}")
        if self.fs.mode == "r":
            data.load()

    @property
    def mode(self):
        return self.fs.mode

    def list_files(self) -> None:
        if self.fs is None:
            raise Exception()
        for x in self.fs.list_files():
            if x.startswith(self.path):
                yield x[len(self.path) + 1 :]

    def close(self, data) -> None:
        logging.debug(f"close {self.path}")
        if self.fs is None:
            return

        if self.fs.mode == "r":
            return

        data.save()

    def open_file(self, filename: str, mode: str = "r"):
        logging.debug(f"{self.__class__.__name__} open_file {self.path} {filename}")
        if self.fs is None:
            logging.error("")
            return None

        if mode == "w" and self.fs.mode == "r":
            raise ValueError

        return self.fs.open_file(os.path.join(self.path, filename), mode=mode)
