"""Correlation IDs on log records (ADR 0006 decision 4).

Code that works on one video, plugin run or analyser job binds its IDs once:

    with log_context(video_id=video_id_hex, task_id=self.request.id):
        ...

and every record logged inside the block, from any module, ends in
` video_id=... task_id=...` (logfmt). The context is a contextvar, so it belongs to one
thread (celery's thread pool, gunicorn's gthread workers) and doesn't leak into other
tasks or requests. A new thread starts without it; start the thread with
`contextvars.copy_context().run` to keep the caller's IDs (see cancellation_watcher).

Events that carry their own fields are logged with log_event():

    log_event(logger, "plugin_run.cancel", plugin_run_id=run_id, stage="queued", revoked=True)

This module is loaded by the LOGGING config (ContextFormatter), before the apps are
ready, so it must not import Django models.
"""
import contextvars
import json
import logging
import uuid
from contextlib import contextmanager

_fields = contextvars.ContextVar("log_fields", default={})


def _value(value):
    if isinstance(value, uuid.UUID):
        return value.hex
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


@contextmanager
def log_context(**fields):
    """Add `fields` to every record logged in this block; None values are left out."""
    added = {k: _value(v) for k, v in fields.items() if v is not None}
    token = _fields.set({**_fields.get(), **added})
    try:
        yield
    finally:
        _fields.reset(token)


def log_event(logger, event, *, level=logging.INFO, exc_info=None, **fields):
    """Log `event` (a dotted name such as "video.delete") with its own fields after the context's."""
    logger.log(level, event, exc_info=exc_info, stacklevel=2,
               extra={"log_fields": {k: _value(v) for k, v in fields.items() if v is not None}})


def _render(fields):
    parts = []
    for key, value in fields.items():
        text = str(value)
        if not text or any(c in text for c in ' ="\n'):
            text = json.dumps(text)
        parts.append(f"{key}={text}")
    return " ".join(parts)


class ContextFormatter(logging.Formatter):
    """logging.Formatter that appends the bound context and the event's fields to the message line.

    They go before the traceback, so `grep video_id=<id>` finds the line that explains it.
    """

    def formatMessage(self, record):
        fields = {**_fields.get(), **getattr(record, "log_fields", {})}
        line = super().formatMessage(record)
        return f"{line} {_render(fields)}" if fields else line
