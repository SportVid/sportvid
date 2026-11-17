"""The scheduled cleanup of plugin results under DATA_OUTPUT_PATH that belong to no row.

Results live under DATA_OUTPUT_PATH (/predictions). A result is <data_id>.zip; an image result's images are also extracted next to it as
<image_id>.jpg (thumbnails, faces), which the frontend loads directly.
"""
import os
import time
import uuid
from pathlib import Path

import numpy as np
import pytest
from django.core.management import call_command

from backend.cleanup import cleanup_prediction_orphans, find_prediction_orphans
from backend.models import ClusterItem, ClusterTimelineItem, PluginRun, PluginRunResult
from data import DataManager
from tests.factories import make_run, make_user, make_video

DAY = 24 * 3600
OLD = time.time() - 3 * DAY


@pytest.fixture
def predictions(db, settings, tmp_path):
    # DataManager paths are redirected into the test data root (conftest); one folder per test
    manager = DataManager(f"/{tmp_path.name}/predictions/")
    settings.DATA_OUTPUT_PATH = manager.data_dir
    settings.MEDIA_ROOT = f"{tmp_path}/media/"
    settings.PLUGIN_RUN_TIMEOUT = 12 * 3600
    settings.ORPHAN_CLEANUP_MIN_AGE = DAY
    return manager


@pytest.fixture
def run(db):
    return make_run(make_video(make_user()), type="thumbnail", status=PluginRun.STATUS_DONE)


def age(paths, when=OLD):
    for path in paths:
        os.utime(path, (when, when))
    return paths


def files(manager):
    return sorted(str(p) for p in Path(manager.data_dir).rglob("*") if p.is_file())


def store_scalar(manager):
    with manager.create_data("ScalarData") as data:
        data.y, data.time, data.delta_time = np.array([0.5]), np.array([0.0]), 1.0
    return data.id


def store_images(manager, count=2):
    """An image result, extracted like the thumbnail task does; returns (data ID, jpg paths)."""
    with manager.create_data("ImagesData") as data:
        for i in range(count):
            data.save_image(np.zeros((8, 8, 3), dtype=np.uint8), time=float(i))
    with manager.load(data.id) as loaded:
        loaded.extract_all(manager)
        jpgs = [manager._create_file_path(image.id, image.ext) for image in loaded.images]
    return data.id, jpgs


def zip_path(manager, data_id):
    return manager._create_data_path(data_id)


def found(**kwargs):
    return sorted(str(path) for path, _ in find_prediction_orphans(**kwargs))


def test_results_and_their_images_are_kept(predictions, run):
    scalar = store_scalar(predictions)
    images, jpgs = store_images(predictions)
    PluginRunResult.objects.create(plugin_run=run, name="s", data_id=scalar, type=PluginRunResult.TYPE_SCALAR)
    PluginRunResult.objects.create(plugin_run=run, name="images", data_id=images, type=PluginRunResult.TYPE_IMAGES)
    age(files(predictions))

    assert found() == []


def test_face_images_referenced_by_cluster_items_are_kept(predictions, run):
    """Face clustering extracts images from data it keeps no result row for."""
    images, jpgs = store_images(predictions, count=1)
    result = PluginRunResult.objects.create(plugin_run=run, name="clusters", data_id=store_scalar(predictions),
                                            type=PluginRunResult.TYPE_SCALAR)
    timeline = ClusterTimelineItem.objects.create(plugin_run=run, video=run.video, name="faces")
    ClusterItem.objects.create(cluster_timeline_item=timeline, video=run.video, embedding_id="e",
                               image_path=f"/thumbnails/{jpgs[0][-45:]}", plugin_run_result=result,
                               time=0.0, delta_time=1.0)
    age(files(predictions))

    assert found() == [zip_path(predictions, images)]  # the images' own result was never kept


def test_results_of_deleted_runs_are_orphans(predictions, run):
    """A run or result removed without its files (here: bypassing post_delete) leaves everything behind."""
    scalar = store_scalar(predictions)
    images, jpgs = store_images(predictions)
    kept = store_scalar(predictions)
    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=kept, type=PluginRunResult.TYPE_SCALAR)
    age(files(predictions))

    assert found() == sorted([zip_path(predictions, scalar), zip_path(predictions, images), *jpgs])


def test_a_task_that_failed_before_its_rows_leaves_orphans(predictions, run):
    """Downloaded, then the task died before PluginRunResult.objects.create()."""
    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=store_scalar(predictions),
                                   type=PluginRunResult.TYPE_SCALAR)
    stray = store_scalar(predictions)
    partial = zip_path(predictions, uuid.uuid4().hex) + ".partial-1a2b3c4d"  # an interrupted download
    Path(partial).parent.mkdir(parents=True, exist_ok=True)
    Path(partial).write_bytes(b"\x00" * 10)
    age(files(predictions))

    assert found() == sorted([zip_path(predictions, stray), partial])


