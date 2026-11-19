"""Recovery of plugin runs whose Celery task is gone.

When a worker restarts or crashes, the run it was executing stays RUNNING (or WAITING)
in the database, because `run_plugin` is acknowledged when a worker takes it and is not
redelivered. `recover_plugin_runs()` handles such runs in two steps:

1. Mark: RUNNING/WAITING runs that no worker holds become UNKNOWN with the failure reason
   `interrupted`. This needs one answering worker.
2. Re-queue: an interrupted run is started again, once, when that is safe (see
   `_plan_requeue`). This needs an answer from a worker of every queue, so a worker
   that is merely slow to answer cannot make its runs look orphaned and start them twice.

It runs before gunicorn starts (`manage.py reconcile_plugin_runs`) and when a Celery worker
becomes ready (`sportvid/celery.py`), never in AppConfig.ready(). Several passes may run at
the same time: every status change is a compare-and-set on the row.

QUEUED runs are left alone: their task may still wait in the broker queue, which
celery's inspect() cannot see. The broker keeps its queue across restarts (Valkey
append-only file, see the compose files).
"""
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from backend.log_context import log_event

logger = logging.getLogger(__name__)

RUN_PLUGIN_TASK = "backend.plugin_manager.run_plugin"

# failure_reason type of a run that reconciliation found without a task
INTERRUPTED = "interrupted"
# automatic restarts one run gets; a run that is interrupted again probably caused the crash
MAX_AUTOMATIC_RESTARTS = 1


def _task_requests(reply):
    """Flatten one inspect() reply ({worker: [entry, ...]}) into task request dicts."""
    for entries in (reply or {}).values():
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            # scheduled() wraps the request: {"eta": ..., "priority": ..., "request": {...}}
            yield entry.get("request", entry)


def _run_key(run_id):
    """One spelling for a run ID, whether it comes from a task payload or a model."""
    try:
        return uuid.UUID(str(run_id)).hex
    except ValueError:
        return str(run_id)


def _snapshot(inspect):
    """(run keys held by workers, names of the workers that answered every query), or None
    if no worker answered."""
    replies = [inspect.active(), inspect.reserved(), inspect.scheduled()]
    if any(reply is None for reply in replies):
        return None

    held = set()
    for reply in replies:
        for request in _task_requests(reply):
            if request.get("name") != RUN_PLUGIN_TASK:
                continue
            args = request.get("args") or []
            payload = args[0] if args else None
            if isinstance(payload, dict) and payload.get("plugin_run"):
                held.add(_run_key(payload["plugin_run"]))
    workers = set(replies[0]) & set(replies[1]) & set(replies[2])
    return held, workers


def plugin_run_ids_held_by_workers(inspect):
    """Keys (hex IDs) of the plugin runs that Celery workers currently hold, or None if no worker answered."""
    snapshot = _snapshot(inspect)
    return None if snapshot is None else snapshot[0]


def expected_worker_queues():
    """The queues that each need an answering worker before runs are re-queued."""
    return [queue.name for queue in settings.CELERY_TASK_QUEUES]


def all_queues_answered(worker_names):
    """True if a worker of every queue is among `worker_names` (workers are named <queue>@<host>)."""
    return all(
        any(str(name).startswith(f"{queue}@") for name in worker_names)
        for queue in expected_worker_queues()
    )


def _publish(run):
    from backend.utils.events import publish_plugin_run

    # .update() skips post_save, so the change is pushed to the browsers explicitly.
    try:
        publish_plugin_run(run)
    except Exception:
        logger.warning("Failed to publish plugin run %s", run.id, exc_info=True)


