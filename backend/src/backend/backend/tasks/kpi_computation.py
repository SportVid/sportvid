import json
import logging

from typing import Dict, List, Callable

from data import DataManager, Data

from ..utils.analyser_client import TaskAnalyserClient

from backend.models import (
    PluginRun,
    PluginRunResult,
    TrackingData,
    CalibrationAssets,
)
from backend.plugin_manager import PluginManager
from backend.utils import media_path_to_file
from backend.utils.parser import Parser
from backend.utils.task import Task

from django.db import transaction
from django.conf import settings


@PluginManager.export_parser("kpi_computation")
class KpiComputationParser(Parser):
    def __init__(self):
        self.valid_parameter = {
            "tracking_data_id": {"parser": str, "required": False, "default": ""},
            "bytetrack_run_id": {"parser": str, "required": False, "default": ""},
            "calibration_id": {"parser": str, "required": False, "default": ""},
            "format": {"parser": str, "required": True},
            "pos_meta": {"parser": str, "required": False, "default": ""},
            "filter_type": {"parser": str, "required": False, "default": ""},
            "order": {"parser": int, "required": False, "default": 3},
            "Wn": {"parser": float, "required": False, "default": 1.0},
            "window_length": {"parser": int, "required": False, "default": 5},
            "poly_order": {"parser": int, "required": False, "default": 3},
        }


