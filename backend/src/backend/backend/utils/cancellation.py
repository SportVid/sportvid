"""Stopping the Celery work behind plugin runs and videos that are being deleted, and logging how.

A queued task is stopped by revoke: the worker discards it when it would start. A task that
is already running only stops on the cancel message its cancellation_watcher listens for.
Both are sent, because the status read here can change before they arrive; the log's
`stage` says which one is expected to take effect, so a task that kept going can be traced
from its `plugin_run.cancel` or `video.conversion.cancel` line to the task's own
`cancel.received` (or its absence).
"""
import logging

from sportvid.celery import app as celery_app

from backend.log_context import log_event
from backend.models import PluginRun
from backend.utils.events import publish_cancel


logger = logging.getLogger(__name__)


def active_plugin_runs(runs):
    """(id, task_id, status, type) of the runs in the queryset `runs` that may still have work going.

    Read them before deleting the runs: the cancellation addresses them by id.
    """
    return list(
        runs.exclude(status__in=[PluginRun.STATUS_DONE, PluginRun.STATUS_ERROR])
        .values_list("id", "task_id", "status", "type")
    )


def cancel_plugin_runs(active, reason):
    """Revoke and cancel the runs from active_plugin_runs(); `reason` goes into the log."""
    for run_id, task_id, status, plugin in active:
        if task_id:
            celery_app.control.revoke(task_id, terminate=False)
        cancel_sent = publish_cancel("plugin_run", run_id.hex)
        log_event(
            logger, "plugin_run.cancel",
            plugin_run_id=run_id, plugin=plugin, task_id=task_id,
            stage=PluginRun.STATUS.get(status, status).lower(),
            revoked=bool(task_id), cancel_sent=cancel_sent, reason=reason,
        )


def cancel_conversion(video, reason):
    """Revoke and cancel the HLS conversion of `video`; `reason` goes into the log."""
    if video.task_id:
        celery_app.control.revoke(video.task_id, terminate=False)
    cancel_sent = publish_cancel("video", video.id.hex)
    log_event(
        logger, "video.conversion.cancel",
        video_id=video.id, task_id=video.task_id,
        stage=video.STATUS.get(video.status, video.status).lower(),
        revoked=bool(video.task_id), cancel_sent=cancel_sent, reason=reason,
    )
