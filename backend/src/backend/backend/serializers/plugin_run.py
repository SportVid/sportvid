from rest_framework import serializers
from django.shortcuts import get_object_or_404
from backend.plugin_manager import PluginManager
from backend.models import Video

class PluginRunRequestSerializer(serializers.Serializer):
    plugin = serializers.CharField()
    video_id = serializers.IntegerField()
    parameters = serializers.JSONField()

    def validate_plugin(self, value):
        plugin_manager = PluginManager()
        if value not in plugin_manager:
            raise serializers.ValidationError("Unknown plugin")
        return value

    def validate_video_id(self, value):
        if not Video.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown video")
        return value

    def validate_parameters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("parameters must be an object")
        return value