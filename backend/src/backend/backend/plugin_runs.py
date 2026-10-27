"""Reconciliation of plugin runs whose Celery task is gone.

When a worker restarts or crashes, the run it was executing stays RUNNING (or WAITING)
in the database. `reconcile_plugin_runs()` marks such runs UNKNOWN. It runs once at
backend start through `manage.py reconcile_plugin_runs`, never in AppConfig.ready().

QUEUED runs are left alone: their task may still wait in the broker queue, which
celery's inspect() cannot see.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

RUN_PLUGIN_TASK = "backend.plugin_manager.run_plugin"


def _task_requests(reply):
    """Flatten one inspect() reply ({worker: [entry, ...]}) into task request dicts."""
    for entries in (reply or {}).values():
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            # scheduled() wraps the request: {"eta": ..., "priority": ..., "request": {...}}
            yield entry.get("request", entry)


def plugin_run_ids_held_by_workers(inspect):
    """IDs of the plugin runs that Celery workers currently hold, or None if no worker answered."""
    replies = [inspect.active(), inspect.reserved(), inspect.scheduled()]
    if any(reply is None for reply in replies):
        return None

    ids = set()
    for reply in replies:
        for request in _task_requests(reply):
            if request.get("name") != RUN_PLUGIN_TASK:
                continue
            args = request.get("args") or []
            payload = args[0] if args else None
            if isinstance(payload, dict) and payload.get("plugin_run"):
                ids.add(str(payload["plugin_run"]))
    return ids


def reconcile_plugin_runs(inspect=None) -> int:
    """Mark RUNNING/WAITING runs that no worker holds as UNKNOWN; return how many changed.

    Never raises: a failure is logged and leaves every run as it was.
    """
    from backend.models import PluginRun
    from backend.utils.events import publish_plugin_run

    try:
        if inspect is None:
            from sportvid.celery import app
            inspect = app.control.inspect()
        held = plugin_run_ids_held_by_workers(inspect)
        if held is None:
            logger.warning("Plugin run reconciliation skipped: no Celery worker answered")
            return 0

        orphaned = list(
            PluginRun.objects.filter(status__in=[PluginRun.STATUS_RUNNING, PluginRun.STATUS_WAITING])
            .exclude(id__in=held)
        )
        if not orphaned:
            return 0

        now = timezone.now()
        PluginRun.objects.filter(id__in=[run.id for run in orphaned]).update(
            status=PluginRun.STATUS_UNKNOWN, update_date=now
        )
        logger.warning("Set %d plugin runs without a Celery task to UNKNOWN", len(orphaned))
    except Exception:
        logger.exception("Plugin run reconciliation failed; no run was changed")
        return 0

    # .update() skips post_save, so push the change to the browsers explicitly.
    for run in orphaned:
        run.status, run.update_date = PluginRun.STATUS_UNKNOWN, now
        try:
            publish_plugin_run(run)
        except Exception:
            logger.warning("Failed to publish plugin run %s", run.id, exc_info=True)
    return len(orphaned)
