from rest_framework import serializers
from backend.plugin_manager import PluginManager

@PluginManager.export_serializer("posdata_convert")
class PosDataConvertSerializer(serializers.Serializer):
    tracking_data_id = serializers.UUIDField(required=True)
    
    format = serializers.ChoiceField(
        required=True,
        choices=["dfl", "kinexon"]
    )
    fps = serializers.IntegerField(
        required=False,
        default=-1,
        min_value=-1,
        max_value=60
    )
    delimiter = serializers.CharField(
        required=False,
        default=";",
        max_length=1
    )
    origin = serializers.ChoiceField(
        required=False,
        choices=["kickoff", "bottom_left"],
        default="kickoff"
    )
    field_length = serializers.FloatField(
        required=False,
        default=105.,
        min_value=1.0,
        max_value=1337.
    )
    field_width = serializers.FloatField(
        required=False,
        default=68.,
        min_value=1.0,
        max_value=1337.
    )
    team_id_ball = serializers.CharField(
        required=False,
        default="ball",
        max_length=100,
        allow_blank=False,
        #trim_whitespace=True,
    )
    
    team_id_ref = serializers.CharField(
        required=False,
        default="",
        max_length=100,
        allow_blank=True,
        #trim_whitespace=True,
    )