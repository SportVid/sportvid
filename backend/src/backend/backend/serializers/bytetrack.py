from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("bytetrack")
class ByteTrackSerializer(serializers.Serializer):
    fps = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=30,
    )