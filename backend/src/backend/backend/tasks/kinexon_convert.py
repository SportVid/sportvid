from typing import Dict, List
import logging

from ..utils.analyser_client import TaskAnalyserClient

from backend.models import (
    PluginRun, 
    PluginRunResult, 
    Video, 
    Timeline,
    TrackingData
)
from backend.plugin_manager import PluginManager
from backend.utils import media_path_to_video
from backend.utils.parser import Parser
from backend.utils.task import Task
from data import DataManager
from django.db import transaction
from django.conf import settings


from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

import logging
from data import PositionsData
from data import DataManager, Data

from typing import Callable, Dict


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    # TODO
}

requires = {
    # TODO
}

provides = {
    "pos_data": PositionsData, 
}


@PluginManager.export_plugin("kinexon_convert")
class KinexonConvert(Task):
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
        
        # obtain ref to position data
        data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))

        video_id = self.upload_video(client, video)
        result = self.run_analyser(
            client,
            "kinexon_convert",
            parameters={}, # TODO
            inputs={"video": video_id}, # TODO
            outputs=[""], # TODO
            downloads=["pos_data"]
        )

        if plugin_run is not None:
            plugin_run.progress = 0.6
            plugin_run.save()

        if result is None:
            raise Exception

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        with transaction.atomic():
            with result[1]["poss"] as pos_data:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=data.id,
                    name="poss",
                    type=PluginRunResult.TYPE_POSS,
                )

                return {
                    "plugin_run": plugin_run.id.hex,
                    "plugin_run_results": [plugin_run_result_db.id.hex],
                    "data": {"poss": result[1]["poss"].id},
                }
