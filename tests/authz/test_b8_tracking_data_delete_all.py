"""B8: tracking_data/delete with id "all" must only delete the caller's own tracking data."""
import json

from backend.models import PluginRun, TrackingData


def test_delete_all_keeps_other_users_data_and_their_plugin_runs(as_user, world):
    alice_run = PluginRun.objects.create(video=world.video, type="posdata_convert", tracking_data=world.tracking_data)

    response = as_user("bob").post("/tracking_data/delete", json.dumps({"id": "all"}), content_type="application/json")

    assert response.json()["status"] == "ok"
    assert not TrackingData.objects.filter(owner=world.bob).exists()
    assert TrackingData.objects.filter(id=world.tracking_data.id).exists()
    assert PluginRun.objects.filter(id=alice_run.id).exists()


def test_delete_by_id_cannot_delete_other_users_data(as_user, world):
    response = as_user("bob").post(
        "/tracking_data/delete", json.dumps({"id": world.tracking_data.id.hex}), content_type="application/json"
    )
    assert response.json()["status"] == "error"
    assert TrackingData.objects.filter(id=world.tracking_data.id).exists()
