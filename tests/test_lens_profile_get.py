"""lens_profile/get returns one lens profile by id, e.g. to pre-fill the picker with a video's profile."""
import uuid

import pytest

from backend.models import LensProfile, SportVidUser, Video


def _profile(**fields):
    defaults = dict(
        key=f"GoPro/{uuid.uuid4().hex}.json", name="HERO9 Wide", group="action", brand="GoPro", model="HERO9 Black",
        calib_width=1920, calib_height=1080, camera_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        distortion_coeffs=[0, 0, 0, 0], source_commit="abc", raw={},
    )
    return LensProfile.objects.create(**{**defaults, **fields})


@pytest.fixture
def alice(db, client):
    user = SportVidUser.objects.create_user("alice", "a@example.org", "Correct-Horse-Battery-42")
    client.force_login(user)
    return user


def test_returns_the_profile(client, alice):
    profile = _profile()
    r = client.get("/lens_profile/get", {"id": profile.id.hex}).json()
    assert r["status"] == "ok"
    assert r["entry"] == profile.to_dict()


def test_with_video_adds_the_per_video_fields(client, alice):
    profile = _profile()
    video = Video.objects.create(owner=alice, name="v", ext=".mp4", width=3840, height=2160, lens_profile=profile)
    entry = client.get("/lens_profile/get", {"id": profile.id.hex, "video_id": video.id.hex}).json()["entry"]
    assert entry["compatible"] is True
    assert entry["aspect_fit"] is not None
    assert "recording_modes" in entry


def test_unsupported_profile_is_still_returned(client, alice):
    profile = _profile(unsupported_reason="SuperView")
    entry = client.get("/lens_profile/get", {"id": profile.id.hex}).json()["entry"]
    assert entry["supported"] is False
    assert entry["unsupported_reason"] == "SuperView"


@pytest.mark.parametrize("profile_id", [uuid.uuid4().hex, "not-a-uuid"])
def test_unknown_id(client, alice, profile_id):
    assert client.get("/lens_profile/get", {"id": profile_id}).json() == {"status": "error", "type": "not_exist"}


def test_missing_id(client, alice):
    assert client.get("/lens_profile/get").json()["type"] == "missing_values"


def test_other_users_video_is_not_exist(client, alice):
    bob = SportVidUser.objects.create_user("bob", "b@example.org", "Correct-Horse-Battery-42")
    video = Video.objects.create(owner=bob, name="v", ext=".mp4", width=1920, height=1080)
    r = client.get("/lens_profile/get", {"id": _profile().id.hex, "video_id": video.id.hex}).json()
    assert r == {"status": "error", "type": "not_exist"}


def test_requires_login(client, db):
    assert client.get("/lens_profile/get", {"id": _profile().id.hex}).json()["type"] == "not_authenticated"
