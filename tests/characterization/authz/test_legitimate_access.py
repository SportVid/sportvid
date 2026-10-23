"""Characterization: legitimate access that the authorization fixes must keep working.

Pinned on the unchanged code (develop @ bfa2cf9): the HTTP status and the body's "status"
field for the video owner, an admin, and a researcher reading. Some pinned responses are
errors that already happen today for valid input (e.g. shortcut/create is broken); they
are pinned on purpose and tracked in docs/todos/BACKEND.md.
"""
import pytest

from .endpoints import ENDPOINTS

OWNER_RESPONSES = {
    "timeline/list": (200, "ok"),
    "timeline/segment/annotation/list": (200, "ok"),
    "cluster/timeline/item/fetch": (200, "ok"),
    "cluster/item/fetch": (200, "ok"),
    "video/analysis/get": (200, "ok"),
    "plugin/list": (200, "ok"),
    "plugin/run/result/list": (200, "ok"),
    "plugin/run/result/kpi/chunk": (404, "error"),
    "tracking_data/pos_data/chunk": (404, "error"),
    "annotation/shortcut/list": (200, "ok"),
    "video/export": (200, "ok"),
    "timeline/duplicate": (200, "ok"),
    "timeline/create": (200, "ok"),
    "timeline/rename": (200, "ok"),
    "timeline/changevisualization": (200, "ok"),
    "timeline/setparent": (200, "ok"),
    "timeline/setcollapse": (200, "ok"),
    "timeline/setorder": (200, "ok"),
    "timeline/delete": (200, "ok"),
    "timeline/import/eaf": (200, "error"),
    "timeline/segment/annotate": (200, "ok"),
    "timeline/segment/annotate/range": (200, "ok"),
    "timeline/segment/merge": (200, "ok"),
    "timeline/segment/split": (200, "ok"),
    "timeline/segment/annotation/create": (200, "ok"),
    "timeline/segment/annotation/toggle": (200, "ok"),
    "timeline/segment/annotation/delete": (200, "ok"),
    "annotation/create": (200, "ok"),
    "annotation/update": (200, "ok"),
    "annotation/category/create": (200, "ok"),
    "annotation/shortcut/update": (200, "ok"),
    "shortcut/create": (200, "error"),
    "position_data/bboxes/edit": (200, "ok"),
    "position_data/bboxes/replace": (200, "ok"),
    "position_data/bboxes/delete": (200, "ok"),
    "calibration_assets/create": (200, "ok"),
    "calibration_assets/update": (200, "ok"),
    "calibration_assets/delete": (200, "ok"),
    "cluster/timeline/item/create": (200, "ok"),
    "cluster/timeline/item/delete": (200, "ok"),
    "cluster/timeline/item/rename": (200, "ok"),
    "cluster/timeline/item/merge": (200, "ok"),
    "cluster/item/delete": (200, "ok"),
    "cluster/item/move": (200, "ok"),
    "video/analysis/setselectedshots": (200, "ok"),
    "video/analysis/setselectedplaceclustering": (500, "error"),
    "video/analysis/setselectedfaceclustering": (500, "error"),
    "tracking_data/rename": (200, "ok"),
    "plugin/run/new": (200, "ok"),
}


def _status(response):
    try:
        return response.json().get("status")
    except ValueError:
        return None


def test_every_endpoint_is_pinned():
    assert {e.path for e in ENDPOINTS} == set(OWNER_RESPONSES)


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: e.id)
def test_owner(endpoint, as_user, world):
    response, _ = endpoint.call(as_user("alice"), world)
    assert (response.status_code, _status(response)) == OWNER_RESPONSES[endpoint.path]


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: e.id)
def test_admin_has_owner_access(endpoint, as_user, world):
    response, _ = endpoint.call(as_user("adam"), world)
    assert (response.status_code, _status(response)) == OWNER_RESPONSES[endpoint.path]


@pytest.mark.parametrize("endpoint", [e for e in ENDPOINTS if e.kind == "read"], ids=lambda e: e.id)
def test_researcher_can_read(endpoint, as_user, world):
    response, _ = endpoint.call(as_user("rita"), world)
    assert (response.status_code, _status(response)) == OWNER_RESPONSES[endpoint.path]
