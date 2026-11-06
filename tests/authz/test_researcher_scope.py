"""Researchers read other users' videos, timelines and runs, but for now only their own
timeline segments and annotations (permissions.RESEARCHER_OWN_ONLY, decided 2026-10-30)."""
import pytest

from backend.models import Annotation, AnnotationCategory, TimelineSegment


@pytest.mark.parametrize("path", [
    "timeline/segment/annotation/list",
    "timeline/segment/list",
    "annotation/list",
    "annotation/category/list",
    "annotation/shortcut/list",
])
def test_researcher_does_not_see_other_users_segments_and_annotations(as_user, world, path):
    response = as_user("rita").get(f"/{path}", {"video_id": world.video.id.hex})

    assert response.json()["status"] == "ok"
    assert response.json()["entries"] == []


def test_researcher_still_reads_other_users_timelines(as_user, world):
    response = as_user("rita").get("/timeline/list", {"video_id": world.video.id.hex})
    assert world.timeline.id.hex in response.content.decode()


def test_researcher_sees_own_annotations(as_user, world):
    category = AnnotationCategory.objects.create(owner=world.rita, video=world.video, name="rita cat")
    annotation = Annotation.objects.create(owner=world.rita, video=world.video, category=category, name="rita ann")

    response = as_user("rita").get("/annotation/list", {"video_id": world.video.id.hex})
    assert [e["id"] for e in response.json()["entries"]] == [annotation.id.hex]


def test_admin_sees_other_users_segment_annotations(as_user, world):
    response = as_user("adam").get("/timeline/segment/annotation/list", {"video_id": world.video.id.hex})
    assert world.segment_annotation.id.hex in response.content.decode()


def test_readable_scopes_segments_for_researchers_only(world):
    from backend.permissions import readable

    assert set(readable(TimelineSegment, world.rita)) == set()
    assert set(readable(TimelineSegment, world.adam)) == {world.segment, world.segment2}
