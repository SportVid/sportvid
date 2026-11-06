"""osnet_reid parameters: the API defaults, the UI's parameter set, the checkpoint following the model."""
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


def test_api_defaults():
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
    for bad in ("/etc/passwd", "/models/reid/osnet_ain_ms_d_c.pt.tarh"):
        s = OSNetReIdentificationSerializer(data={"object_tracker_id": TRACKER_RUN, "checkpoint": bad})
        assert not s.is_valid() and "checkpoint" in s.errors, bad


def test_reid_preset_replaces_model_name_and_checkpoint():
    data = validate({**UI_PARAMS, "reid_preset": "deit_l_sportsreid"})
    assert (data["model_name"], data["checkpoint"]) == ("deit_l_16_ls", "/models/reid/model_soup.deit_l.pth")
    assert data["reid_amp"] and (data["crop_size_x"], data["crop_size_y"]) == (224, 224)
    data = validate({"object_tracker_id": TRACKER_RUN, "reid_preset": "osnet_sportsmot"})
    assert (data["model_name"], data["checkpoint"]) == ("osnet_x1_0", "/models/reid/sports_model.pth.tar-60")


def test_model_name_alone_maps_to_its_preset():
    data = validate({"object_tracker_id": TRACKER_RUN, "model_name": "osnet_ibn_x1_0"})
    assert data["reid_preset"] == "osnet_ibn" and not data["reid_amp"]
    assert data["checkpoint"] == "/models/reid/osnet_ibn_ms_d_c.pth.tar"