def _mark_interrupted(orphaned):
    """Set the orphaned runs UNKNOWN; returns the ones that were still RUNNING/WAITING."""
    from backend.models import PluginRun

    marked = []
    for run in orphaned:
        now = timezone.now()
        reason = {
            "type": INTERRUPTED,
            "message": "The run was interrupted by a restart of the worker that executed it",
            # when the run was last heard of; update_date itself moves with this write
            "details": {"last_update": run.update_date.isoformat() if run.update_date else None},
        }
        updated = PluginRun.objects.filter(
            id=run.id, status__in=[PluginRun.STATUS_RUNNING, PluginRun.STATUS_WAITING]
        ).update(status=PluginRun.STATUS_UNKNOWN, eta_seconds=None, failure_reason=reason, update_date=now)
        if not updated:
            continue  # finished or deleted meanwhile
        run.status, run.eta_seconds, run.failure_reason, run.update_date = (
            PluginRun.STATUS_UNKNOWN, None, reason, now,
        )
        marked.append(run)
    if marked:
        logger.warning("Set %d plugin runs without a Celery task to UNKNOWN", len(marked))
    for run in marked:
        _publish(run)
    return marked


def _plan_requeue(run):
    """(None, validated parameters) if `run` can be started again automatically, else (why not, None)."""
    from backend.models import PluginRunResult
    from backend.plugin_manager import PluginManager
    from rest_framework import serializers

    if run.restart_count >= MAX_AUTOMATIC_RESTARTS:
        return "interrupted_again", None
    # after a long outage, old runs are not started out of the blue
    last_update = parse_datetime(((run.failure_reason or {}).get("details") or {}).get("last_update") or "")
    if last_update is None or timezone.now() - last_update > timedelta(seconds=settings.PLUGIN_RUN_REQUEUE_WINDOW):
        return "too_old", None
    if "_files" in (run.parameters or {}):
        # only the names of uploaded files are recorded; the files are gone
        return "uploaded_files", None
    if run.request_parameters is None:
        return "no_request_parameters", None
    owner = run.video.owner
    if owner is None or not owner.is_active:
        return "owner_missing", None
    if not PluginManager.has_plugin(run.type):
        return "unknown_plugin", None
    if PluginRunResult.objects.filter(plugin_run=run).exists():
        # the task got as far as storing results; a second run would store them twice
        return "has_results", None
    # Validated like a new run: the release that started it may have had other rules.
    try:
        return None, PluginManager.validate_parameters(run.type, dict(run.request_parameters))
    except serializers.ValidationError:
        return "parameters_invalid", None


def _requeue(run, parameters):
    """Start an interrupted run again under the same row with the validated `parameters`;
    returns whether it was enqueued."""
    from backend.models import PluginRun
    from backend.plugin_manager import _recordable_parameters, build_task_payload, run_plugin

    now = timezone.now()
    recorded = _recordable_parameters(parameters)
    # Compare-and-set: of several passes that see the same interrupted run, one wins.
    updated = PluginRun.objects.filter(
        id=run.id, status=PluginRun.STATUS_UNKNOWN, restart_count=run.restart_count
    ).update(
        status=PluginRun.STATUS_QUEUED,
        progress=0.0,
        eta_seconds=None,
        failure_reason=None,
        outcome=None,
        parameters=recorded,
        # run_plugin stops when it finds this set ("already picked up")
        in_scheduler=False,
        restart_count=run.restart_count + 1,
        task_id=None,
        update_date=now,
    )
    if not updated:
        return False

    # The run does not record who started it; an admin's run on another user's video is
    # continued in the name of the video's owner.
    payload = build_task_payload(run.type, parameters, run.video, run.video.owner, run)
    try:
        task = run_plugin.apply_async(args=[payload])
    except Exception:
        logger.exception("Failed to re-queue plugin run %s", run.id.hex)
        # back to interrupted with the retry unspent, so the next pass tries again
        PluginRun.objects.filter(id=run.id, status=PluginRun.STATUS_QUEUED, task_id=None).update(
            status=PluginRun.STATUS_UNKNOWN, failure_reason=run.failure_reason, parameters=run.parameters,
            restart_count=run.restart_count, update_date=timezone.now(),
        )
        return False
    PluginRun.objects.filter(id=run.id).update(task_id=task.id)

    log_event(logger, "plugin_run.requeue", plugin_run_id=run.id.hex, plugin=run.type,
              video_id=run.video_id.hex, restart_count=run.restart_count + 1)
    run.status, run.progress, run.eta_seconds, run.failure_reason, run.outcome, run.parameters = (
        PluginRun.STATUS_QUEUED, 0.0, None, None, None, recorded,
    )
    run.restart_count += 1
    run.update_date = now
    _publish(run)
    return True


