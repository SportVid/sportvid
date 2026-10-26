"""Characterization: account flows that the password/approval changes must keep working."""
import json

import pytest

from backend.models import SportVidUser

STRONG = "Correct-Horse-Battery-42"


def post(client, path, params):
    return client.post(path, json.dumps({"params": params}), content_type="application/json")


@pytest.fixture
def alice(db):
    return SportVidUser.objects.create_user("alice", "alice@example.org", STRONG)


def test_login_with_correct_password(client, alice):
    r = post(client, "/user/login", {"name": "alice", "password": STRONG})
    assert r.json()["status"] == "ok" and r.json()["data"]["username"] == "alice"


def test_login_with_wrong_password(client, alice):
    r = post(client, "/user/login", {"name": "alice", "password": "nope"})
    assert r.json() == {"status": "error", "message": "Invalid login credentials"}


def test_password_change(client, alice):
    client.force_login(alice)
    r = post(client, "/user/update", {"password_current": STRONG, "password_new": "Another-Strong-Pass-7"})
    assert r.json()["status"] == "ok"
    alice.refresh_from_db()
    assert alice.check_password("Another-Strong-Pass-7")


def test_register_with_existing_name(client, alice):
    r = post(client, "/user/register", {"name": "alice", "password": STRONG, "email": "a@b.c"})
    assert r.json() == {"status": "error", "message": "User already exists"}


def test_admin_update_returns_the_user(client, alice):
    admin = SportVidUser.objects.create_user("adam", "adam@example.org", STRONG)
    admin.role = "admin"
    admin.save()
    client.force_login(admin)
    r = post(client, "/user/update", {"update_type": "admin", "id": alice.id, "max_video_size": 5})
    assert r.json()["status"] == "ok"
    assert {"id", "username", "email", "role", "max_video_size"} <= set(r.json()["data"])
