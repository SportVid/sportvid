from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("calibration_lens_solve")
class CalibrationLensSolveSerializer(serializers.Serializer):
    calibration_id = serializers.UUIDField(required=True)
    # frames sampled across the video to detect the pitch markings in
    num_frames = serializers.IntegerField(required=False, min_value=1, max_value=30)
    # maximum detect-and-fit rounds (stops earlier once the detected markings stop growing)
    rounds = serializers.IntegerField(required=False, min_value=1, max_value=10)
    poly_degree = serializers.IntegerField(required=False, min_value=3, max_value=8)
