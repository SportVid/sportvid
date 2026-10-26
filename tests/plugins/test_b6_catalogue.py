"""B6: only plugins whose Ray plugins are deployed are offered and accepted."""
import ast
import inspect
import json

import pytest

import backend.tasks  # noqa: F401  (registers the plugins for the parametrization below)
from backend.models import PluginRun, SportVidUser, Video
from backend.plugin_manager import PluginManager


@pytest.fixture
def alice(db, client):
    user = SportVidUser.objects.create_user("alice", "a@example.org", "Correct-Horse-Battery-42")
    client.force_login(user)
    return user


def run_new(client, video, plugin, parameters=None):
    return client.post("/plugin/run/new", json.dumps({"plugin": plugin, "video_id": video.id.hex, "parameters": parameters or {}}),
                       content_type="application/json")


def test_available_lists_plugins_whose_ray_plugins_are_all_deployed(client, alice, deployed_ray_plugins):
    del deployed_ray_plugins["whisper"]  # video_to_audio stays deployed
    plugins = client.get("/plugin/available").json()["plugins"]
    assert "object_tracker" in plugins and "audio_rms" in plugins
    assert "whisper" not in plugins


def test_unavailable_plugin_is_rejected_before_a_run_exists(client, alice, deployed_ray_plugins, enqueued_tasks):
    del deployed_ray_plugins["object_tracker"]
    video = Video.objects.create(owner=alice, name="v", ext=".mp4")
    r = run_new(client, video, "object_tracker")
    assert (r.status_code, r.json()) == (400, {"status": "error", "type": "plugin_unavailable"})
    assert PluginRun.objects.count() == 0 and enqueued_tasks == []


def test_unknown_catalogue_keeps_the_old_behaviour(client, alice, monkeypatch, enqueued_tasks):
    from backend import plugin_catalogue

    monkeypatch.setattr(plugin_catalogue, "deployed_ray_plugins", lambda: None)
    assert client.get("/plugin/available").json() == {"status": "ok", "plugins": None}
    video = Video.objects.create(owner=alice, name="v", ext=".mp4")
    assert run_new(client, video, "object_tracker").json()["status"] == "ok"


def test_available_needs_a_login(client, db):
    assert client.get("/plugin/available").status_code == 401


@pytest.mark.real_catalogue
def test_unreachable_analyser_means_unknown(db, settings):
    from backend import plugin_catalogue

    settings.GRPC_HOST, settings.GRPC_PORT = "127.0.0.1", 1  # nothing listens there
    assert plugin_catalogue.deployed_ray_plugins() is None
    assert plugin_catalogue.available_plugins() is None


@pytest.mark.parametrize("plugin", sorted(PluginManager._plugins) or ["(none)"])
def test_declared_ray_plugins_match_the_task_code(plugin):
    """Task.ray_plugins must list exactly the Ray plugins its run_analyser() calls name."""
    task_cls = PluginManager.get_plugin(plugin)
    tree = ast.parse(inspect.getsource(inspect.getmodule(task_cls)))
    called = {
        node.args[1].value for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "run_analyser"
        and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
    }
    assert set(task_cls.ray_plugins) == called
