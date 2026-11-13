"""The scheduled cleanup of files under MEDIA_ROOT that belong to no row."""
import os
import time
import uuid

import pytest
from django.core.management import call_command

from backend.cleanup import cleanup_media_orphans, find_media_orphans
from backend.models import TrackingData
from backend.utils import media_dir_to_file, media_path_to_file
from tests.factories import make_user, make_video

OLD = time.time() - 3 * 24 * 3600


def put(path, age=OLD, directory=False):
    if directory:
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "init.mp4"), "wb") as f:
            f.write(b"\x00" * 10)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\x00" * 10)
    os.utime(path, (age, age))
    return path


@pytest.fixture
def media(db, settings, tmp_path):
    settings.MEDIA_ROOT = f"{tmp_path}/media/"
    os.makedirs(settings.MEDIA_ROOT)
    return settings.MEDIA_ROOT


def found(**kwargs):
    return sorted(str(path) for path, _ in find_media_orphans(**kwargs))


def test_files_of_existing_rows_are_kept(media):
    video = make_video(make_user())
    tracking = TrackingData.objects.create(owner=video.owner, video=video, name="td", ext=".csv",
                                           meta_file=uuid.uuid4(), meta_ext=".xml")
    put(media_path_to_file(video.id.hex, ".tar.gz"))
    put(media_path_to_file(video.id.hex, ".mp4"))
    put(media_dir_to_file(video.id.hex) + video.id.hex, directory=True)
    put(media_path_to_file(tracking.id.hex, ".csv"))
    put(media_path_to_file(tracking.meta_file.hex, ".xml"))

    assert found() == []


def test_files_and_folders_without_a_row_are_orphans(media):
    gone = uuid.uuid4().hex
    archive = put(media_path_to_file(gone, ".tar.gz"))
    partial = put(media_path_to_file(gone, ".tar.gz.partial"))
    folder = put(media_dir_to_file(gone) + gone, directory=True)

    assert found() == sorted([archive, partial, folder])
    assert dict((str(p), s) for p, s in find_media_orphans())[folder] == 10


def test_young_entries_are_left_alone(media):
    """An upload writes its file before its row exists."""
    put(media_path_to_file(uuid.uuid4().hex, ".mp4"), age=time.time() - 60)
    assert found() == []
    assert len(found(min_age_seconds=30)) == 1


def test_anything_that_is_not_an_upload_is_ignored(media):
    gone = uuid.uuid4().hex
    put(os.path.join(media, "README.txt"))
    put(os.path.join(media, "backup", "2026", f"{gone}.mp4"))                # not the xx/yy layout
    put(os.path.join(media, gone[:2], gone[2:4], "notes.txt"))               # no ID
    put(os.path.join(media, "ff", "ff", f"{'0' * 32}.mp4"))                  # ID does not belong into this folder
    assert found() == []


def test_orphans_are_only_reported_by_default(media, caplog):
    orphan = put(media_path_to_file(uuid.uuid4().hex, ".mp4"))
    caplog.set_level("INFO", logger="backend")

    assert cleanup_media_orphans() == (1, 10)

    assert os.path.exists(orphan)
    [event] = [r for r in caplog.records if r.msg == "media.orphan"]
    assert (event.log_fields["path"], event.log_fields["removed"]) == (orphan, "false")


def test_orphans_are_removed_when_deleting_is_on(media, settings):
    settings.ORPHAN_CLEANUP_DELETE = True
    video = make_video(make_user())
    kept = put(media_path_to_file(video.id.hex, ".tar.gz"))
    gone = uuid.uuid4().hex
    orphan_file = put(media_path_to_file(gone, ".mp4"))
    orphan_dir = put(media_dir_to_file(gone) + gone, directory=True)

    assert cleanup_media_orphans() == (2, 20)

    assert os.path.exists(kept)
    assert not os.path.exists(orphan_file) and not os.path.exists(orphan_dir)


def test_the_scheduled_task_follows_the_setting(media):
    from backend.tasks.convert_video import cleanup_orphans

    orphan = put(media_path_to_file(uuid.uuid4().hex, ".mp4"))
    assert cleanup_orphans() == {"count": 1, "size": 10}
    assert os.path.exists(orphan)


def test_the_command_lists_and_deletes_only_on_request(media, capsys):
    orphan = put(media_path_to_file(uuid.uuid4().hex, ".mp4"))

    call_command("cleanup_orphans")
    assert orphan in capsys.readouterr().out and os.path.exists(orphan)

    call_command("cleanup_orphans", delete=True)
    assert not os.path.exists(orphan)


def test_beat_schedules_a_registered_task(settings):
    from sportvid.celery import app
    import backend.tasks  # noqa: F401

    for entry in settings.CELERY_BEAT_SCHEDULE.values():
        assert entry["task"] in app.tasks, entry["task"]
