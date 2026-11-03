"""Startup reconciliation must never break the app and must read every inspect() format."""
import uuid

import pytest
from django.apps import apps

from backend.models import PluginRun
from tests.characterization.reconcile.test_reconcile_plugin_runs import (  # noqa: F401
    FakeInspect, fake_inspect, reconcile, runs, status, task_entry,
)


def test_other_tasks_in_the_queue_do_not_crash_it(fake_inspect, runs):
    """convert_video_to_hls has a hex string as its first argument (crashed ready() before)."""
    running, orphan = runs(PluginRun.STATUS_RUNNING), runs(PluginRun.STATUS_RUNNING)
    hls = {"id": uuid.uuid4().hex, "name": "backend.tasks.convert_video.convert_video_to_hls",
           "args": [uuid.uuid4().hex, ".mp4", []], "kwargs": {}}
    fake_inspect["inspect"] = FakeInspect(active=[hls, task_entry(running)])
    reconcile()
    assert (status(running), status(orphan)) == (PluginRun.STATUS_RUNNING, PluginRun.STATUS_UNKNOWN)


def test_scheduled_entries_are_unwrapped(fake_inspect, runs):
    """scheduled() wraps each request in {"eta", "priority", "request"} (KeyError before)."""
    waiting = runs(PluginRun.STATUS_WAITING)
    fake_inspect["inspect"] = FakeInspect(scheduled=[{"eta": None, "priority": 0, "request": task_entry(waiting)}])
    reconcile()
    assert status(waiting) == PluginRun.STATUS_WAITING


def test_failing_inspect_changes_nothing(fake_inspect, runs):
    running = runs(PluginRun.STATUS_RUNNING)

    class Broken(FakeInspect):
        def active(self):
            raise ConnectionError("broker down")

    fake_inspect["inspect"] = Broken()
    reconcile()
    assert status(running) == PluginRun.STATUS_RUNNING


def test_orphaned_runs_are_published_to_their_owner(fake_inspect, runs, published_events):
    orphan = runs(PluginRun.STATUS_RUNNING)
    fake_inspect["inspect"] = FakeInspect()
    published_events.clear()  # drop the post_save event from creating the run
    reconcile()
    updates = [p["entry"] for _, p in published_events if p["type"] == "plugin_run.update"]
    assert [e["id"] for e in updates] == [orphan.id.hex]


def test_app_ready_does_not_touch_celery_or_the_database(fake_inspect, runs, django_assert_num_queries):
    running = runs(PluginRun.STATUS_RUNNING)

    class Explodes(FakeInspect):
        def active(self):
            raise AssertionError("ready() must not inspect Celery")

    fake_inspect["inspect"] = Explodes()
    with django_assert_num_queries(0):
        apps.get_app_config("backend").ready()
    assert status(running) == PluginRun.STATUS_RUNNING
