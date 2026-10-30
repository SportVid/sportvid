"""TaskAnalyserClient: a gRPC failure marks the run ERROR, but never inserts a deleted run again."""
import logging

import grpc
import pytest

from analyser.client import AnalyserClient
from backend.models import PluginRun
from backend.utils.analyser_client import TaskAnalyserClient
from tests.factories import make_run, make_user, make_video


class Unavailable(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE

    def details(self):
        return "analyser down"


@pytest.fixture
def run(db):
    return make_run(make_video(make_user()), status=PluginRun.STATUS_RUNNING)


def client_for(run):
    client = TaskAnalyserClient.__new__(TaskAnalyserClient)
    client.plugin_run_db = run
    return client


def fail(*args, **kwargs):
    raise Unavailable()


METHODS = ["list_plugins", "upload_data", "upload_file", "run_plugin", "get_plugin_status",
           "download_data", "download_data_to_blob"]


@pytest.mark.parametrize("method", METHODS)
def test_a_grpc_error_marks_the_run_error(run, monkeypatch, published_events, caplog, method):
    monkeypatch.setattr(AnalyserClient, method, fail)
    published_events.clear()

    assert getattr(client_for(run), method)() is None

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    assert [p["entry"]["status"] for _, p in published_events if p["type"] == "plugin_run.update"] == ["ERROR"]
    [error] = [r for r in caplog.records if r.msg == "analyser.grpc_error"]
    assert error.levelno == logging.ERROR
    assert error.log_fields == {"call": method, "code": "UNAVAILABLE", "message": "analyser down"}


@pytest.mark.parametrize("method", METHODS)
def test_a_grpc_error_after_the_run_was_deleted_leaves_it_deleted(run, monkeypatch, caplog, method):
    monkeypatch.setattr(AnalyserClient, method, fail)
    client = client_for(run)
    PluginRun.objects.filter(id=run.id).delete()

    with caplog.at_level(logging.INFO, logger="backend"):
        getattr(client, method)()

    assert not PluginRun.objects.filter(id=run.id).exists()
    assert "plugin_run.deleted_while_running" in [r.msg for r in caplog.records]


def test_abort_errors_leave_the_run_alone(run, monkeypatch):
    monkeypatch.setattr(AnalyserClient, "abort_plugin", fail)

    assert client_for(run).abort_plugin("job-1") is None

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_RUNNING


def test_a_status_poll_error_marks_the_run_error(run, monkeypatch, published_events):
    monkeypatch.setattr(AnalyserClient, "get_plugin_status", fail)
    from backend.utils import analyser_client
    import contextlib, threading
    monkeypatch.setattr(analyser_client, "cancellation_watcher",
                        lambda *a, **k: contextlib.nullcontext(threading.Event()))

    published_events.clear()

    assert client_for(run).get_plugin_results("job-1", plugin_run_db=run, timeout=60) is None

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    # get_plugin_status marks it; the poll doesn't mark it a second time
    assert [p["entry"]["status"] for _, p in published_events if p["type"] == "plugin_run.update"] == ["ERROR"]
