"""A plugin run interrupted by a worker restart is started again once, when that is safe."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import serializers

from backend.models import PluginRun, PluginRunResult
from backend.plugin_manager import PluginManager
from backend.plugin_runs import recover_plugin_runs
from tests.factories import make_run, make_user, make_video

RUN_PLUGIN = "backend.plugin_manager.run_plugin"


class Workers:
    """celery.app.control.inspect() of the given workers; `active` lists the runs they hold."""

    def __init__(self, names=("io@host", "gpu@host"), active=()):
        self.names = names
        self._active = [
            {"id": uuid.uuid4().hex, "name": RUN_PLUGIN, "args": [{"plugin_run": str(run.id)}], "kwargs": {}}
            for run in active
        ]

    def active(self):
        return {name: (self._active if name.startswith("io@") else []) for name in self.names} or None

    def reserved(self):
        return {name: [] for name in self.names} or None

    scheduled = reserved


@pytest.fixture
def video(db, register_plugin):
    register_plugin("fake", lambda self, **kwargs: {})
    return make_video(make_user())


def interrupted(video, **fields):
    """A run that was RUNNING when its worker went away."""
    fields = {"type": "fake", "status": PluginRun.STATUS_RUNNING, "parameters": {"fps": 5},
              "progress": 0.4, "in_scheduler": True, "task_id": "old-task", **fields}
    # as PluginManager.run stores them; without a serializer both are the same
    fields.setdefault("request_parameters", None if "_files" in fields["parameters"] else fields["parameters"])
    return make_run(video, **fields)


def requeues(enqueued_tasks):
    return [kwargs["args"][0] for name, args, kwargs in enqueued_tasks if name == "run_plugin"]


def not_requeued(run):
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_UNKNOWN
    return run.failure_reason["details"].get("not_requeued")


def test_interrupted_run_is_queued_again_under_the_same_row(video, enqueued_tasks, published_events):
    run = interrupted(video)

    assert recover_plugin_runs(Workers()) == (1, 1)

    run.refresh_from_db()
    assert (run.status, run.restart_count, run.progress) == (PluginRun.STATUS_QUEUED, 1, 0.0)
    assert (run.in_scheduler, run.failure_reason) == (False, None)  # in_scheduler set would stop the new task
    assert run.task_id not in (None, "old-task")
    [payload] = requeues(enqueued_tasks)
    assert payload == {
        "plugin": "fake", "parameters": {"fps": 5}, "video": str(video.id), "user": str(video.owner.id),
        "plugin_run": str(run.id), "dry_run": False, "kwargs": {},
    }
    statuses = [p["entry"]["status"] for _, p in published_events
                if p.get("type") == "plugin_run.update" and p["entry"]["id"] == run.id.hex]
    assert statuses[-2:] == ["UNKNOWN", "QUEUED"]


def test_waiting_runs_are_queued_again_too(video, enqueued_tasks):
    run = interrupted(video, status=PluginRun.STATUS_WAITING, in_scheduler=False)
    assert recover_plugin_runs(Workers()) == (1, 1)
    assert len(requeues(enqueued_tasks)) == 1


def test_second_interruption_stays_unknown(video, enqueued_tasks):
    run = interrupted(video, restart_count=1)

    assert recover_plugin_runs(Workers()) == (1, 0)

    assert not_requeued(run) == "interrupted_again"
    assert requeues(enqueued_tasks) == []


def test_run_held_by_a_worker_is_left_alone(video, enqueued_tasks):
    run = interrupted(video)
    assert recover_plugin_runs(Workers(active=[run])) == (0, 0)
    run.refresh_from_db()
    assert (run.status, run.restart_count) == (PluginRun.STATUS_RUNNING, 0)


def test_nothing_is_requeued_until_a_worker_of_every_queue_answers(video, enqueued_tasks):
    """A worker that answers too slowly must not have its runs started a second time."""
    run = interrupted(video)

    assert recover_plugin_runs(Workers(names=("io@host",))) == (1, 0)
    run.refresh_from_db()
    assert (run.status, requeues(enqueued_tasks)) == (PluginRun.STATUS_UNKNOWN, [])

    # the next pass, e.g. when the gpu worker is ready, picks the marked run up
    assert recover_plugin_runs(Workers()) == (0, 1)
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_QUEUED


def test_marked_run_that_is_still_running_is_not_requeued(video, enqueued_tasks):
    run = interrupted(video)
    recover_plugin_runs(Workers(names=("gpu@host",)))  # io answered too late: marked by mistake

    assert recover_plugin_runs(Workers(active=[run])) == (0, 0)
    assert requeues(enqueued_tasks) == []


def test_runs_with_uploaded_files_are_not_requeued(video, enqueued_tasks):
    run = interrupted(video, parameters={"_files": {"positions": "pos.csv"}})
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "uploaded_files"
    assert requeues(enqueued_tasks) == []


def test_runs_that_stored_results_are_not_requeued(video, enqueued_tasks):
    run = interrupted(video)
    PluginRunResult.objects.create(plugin_run=run, name="r", type=PluginRunResult.TYPE_SCALAR)
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "has_results"


def test_runs_last_heard_of_before_the_window_are_not_requeued(video, enqueued_tasks, settings):
    run = interrupted(video)
    PluginRun.objects.filter(id=run.id).update(update_date=timezone.now() - timedelta(hours=30))
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "too_old"


def test_runs_of_an_inactive_owner_are_not_requeued(video, enqueued_tasks):
    run = interrupted(video)
    video.owner.is_active = False
    video.owner.save()
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "owner_missing"


def test_runs_of_a_plugin_that_no_longer_exists_are_not_requeued(video, enqueued_tasks):
    run = interrupted(video, type="removed_plugin")
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "unknown_plugin"


class _Tracker(serializers.Serializer):
    """Like the real serializers: the output has server-side values the input may not contain."""
    fps = serializers.IntegerField(max_value=10)

    def validate(self, attrs):
        if "checkpoint" in self.initial_data:
            raise serializers.ValidationError("checkpoint is chosen by the server")
        return {**attrs, "checkpoint": "/models/current.pt"}


def test_run_is_validated_again_from_what_was_submitted(video, enqueued_tasks, monkeypatch):
    """The stored validated parameters come from the release that started the run; the
    re-queued run gets what this release makes of the submitted ones."""
    monkeypatch.setitem(PluginManager._serializers, "fake", _Tracker)
    run = interrupted(video, parameters={"fps": 5, "checkpoint": "/models/old.pt"}, request_parameters={"fps": 5})

    assert recover_plugin_runs(Workers()) == (1, 1)

    run.refresh_from_db()
    assert run.parameters == {"fps": 5, "checkpoint": "/models/current.pt"}
    assert requeues(enqueued_tasks)[0]["parameters"] == {"fps": 5, "checkpoint": "/models/current.pt"}


def test_parameters_the_current_serializer_rejects_are_not_sent_again(video, enqueued_tasks, monkeypatch):
    monkeypatch.setitem(PluginManager._serializers, "fake", _Tracker)
    run = interrupted(video, parameters={"fps": 50}, request_parameters={"fps": 50})
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "parameters_invalid"
    assert run.parameters == {"fps": 50}


def test_runs_from_before_the_submitted_parameters_were_stored_are_not_requeued(video, enqueued_tasks):
    run = interrupted(video, request_parameters=None)
    recover_plugin_runs(Workers())
    assert not_requeued(run) == "no_request_parameters"


def test_starting_a_run_stores_what_was_submitted(video, monkeypatch):
    monkeypatch.setitem(PluginManager._serializers, "fake", _Tracker)
    result = PluginManager().run("fake", video=video, user=video.owner, parameters={"fps": 5, "_files": {}})
    run = PluginRun.objects.get(id=result["plugin_run_id"])
    assert run.request_parameters == {"fps": 5, "_files": {}}
    assert run.parameters == {"fps": 5, "checkpoint": "/models/current.pt"}


def test_a_run_with_uploaded_files_stores_no_submitted_parameters(video):
    files = {"positions": {"value": "pos.csv", "path": "/tmp/x/pos.csv"}}
    result = PluginManager().run("fake", video=video, user=video.owner, parameters={"_files": files})
    run = PluginRun.objects.get(id=result["plugin_run_id"])
    assert run.request_parameters is None
    assert run.parameters == {"_files": {"positions": "pos.csv"}}


def test_skipped_runs_are_decided_once(video, enqueued_tasks, monkeypatch):
    run = interrupted(video, restart_count=1)
    recover_plugin_runs(Workers())
    PluginRun.objects.filter(id=run.id).update(restart_count=0)  # would qualify now
    assert recover_plugin_runs(Workers()) == (0, 0)


def test_requeue_can_be_turned_off(video, enqueued_tasks, settings):
    settings.PLUGIN_RUN_REQUEUE_WINDOW = 0
    run = interrupted(video)
    assert recover_plugin_runs(Workers()) == (1, 0)
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_UNKNOWN


def test_failed_enqueue_leaves_the_run_for_the_next_pass(video, monkeypatch):
    from backend import plugin_manager

    run = interrupted(video)

    def broker_down(*args, **kwargs):
        raise ConnectionError("broker down")
    monkeypatch.setattr(plugin_manager.run_plugin, "apply_async", broker_down)

    assert recover_plugin_runs(Workers()) == (1, 0)
    run.refresh_from_db()
    assert (run.status, run.restart_count) == (PluginRun.STATUS_UNKNOWN, 0)
    assert run.failure_reason["type"] == "interrupted" and "not_requeued" not in run.failure_reason["details"]


def test_other_unknown_runs_are_never_started(video, enqueued_tasks):
    """UNKNOWN is also the status of old rows; only runs marked as interrupted are candidates."""
    make_run(video, type="fake", status=PluginRun.STATUS_UNKNOWN)
    assert recover_plugin_runs(Workers()) == (0, 0)
    assert requeues(enqueued_tasks) == []


def test_requeued_run_executes(video, enqueued_tasks):
    """The re-queued payload goes through run_plugin like a fresh run (in_scheduler was reset)."""
    from backend.plugin_manager import run_plugin

    run = interrupted(video)
    recover_plugin_runs(Workers())
    run_plugin(requeues(enqueued_tasks)[0])
    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_DONE
