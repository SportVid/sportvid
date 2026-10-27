"""Clients cannot choose which model file a plugin loads."""
import pytest
from rest_framework import serializers

from backend.plugin_manager import PluginManager
from utils.model_paths import checked_model_path

ATTACKER_VALUES = [
    "/etc/passwd",
    "/data/uploaded.pt",
    "/models/../etc/passwd",
    "https://example.org/evil.pt",
    "yolo11x.pt",
    "/models/yolo_ultra/other.pt",
]


@pytest.mark.parametrize("value", ATTACKER_VALUES)
@pytest.mark.parametrize("detector", ["yolo11", "rfdetr", "rtdetr"])
def test_detector_rejects_non_preset_checkpoint(db, detector, value):
    with pytest.raises(serializers.ValidationError):
        PluginManager.validate_parameters("object_tracker", {"detector": detector, "detector_params": {"checkpoint": value}})


@pytest.mark.parametrize("key", ["model_path", "model_checkpoint"])
def test_yolox_rejects_custom_model_files(db, key):
    with pytest.raises(serializers.ValidationError):
        PluginManager.validate_parameters("object_tracker", {"detector": "yolox", "detector_params": {key: "/tmp/evil.pt"}})


@pytest.mark.parametrize("value", ATTACKER_VALUES)
def test_reid_rejects_unlisted_checkpoint(world, value):
    with pytest.raises(serializers.ValidationError):
        PluginManager.validate_parameters("osnet_reid", {"object_tracker_id": world.plugin_run.id.hex, "checkpoint": value})


def test_plugin_run_new_returns_400_for_custom_checkpoint(as_user, world, enqueued_tasks):
    import json

    response = as_user("alice").post("/plugin/run/new", json.dumps({
        "plugin": "object_tracker", "video_id": world.video.id.hex,
        "parameters": {"detector": "yolo11", "detector_params": {"checkpoint": "https://example.org/evil.pt"}},
    }), content_type="application/json")
    assert response.status_code == 400
    assert enqueued_tasks == []


# ---------- second line of defence inside Ray
@pytest.mark.parametrize("value", ["/models/yolo_ultra/yolo11x.pt", "/models/reid/osnet_x1_0_ms_d_c.pth.tar"])
def test_ray_guard_accepts_model_folder_paths(value):
    assert checked_model_path(value) == value


@pytest.mark.parametrize("value", ["/etc/passwd", "/models/../etc/passwd", "https://example.org/x.pt", "x.pt", "/modelsx/a.pt", "/models"])
def test_ray_guard_rejects_everything_else(value):
    with pytest.raises(ValueError):
        checked_model_path(value)