def test_results_of_a_running_task_are_left_alone(predictions, run, settings):
    """A task downloads results before it creates their rows, and may run PLUGIN_RUN_TIMEOUT long:
    the minimum age never drops below that."""
    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=store_scalar(predictions),
                                   type=PluginRunResult.TYPE_SCALAR)
    stray = store_scalar(predictions)
    age([zip_path(predictions, stray)], time.time() - 11 * 3600)

    assert found(min_age_seconds=60) == []
    settings.PLUGIN_RUN_TIMEOUT = 10 * 3600
    assert found(min_age_seconds=60) == [zip_path(predictions, stray)]


def test_images_of_an_unreadable_result_are_orphans(predictions, run):
    """The backend reaches the images only through their result; if that is broken, so are they."""
    images, jpgs = store_images(predictions, count=1)
    PluginRunResult.objects.create(plugin_run=run, name="images", data_id=images, type=PluginRunResult.TYPE_IMAGES)
    Path(zip_path(predictions, images)).write_bytes(b"not a zip")
    age(files(predictions))

    assert found() == jpgs


def test_an_io_error_on_an_image_result_stops_the_pass(predictions, run, monkeypatch, settings):
    import zipfile

    settings.ORPHAN_CLEANUP_DELETE = True
    images, jpgs = store_images(predictions, count=1)
    PluginRunResult.objects.create(plugin_run=run, name="images", data_id=images, type=PluginRunResult.TYPE_IMAGES)
    age(files(predictions))

    def io_error(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(zipfile, "ZipFile", io_error)

    with pytest.raises(PermissionError):
        cleanup_prediction_orphans()
    assert all(os.path.exists(path) for path in jpgs)


def test_orphans_are_removed_when_deleting_is_on(predictions, run, settings):
    settings.ORPHAN_CLEANUP_DELETE = True
    kept, kept_jpgs = store_images(predictions)
    PluginRunResult.objects.create(plugin_run=run, name="images", data_id=kept, type=PluginRunResult.TYPE_IMAGES)
    gone, gone_jpgs = store_images(predictions)
    age(files(predictions))

    count, _ = cleanup_prediction_orphans()

    assert count == 3
    assert files(predictions) == sorted([zip_path(predictions, kept), *kept_jpgs])


def test_orphans_are_only_reported_by_default(predictions, run):
    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=store_scalar(predictions),
                                   type=PluginRunResult.TYPE_SCALAR)
    stray = store_scalar(predictions)
    age(files(predictions))

    assert cleanup_prediction_orphans()[0] == 1
    assert os.path.exists(zip_path(predictions, stray))


def test_nothing_is_deleted_without_any_result_row(predictions, settings, caplog):
    settings.ORPHAN_CLEANUP_DELETE = True
    stray = store_scalar(predictions)
    age(files(predictions))

    assert cleanup_prediction_orphans()[0] == 1
    assert os.path.exists(zip_path(predictions, stray))
    assert "refuses to delete" in caplog.text


def test_anything_outside_the_layout_is_ignored(predictions, run):
    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=store_scalar(predictions),
                                   type=PluginRunResult.TYPE_SCALAR)
    root = Path(predictions.data_dir)
    gone = uuid.uuid4().hex
    (root / gone).mkdir()                                   # a video asset folder sits at the top
    (root / gone / "index.m3u8").write_bytes(b"#EXTM3U")
    (root / "notes.txt").write_bytes(b"x")
    age(files(predictions) + [str(root / gone)])

    assert found() == []


def test_the_scheduled_task_and_command_cover_both_folders(predictions, run, capsys):
    from backend.tasks.convert_video import cleanup_orphans

    PluginRunResult.objects.create(plugin_run=run, name="k", data_id=store_scalar(predictions),
                                   type=PluginRunResult.TYPE_SCALAR)
    stray = store_scalar(predictions)
    age(files(predictions))
    size = os.path.getsize(zip_path(predictions, stray))

    assert cleanup_orphans() == {"media": {"count": 0, "size": 0}, "predictions": {"count": 1, "size": size}}

    call_command("cleanup_orphans", store="predictions")
    assert zip_path(predictions, stray) in capsys.readouterr().out
    call_command("cleanup_orphans", store="predictions", delete=True)
    assert not os.path.exists(zip_path(predictions, stray))
