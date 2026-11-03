"""pitch_filter: tracks whose foot points stay off the pitch become bystanders (or are removed)."""
import json

import pytest

from backend.models import Calibration, CalibrationAssets, PluginRun, PluginRunResult, SportVidUser, Video
from backend.plugin_manager import run_plugin
from backend.serializers.pitch_filter import PitchFilterSerializer
from backend.tasks.pitch_filter import apply_pitch_filter, off_pitch_tracks
from data import DataManager

IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]  # video rel. coords = pitch rel. coords


def row(entity, team, foot_x, foot_y):
    """[entity_id, team_id, game_section, x_center, y_bottom, x, y, w, h, score]"""
    return [entity, team, 0, foot_x, foot_y, foot_x - 0.01, foot_y - 0.05, 0.02, 0.05, 0.9]


def tracklets():
    # track 1 on the pitch; track 2 beyond the touch line (> 3 m); track 3 off for 1 of 4 frames (a throw-in);
    # the ball (entity 0) and a referee (team 2) off the pitch are not judged
    frames = {}
    for i in range(4):
        frames[str(i * 40)] = [
            row(1, 3, 0.5, 0.5),
            row(2, 3, 0.5, 1.2),
            row(3, 3, 1.1 if i == 0 else 0.9, 0.5),
            row(0, 0, 1.5, 1.5),
            row(7, 2, -0.5, 0.5),
        ]
    return frames


def test_off_pitch_tracks():
    off, stats = off_pitch_tracks(tracklets(), IDENTITY, None, 105.0, 68.0, margin_m=3.0, min_outside_fraction=0.5)
    assert off == {2}
    assert stats[1] == (0, 4) and stats[2] == (4, 4) and stats[3] == (1, 4)
    assert 0 not in stats and 7 not in stats


def test_margin_keeps_a_player_near_the_line():
    # 2 m beyond the goal line on a 105 m pitch
    frames = {"0": [row(1, 3, 1.0 + 2.0 / 105.0, 0.5)]}
    assert off_pitch_tracks(frames, IDENTITY, None, 105.0, 68.0, 3.0, 0.5)[0] == set()
    assert off_pitch_tracks(frames, IDENTITY, None, 105.0, 68.0, 1.0, 0.5)[0] == {1}


def test_bystander_and_remove():
    frames = tracklets()
    relabelled = apply_pitch_filter(frames, {2}, "bystander")
    assert all(r[1] == 1 for rows in relabelled.values() for r in rows if r[0] == 2)
    assert all(r[1] == 3 for rows in relabelled.values() for r in rows if r[0] in (1, 3))
    removed = apply_pitch_filter(frames, {2}, "remove")
    assert all(r[0] != 2 for rows in removed.values() for r in rows)
    assert sum(len(rows) for rows in removed.values()) == sum(len(rows) for rows in frames.values()) - 4


def test_serializer_defaults():
    s = PitchFilterSerializer(data={"object_tracker_id": "0" * 32, "calibration_id": "1" * 32})
    assert s.is_valid(), s.errors
    assert s.validated_data["margin_m"] == 3.0 and s.validated_data["min_outside_fraction"] == 0.5
    assert s.validated_data["action"] == "bystander"
    assert not PitchFilterSerializer(data={"object_tracker_id": "0" * 32}).is_valid()


@pytest.fixture
def video(db):
    owner = SportVidUser.objects.create_user("owner", "o@example.org", "Correct-Horse-Battery-42")
    return Video.objects.create(owner=owner, name="v", ext=".mp4", width=1920, height=1080,
                                field_length=105.0, field_width=68.0)


def _tracker_run(video):
    run = PluginRun.objects.create(video=video, type="object_tracker", status=PluginRun.STATUS_DONE)
    with DataManager("/predictions/").create_data("BboxesData") as data:
        data.bboxes = json.dumps(tracklets())
        data.meta_data = json.dumps({"video": {"fps": 25.0, "h": 1080, "w": 1920}})
    PluginRunResult.objects.create(plugin_run=run, data_id=data.id, name="bboxes", type=PluginRunResult.TYPE_BBOXES)
    return run


def _run(video, parameters):
    run = PluginRun.objects.create(video=video, type="pitch_filter", status=PluginRun.STATUS_QUEUED)
    run_plugin({
        "plugin": "pitch_filter",
        "parameters": parameters,
        "video": str(video.id),
        "user": str(video.owner.id),
        "plugin_run": str(run.id),
        "dry_run": False,
    })
    run.refresh_from_db()
    return run


def test_task_writes_filtered_tracklets(video):
    tracker = _tracker_run(video)
    asset = CalibrationAssets.objects.create(owner=video.owner, video=video, name="cal", sport="soccer")
    asset.apply_calibration(Calibration.objects.create(calibration_asset=asset, homography_matrix=IDENTITY))

    run = _run(video, {"object_tracker_id": tracker.id.hex, "calibration_id": asset.id.hex})
    assert run.status == PluginRun.STATUS_DONE, run.failure_reason
    assert run.source_plugin_run_id == tracker.id
    result = PluginRunResult.objects.get(plugin_run=run, type=PluginRunResult.TYPE_BBOXES)
    with DataManager("/predictions/").load(result.data_id) as data:
        bboxes, meta = json.loads(data.bboxes), json.loads(data.meta_data)
    teams = {r[0]: r[1] for rows in bboxes.values() for r in rows}
    assert teams == {1: 3, 2: 1, 3: 3, 0: 0, 7: 2}
    assert meta["video"] == {"fps": 25.0, "h": 1080, "w": 1920}
    assert meta["player_ids"]["2"]["team_id"] == 1 and meta["player_ids"]["1"]["team_id"] == 3


def test_task_needs_a_computed_calibration(video):
    tracker = _tracker_run(video)
    asset = CalibrationAssets.objects.create(owner=video.owner, video=video, name="cal", sport="soccer")
    run = _run(video, {"object_tracker_id": tracker.id.hex, "calibration_id": asset.id.hex})
    assert run.status == PluginRun.STATUS_ERROR
    assert run.failure_reason["type"] == "calibration_not_computed"
