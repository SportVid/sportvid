from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("floodlight_convert")
class FloodlightConvertSerializer(serializers.Serializer):
    tracking_data_id = serializers.UUIDField(required=True)
    
    format = serializers.ChoiceField(
        required=True,
        choices=["dfl", "kinexon", "sportvid"]
    )
    delimiter = serializers.CharField(
        required=False,
        default=";",
        max_length=1
    )