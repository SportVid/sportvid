"""The worker side of a plugin run: run_plugin moves a PluginRun QUEUED -> RUNNING -> DONE/ERROR.

The plugin itself is a stand-in; these tests pin the state machine around it (T12, T17),
which every backend plugin relies on.
"""
import json
import os

import pytest
from celery.exceptions import MaxRetriesExceededError, Retry
from django.conf import settings

from backend.models import PluginRun, PluginRunResult
from backend.plugin_manager import run_plugin
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def video(db):
    return make_video(make_user())


def _payload(run, plugin=None, parameters=None):
    return {
        "plugin": plugin or run.type,
        "parameters": parameters or {},
        "video": str(run.video.id),
        "user": str(run.video.owner.id),
        "plugin_run": str(run.id),
        "dry_run": False,
    }


def _statuses(published_events, run):
    return [p["entry"]["status"] for _, p in published_events
            if p.get("type") == "plugin_run.update" and p["entry"]["id"] == run.id.hex]


def test_successful_run_ends_done(video, register_plugin, published_events):
    seen = {}

    def call(self, parameters=None, user=None, video=None, plugin_run=None, **kwargs):
        seen.update(parameters=parameters, user=user, video=video, status=plugin_run.status)
        return {}

    register_plugin("fake", call)
    run = make_run(video, type="fake", eta_seconds=12.0)
    run_plugin(_payload(run, parameters={"k": 1}))

    run.refresh_from_db()
    assert (run.status, run.progress, run.eta_seconds) == (PluginRun.STATUS_DONE, 1.0, None)
    assert run.in_scheduler
    # the plugin sees the run as RUNNING, and the frontend was told before the work started
    assert seen == {"parameters": {"k": 1}, "user": video.owner, "video": video, "status": PluginRun.STATUS_RUNNING}
    assert _statuses(published_events, run)[-2:] == ["RUNNING", "DONE"]


def test_results_are_written_to_the_result_cache(video, register_plugin):
    from data import DataManager

    os.makedirs(settings.DATA_CACHE_ROOT, exist_ok=True)

    def call(self, plugin_run=None, **kwargs):
        with DataManager("/predictions/").create_data("ScalarData") as scalar:
            scalar.y = [0.5, 1.0]
            scalar.time = [0.0, 1.0]
            scalar.delta_time = 1.0
        result = PluginRunResult.objects.create(
            plugin_run=plugin_run, name="score", data_id=scalar.id, type=PluginRunResult.TYPE_SCALAR
        )
        return {"plugin_run_results": [result.id]}

    register_plugin("fake", call)
    run = make_run(video, type="fake")
    run_plugin(_payload(run))

    result = PluginRunResult.objects.get(plugin_run=run)
    with open(os.path.join(settings.DATA_CACHE_ROOT, f"{result.id}.json")) as f:
        cached = json.load(f)
    assert cached["id"] == result.id.hex
    assert cached["data"]["y"] == [0.5, 1.0]


def test_run_deleted_while_queued_is_skipped(video, register_plugin):
    called = []
    register_plugin("fake", lambda self, **kwargs: called.append(1) or {})
    run = make_run(video, type="fake")
    payload = _payload(run)
    run.delete()

    run_plugin(payload)  # no exception, no work
    assert called == []


def test_redelivered_task_does_not_run_twice(video, register_plugin):
    """A task already picked up once (in_scheduler) is not started again, e.g. after a broker redelivery."""
    called = []
    register_plugin("fake", lambda self, **kwargs: called.append(1) or {})
    run = make_run(video, type="fake", status=PluginRun.STATUS_RUNNING, in_scheduler=True, progress=0.4)
    run_plugin(_payload(run))

    run.refresh_from_db()
    assert called == []
    assert (run.status, run.progress) == (PluginRun.STATUS_RUNNING, 0.4)


