"""Correlation IDs on log lines (ADR 0006 decision 4): backend.log_context and where it is bound."""
import json
import logging
import threading
import types
import uuid

import pytest

from backend.log_context import ContextFormatter, log_context, log_event
from backend.models import PluginRun
from backend.plugin_manager import run_plugin
from tests.factories import make_run, make_user, make_video

logger = logging.getLogger("backend.tests")


def test_fields_are_appended_inside_the_block_only(log_lines):
    run_id = uuid.uuid4()
    with log_context(video_id="v1", plugin_run_id=run_id, job_id=None):
        logger.info("inside")
    logger.info("outside")

    assert log_lines() == [f"INFO inside video_id=v1 plugin_run_id={run_id.hex}", "INFO outside"]


def test_nested_blocks_add_and_restore(log_lines):
    with log_context(video_id="v1"):
        with log_context(job_id="j1", video_id="v2"):
            logger.info("inner")
        logger.info("outer")

    assert log_lines() == ["INFO inner video_id=v2 job_id=j1", "INFO outer video_id=v1"]


def test_events_carry_their_fields_after_the_context(log_lines):
    with log_context(video_id="v1"):
        log_event(logger, "video.delete", storage_released=300, files_removed=True, reason="a b", task_id=None)

    assert log_lines() == ['INFO video.delete video_id=v1 storage_released=300 files_removed=true reason="a b"']


def test_fields_come_before_the_traceback(log_lines):
    with log_context(video_id="v1"):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            logger.exception("failed")

    assert log_lines()[0] == "ERROR failed video_id=v1"
    assert log_lines()[-1] == "RuntimeError: boom"


def test_the_console_handler_uses_the_context_formatter():
    handler = logging.getLogger("backend").handlers[0]
    assert isinstance(handler.formatter, ContextFormatter)


def test_the_cancellation_watcher_thread_logs_with_the_callers_ids(monkeypatch, log_lines):
    """on_cancel runs on the listener thread; it must still know which video it cancels."""
    from backend.utils import events

    messages = iter([{"type": "message", "data": b"cancel"}])
    pubsub = types.SimpleNamespace(subscribe=lambda channel: None, close=lambda: None,
                                   get_message=lambda timeout: next(messages, None))
    monkeypatch.setattr(events, "get_client", lambda: types.SimpleNamespace(pubsub=lambda **kw: pubsub))

    called = threading.Event()

    def on_cancel():
        logger.info("killing ffmpeg")
        called.set()

    with log_context(video_id="v1", task_id="t1"):
        with events.cancellation_watcher("video", "v1", on_cancel=on_cancel):
            # not the yielded event: the watcher sets that before it calls on_cancel
            assert called.wait(timeout=5)

    assert "INFO killing ffmpeg video_id=v1 task_id=t1" in log_lines()


def test_run_plugin_lines_carry_the_run(db, register_plugin, log_lines):
    run = make_run(make_video(make_user()), type="fake")
    register_plugin("fake", lambda self, **kwargs: logger.info("working") or {})

    run_plugin({"plugin": "fake", "parameters": {}, "video": str(run.video.id), "user": str(run.video.owner.id),
                "plugin_run": str(run.id), "dry_run": False})

    assert f"INFO working plugin=fake plugin_run_id={run.id.hex} video_id={run.video.id.hex}" in log_lines()


def test_plugin_run_cancel_logs_stage_and_mechanism(db, client, caplog, cancel_messages):
    user = make_user("alice")
    client.force_login(user)
    video = make_video(user)
    queued = make_run(video, status=PluginRun.STATUS_QUEUED, task_id="t-queued")
    running = make_run(video, status=PluginRun.STATUS_RUNNING)

    with caplog.at_level(logging.INFO, logger="backend.utils.cancellation"):
        client.post("/plugin/run/delete", json.dumps({"plugin_list": [queued.id.hex, running.id.hex]}),
                    content_type="application/json")

    fields = {r.log_fields["plugin_run_id"]: r.log_fields for r in caplog.records if r.msg == "plugin_run.cancel"}
    assert fields[queued.id.hex] == {"plugin_run_id": queued.id.hex, "plugin": "object_tracker", "task_id": "t-queued",
                                     "stage": "queued", "revoked": "true", "cancel_sent": "true", "reason": "user_delete"}
    assert fields[running.id.hex]["stage"] == "running"
    assert fields[running.id.hex]["revoked"] == "false"


def test_the_cancel_log_says_when_valkey_did_not_take_it(db, client, caplog, monkeypatch):
    """cancel_sent=false is how a task that kept running is explained."""
    from backend.utils import events

    def down():
        raise ConnectionError("valkey down")
    monkeypatch.setattr(events, "get_client", down)
    user = make_user("alice")
    client.force_login(user)
    run = make_run(make_video(user), status=PluginRun.STATUS_RUNNING)

    with caplog.at_level(logging.INFO, logger="backend.utils.cancellation"):
        client.post("/plugin/run/delete", json.dumps({"plugin_list": [run.id.hex]}), content_type="application/json")

    [event] = [r for r in caplog.records if r.msg == "plugin_run.cancel"]
    assert event.log_fields["cancel_sent"] == "false"


@pytest.mark.parametrize("deleted, level", [(True, logging.INFO), (False, logging.ERROR)], ids=["cancelled", "failed"])
def test_no_analyser_result_is_an_error_only_if_the_run_still_exists(db, caplog, deleted, level):
    from backend.utils.task import Task

    run = make_run(make_video(make_user()), status=PluginRun.STATUS_RUNNING)
    client = types.SimpleNamespace(run_plugin=lambda *a: "job-1", get_plugin_results=lambda **kw: None)
    if deleted:
        PluginRun.objects.filter(id=run.id).delete()

    with caplog.at_level(logging.INFO, logger="backend"):
        assert Task().run_analyser(client, "thumbnail_generator", plugin_run=run) is None

    [event] = [r for r in caplog.records if r.msg == "analyser.job.no_result"]
    assert event.levelno == level
