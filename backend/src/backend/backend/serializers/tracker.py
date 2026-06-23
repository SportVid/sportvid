from rest_framework import serializers
from backend.plugin_manager import PluginManager


class DetectorParamsSerializer(serializers.Serializer):
    confidence_threshold = serializers.FloatField(
        required=False,
        default=0.25,
        min_value=0.0,
        max_value=1.0,
    )


class TrackerParamsSerializer(serializers.Serializer):
    fps = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
    )


@PluginManager.export_serializer("tracker")
class TrackerExecutionSerializer(serializers.Serializer):
    detector = serializers.ChoiceField(
        choices=["yolox", "yolo10", "yolo11", "yolo26", "rfdetr", "rtdetr"],
        required=False,
        default="yolox",
    )
    detector_params = DetectorParamsSerializer(required=False, default=dict)
    tracker = serializers.ChoiceField(
        choices=["bytetrack"],
        required=False,
        default="bytetrack",
    )
    tracker_params = TrackerParamsSerializer(required=False, default=dict)