"""object_tracker parameters: ByteTrack buffer default, the ball detector instance and the Kalman ball tracker."""
import pytest

from backend.serializers.object_tracker import (
    ObjectTrackerSerializer,
    DETECTOR_DEFAULTS,
    default_kalman_ball_params,
)


def validate(params):
    s = ObjectTrackerSerializer(data=params)
    assert s.is_valid(), s.errors
    return s.validated_data


def errors(params):
    s = ObjectTrackerSerializer(data=params)
    assert not s.is_valid()
    return s.errors


def test_bytetrack_buffer_default_is_five_seconds_at_30fps():
    data = validate({"detector": "rfdetr", "tracker": "bytetrack"})
    assert data["tracker_params"]["track_buffer"] == 150


def test_ui_player_run_gets_the_kalman_ball_tracker_and_no_ball_detector():
    # the shape the frontend sends for a player run (usePluginParams.js), no ball_* keys
    data = validate({
        "fps": 1, "detector": "rfdetr", "tracker": "bytetrack",
        "detector_params": {"confidence_threshold": 0.5, "classes": ["player", "referee", "goalkeeper"]},
        "tracker_params": {"track_thresh": 0.4, "track_buffer": 300, "match_thresh": 0.8},
    })
    assert data["tracker_params"]["track_buffer"] == 300
    assert data["ball_detector"] is None and data["ball_detector_params"] == {}
    assert data["ball_tracker"] == "kalman"
    assert data["ball_tracker_params"] == default_kalman_ball_params


def test_ui_ball_run_without_tracker():
    data = validate({"fps": 10, "detector": "yolo11", "detector_params": {"classes": [32]}})
    assert data["tracker_params"] == {}
    assert data["ball_tracker"] == "kalman"


def test_ball_detector_is_the_preset_with_ball_overrides():
    data = validate({"detector": "rfdetr", "tracker": "bytetrack", "ball_detector": "rfdetr",
                     "ball_detector_params": {"confidence_threshold": 0.15}})
    p = data["ball_detector_params"]
    assert p["classes"] == ["ball"] and p["conf"] == 0.15
    assert p["checkpoint"] == DETECTOR_DEFAULTS["rfdetr"]["checkpoint"]
    assert p["output_class_mapping"] == DETECTOR_DEFAULTS["rfdetr"]["output_class_mapping"]
    # the player detector keeps its own parameters
    assert data["detector_params"]["conf"] == DETECTOR_DEFAULTS["rfdetr"]["conf"]


def test_ball_detector_default_confidence_floor():
    data = validate({"detector": "rfdetr", "tracker": "bytetrack", "ball_detector": "yolo11"})
    assert data["ball_detector_params"]["conf"] == 0.1 and data["ball_detector_params"]["classes"] == [32]


def test_ball_detector_model_file_must_be_the_preset():
    errs = errors({"detector": "rfdetr", "tracker": "bytetrack", "ball_detector": "rfdetr",
                   "ball_detector_params": {"checkpoint": "/tmp/evil.pth"}})
    assert "ball_detector_params" in errs


@pytest.mark.parametrize("ball_detector", ["yolox", "unknown"])
def test_ball_detector_needs_a_preset_with_a_ball_class(ball_detector):
    assert "ball_detector" in errors({"detector": "rfdetr", "ball_detector": ball_detector})


def test_ball_detector_params_need_a_ball_detector():
    assert "ball_detector_params" in errors({"detector": "rfdetr", "ball_detector_params": {"conf": 0.2}})


def test_ball_tracker_params_are_merged_with_the_defaults():
    data = validate({"detector": "rfdetr", "ball_tracker_params": {"init_conf": 0.5, "min_fps": 15}})
    p = data["ball_tracker_params"]
    assert p["init_conf"] == 0.5 and p["min_fps"] == 15 and p["gate_px"] == default_kalman_ball_params["gate_px"]


def test_ball_tracker_off():
    data = validate({"detector": "rfdetr", "ball_tracker": None})
    assert data["ball_tracker"] is None and data["ball_tracker_params"] == {}


def test_ball_tracker_params_need_a_ball_tracker():
    assert "ball_tracker_params" in errors({"detector": "rfdetr", "ball_tracker": None,
                                            "ball_tracker_params": {"init_conf": 0.5}})


def test_ball_tracker_rejects_unknown_and_inconsistent_params():
    assert "ball_tracker_params" in errors({"detector": "rfdetr", "ball_tracker_params": {"gate": 10}})
    assert "ball_tracker_params" in errors({"detector": "rfdetr",
                                            "ball_tracker_params": {"min_conf": 0.5, "init_conf": 0.4}})


# ---- Deep-EIoU, GTA-Link, interpolation (API-only)
from backend.serializers.object_tracker import default_deep_eiou_params, REID_MODEL  # noqa: E402


def test_deep_eiou_defaults_are_deep_eiou_to_gta_link_with_osnet_ain():
    p = validate({"detector": "rfdetr", "tracker": "deep_eiou"})["tracker_params"]
    assert p == default_deep_eiou_params
    assert p["gta_link"]["enabled"] and not p["interpolation"]["enabled"]
    assert p["reid_model_path"] == p["gta_link"]["model_path"] == REID_MODEL["model_path"]


def test_nested_overrides_keep_the_preset_model_files():
    p = validate({"detector": "rfdetr", "tracker": "deep_eiou",
                  "tracker_params": {"track_buffer": 90, "gta_link": {"eps": 0.65}, "interpolation": {"enabled": True}}})["tracker_params"]
    assert p["track_buffer"] == 90 and p["gta_link"]["eps"] == 0.65 and p["gta_link"]["enabled"]
    assert p["gta_link"]["model_path"] == REID_MODEL["model_path"] and p["interpolation"]["n_dti"] == 20


