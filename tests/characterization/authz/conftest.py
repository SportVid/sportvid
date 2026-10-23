"""A small "world" of users and objects for the access-control tests.

alice owns one video with one object of every kind. bob is another normal user, rita a
researcher and adam an admin. Every test gets a fresh world.
"""
import types
import uuid

import pytest
from django.apps import apps


def _make_user(username, role):
    from backend.models import SportVidUser

    user = SportVidUser.objects.create_user(username, f"{username}@example.org", "pw")
    user.role = role
    user.save()
    return user


@pytest.fixture
def world(db):
    from backend.models import (
        Annotation, AnnotationCategory, AnnotationShortcut, CalibrationAssets, ClusterItem,
        ClusterTimelineItem, PluginRun, PluginRunResult, Shortcut, Timeline, TimelineSegment,
        TimelineSegmentAnnotation, TrackingData, Video, VideoAnalysisState,
    )

    w = types.SimpleNamespace()
    w.alice = _make_user("alice", "user")
    w.bob = _make_user("bob", "user")
    w.rita = _make_user("rita", "researcher")
    w.adam = _make_user("adam", "admin")

    w.video = Video.objects.create(owner=w.alice, name="alice video", ext=".mp4", duration=10.0, fps=25.0)
    w.bob_video = Video.objects.create(owner=w.bob, name="bob video", ext=".mp4", duration=10.0, fps=25.0)

    w.timeline = Timeline.objects.create(video=w.video, name="annotations", type=Timeline.TYPE_ANNOTATION)
    w.segment = TimelineSegment.objects.create(timeline=w.timeline, start=0.0, end=5.0)
    w.segment2 = TimelineSegment.objects.create(timeline=w.timeline, start=5.0, end=10.0)

    w.category = AnnotationCategory.objects.create(owner=w.alice, video=w.video, name="cat")
    w.annotation = Annotation.objects.create(owner=w.alice, video=w.video, category=w.category, name="ann")
    w.annotation2 = Annotation.objects.create(owner=w.alice, video=w.video, category=w.category, name="ann2")
    w.segment_annotation = TimelineSegmentAnnotation.objects.create(timeline_segment=w.segment, annotation=w.annotation)

    w.tracking_data = TrackingData.objects.create(owner=w.alice, video=w.video, name="td", ext=".csv", file_size=10)
    w.bob_tracking_data = TrackingData.objects.create(owner=w.bob, video=w.bob_video, name="bob td", ext=".csv", file_size=10)

    # A finished object-tracker run with one stored frame: player 1 of team 3 in frame "0".
    from data import DataManager
    with DataManager("/predictions/").create_data("BboxesData") as bboxes:
        bboxes.bboxes = '{"0": [[1, 3, 0.1, 0.1, 0.2, 0.2]]}'
        bboxes.meta_data = "{}"
    w.plugin_run = PluginRun.objects.create(video=w.video, type="object_tracker", status=PluginRun.STATUS_DONE)
    w.result = PluginRunResult.objects.create(
        plugin_run=w.plugin_run, name="tracklets", data_id=bboxes.id, type=PluginRunResult.TYPE_BBOXES
    )
    w.cluster = ClusterTimelineItem.objects.create(plugin_run=w.plugin_run, video=w.video, name="c1", type="A", cluster_id=uuid.uuid4())
    w.cluster2 = ClusterTimelineItem.objects.create(plugin_run=w.plugin_run, video=w.video, name="c2", type="A", cluster_id=uuid.uuid4())
    w.cluster_item = ClusterItem.objects.create(
        cluster_timeline_item=w.cluster, video=w.video, embedding_id="e1", plugin_run_result=w.result,
        time=1.0, delta_time=0.04,
    )

    # The frontend calls video/analysis/get (which creates this row) before any setter;
    # the setters crash without it (see the findings in docs/todos/BACKEND.md).
    w.analysis_state = VideoAnalysisState.objects.create(video=w.video)

    w.calibration = CalibrationAssets.objects.create(owner=w.alice, video=w.video, name="cal")
    w.shortcut = Shortcut.objects.create(owner=w.alice, video=w.video, type="annotation", keys=["a"], keys_string="a")
    w.annotation_shortcut = AnnotationShortcut.objects.create(shortcut=w.shortcut, annotation=w.annotation)

    # Every id that belongs to alice and must never reach bob or anonymous users.
    w.alice_ids = {
        obj.id.hex for obj in (
            w.video, w.timeline, w.segment, w.segment2, w.category, w.annotation, w.annotation2,
            w.segment_annotation, w.tracking_data, w.plugin_run, w.result, w.cluster, w.cluster2,
            w.cluster_item, w.calibration, w.shortcut, w.annotation_shortcut,
        )
    }
    return w


def db_fingerprint():
    """Every row of every backend model, used to prove that a request changed nothing."""
    rows = {}
    for model in apps.get_app_config("backend").get_models():
        rows[model.__name__] = sorted(
            (repr(sorted(r.items())) for r in model.objects.values()), key=str
        )
    return rows


@pytest.fixture
def as_user(client, world):
    """Log the test client in as one of the world's users (or nobody)."""
    def login(name):
        client.logout()
        if name is not None:
            client.force_login(getattr(world, name))
        return client
    return login
