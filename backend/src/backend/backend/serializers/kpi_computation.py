from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("kpi_computation")
class KPIComputationSerializer(serializers.Serializer):
    # Which of these is required depends on `format` -- see validate() below.
    tracking_data_id = serializers.UUIDField(required=False, allow_null=True)
    bytetrack_run_id = serializers.UUIDField(required=False, allow_null=True)
    calibration_id = serializers.UUIDField(required=False, allow_null=True)

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

    def validate(self, attrs):
        fmt = attrs.get("format")
        if fmt == "sportvid":
            if not attrs.get("bytetrack_run_id"):
                raise serializers.ValidationError({
                    "bytetrack_run_id": ["This field is required when format is 'sportvid'."]
                })
            if not attrs.get("calibration_id"):
                raise serializers.ValidationError({
                    "calibration_id": ["This field is required when format is 'sportvid'."]
                })
        else:
            if not attrs.get("tracking_data_id"):
                raise serializers.ValidationError({
                    "tracking_data_id": ["This field is required when format is 'dfl' or 'kinexon'."]
                })
        return attrs