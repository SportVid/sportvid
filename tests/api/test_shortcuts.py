"""shortcut/create and annotation/shortcut/create (both always failed before 2026-10-30)."""
import json

from backend.models import AnnotationShortcut, Shortcut


def post(client, path, body):
    return client.post(f"/{path}", json.dumps(body), content_type="application/json")


def test_shortcut_create_from_the_store_key_string(as_user, world):
    alice = as_user("alice")
    r = post(alice, "shortcut/create", {"key": "Ctrl+A", "video_id": world.video.id.hex})

    assert r.json()["status"] == "ok"
    shortcut = Shortcut.objects.get(id=r.json()["entry"]["id"])
    assert (shortcut.owner, shortcut.video, shortcut.keys_string) == (world.alice, world.video, "ctrl+a")
    # the same keys again give the same shortcut
    again = post(alice, "shortcut/create", {"keys": ["a", "ctrl"], "video_id": world.video.id.hex})
    assert again.json()["entry"]["id"] == shortcut.id.hex


def test_shortcut_create_without_a_video(as_user, world):
    r = post(as_user("alice"), "shortcut/create", {"keys": ["x"]})
    assert r.json()["status"] == "ok"
    assert r.json()["entry"]["video_id"] is None


def test_shortcut_create_needs_keys(as_user, world):
    for body in ({}, {"keys": []}, {"keys": [""]}, {"key": 3}):
        assert post(as_user("alice"), "shortcut/create", body).json()["type"] == "missing_values"


def test_annotation_shortcut_create_binds_keys_to_the_annotation(as_user, world):
    alice = as_user("alice")
    body = {"annotation_id": world.annotation2.id.hex, "keys": ["shift", "b"], "video_id": world.video.id.hex}
    r = post(alice, "annotation/shortcut/create", body)

    assert r.json()["status"] == "ok"
    binding = AnnotationShortcut.objects.get(annotation=world.annotation2)
    assert r.json()["entry"]["id"] == binding.id.hex
    assert r.json()["shortcut"]["id"] == binding.shortcut.id.hex
    assert (binding.shortcut.keys_string, binding.shortcut.type) == ("shift+b", "annotation")

    # new keys replace the annotation's binding instead of adding a second one
    post(alice, "annotation/shortcut/create", {**body, "keys": ["c"]})
    assert AnnotationShortcut.objects.get(annotation=world.annotation2).shortcut.keys_string == "c"


def test_annotation_shortcut_create_and_update_share_shortcuts(as_user, world):
    """Both endpoints reuse the user's shortcut for the same keys and video."""
    alice = as_user("alice")
    post(alice, "annotation/shortcut/create",
         {"annotation_id": world.annotation2.id.hex, "keys": ["a"], "video_id": world.video.id.hex})

    assert AnnotationShortcut.objects.get(annotation=world.annotation2).shortcut == world.shortcut


def test_annotation_shortcut_create_for_another_users_annotation(as_user, world):
    r = post(as_user("bob"), "annotation/shortcut/create",
             {"annotation_id": world.annotation2.id.hex, "keys": ["z"]})

    assert r.json()["type"] == "not_exist"
    assert not AnnotationShortcut.objects.filter(annotation=world.annotation2).exists()
    assert not Shortcut.objects.filter(owner=world.bob).exists()
