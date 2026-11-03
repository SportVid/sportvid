import json
import logging
from collections import defaultdict
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from django.db import transaction

from backend.models import CalibrationAssets, PluginRun, PluginRunResult
from backend.plugin_manager import PluginManager
from backend.utils.lens import apply_homography, undistort_with_snapshot
from backend.utils.task import Task, TaskFailure
from data import DataManager, compute_bboxes_meta

# TeamId of the tracklet format (inference_ray plugins/tracker/tracklets.py)
TEAM_BALL = 0
TEAM_BYSTANDER = 1
TEAM_REFEREE = 2
UNTRACKED_ID = 0  # entity id of the ball and of untracked detections

ACTION_BYSTANDER = "bystander"
ACTION_REMOVE = "remove"


def off_pitch_tracks(
    bboxes: Dict[str, list],
    homography: Sequence[Sequence[float]],
    lens_intrinsics: Optional[Dict],
    field_length: float,
    field_width: float,
    margin_m: float,
    min_outside_fraction: float,
) -> Tuple[set, Dict[int, Tuple[int, int]]]:
    """Track ids whose foot points lie outside the pitch (widened by ``margin_m``) in at least
    ``min_outside_fraction`` of the boxes that project, and ``{track_id: (outside, projected)}`` of every track.

    Foot points are undistorted with the calibration's lens snapshot when the homography was fitted on undistorted
    points, as in kpi_computation; one beyond the lens model's valid range (NaN) counts neither way. The ball,
    untracked detections and the referees are not judged."""
    lo_x, hi_x = -margin_m / field_length, 1.0 + margin_m / field_length
    lo_y, hi_y = -margin_m / field_width, 1.0 + margin_m / field_width
    counts = defaultdict(lambda: [0, 0])  # tid -> [outside, projected]
    for rows in bboxes.values():
        rows = [r for r in rows if int(r[0]) != UNTRACKED_ID and int(r[1]) not in (TEAM_BALL, TEAM_REFEREE)]
        if not rows:
            continue
        feet = undistort_with_snapshot([[r[3], r[4]] for r in rows], lens_intrinsics)
        valid = np.isfinite(feet).all(axis=1)
        pitch = np.full_like(feet, np.nan)
        if valid.any():
            pitch[valid] = apply_homography(homography, feet[valid])
        for r, (x, y) in zip(rows, pitch):
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            c = counts[int(r[0])]
            c[1] += 1
            if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
                c[0] += 1
    stats = {tid: (c[0], c[1]) for tid, c in counts.items()}
    off = {tid for tid, (outside, projected) in stats.items() if projected and outside >= min_outside_fraction * projected}
    return off, stats


def apply_pitch_filter(bboxes: Dict[str, list], off: set, action: str) -> Dict[str, list]:
    """The tracklets with the ``off`` tracks relabelled as bystanders, or removed."""
    out = {}
    for key, rows in bboxes.items():
        new_rows = []
        for r in rows:
            if int(r[0]) in off:
                if action == ACTION_REMOVE:
                    continue
                r = [r[0], TEAM_BYSTANDER, *r[2:]]
            new_rows.append(r)
        out[key] = new_rows
    return out


@PluginManager.export_plugin("pitch_filter")
class PitchFilter(Task):
    """Post-processing of an object_tracker run: the tracks that stay off the pitch (spectators, coaches,
    substitutes) become bystanders, or are removed. Runs in the backend; no Ray plugin.

    Every box's foot point goes through the calibration asset's active homography onto the pitch (the video's
    ``field_length`` x ``field_width``, 105 x 68 m if unset). A track is off the pitch when at least
    ``min_outside_fraction`` of its foot points lie more than ``margin_m`` outside the touch / goal lines, so a
    player who leaves the pitch for a throw-in stays a player. The result is a tracklets result ("bboxes",
    BBOXES) of this run in the object_tracker format; team_clustering takes this run as its ``object_tracker_id``
    and skips the bystander tracks.
    """

    def __init__(self):
        self.config = {"output_path": "/predictions/"}

    def __call__(
        self,
        parameters: Dict,
        plugin_run: PluginRun = None,
        dry_run: bool = False,
        **kwargs
    ):
        manager = DataManager(self.config["output_path"])
        object_tracker_id = parameters.get("object_tracker_id")
        source_run = PluginRun.objects.get(id=object_tracker_id)
        if plugin_run is not None:
            plugin_run.source_plugin_run = source_run
            plugin_run.save()

        prr = PluginRunResult.objects.filter(
            plugin_run_id=object_tracker_id, type=PluginRunResult.TYPE_BBOXES
        ).first()
        if prr is None:
            raise ValueError(f"No tracklets (TYPE_BBOXES) found for plugin run {object_tracker_id}.")
        tracklets = manager.load(prr.data_id)
        if tracklets is None:
            raise ValueError(f"Could not load BBOXES for plugin run {object_tracker_id}.")
        with tracklets:
            bboxes = json.loads(tracklets.bboxes)
            meta_data = tracklets.meta_data

        calibration_db = CalibrationAssets.objects.get(id=parameters.get("calibration_id"))
        if calibration_db.active_calibration_id is None:
            raise TaskFailure(
                "calibration_not_computed",
                "The calibration has no computed homography yet; run a calibration on it first",
                calibration_id=calibration_db.id.hex,
            )
        video_db = source_run.video or calibration_db.video
        field_length = (video_db.field_length if video_db else None) or 105.0
        field_width = (video_db.field_width if video_db else None) or 68.0

        margin_m = float(parameters.get("margin_m", 3.0))
        action = parameters.get("action", ACTION_BYSTANDER)
        off, stats = off_pitch_tracks(
            bboxes, calibration_db.homography_matrix, calibration_db.lens_intrinsics, field_length, field_width,
            margin_m, float(parameters.get("min_outside_fraction", 0.5)),
        )
        filtered = apply_pitch_filter(bboxes, off, action)
        n_boxes = sum(stats[tid][1] for tid in off)
        logging.info(
            f"pitch_filter: {len(off)} of {len(stats)} tracks off the pitch ({field_length} x {field_width} m, "
            f"margin {margin_m} m) -> {action}, {n_boxes} boxes; tracks {sorted(off)}"
        )

        if plugin_run is not None:
            plugin_run.progress = 0.9
            plugin_run.save()

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        with transaction.atomic():
            # the entity meta follows the new team ids; the rest (video: fps, h, w) is kept
            meta = {**json.loads(meta_data or "{}"), **compute_bboxes_meta(filtered)}
            with manager.create_data("BboxesData") as out:
                out.bboxes = json.dumps(filtered)
                out.meta_data = json.dumps(meta)
            plugin_run_result_db = PluginRunResult.objects.create(
                plugin_run=plugin_run,
                data_id=out.id,
                name="bboxes",
                type=PluginRunResult.TYPE_BBOXES,
            )
        plugin_run.progress = 1.0
        plugin_run.save()
        return {
            "plugin_run": plugin_run.id.hex,
            "plugin_run_results": [plugin_run_result_db.id.hex],
            "data": {"tracklets": out.id, "off_pitch_tracks": sorted(off)},
        }
