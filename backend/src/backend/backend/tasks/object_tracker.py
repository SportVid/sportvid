from typing import Dict, List
import logging

from backend.models import (
    PluginRun,
    PluginRunResult,
    Video
)
from backend.plugin_manager import PluginManager

from ..utils.analyser_client import TaskAnalyserClient
from data import DataManager
from backend.utils.task import Task
from django.db import transaction
from django.conf import settings


""" NOTE: Frontend should send params as a JSON body in this format:
    {
        "fps": 30,
        "detector": "yolox",
        "tracker": "bytetrack",
        "parameters" : { 
            "detector_params":  {"option1": "foo", "option2": "bar", ...},
            "tracker_params":   {"option1" : "foo", "option2": "bar", ...}
        }
    }
"""

@PluginManager.export_plugin("object_tracker")
class ObjectTracker(Task):
    def __init__(self):
        self.config = {
            "output_path": "/predictions/",
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
        manager = DataManager(self.config["output_path"])
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )
        video_id = self.upload_video(client, video)
        if plugin_run is not None:
            plugin_run.progress = 0.05
            plugin_run.save()
        
        logging.error(f'TASK PARAMS: {parameters}')
        tracker_result = self.run_analyser(
            client,
            "object_tracker",
            parameters=parameters,
            inputs={"video": video_id},
            outputs=["tracklets"],
            downloads=["tracklets"],
            plugin_run=plugin_run,
            # Detection/tracking is virtually all of the runtime -- the rest is upload
            # and writing the result, so the analyser owns nearly the whole bar.
            progress_range=(0.05, 0.95),
        )

        if plugin_run is not None:
            plugin_run.progress = 1.0
            plugin_run.save()

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        with transaction.atomic():
            with tracker_result[1]["tracklets"] as tracklets:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=tracklets.id,
                    name="bboxes" if parameters.get("tracker") else "bboxes_ball",
                    type=PluginRunResult.TYPE_BBOXES,
                )
                return {
                    "plugin_run": plugin_run.id.hex,
                    "plugin_run_results": [plugin_run_result_db.id.hex],
                    "data": {"tracklets": tracker_result[1]["tracklets"].id}
                }
