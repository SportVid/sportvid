"""A plugin run deleted while its task works on it stays deleted, and nothing is logged as an error."""
import logging
import types

import pytest

from backend.models import PluginRun
from backend.plugin_manager import run_plugin
from backend.utils.analyser_client import TaskAnalyserClient
from interface import analyser_pb2
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def video(db):
    return make_video(make_user())


def payload(run):
    return {"plugin": run.type, "parameters": {}, "video": str(run.video.id), "user": str(run.video.owner.id),
            "plugin_run": str(run.id), "dry_run": False}


@pytest.mark.parametrize("raises", [False, True], ids=["finishes", "fails"])
def test_finishing_a_deleted_run_does_not_insert_it_again(video, register_plugin, caplog, raises):
    """save() on a row that is gone used to fall back to an INSERT: the deleted run came back."""
    run = make_run(video, type="fake")

    def call(self, **kwargs):
        PluginRun.objects.filter(id=run.id).delete()  # the user deletes the run meanwhile
        if raises:
            raise RuntimeError("analyser gone")
        return {}
    register_plugin("fake", call)

    with caplog.at_level(logging.INFO, logger="backend"):
        run_plugin(payload(run))

    assert not PluginRun.objects.filter(id=run.id).exists()
    assert "plugin_run.deleted_while_running" in [r.msg for r in caplog.records]
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_a_failing_run_that_still_exists_is_marked_error(video, register_plugin):
    run = make_run(video, type="fake")
    register_plugin("fake", lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    run_plugin(payload(run))

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR


def test_analyser_poll_aborts_the_job_when_the_run_is_gone(video, monkeypatch, caplog):
    """Without the cancel message (Valkey down, or sent before the watcher subscribed) the poll notices the delete."""
    run = make_run(video, status=PluginRun.STATUS_RUNNING)
    client = TaskAnalyserClient.__new__(TaskAnalyserClient)
    aborted = []
    running = types.SimpleNamespace(status=analyser_pb2.GetPluginStatusResponse.RUNNING, progress=0.5)
    monkeypatch.setattr(client, "get_plugin_status", lambda job_id: running, raising=False)
    monkeypatch.setattr(client, "abort_plugin", aborted.append, raising=False)
    from backend.utils import analyser_client
    monkeypatch.setattr(analyser_client, "cancellation_watcher", _silent_watcher)
    PluginRun.objects.filter(id=run.id).delete()

    with caplog.at_level(logging.INFO, logger="backend"):
        assert client.get_plugin_results("job-1", plugin_run_db=run, timeout=60) is None

    assert aborted == ["job-1"]
    [event] = [r for r in caplog.records if r.msg == "plugin_run.cancelled"]
    assert event.log_fields == {"plugin_run_id": run.id.hex, "source": "db_fallback"}


def _silent_watcher(kind, resource_id, on_cancel=None):
    import contextlib
    import threading

    return contextlib.nullcontext(threading.Event())


def test_the_tasks_status_writes_keep_the_task_id(video, register_plugin):
    """The task can read its run before PluginManager.run stores the task id; its writes must not erase it."""
    run = make_run(video, type="fake")

    def call(self, **kwargs):
        PluginRun.objects.filter(id=run.id).update(task_id="t-late")
        return {}
    register_plugin("fake", call)

    run_plugin(payload(run))

    run.refresh_from_db()
    assert (run.status, run.task_id) == (PluginRun.STATUS_DONE, "t-late")
