"""Files uploaded with a plugin run (plugin/run/new, `file_<name>` fields).

They are kept on the backend's data volume (DATA_CACHE_ROOT), which the Celery workers mount
too and nginx does not serve. /tmp would not do: it is a tmpfs per container, so the worker
that runs the task cannot see the backend's files there.

The view stores {"value": original name, "path": ...} per field in parameters["_files"],
which it always sets itself, so a client cannot choose a path. A task reads an upload with
uploaded_file_path(); run_plugin removes the folder when the run is over, and the scheduled
cleanup (backend/cleanup.py) removes what a crashed worker left behind.
"""
import logging
import os
import shutil
import tempfile

from django.conf import settings

logger = logging.getLogger(__name__)


def plugin_upload_root():
    return os.path.join(getattr(settings, "DATA_CACHE_ROOT", None) or "/cache/", "plugin_uploads")


def new_upload_dir():
    root = plugin_upload_root()
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(dir=root, prefix="run-")


def _inside_root(path):
    root = os.path.realpath(plugin_upload_root())
    real = os.path.realpath(path)
    return real if os.path.commonpath([root, real]) == root and real != root else None


def uploaded_file_path(parameters, name):
    """Path of the file uploaded for parameter `name`, or None if there is none."""
    info = ((parameters or {}).get("_files") or {}).get(name)
    path = info.get("path") if isinstance(info, dict) else None
    if not path:
        return None
    real = _inside_root(path)
    if real is None:
        logger.warning("Ignoring upload %s outside %s", name, plugin_upload_root())
    return real


def remove_uploaded_files(parameters):
    """Remove the upload folders of a run's parameters; anything outside the upload root is left alone."""
    files = (parameters or {}).get("_files") or {}
    root = os.path.realpath(plugin_upload_root())
    for name in files:
        path = uploaded_file_path(parameters, name)
        folder = os.path.dirname(path) if path else None
        if folder and os.path.dirname(folder) == root:
            shutil.rmtree(folder, ignore_errors=True)
