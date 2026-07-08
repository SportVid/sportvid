from rest_framework import serializers
from backend.plugin_manager import PluginManager


class DetectorParamsSerializer(serializers.Serializer):
    confidence_threshold = serializers.FloatField(
        required=False,
        default=0.25,
        min_value=0.0,
        max_value=1.0,
    )
    # TODO: add all necessary options...

class TrackerParamsSerializer(serializers.Serializer):
    # TODO: add all necessary options...
    pass

@PluginManager.export_serializer("tracker")
class TrackerExecutionSerializer(serializers.Serializer):
    detector = serializers.ChoiceField(
        choices=["yolox", "yolo10", "yolo11", "yolo26", "rfdetr", "rtdetr"],
        required=False,
        default="yolox",
    )
    tracker = serializers.ChoiceField(
        choices=["bytetrack"],
        required=False,
        default="bytetrack",
    )
        
    detector_params = DetectorParamsSerializer(required=False, default=dict)
    tracker_params = TrackerParamsSerializer(required=False, default=dict)

    def validate(self, data):
        detector = data["detector"]
        tracker = data["tracker"]
        detector_params = data.get("detector_params", {})
        tracker_params = data.get("tracker_params", {})

        if detector == "yolox":
            # optional extra rules for YOLOX
            pass

        if tracker == "bytetrack":
            # optional extra rules for ByteTrack
            pass

        return data