def _requeue_interrupted(held):
    """Re-queue the interrupted runs that qualify; returns how many were enqueued."""
    from backend.models import PluginRun

    cutoff = timezone.now() - timedelta(seconds=settings.PLUGIN_RUN_REQUEUE_WINDOW)
    interrupted = PluginRun.objects.filter(
        status=PluginRun.STATUS_UNKNOWN, update_date__gte=cutoff
    ).select_related("video__owner")

    requeued = 0
    for run in interrupted:
        reason = run.failure_reason
        if not isinstance(reason, dict) or reason.get("type") != INTERRUPTED:
            continue
        if (reason.get("details") or {}).get("not_requeued"):
            continue  # decided in an earlier pass
        if _run_key(run.id) in held:
            continue  # marked while its worker was slow to answer; it is still running
        try:
            blocker, parameters = _plan_requeue(run)
            if blocker is None:
                requeued += _requeue(run, parameters)
                continue
        except Exception:
            logger.exception("Failed to re-queue plugin run %s", run.id.hex)
            continue
        # stays UNKNOWN; the reason is kept so later passes skip the run
        PluginRun.objects.filter(id=run.id, status=PluginRun.STATUS_UNKNOWN).update(
            failure_reason={**reason, "details": {**(reason.get("details") or {}), "not_requeued": blocker}}
        )
        log_event(logger, "plugin_run.requeue_skipped", plugin_run_id=run.id.hex, plugin=run.type,
                  reason=blocker, restart_count=run.restart_count)
    return requeued


def recover_plugin_runs(inspect=None):
    """Mark orphaned runs UNKNOWN and re-queue the interrupted ones that qualify.

    Returns (marked, requeued). Never raises: a failure is logged and leaves the
    remaining runs as they were.
    """
    from backend.models import PluginRun

    marked, requeued = [], 0
    try:
        # Read before asking the workers: a run that is RUNNING now and whose task is alive
        # is in the answer that follows. The other order could miss a task that started
        # between the two steps and take its run for an orphan.
        candidates = list(
            PluginRun.objects.filter(status__in=[PluginRun.STATUS_RUNNING, PluginRun.STATUS_WAITING])
        )
        if inspect is None:
            from sportvid.celery import app
            # each of the three queries waits this long for replies; a worker that misses it
            # only postpones the re-queue (all_queues_answered)
            inspect = app.control.inspect(timeout=2.0)
        snapshot = _snapshot(inspect)
        if snapshot is None:
            logger.warning("Plugin run reconciliation skipped: no Celery worker answered")
            return 0, 0
        held, workers = snapshot

        marked = _mark_interrupted([run for run in candidates if _run_key(run.id) not in held])

        if settings.PLUGIN_RUN_REQUEUE_WINDOW > 0:
            if all_queues_answered(workers):
                requeued = _requeue_interrupted(held)
            else:
                logger.info(
                    "Interrupted plugin runs are not re-queued yet: need a worker of each queue %s, got %s",
                    expected_worker_queues(), sorted(workers),
                )
    except Exception:
        logger.exception("Plugin run reconciliation failed")
    return len(marked), requeued


def reconcile_plugin_runs(inspect=None) -> int:
    """recover_plugin_runs(); returns how many runs were marked UNKNOWN."""
    return recover_plugin_runs(inspect)[0]


def wait_for_workers(seconds, poll=2.0):
    """Wait up to `seconds` until a worker of every queue answers a ping; returns whether they did."""
    import time

    from sportvid.celery import app

    deadline = time.monotonic() + seconds
    while True:
        try:
            if all_queues_answered(app.control.inspect().ping() or {}):
                return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll)
