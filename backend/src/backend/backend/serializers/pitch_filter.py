from rest_framework import serializers
from backend.plugin_manager import PluginManager


# Post-processing of an object_tracker run (tasks/pitch_filter.py): a track is off the pitch when at least
# min_outside_fraction of its foot points lie more than margin_m outside the touch / goal lines.
@PluginManager.export_serializer("pitch_filter")
class PitchFilterSerializer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(required=True)
    calibration_id = serializers.UUIDField(required=True)
    margin_m = serializers.FloatField(required=False, default=3.0, min_value=0.0, max_value=50.0)
    min_outside_fraction = serializers.FloatField(required=False, default=0.5, min_value=0.01, max_value=1.0)
    # bystander: the off-pitch tracks keep their boxes with team BYSTANDER (team_clustering skips them);
    # remove: their boxes are dropped
    action = serializers.ChoiceField(
        choices=["bystander", "remove"], required=False, default="bystander"
    )