@PluginManager.export_plugin("kpi_computation")
class KpiComputation(Task):
    def __init__(self):
        self.config = {
            "output_path": "/predictions/",
            "analyser_host": settings.GRPC_HOST,
            "analyser_port": settings.GRPC_PORT,
        }

    def __call__(
        self,
        parameters: Dict,
        plugin_run: PluginRun = None,
        dry_run: bool = False,
        **kwargs
    ):
        # --------> PREPARATION
        manager = DataManager(self.config["output_path"])
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )

        fmt = parameters.get("format")

        if fmt == "sportvid":
            # --------> SPORTVID: load BboxesData from ByteTrack, apply calibration homography,
            # then build a PositionData object for the inference plugin.
            bytetrack_run_id = parameters.get("bytetrack_run_id")
            calibration_id = parameters.get("calibration_id")
            if not bytetrack_run_id:
                raise ValueError("bytetrack_run_id is required for format='sportvid'.")
            if not calibration_id:
                raise ValueError("calibration_id is required for format='sportvid'.")

            # Load BboxesData from the ByteTrack run
            bbox_results = PluginRunResult.objects.filter(
                plugin_run_id=bytetrack_run_id,
                type=PluginRunResult.TYPE_BBOXES,
            )
            if not bbox_results.exists():
                raise ValueError(
                    f"No bounding box data (TYPE_BBOXES) found for ByteTrack run {bytetrack_run_id}."
                )

            prr = bbox_results.first()
            bbox_obj = manager.load(prr.data_id)
            if bbox_obj is None:
                raise ValueError(f"Could not load BboxesData for ByteTrack run {bytetrack_run_id}.")

            # Load homography matrix from CalibrationAssets
            calibration_db = CalibrationAssets.objects.get(id=calibration_id)
            H = calibration_db.homography_matrix  # 3x3 list of lists

            def _apply_homography(H, x, y):
                X = H[0][0] * x + H[0][1] * y + H[0][2]
                Y = H[1][0] * x + H[1][1] * y + H[1][2]
                W = H[2][0] * x + H[2][1] * y + H[2][2]
                return X / W, Y / W

            with bbox_obj:
                bboxes_raw = json.loads(bbox_obj.bboxes)

            # Infer fps from timestamp intervals
            timestamps_ms = sorted(int(k) for k in bboxes_raw.keys())
            if len(timestamps_ms) > 1:
                intervals = [timestamps_ms[i + 1] - timestamps_ms[i] for i in range(len(timestamps_ms) - 1)]
                median_interval = sorted(intervals)[len(intervals) // 2]
                fps = round(1000.0 / median_interval) if median_interval > 0 else 25
            else:
                fps = 25

            # Build PositionData: apply homography to each bbox's center-bottom position.
            # ByteTrack outputs team_id=3 by default (single team under new scheme).
            pos_json = {}
            player_ids_meta = {}
            seen_team_ids = set()
            for ts_str, boxes in bboxes_raw.items():
                frame_players = []
                for b in boxes:
                    pid = b[0]
                    tid = b[1]
                    section = b[2]
                    top_x = b[3]  # center-x normalized in video space
                    top_y = b[4]  # bottom-y normalized in video space
                    hx, hy = _apply_homography(H, top_x, top_y)
                    frame_players.append([pid, tid, section, hx, hy])
                    seen_team_ids.add(tid)
                    if str(pid) not in player_ids_meta:
                        player_ids_meta[str(pid)] = {"id": str(pid), "name": str(pid), "number": pid, "team_id": tid}
                pos_json[ts_str] = frame_players

            team_ids_meta = {}
            for letter_idx, tid in enumerate(sorted(t for t in seen_team_ids if t >= 3)):
                name = f"Team {chr(ord('A') + letter_idx)}" if letter_idx < 26 else f"Team {tid}"
                team_ids_meta[str(tid)] = {"id": tid, "name": name}
            if not team_ids_meta:
                team_ids_meta["3"] = {"id": 3, "name": "Team A"}

            meta_data = {
                "fps": fps,
                "player_ids": player_ids_meta,
                "ref_ids": {},
                "ball_ids": {},
                "team_ids": team_ids_meta,
            }

            # Get field dimensions from the video for denormalization in the inference plugin
            field_length = plugin_run.video.field_length or 105.0
            field_width = plugin_run.video.field_width or 68.0

            with manager.create_data("PositionData") as pos_data_obj:
                pos_data_obj.tracking_data_id = bytetrack_run_id
                pos_data_obj.meta_data = json.dumps(meta_data)
                pos_data_obj.pos = json.dumps(pos_json)

            pos_data_id = client.upload_data(pos_data_obj)

            analyser_params = {
                "format": "sportvid",
                "field_length": field_length,
                "field_width": field_width,
                "filter_type": parameters.get("filter_type"),
                "order": parameters.get("order"),
                "Wn": parameters.get("Wn"),
                "window_length": parameters.get("window_length"),
                "poly_order": parameters.get("poly_order"),
                "tracking_data_id": bytetrack_run_id,
            }
            input_dict = {"pos_data": pos_data_id}
            tracking_data_id_out = bytetrack_run_id

        else:
            # --------> KINEXON / DFL: use raw TrackingData file
            tracking_data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))
            delimiter = tracking_data_db.delimiter or ";"

            tracking_data_ = self.upload_td(client, tracking_data_db.file.hex, tracking_data_db.ext)
            input_dict = {"tracking_data": tracking_data_}
            if tracking_data_db.meta_ext != "":
                meta_data_ = self.upload_td(client, tracking_data_db.meta_file.hex, tracking_data_db.meta_ext)
                input_dict.update({"meta_data": meta_data_})

            # --------> FIND POSDATA METADATA
            pos_meta_json = ""
            pos_data_results = PluginRunResult.objects.filter(
                plugin_run__type="posdata_convert",
                plugin_run__status=PluginRun.STATUS_DONE,
                plugin_run__video=tracking_data_db.video,
                name="pos_data",
                type=PluginRunResult.TYPE_POS,
            ).order_by("-plugin_run__date")

            for prr in pos_data_results:
                pos_data_obj = manager.load(prr.data_id)
                if pos_data_obj is None:
                    continue
                with pos_data_obj:
                    if pos_data_obj.tracking_data_id == parameters.get("tracking_data_id"):
                        pos_meta_json = pos_data_obj.meta_data or ""
                        break

            if not pos_meta_json:
                logging.warning("No matching posdata_convert result found; KPI IDs will use plugin-local mapping.")

            analyser_params = {
                "format": fmt,
                "delimiter": delimiter,
                "tracking_data_id": parameters.get("tracking_data_id"),
                "filter_type": parameters.get("filter_type"),
                "order": parameters.get("order"),
                "Wn": parameters.get("Wn"),
                "window_length": parameters.get("window_length"),
                "poly_order": parameters.get("poly_order"),
                "pos_meta": pos_meta_json,
            }
            tracking_data_id_out = parameters.get("tracking_data_id")

        # --------> RUN
        result = self.run_analyser(
            client,
            "kpi_computation",
            parameters=analyser_params,
            inputs={**input_dict},
            outputs=["kpi_data"],
            downloads=["kpi_data"],
        )

        if plugin_run is not None:
            plugin_run.progress = 0.6
            plugin_run.save()

        if result is None:
            raise Exception

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        # --------> OUTPUT
        with transaction.atomic():
            with result[1]["kpi_data"] as kpi_data:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=kpi_data.id,
                    name="kpi_data",
                    type=PluginRunResult.TYPE_KPI,
                )

        return {
            "plugin_run": plugin_run.id.hex,
            "plugin_run_results": [plugin_run_result_db.id.hex],
            "data": {"kpi_data": kpi_data.id},
            "tracking_data_id": tracking_data_id_out,
        }
