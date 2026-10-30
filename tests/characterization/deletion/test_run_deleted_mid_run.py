"""Characterization: a plugin run deleted while its task works on it."""
import pytest

from backend.models import PluginRun
from backend.plugin_manager import run_plugin
from tests.factories import make_run, make_user, make_video


@pytest.fixture
def video(db):
    return make_video(make_user())


def payload(run):
    return {"plugin": run.type, "parameters": {}, "video": str(run.video.id), "user": str(run.video.owner.id),
            "plugin_run": str(run.id), "dry_run": False}


@pytest.mark.parametrize("raises", [False, True], ids=["finishes", "fails"])
def test_finishing_a_deleted_run_inserts_it_again(video, register_plugin, raises):
    """save() on a row that is gone falls back to an INSERT: the deleted run comes back."""
    run = make_run(video, type="fake")

    def call(self, **kwargs):
        PluginRun.objects.filter(id=run.id).delete()  # the user deletes the run meanwhile
        if raises:
            raise RuntimeError("analyser gone")
        return {}
    register_plugin("fake", call)

    run_plugin(payload(run))

    back = PluginRun.objects.get(id=run.id)
    assert back.status == (PluginRun.STATUS_ERROR if raises else PluginRun.STATUS_DONE)
