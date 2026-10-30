"""Endpoints fixed from docs/todos/BACKEND.md › API conventions (2026-10-30)."""
import json
import uuid

import pytest

from backend.models import Annotation, AnnotationCategory, CalibrationAssets, ClusterItem, VideoAnalysisState


def post(client, path, body):
    return client.post(f"/{path}", json.dumps(body), content_type="application/json")


@pytest.fixture
def alice(as_user):
    return as_user("alice")


@pytest.mark.parametrize("path, ref", [
    ("video/analysis/setselectedshots", lambda w: {"timeline_id": w.timeline.id.hex}),
    ("video/analysis/setselectedplaceclustering", lambda w: {"plugin_run_id": w.plugin_run.id.hex}),
    ("video/analysis/setselectedfaceclustering", lambda w: {"plugin_run_id": w.plugin_run.id.hex}),
])
def test_setselected_creates_a_missing_analysis_state(alice, world, path, ref):
    """Before: get_or_create(video__id=...) could not create the row and raised IntegrityError."""
    VideoAnalysisState.objects.filter(video=world.video).delete()

    post(alice, path, {"video_id": world.video.id.hex, **ref(world)})

    assert VideoAnalysisState.objects.filter(video=world.video).exists()


def test_calibration_asset_delete_with_object_data(alice, world):
    """Before: the asset was deleted, then .delete() on the request's dicts failed and answered error."""
    r = post(alice, "calibration_assets/delete", {"id": world.calibration.id.hex, "object_data": [{"x": 1}]})

    assert r.json()["status"] == "ok"
    assert not CalibrationAssets.objects.filter(id=world.calibration.id).exists()


def test_cluster_item_delete_reports_only_deleted_items(alice, world):
    unknown = uuid.uuid4().hex
    r = post(alice, "cluster/item/delete", {"item_ids": [world.cluster_item.id.hex, unknown], "cluster_id": world.cluster.id.hex})

    assert r.json()["entries"] == [world.cluster_item.id.hex]
    assert not ClusterItem.objects.exists()


def test_cluster_item_delete_of_someone_elses_item_reports_nothing(as_user, world):
    bob = as_user("bob")
    r = post(bob, "cluster/item/delete", {"item_ids": [world.cluster_item.id.hex], "cluster_id": world.cluster.id.hex})

    assert r.json()["entries"] == []
    assert ClusterItem.objects.filter(id=world.cluster_item.id).exists()


@pytest.mark.parametrize("path", ["timeline/segment/annotation/create", "timeline/segment/annotation/toggle"])
@pytest.mark.parametrize("category", [
    lambda w: {"annotation_category_id": w.category.id.hex},
    lambda w: {"annotation_category_name": "new category"},
])
def test_annotations_created_by_name_belong_to_the_caller(alice, world, path, category):
    """The legacy annotation_name branches created annotations and categories without an owner."""
    post(alice, path, {"timeline_segment_id": world.segment.id.hex, "annotation_name": "pass", **category(world)})

    annotation = Annotation.objects.get(name="pass")
    assert (annotation.owner, annotation.video) == (world.alice, world.video)
    assert (annotation.category.owner, annotation.category.video) == (world.alice, world.video)
    assert annotation in Annotation.objects.filter(owner=world.alice)
    assert AnnotationCategory.objects.filter(owner__isnull=True).count() == 0
