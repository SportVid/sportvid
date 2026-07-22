from rest_framework import serializers
from backend.plugin_manager import PluginManager


MODEL_CHOICES = ["osnet_x1_0"]


@PluginManager.export_serializer("osnet_reid")
class OSNetReIdentificationSerializer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(required=True)
    
    model_name = serializers.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        default="osnet_x1_0",
    )
    
    reid_threshold = serializers.FloatField(
        required=False,
        default=0.6,
        min_value=0.01,
        max_value=1.0,
    )
    max_missed = serializers.IntegerField(
        required=False,
        default=300,
        min_value=1
    )
    
    crop_size_x = serializers.IntegerField(
        required=False,
        default=128,
        min_value=5
    )
    crop_size_y = serializers.IntegerField(
        required=False,
        default=256,
        min_value=5
    )

    crop_x1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_y1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_x2_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_y2_offset = serializers.FloatField(
        required=False,
        default=0.6,
        min_value=0.,
        max_value=1.0
    )