"""plugin/run/result/list. exclude_types[] makes a light listing: the listed types are left out and
the others come without data (the analysis view loads data per run on demand)."""
from tests.characterization.authz.conftest import as_user, world  # noqa: F401


def _entries(client, **params):
    response = client.get("/plugin/run/result/list", params)
    assert response.json()["status"] == "ok"
    return {e["id"]: e for e in response.json()["entries"]}


def test_results_come_with_their_data(as_user, world):
    entries = _entries(as_user("alice"), video_id=world.video.id.hex)
    assert entries[world.result.id.hex]["data"]["bboxes"] == '{"0": [[1, 3, 0.1, 0.1, 0.2, 0.2]]}'


def test_excluded_types_are_left_out(as_user, world):
    entries = _entries(as_user("alice"), video_id=world.video.id.hex, **{"exclude_types[]": ["BBOXES"]})
    assert world.result.id.hex not in entries


def test_other_types_come_without_data_when_excluding(as_user, world):
    entries = _entries(as_user("alice"), video_id=world.video.id.hex, **{"exclude_types[]": ["KPI", "POS"]})
    assert "data" not in entries[world.result.id.hex]


def test_results_of_one_run(as_user, world):
    entries = _entries(as_user("alice"), plugin_run_id=world.plugin_run.id.hex)
    assert list(entries) == [world.result.id.hex]
