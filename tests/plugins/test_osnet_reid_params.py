"""osnet_reid parameters: the evaluated defaults, the UI's parameter set, the checkpoint following the model."""
import uuid

from backend.serializers.osnet_reid import MODEL_CHECKPOINT, OSNetReIdentificationSerializer

TRACKER_RUN = str(uuid.uuid4())
# the shape the frontend sends (usePluginParams.js, its default values)
UI_PARAMS = {
    "object_tracker_id": TRACKER_RUN, "gallery_mode": "protos", "model_name": "osnet_x1_0",
    "checkpoint": "/models/reid/osnet_x1_0_ms_d_c.pth.tar", "match_thresh": 0.72, "update_threshold": 0.85,
    "ema_alpha": 0.98, "margin": 0.06, "prototype_weight": 0.7, "cache_weight": 0.3, "cache_size": 10,
    "max_missed": 120, "crop_size_x": 128, "crop_size_y": 256,
    "crop_x1_offset": 0, "crop_y1_offset": 0, "crop_x2_offset": 0, "crop_y2_offset": 0,
}


def validate(params):
    s = OSNetReIdentificationSerializer(data=params)
    assert s.is_valid(), s.errors
    return s.validated_data


def test_api_defaults_are_the_evaluated_settings():
    data = validate({"object_tracker_id": TRACKER_RUN})
    assert data["model_name"] == "osnet_ain_x1_0"
    assert data["checkpoint"] == "/models/reid/osnet_ain_ms_d_c.pth.tar"
    assert (data["match_thresh"], data["update_threshold"], data["ema_alpha"]) == (0.6, 0.88, 0.99)
    assert (data["max_missed"], data["active_ttl"], data["lost_ttl"]) == (150, 30, 300)
    assert data["reentry_threshold"] == 0.55 and data["spatial_gate_px"] == 150.0 and data["use_spatial_gate"]
    assert data["keep_tracker_binding"]
    assert (data["min_box_w"], data["min_box_h"]) == (16, 32)


def test_ui_parameters_are_kept():
    data = validate(UI_PARAMS)
    for key, value in UI_PARAMS.items():
        if key != "object_tracker_id":
            assert data[key] == value, key


def test_checkpoint_follows_the_model():
    # the frontend sends osnet_x1_0's checkpoint for every model it offers
    for model in ("osnet_ibn_x1_0", "osnet_ain_x1_0"):
        data = validate({**UI_PARAMS, "model_name": model})
        assert data["checkpoint"] == MODEL_CHECKPOINT[model]


def test_checkpoints_exist_under_their_real_names():
    assert all(path.endswith(".pth.tar") for path in MODEL_CHECKPOINT.values())
    s = OSNetReIdentificationSerializer(data={"object_tracker_id": TRACKER_RUN, "checkpoint": "/etc/passwd"})
    assert not s.is_valid() and "checkpoint" in s.errors
