"""V3: every plugin run and external call has a time limit (PLUGIN_RUN_TIMEOUT)."""
import types
from contextlib import nullcontext

import pytest

from backend.models import PluginRun, SportVidUser, Video
from interface import analyser_pb2

RUNNING = analyser_pb2.GetPluginStatusResponse.RUNNING


@pytest.fixture
def run(db):
    owner = SportVidUser.objects.create_user("owner", "o@example.org", "Correct-Horse-Battery-42")
    video = Video.objects.create(owner=owner, name="v", ext=".mp4")
    return PluginRun.objects.create(video=video, type="object_tracker", status=PluginRun.STATUS_RUNNING)


def test_analyser_job_that_never_finishes_is_aborted_and_marked_error(run, settings, monkeypatch, published_events):
    from backend.utils import analyser_client

    monkeypatch.setattr(analyser_client, "cancellation_watcher", lambda *a, **k: nullcontext(None))
    settings.PLUGIN_RUN_TIMEOUT = 0.5
    client = analyser_client.TaskAnalyserClient(host="localhost", port=1, plugin_run_db=run)
    aborted = []
    monkeypatch.setattr(client, "get_plugin_status", lambda job_id: types.SimpleNamespace(status=RUNNING, progress=0.1))
    monkeypatch.setattr(client, "abort_plugin", lambda job_id: aborted.append(job_id))

    assert client.get_plugin_results("job-1") is None
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    assert aborted == ["job-1"]
    assert any(p["type"] == "plugin_run.update" and p["entry"]["status"] == "ERROR" for _, p in published_events)


def _manager(monkeypatch):
    from inference_ray import plugin as ray_plugin

    # skip importing every plugin module (several need torch, which CI does not install)
    monkeypatch.setattr(ray_plugin.AnalyserPluginManager, "find", lambda self, path=None: None)
    return ray_plugin, ray_plugin.AnalyserPluginManager({"host": "inference_ray", "port": 8010, "status_port": 52365})


def test_ray_call_has_connect_and_read_timeouts(monkeypatch):
    ray_plugin, manager = _manager(monkeypatch)

    calls = {}

    class Session:
        def post(self, url, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(json=lambda: {"out": "id"})

    monkeypatch.setattr(manager, "plugin_status", lambda: [{"plugin": "x", "route": "/x"}])
    assert manager("x", inputs={}, data_manager=None, session=Session()) == {"out": "id"}
    assert calls["timeout"] == (ray_plugin.RAY_CONNECT_TIMEOUT, ray_plugin.PLUGIN_RUN_TIMEOUT)


def test_ray_status_query_has_a_timeout(monkeypatch):
    ray_plugin, manager = _manager(monkeypatch)
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        return types.SimpleNamespace(json=lambda: {"applications": {}})

    monkeypatch.setattr(ray_plugin.requests, "get", fake_get)
    manager.plugin_status()
    assert seen["timeout"] == ray_plugin.RAY_STATUS_TIMEOUT


def test_download_by_url_has_a_timeout(monkeypatch, tmp_path):
    from backend.utils import upload

    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        raise ConnectionError("stop here")

    monkeypatch.setattr(upload.requests, "get", fake_get)
    upload.download_url("http://example.org/v.mp4", str(tmp_path))
    assert seen["timeout"] == (10, 300)
