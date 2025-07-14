from typing import Dict
import logging
import json

from backend.models import (
    CalibrationAssets,
    PluginRun,
    Video,
)
from backend.plugin_manager import PluginManager

from ..utils.analyser_client import TaskAnalyserClient
from analyser.data import DataManager
from backend.utils.parser import Parser
from backend.utils.task import Task
from django.db import transaction
from django.conf import settings
import numpy as np
import logging

@PluginManager.export_parser("calibration_static_dlt")
class CalibrationStaticDltParser(Parser):
    def __init__(self):

        self.valid_parameter = {
            "calibration_id": {"parser": str, "required": True},
        }


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

        point_correspondences = data_db.marker_data.all()
        logging.info(point_correspondences)
        # Convert point correspondences
        point_correspondences_dict = []
        for point in point_correspondences:
            point_correspondences_dict.append({
                "dst": {
                    "x": point.compAreaCoord_x,
                    "y": point.compAreaCoord_y
                },
                "src": {
                    "x": point.videoCoord_x,
                    "y": point.videoCoord_y
                }
            })
        if len(point_correspondences_dict) == 0:
            raise Exception("No point correspondences fetched")
        # all parameters are serialized based on strings when calling run_analyser
        plugin_parameters = {
            "point_correspondences": json.dumps(point_correspondences_dict),
        }

        manager = DataManager(self.config["output_path"]) 
        # TODO use DataManager and use point_correspondences as input instead of parameters
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

        if result is None:
            raise Exception

        with transaction.atomic():
            with result[1]["homography"] as homography_data:
                # update homography matrix in database
                homography_matrix = homography_data.y.tolist()
                logging.info(f"Homography matrix: {homography_matrix}")
                data_db.homography_matrix = homography_matrix
                data_db.save()
                logging.info(f"Updated homography matrix for calibration asset {data_db.id}")

        return {
            "plugin_run": plugin_run.id.hex,
            # "plugin_run_results": [plugin_run_result_db.id.hex],
            # "data": {"homography": result[1]["homography"].id},
        }
