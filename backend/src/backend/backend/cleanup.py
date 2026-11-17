"""Files under MEDIA_ROOT that no database row refers to any more.

Uploads live at MEDIA_ROOT/<id[0:2]>/<id[2:4]>/<id><ext>; a video also has its HLS folder
<id>/ and archive <id>.tar.gz next to it. A file becomes an orphan when an upload fails
half-way, a conversion is killed, or a row is removed without its files.

Only entries that follow this layout and are older than a minimum age are considered, so a
file that is being uploaded or converted right now, and anything else an operator put
there, is left alone.
"""
import logging
import os
import re
import shutil
import time
from pathlib import Path

from django.conf import settings

from backend.log_context import log_event

logger = logging.getLogger(__name__)

_ID = re.compile(r"^[0-9a-f]{32}")
_SHARD = re.compile(r"^[0-9a-f]{2}$")


def _known_ids():
    from backend.models import TrackingData, Video

    ids = set()
    for model, fields in ((Video, ("id", "file")), (TrackingData, ("id", "file", "meta_file"))):
        for row in model.objects.values_list(*fields):
            ids.update(value.hex for value in row if value)
    return ids


def _any_rows():
    from backend.models import TrackingData, Video

    return Video.objects.exists() or TrackingData.objects.exists()


def _size(path: Path) -> int:
    if path.is_dir():
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return path.stat().st_size


def find_media_orphans(min_age_seconds=None, now=None):
    """[(path, size in bytes)] of the entries under MEDIA_ROOT that belong to no row."""
    min_age = settings.ORPHAN_CLEANUP_MIN_AGE if min_age_seconds is None else min_age_seconds
    now = time.time() if now is None else now
    root = Path(settings.MEDIA_ROOT)
    if not root.is_dir():
        return []

    # Listed before the rows are read: an upload that starts after this is not in the listing,
    # and one that was in it has its row by the time the IDs are read or is too young anyway.
    entries = []
    for first in sorted(root.iterdir()):
        if not (first.is_dir() and _SHARD.match(first.name)):
            continue
        for second in sorted(first.iterdir()):
            if not (second.is_dir() and _SHARD.match(second.name)):
                continue
            for entry in sorted(second.iterdir()):
                match = _ID.match(entry.name)
                # the name must start with an ID that belongs into this folder
                if match and match.group(0)[:2] == first.name and match.group(0)[2:4] == second.name:
                    entries.append((entry, match.group(0)))

    known = _known_ids()
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


def cleanup_media_orphans(delete=None, min_age_seconds=None):
    """Report the orphans under MEDIA_ROOT and, if `delete`, remove them.

    `delete` defaults to settings.ORPHAN_CLEANUP_DELETE. Returns (count, bytes) of the
    orphans found; every one is logged as media.orphan with its path and whether it was removed.
    """
    delete = settings.ORPHAN_CLEANUP_DELETE if delete is None else delete
    orphans = find_media_orphans(min_age_seconds)
    if delete and orphans and not _any_rows():
        # An empty table next to a full media folder is a wrong database (fresh volume, wrong
        # env file), not a folder full of orphans.
        logger.error("Orphan cleanup refuses to delete: no video or tracking data row exists")
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
        log_event(logger, "media.orphan", path=str(path), size=size, removed=removed)
    total = sum(size for _, size in orphans)
    log_event(logger, "media.orphans", count=len(orphans), size=total, delete=bool(delete))
    return len(orphans), total