@pytest.mark.parametrize("params", [
    {"reid_model_path": "/tmp/evil.pth"},
    {"gta_link": {"model_path": "/tmp/evil.pth"}},
    {"track_thresh": 0.5},                       # a ByteTrack key
    {"track_low_thresh": 0.7, "track_high_thresh": 0.6},
])
def test_deep_eiou_rejects_model_files_unknown_keys_and_bad_thresholds(params):
    assert "tracker_params" in errors({"detector": "rfdetr", "tracker": "deep_eiou", "tracker_params": params})


def test_bytetrack_can_use_gta_link_and_stays_off_by_default():
    p = validate({"detector": "rfdetr", "tracker": "bytetrack"})["tracker_params"]
    assert not p["gta_link"]["enabled"] and not p["interpolation"]["enabled"]
    p = validate({"detector": "rfdetr", "tracker": "bytetrack", "tracker_params": {"gta_link": {"enabled": True}}})["tracker_params"]
    assert p["gta_link"]["enabled"] and p["gta_link"]["model_path"] == REID_MODEL["model_path"]


def test_bytetrack_rejects_unknown_keys():
    assert "tracker_params" in errors({"detector": "rfdetr", "tracker": "bytetrack", "tracker_params": {"buffer": 30}})


def test_sahi_is_validated_and_filled_with_defaults():
    data = validate({"detector": "rfdetr", "tracker": "bytetrack", "ball_detector": "rfdetr",
                     "ball_detector_params": {"sahi": {"enabled": True, "full_frame": False}}})
    sahi = data["ball_detector_params"]["sahi"]
    assert sahi["enabled"] and not sahi["full_frame"]
    assert sahi["slice_size"] == [560, 560] and sahi["overlap"] == [0.2, 0.2]
    assert sahi["merge"] == "nmm" and sahi["match_metric"] == "ios" and sahi["match_threshold"] == 0.5
    assert "sahi" not in data["detector_params"]


def test_sahi_for_every_detector():
    for detector in ("yolox", "yolo11", "rfdetr", "rtdetr"):
        data = validate({"detector": detector, "detector_params": {"sahi": {"enabled": True, "slice_size": [540, 960]}}})
        assert data["detector_params"]["sahi"]["slice_size"] == [540, 960]


def test_sahi_rejects_unknown_keys_and_bad_values():
    assert "detector_params" in errors({"detector": "yolox", "detector_params": {"sahi": {"enabled": True, "tiles": 4}}})
    assert "detector_params" in errors({"detector": "yolox", "detector_params": {"sahi": {"merge": "wbf"}}})
    assert "detector_params" in errors({"detector": "yolox", "detector_params": {"sahi": {"slice_size": [560]}}})


def test_yolox_input_format():
    assert validate({"detector": "yolox"})["detector_params"]["input_format"] == "auto"
    assert validate({"detector": "yolox", "detector_params": {"input_format": "bgr255"}})["detector_params"]["input_format"] == "bgr255"
    assert "detector_params" in errors({"detector": "yolox", "detector_params": {"input_format": "rgb"}})
    # the other backends have no input convention to choose
    assert "detector_params" in errors({"detector": "rfdetr", "detector_params": {"input_format": "legacy"}})


def test_yolox_sn_player_preset():
    data = validate({"detector": "yolox_sn_player", "tracker": "deep_eiou", "detector_params": {"confidence_threshold": 0.4}})
    p = data["detector_params"]
    assert p["checkpoint"] == "/models/yolox/yolox_l_sn_player.pth" and p["model_path"] == "yolox-l"
    assert p["test_size"] == [736, 1280] and p["input_format"] == "auto"
    assert p["conf_thresh"] == 0.4 and "conf" not in p          # the YOLOX name of the alias
    assert "sahi" not in p


def test_yolox_sn_ball_preset_runs_sliced():
    data = validate({"detector": "yolox_sn_player", "tracker": "deep_eiou", "ball_detector": "yolox_sn_ball"})
    p = data["ball_detector_params"]
    assert p["checkpoint"] == "/models/yolox/yolox_l_sn_ball_tiles.pth" and p["test_size"] == [576, 576]
    assert p["sahi"]["enabled"] and not p["sahi"]["full_frame"] and p["sahi"]["slice_size"] == [560, 560]
    assert p["sahi"]["merge"] == "nmm" and p["sahi"]["overlap"] == [0.2, 0.2]   # filled from SAHI_DEFAULTS
    assert p["output_class_mapping"][0]["entity_type"] == "ball"


def test_partial_sahi_override_keeps_the_preset():
    data = validate({"detector": "rfdetr", "ball_detector": "yolox_sn_ball",
                     "ball_detector_params": {"sahi": {"overlap": [0.3, 0.3]}, "conf_thresh": 0.2}})
    p = data["ball_detector_params"]
    assert p["sahi"]["enabled"] and not p["sahi"]["full_frame"] and p["sahi"]["overlap"] == [0.3, 0.3]
    assert p["conf_thresh"] == 0.2


def test_yolox_sn_presets_keep_their_model_files():
    for detector in ("yolox_sn_player", "yolox_sn_ball"):
        assert "detector_params" in errors({"detector": detector,
                                            "detector_params": {"model_path": "/models/yolox/yolox_x.pth"}})