@pytest.mark.parametrize("dependency_status", [PluginRun.STATUS_QUEUED, PluginRun.STATUS_RUNNING])
def test_waits_for_an_unfinished_dependency(video, register_plugin, dependency_status):
    called = []
    register_plugin("fake", lambda self, **kwargs: called.append(1) or {})
    tracker = make_run(video, type="object_tracker", status=dependency_status)
    run = make_run(video, type="fake")

    with pytest.raises(Retry):
        run_plugin(_payload(run, parameters={"object_tracker_id": tracker.id.hex}))

    run.refresh_from_db()
    assert called == []
    # still claimable by the retry: the in_scheduler guard must not be set yet
    assert (run.status, run.in_scheduler) == (PluginRun.STATUS_QUEUED, False)


@pytest.mark.parametrize("parameter", ["object_tracker_id", "object_tracker_run_id"])
def test_runs_once_the_dependency_is_done(video, register_plugin, parameter):
    register_plugin("fake", lambda self, **kwargs: {})
    tracker = make_run(video, type="object_tracker", status=PluginRun.STATUS_DONE)
    run = make_run(video, type="fake")
    run_plugin(_payload(run, parameters={parameter: tracker.id.hex}))

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_DONE


def test_gives_up_when_the_dependency_never_finishes(video, register_plugin, monkeypatch):
    register_plugin("fake", lambda self, **kwargs: {})
    tracker = make_run(video, type="object_tracker", status=PluginRun.STATUS_RUNNING)
    run = make_run(video, type="fake")

    def retry(*args, **kwargs):
        raise MaxRetriesExceededError()

    monkeypatch.setattr(run_plugin, "retry", retry)
    run_plugin(_payload(run, parameters={"object_tracker_id": tracker.id.hex}))

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason["type"] == "dependency_timeout"
    assert run.failure_reason["details"] == {"plugin_run_id": tracker.id.hex, "plugin": "object_tracker"}


# waiting for the video's HLS conversion

@pytest.fixture
def retries(monkeypatch):
    """Record run_plugin.retry calls; each one raises Retry as Celery does."""
    calls = []

    def retry(*args, **kwargs):
        calls.append(kwargs)
        raise Retry()

    monkeypatch.setattr(run_plugin, "retry", retry)
    return calls


def test_waits_while_the_video_is_converting(video, register_plugin, retries, published_events):
    from backend.models import Video

    called = []
    register_plugin("fake", lambda self, **kwargs: called.append(1) or {})
    video.status = Video.STATUS_PROCESSING
    video.save()
    run = make_run(video, type="fake")

    with pytest.raises(Retry):
        run_plugin(_payload(run))

    run.refresh_from_db()
    assert called == []
    assert (run.status, run.in_scheduler) == (PluginRun.STATUS_WAITING, False)
    assert _statuses(published_events, run)[-1] == "WAITING"
    [retry] = retries
    assert retry["args"][0]["conversion_retries"] == 1
    assert retry["countdown"] * retry["max_retries"] == 7200  # as long as the conversion's time limit


def test_runs_once_the_conversion_is_done(video, register_plugin):
    register_plugin("fake", lambda self, **kwargs: {})
    run = make_run(video, type="fake", status=PluginRun.STATUS_WAITING)

    run_plugin({**_payload(run), "conversion_retries": 30})

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_DONE


def test_gives_up_when_the_conversion_never_finishes(video, register_plugin, monkeypatch):
    from backend.models import Video

    register_plugin("fake", lambda self, **kwargs: {})
    video.status = Video.STATUS_PROCESSING
    video.save()
    run = make_run(video, type="fake")

    def retry(*args, **kwargs):
        raise MaxRetriesExceededError()

    monkeypatch.setattr(run_plugin, "retry", retry)
    run_plugin(_payload(run))

    run.refresh_from_db()
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason["type"] == "video_conversion_timeout"


def test_conversion_wait_does_not_use_up_the_dependency_wait(video, register_plugin, retries):
    register_plugin("fake", lambda self, **kwargs: {})
    tracker = make_run(video, type="object_tracker", status=PluginRun.STATUS_RUNNING)
    run = make_run(video, type="fake")

    with pytest.raises(Retry):
        run_plugin({**_payload(run, parameters={"object_tracker_id": tracker.id.hex}), "conversion_retries": 50})

    assert retries[0]["max_retries"] == 360 + 50
