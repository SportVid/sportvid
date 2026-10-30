"""PluginManager.run without Celery (run_async=False), as the management commands use it."""
from rest_framework import serializers

from backend.models import PluginRun
from backend.plugin_manager import PluginManager
from tests.factories import make_user, make_video


class FakeSerializer(serializers.Serializer):
    threshold = serializers.FloatField(default=0.5)


def test_sync_run_passes_validated_parameters(db, register_plugin, monkeypatch):
    seen = {}
    register_plugin("fake", lambda self, parameters, **kwargs: seen.update(parameters) or {})
    monkeypatch.setitem(PluginManager._serializers, "fake", FakeSerializer)
    video = make_video(make_user())

    result = PluginManager().run("fake", video=video, user=video.owner, parameters={"threshold": "0.7"}, run_async=False)

    assert result["status"] is True
    assert seen == {"threshold": 0.7}  # parsed by the serializer, not the raw string
    run = PluginRun.objects.get(id=result["plugin_run_id"])
    assert (run.status, run.parameters) == (PluginRun.STATUS_DONE, {"threshold": 0.7})


def test_sync_run_fills_in_serializer_defaults(db, register_plugin, monkeypatch):
    seen = {}
    register_plugin("fake", lambda self, parameters, **kwargs: seen.update(parameters) or {})
    monkeypatch.setitem(PluginManager._serializers, "fake", FakeSerializer)
    video = make_video(make_user())

    PluginManager().run("fake", video=video, user=video.owner, parameters={}, run_async=False)

    assert seen == {"threshold": 0.5}
