"""Characterization: legitimate uses of the code paths behind B1, B8 and B3."""
import json

import pytest

from backend.models import SportVidUser, TrackingData


def post_json(client, path, payload):
    return client.post(path, json.dumps(payload), content_type="application/json")


# ---------- B1: admin user management
def test_admin_can_change_another_users_role_and_limits(as_user, world):
    response = post_json(as_user("adam"), "/user/update", {
        "params": {"update_type": "admin", "id": world.bob.id, "role": "researcher", "max_video_size": 123},
    })
    assert response.json()["status"] == "ok"
    world.bob.refresh_from_db()
    assert (world.bob.role, world.bob.max_video_size) == ("researcher", 123)


def test_admin_can_delete_another_user(as_user, world):
    response = post_json(as_user("adam"), "/user/delete", {"params": {"update_type": "admin", "id": world.bob.id}})
    assert response.json()["status"] == "ok"
    assert not SportVidUser.objects.filter(id=world.bob.id).exists()


def test_user_can_update_own_email(as_user, world):
    response = post_json(as_user("bob"), "/user/update", {"params": {"email": "new@example.org"}})
    assert response.json()["status"] == "ok"
    world.bob.refresh_from_db()
    assert world.bob.email == "new@example.org"


# ---------- B8: deleting tracking data
def test_owner_can_delete_own_tracking_data(as_user, world):
    response = post_json(as_user("alice"), "/tracking_data/delete", {"id": world.tracking_data.id.hex})
    assert response.json()["status"] == "ok"
    assert not TrackingData.objects.filter(id=world.tracking_data.id).exists()


def test_delete_all_removes_the_callers_tracking_data(as_user, world):
    response = post_json(as_user("bob"), "/tracking_data/delete", {"id": "all"})
    assert response.json()["status"] == "ok"
    assert not TrackingData.objects.filter(owner=world.bob).exists()


# ---------- B3: model checkpoints the UI and the presets use
def _validate(plugin, parameters):
    from backend.plugin_manager import PluginManager

    return PluginManager.validate_parameters(plugin, parameters)


@pytest.mark.parametrize("detector", ["yolox", "yolo10", "yolo11", "yolo12", "yolo26", "rfdetr", "rtdetr"])
def test_detector_presets_validate(db, detector):
    from backend.serializers.object_tracker import DETECTOR_DEFAULTS

    params = _validate("object_tracker", {"detector": detector})
    assert params["detector_params"]["checkpoint"] == DETECTOR_DEFAULTS[detector]["checkpoint"]


@pytest.mark.parametrize("detector", ["yolo11", "rfdetr", "rtdetr"])
def test_detector_accepts_its_preset_checkpoint_explicitly(db, detector):
    from backend.serializers.object_tracker import DETECTOR_DEFAULTS

    checkpoint = DETECTOR_DEFAULTS[detector]["checkpoint"]
    params = _validate("object_tracker", {"detector": detector, "detector_params": {"checkpoint": checkpoint}})
    assert params["detector_params"]["checkpoint"] == checkpoint


@pytest.mark.parametrize("checkpoint", [
    # the values frontend/src/composables/usePluginParams.js sends
    "/models/reid/osnet_x1_0_ms_d_c.pth.tar",
    "/models/reid/osnet_ain_ms_d_c.pt.tarh",
    "/models/reid/osnet_ibn_ms_d_c.pth.tar",
])
def test_reid_accepts_frontend_checkpoints(world, checkpoint):
    params = _validate("osnet_reid", {"object_tracker_id": world.plugin_run.id.hex, "checkpoint": checkpoint})
    assert params["checkpoint"] == checkpoint
