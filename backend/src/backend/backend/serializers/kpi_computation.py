from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("kpi_computation")
class KPIComputationSerializer(serializers.Serializer):
    tracking_data_id = serializers.UUIDField(required=True)
    bytetrack_run_id = serializers.UUIDField(required=True)
    calibration_id = serializers.UUIDField(required=True)
    
    format = serializers.ChoiceField(
        required=True,
        choices=["dfl", "kinexon", "sportvid"]
    )
    pos_meta = serializers.JSONField(
        required=False,
        allow_null=True, 
        default=None
    )
    filter_type = serializers.CharField(
        required=False,
        default="",
        allow_blank=True

    )
    order = serializers.IntegerField(
        required=False,
        default=3,
    )
    Wn = serializers.FloatField(
        required=False,
        default=1.0
    )
    window_length = serializers.IntegerField(
        required=False,
        default=5
    )
    poly_order = serializers.IntegerField(
        required=False,
        default=3
    )