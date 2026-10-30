"""Correlation IDs on log lines (ADR 0006 decision 4): backend.log_context and where it is bound."""
import io
import json
import logging
import types
import uuid

import pytest
from django.conf import settings

from backend.log_context import ContextFormatter, log_context, log_event
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def log():
    """A logger whose lines are formatted like the console handler's; returns (logger, lines())."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ContextFormatter(fmt="%(levelname)s %(message)s"))
    logger = logging.getLogger(f"test.log_context.{uuid.uuid4().hex}")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, lambda: stream.getvalue().splitlines()


def test_fields_are_appended_inside_the_block_only(log):
    logger, lines = log
    run_id = uuid.uuid4()
    with log_context(video_id="v1", plugin_run_id=run_id, job_id=None):
        logger.info("inside")
    logger.info("outside")

    assert lines() == [f"INFO inside video_id=v1 plugin_run_id={run_id.hex}", "INFO outside"]


def test_nested_blocks_add_and_restore(log):
    logger, lines = log
    with log_context(video_id="v1"):
        with log_context(job_id="j1", video_id="v2"):
            logger.info("inner")
        logger.info("outer")

    assert lines() == ["INFO inner video_id=v2 job_id=j1", "INFO outer video_id=v1"]


def test_events_carry_their_fields_after_the_context(log):
    logger, lines = log
    with log_context(video_id="v1"):
        log_event(logger, "video.delete", storage_released=300, files_removed=True, reason="a b", task_id=None)

    assert lines() == ['INFO video.delete video_id=v1 storage_released=300 files_removed=true reason="a b"']


def test_fields_come_before_the_traceback(log):
    logger, lines = log
    with log_context(video_id="v1"):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            logger.exception("failed")

    assert lines()[0] == "ERROR failed video_id=v1"
    assert lines()[-1] == "RuntimeError: boom"


def test_the_console_handler_uses_the_context_formatter():
    formatter = settings.LOGGING["formatters"]["verbose"]
    assert formatter["()"] == "backend.log_context.ContextFormatter"
    handler = logging.getLogger("backend").handlers[0]
    assert isinstance(handler.formatter, ContextFormatter)


def test_the_cancellation_watcher_thread_logs_with_the_callers_ids(monkeypatch, log):
    """on_cancel runs on the listener thread; it must still know which video it cancels."""
    from backend.utils import events

    logger, lines = log
    messages = iter([{"type": "message", "data": b"cancel"}])
    pubsub = types.SimpleNamespace(subscribe=lambda channel: None, close=lambda: None,
                                   get_message=lambda timeout: next(messages, None))
    monkeypatch.setattr(events, "get_client", lambda: types.SimpleNamespace(pubsub=lambda **kw: pubsub))

    with log_context(video_id="v1", task_id="t1"):
        with events.cancellation_watcher("video", "v1", on_cancel=lambda: logger.info("killing ffmpeg")) as cancelled:
            assert cancelled.wait(timeout=5)

    assert "INFO killing ffmpeg video_id=v1 task_id=t1" in lines()


def test_plugin_run_cancel_logs_stage_and_mechanism(db, client, caplog, cancel_messages):
    user = make_user("alice")
    client.force_login(user)
    video = make_video(user)
    queued = make_run(video, status="Q", task_id="t-queued")
    running = make_run(video, status="R")

    with caplog.at_level(logging.INFO, logger="backend.utils.cancellation"):
        client.post("/plugin/run/delete", json.dumps({"plugin_list": [queued.id.hex, running.id.hex]}),
                    content_type="application/json")

    fields = {r.log_fields["plugin_run_id"]: r.log_fields for r in caplog.records if r.msg == "plugin_run.cancel"}
    assert fields[queued.id.hex] == {"plugin_run_id": queued.id.hex, "plugin": "object_tracker", "task_id": "t-queued",
                                     "stage": "queued", "revoked": "true", "cancel_sent": "true", "reason": "user_delete"}
    assert fields[running.id.hex]["stage"] == "running"
    assert fields[running.id.hex]["revoked"] == "false"
