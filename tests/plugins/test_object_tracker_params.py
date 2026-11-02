"""object_tracker parameters: ByteTrack buffer default."""
from backend.serializers.object_tracker import ObjectTrackerSerializer


def validate(params):
    s = ObjectTrackerSerializer(data=params)
    assert s.is_valid(), s.errors
    return s.validated_data


def test_bytetrack_buffer_default_is_five_seconds_at_30fps():
    data = validate({"detector": "rfdetr", "tracker": "bytetrack"})
    assert data["tracker_params"]["track_buffer"] == 150


def test_ui_player_run_keeps_its_track_buffer():
    # the shape the frontend sends for a player run (usePluginParams.js)
    data = validate({
        "fps": 1, "detector": "rfdetr", "tracker": "bytetrack",
        "detector_params": {"confidence_threshold": 0.5, "classes": ["player", "referee", "goalkeeper"]},
        "tracker_params": {"track_thresh": 0.4, "track_buffer": 300, "match_thresh": 0.8},
    })
    assert data["tracker_params"]["track_buffer"] == 300
