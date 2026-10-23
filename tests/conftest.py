"""Shared test setup: isolate the backend from Valkey, Celery's broker and the real data folders."""
import os
import types
import uuid

import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def _isolated_data_manager(monkeypatch):
    """Code constructs DataManager("/predictions/") etc. directly; redirect it to a temp dir."""
    from data import manager

    original_init = manager.DataManager.__init__

    def init(self, data_dir=None, cache=None):
        if data_dir and str(data_dir).startswith("/"):
            data_dir = os.path.join(settings.TEST_DATA_ROOT, str(data_dir).strip("/"))
        original_init(self, data_dir=data_dir, cache=cache)

    monkeypatch.setattr(manager.DataManager, "__init__", init)


@pytest.fixture(autouse=True)
def published_events(monkeypatch):
    """Record SSE publishes instead of talking to Valkey."""
    from backend.utils import events

    calls = []
    monkeypatch.setattr(events, "publish", lambda user_id, payload: calls.append((user_id, payload)))
    return calls


@pytest.fixture(autouse=True)
def enqueued_tasks(monkeypatch):
    """Record Celery enqueues and control calls instead of contacting the broker."""
    from backend import plugin_manager
    from backend.tasks import convert_video
    from sportvid.celery import app

    calls = []

    def fake_apply_async(name):
        def apply_async(*args, **kwargs):
            calls.append((name, args, kwargs))
            return types.SimpleNamespace(id=uuid.uuid4().hex)
        return apply_async

    monkeypatch.setattr(plugin_manager.run_plugin, "apply_async", fake_apply_async("run_plugin"))
    monkeypatch.setattr(convert_video.convert_video_to_hls, "apply_async", fake_apply_async("convert_video_to_hls"))
    monkeypatch.setattr(app.control, "revoke", lambda *a, **k: calls.append(("revoke", a, k)))
    return calls
