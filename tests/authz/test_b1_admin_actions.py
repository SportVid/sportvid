"""B1: only admins may use the admin branches of user/update, user/delete and user/admin/user/list."""
import json

import pytest

from backend.models import SportVidUser


def post_json(client, path, payload):
    return client.post(path, json.dumps(payload), content_type="application/json")


@pytest.mark.parametrize("caller", ["bob", "rita"])
def test_non_admin_cannot_promote_themselves(as_user, world, caller):
    user = getattr(world, caller)
    response = post_json(as_user(caller), "/user/update", {"params": {"update_type": "admin", "id": user.id, "role": "admin"}})
    assert response.status_code == 403
    user.refresh_from_db()
    assert user.role != "admin"


@pytest.mark.parametrize("caller", ["bob", "rita"])
def test_non_admin_cannot_change_other_users(as_user, world, caller):
    response = post_json(as_user(caller), "/user/update", {"params": {"update_type": "admin", "id": world.alice.id, "max_video_size": 1}})
    assert response.status_code == 403
    world.alice.refresh_from_db()
    assert world.alice.max_video_size != 1


@pytest.mark.parametrize("caller", ["bob", "rita"])
def test_non_admin_cannot_delete_other_users(as_user, world, caller):
    response = post_json(as_user(caller), "/user/delete", {"params": {"update_type": "admin", "id": world.alice.id}})
    assert response.status_code == 403
    assert SportVidUser.objects.filter(id=world.alice.id).exists()


@pytest.mark.parametrize("caller", [None, "bob", "rita"])
def test_user_list_is_admin_only(as_user, world, caller):
    response = as_user(caller).get("/user/admin/user/list")
    assert response.json()["status"] == "error"
    assert "alice" not in response.content.decode()


def test_admin_can_list_users(as_user, world):
    response = as_user("adam").get("/user/admin/user/list")
    assert response.json()["status"] == "ok"
