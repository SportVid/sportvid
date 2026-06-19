from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("calibration_static_dlt")
class CalibrationSerializer(serializers.Serializer):
    calibration_id = serializers.UUIDField(required=True)