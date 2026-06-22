import logging
import json
from django.db import transaction
from django.conf import settings
from typing import Dict

from backend.models import (
    CalibrationAssets,
    PluginRun,
    Video,
)
from backend.plugin_manager import PluginManager
from backend.utils.parser import Parser
from backend.utils.task import Task
from data import DataManager
from ..utils.analyser_client import TaskAnalyserClient


@PluginManager.export_plugin("calibration_static_dlt")
class CalibrationStaticDlt(Task):
    def __init__(self):
        self.config = {
            "output_path": None, # "/predictions/", 
            "analyser_host": settings.GRPC_HOST,
            "analyser_port": settings.GRPC_PORT,
        }

    def __call__(
        self,
        parameters: Dict,
        video: Video = None,
        plugin_run: PluginRun = None,
        dry_run: bool = False,
        **kwargs
    ):
        # get point correspondences from database and pass them as plugin parameters
        data_db = CalibrationAssets.objects.get(id=parameters.get("calibration_id"))
        point_correspondences = [
            p for p in data_db.object_data.all()
            if (
                p.video_coords_rel
                and p.video_coords_rel[0].get("x") is not None
                and p.video_coords_rel[0].get("y") is not None
                and p.comp_area_coords_rel
                and p.comp_area_coords_rel[0].get("x") is not None
                and p.comp_area_coords_rel[0].get("y") is not None
            )
        ]

        if len(point_correspondences) == 0:
            raise Exception("No point correspondences fetched")
        if len(point_correspondences) < 4:
            raise Exception("Not enough valid point correspondences (min 4 required)")
        
        # convert point correspondences
        point_correspondences_dict = []
        for point in point_correspondences:
            point_correspondences_dict.append({
                "dst": {
                    "x": point.comp_area_coords_rel[0]["x"],
                    "y": point.comp_area_coords_rel[0]["y"]
                },
                "src": {
                    "x": point.video_coords_rel[0]["x"],
                    "y": point.video_coords_rel[0]["y"]
                }
            })
        # all parameters are serialized based on strings when calling run_analyser
        plugin_parameters = {
            "point_correspondences": json.dumps(point_correspondences_dict),
        }
        manager = DataManager(self.config["output_path"]) 
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )
        result = self.run_analyser(
            client,
            "calibration_static_dlt",
            parameters=plugin_parameters,
            inputs={},
            downloads=["homography"],
        )

        if result is None: raise Exception

        with transaction.atomic():
            with result[1]["homography"] as homography_data:
                homography_matrix = homography_data.y.tolist()
                data_db.homography_matrix = homography_matrix
                data_db.save()
                logging.debug(f"Updated homography matrix {homography_matrix} for calibration asset {data_db.id}")

        return {
            "plugin_run": plugin_run.id.hex,
            # "plugin_run_results": [plugin_run_result_db.id.hex],
            # "data": {"homography": result[1]["homography"].id},
        }
