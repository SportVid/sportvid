"""Files that no database row refers to any more.

Two folders are checked, both laid out as <root>/<id[0:2]>/<id[2:4]>/<id>...:

- MEDIA_ROOT: uploads. A video has its original <id><ext>, its HLS folder <id>/ and its
  archive <id>.tar.gz; tracking data its file and meta file. Orphans come from uploads that
  failed half-way, killed conversions and rows removed without their files.
- DATA_OUTPUT_PATH (/predictions): plugin results. A result is <data_id>.zip; image results also have their
  images extracted next to them as <image_id>.jpg, which the frontend loads directly. Orphans
  come from tasks that stored data and then failed before creating the result rows, and from
  rows removed without their files.

Only entries that follow this layout and are older than a minimum age are considered, so a
file that is being written right now, and anything else an operator put there, is left
alone. Nothing is deleted when the tables are empty: that is a wrong database, not a folder
full of orphans.
"""
import logging
import os
import re
import shutil
import time
import zipfile
from pathlib import Path

from django.conf import settings

from backend.log_context import log_event

logger = logging.getLogger(__name__)

_ID = re.compile(r"^[0-9a-f]{32}")
_SHARD = re.compile(r"^[0-9a-f]{2}$")


def _id_in(name):
    match = _ID.match(os.path.basename(name or ""))
    return match.group(0) if match else None


# --- what the rows refer to


def _known_media_ids():
    from backend.models import TrackingData, Video

    ids = set()
    for model, fields in ((Video, ("id", "file")), (TrackingData, ("id", "file", "meta_file"))):
        for row in model.objects.values_list(*fields):
            ids.update(value.hex for value in row if value)
    return ids


def _any_media_rows():
    from backend.models import TrackingData, Video

    return Video.objects.exists() or TrackingData.objects.exists()


def _image_ids(root: Path, data_id):
    """IDs of the images an image result lists, i.e. its extracted <image_id>.jpg files."""
    path = root / data_id[0:2] / data_id[2:4] / f"{data_id}.zip"
    try:
        with zipfile.ZipFile(path) as archive:
            return {image_id for image_id in map(_id_in, archive.namelist()) if image_id}
    except (FileNotFoundError, zipfile.BadZipFile):
        # The backend cannot read this result either, so nothing reaches its images through it.
        # Any other error (permissions, I/O) is raised and stops the pass before it deletes.
        logger.warning("Image result %s is missing or unreadable", data_id)
        return set()


def _known_prediction_ids():
    from backend.models import ClusterItem, PluginRunResult

    root = Path(predictions_root())
    ids, image_results = set(), []
    for data_id, result_type in PluginRunResult.objects.values_list("data_id", "type"):
        if not data_id:
            continue
        ids.add(data_id)
        if result_type == PluginRunResult.TYPE_IMAGES:
            image_results.append(data_id)
    for data_id in image_results:
        ids.update(_image_ids(root, data_id))
    # face clustering points at the images it extracted, whatever result they came from
    for image_path in ClusterItem.objects.exclude(image_path=None).values_list("image_path", flat=True):
        image_id = _id_in(image_path)
        if image_id:
            ids.add(image_id)
    return ids


def _any_prediction_rows():
    from backend.models import PluginRunResult

    return PluginRunResult.objects.exists()


# --- the scan


def _size(path: Path) -> int:
    if path.is_dir():
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return path.stat().st_size


def _layout_entries(root: Path):
    """[(entry, id)] of the entries in <root>/xx/yy/ whose name starts with an ID of that folder."""
    entries = []
    for first in sorted(root.iterdir()):
        if not (first.is_dir() and _SHARD.match(first.name)):
            continue
        for second in sorted(first.iterdir()):
            if not (second.is_dir() and _SHARD.match(second.name)):
                continue
            for entry in sorted(second.iterdir()):
                id_hex = _id_in(entry.name)
                if id_hex and id_hex[:2] == first.name and id_hex[2:4] == second.name:
                    entries.append((entry, id_hex))
    return entries


def _find_orphans(root, known_ids, min_age, now):
    root = Path(root)
    if not root.is_dir():
        return []
    # Listed before the rows are read: an entry that is written after this is not in the
    # listing, and one that was in it has its row by the time the IDs are read or is too young.
    entries = _layout_entries(root)
    known = known_ids()
    orphans = []
    for entry, id_hex in entries:
        if id_hex in known:
            continue
        try:
            if now - entry.stat().st_mtime < min_age:
                continue
            orphans.append((entry, _size(entry)))
        except OSError:
            continue  # removed meanwhile
    return orphans


def _cleanup(store, orphans, delete, any_rows):
    if delete and orphans and not any_rows():
        logger.error("Orphan cleanup refuses to delete under %s: the tables are empty", store)
        delete = False
    for path, size in orphans:
        removed = False
        if delete:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                removed = True
            except OSError:
                logger.warning("Failed to remove orphan %s", path, exc_info=True)
        log_event(logger, f"{store}.orphan", path=str(path), size=size, removed=removed)
    total = sum(size for _, size in orphans)
    log_event(logger, f"{store}.orphans", count=len(orphans), size=total, delete=bool(delete))
    return len(orphans), total


def predictions_root():
    # the tasks write to "/predictions/" (their output_path); the setting says the same on every setup
    return getattr(settings, "DATA_OUTPUT_PATH", None) or "/predictions/"


def _min_age(min_age_seconds):
    return settings.ORPHAN_CLEANUP_MIN_AGE if min_age_seconds is None else min_age_seconds


def find_media_orphans(min_age_seconds=None, now=None):
    """[(path, size in bytes)] of the entries under MEDIA_ROOT that belong to no row."""
    now = time.time() if now is None else now
    return _find_orphans(settings.MEDIA_ROOT, _known_media_ids, _min_age(min_age_seconds), now)


def find_prediction_orphans(min_age_seconds=None, now=None):
    """[(path, size in bytes)] of the entries under DATA_OUTPUT_PATH that belong to no result.

    The minimum age is at least PLUGIN_RUN_TIMEOUT: a task downloads its results before it
    creates their rows, and may run that long in between.
    """
    now = time.time() if now is None else now
    min_age = max(_min_age(min_age_seconds), settings.PLUGIN_RUN_TIMEOUT)
    return _find_orphans(predictions_root(), _known_prediction_ids, min_age, now)


def cleanup_media_orphans(delete=None, min_age_seconds=None):
    """Report the orphans under MEDIA_ROOT and, if `delete`, remove them.

    `delete` defaults to settings.ORPHAN_CLEANUP_DELETE. Returns (count, bytes) of the
    orphans found; every one is logged as media.orphan with its path and whether it was removed.
    """
    delete = settings.ORPHAN_CLEANUP_DELETE if delete is None else delete
    return _cleanup("media", find_media_orphans(min_age_seconds), delete, _any_media_rows)


def cleanup_prediction_orphans(delete=None, min_age_seconds=None):
    """Like cleanup_media_orphans() for DATA_OUTPUT_PATH; logs predictions.orphan."""
    delete = settings.ORPHAN_CLEANUP_DELETE if delete is None else delete
    return _cleanup("predictions", find_prediction_orphans(min_age_seconds), delete, _any_prediction_rows)
