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
