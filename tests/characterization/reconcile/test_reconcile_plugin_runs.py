"""Characterization: startup reconciliation of unfinished plugin runs.

At startup, runs that no Celery worker reports any more are marked UNKNOWN. The fake
inspect below answers like celery.app.control.inspect() does.
"""
import uuid

import pytest

from backend.models import PluginRun, Video

RUN_PLUGIN = "backend.plugin_manager.run_plugin"


def reconcile():
    """The seam under test: startup reconciliation, run once at backend start."""
    from django.core.management import call_command

    call_command("reconcile_plugin_runs", wait_for_workers=0)


class FakeInspect:
    def __init__(self, active=None, reserved=None, scheduled=None, answer=True):
        self._active, self._reserved, self._scheduled = active or [], reserved or [], scheduled or []
        self._answer = answer

    def _reply(self, entries):
        return {"io@worker": entries} if self._answer else None

    def active(self):
        return self._reply(self._active)

    def reserved(self):
        return self._reply(self._reserved)

    def scheduled(self):
        return self._reply(self._scheduled)

    def ping(self):
        return {"io@worker": {"ok": "pong"}} if self._answer else None


def task_entry(run):
    return {"id": uuid.uuid4().hex, "name": RUN_PLUGIN, "args": [{"plugin_run": str(run.id)}], "kwargs": {}}


@pytest.fixture
def fake_inspect(monkeypatch):
    from sportvid.celery import app

    holder = {}
    monkeypatch.setattr(app.control, "inspect", lambda *a, **k: holder["inspect"])
    return holder


@pytest.fixture
def runs(db):
    from backend.models import SportVidUser

    owner = SportVidUser.objects.create_user("owner", "owner@example.org", "pw")
    video = Video.objects.create(name="v", ext=".mp4", owner=owner)

    def make(status):
        return PluginRun.objects.create(video=video, type="object_tracker", status=status)
    return make


def status(run):
    run.refresh_from_db()
    return run.status


def test_runs_reported_by_a_worker_are_untouched(fake_inspect, runs):
    running = runs(PluginRun.STATUS_RUNNING)
    fake_inspect["inspect"] = FakeInspect(active=[task_entry(running)])
    reconcile()
    assert status(running) == PluginRun.STATUS_RUNNING


def test_running_runs_unknown_to_workers_become_unknown(fake_inspect, runs):
    running, waiting = runs(PluginRun.STATUS_RUNNING), runs(PluginRun.STATUS_WAITING)
    fake_inspect["inspect"] = FakeInspect()
    reconcile()
    assert (status(running), status(waiting)) == (PluginRun.STATUS_UNKNOWN, PluginRun.STATUS_UNKNOWN)


def test_finished_runs_are_untouched(fake_inspect, runs):
    done, error = runs(PluginRun.STATUS_DONE), runs(PluginRun.STATUS_ERROR)
    fake_inspect["inspect"] = FakeInspect()
    reconcile()
    assert (status(done), status(error)) == (PluginRun.STATUS_DONE, PluginRun.STATUS_ERROR)


def test_nothing_changes_when_no_worker_answers(fake_inspect, runs):
    running = runs(PluginRun.STATUS_RUNNING)
    fake_inspect["inspect"] = FakeInspect(answer=False)
    reconcile()
    assert status(running) == PluginRun.STATUS_RUNNING


def test_queued_runs_are_untouched(fake_inspect, runs):
    # Changed on purpose (agreed 2026-10-23): a queued task may still wait in the
    # broker, which inspect() cannot see. Before, every restart flipped them to UNKNOWN.
    queued = runs(PluginRun.STATUS_QUEUED)
    fake_inspect["inspect"] = FakeInspect()
    reconcile()
    assert status(queued) == PluginRun.STATUS_QUEUED
