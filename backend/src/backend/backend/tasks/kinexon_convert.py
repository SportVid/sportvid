import logging

from typing import Dict, List, Callable

from data import DataManager, Data

from ..utils.analyser_client import TaskAnalyserClient

from backend.models import (
    PluginRun, 
    PluginRunResult,
    Video,
    TrackingData
)
from backend.plugin_manager import PluginManager
from backend.utils import media_path_to_video
from backend.utils.parser import Parser
from backend.utils.task import Task

from django.db import transaction
from django.conf import settings

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager


@PluginManager.export_parser("kinexon_convert")
class KinexonConvertParser(Parser):
    def __init__(self):
        self.valid_parameter = {
            "tracking_data_id": {"parser": str, "required": True},
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
        # obtain ref. object from DB to position data table
        logging.error(f'[TASKS]\tparams: {parameters}')
        logging.error(f'[TASKS]\ttdid: {parameters.get("tracking_data_id")}')
        
        tracking_data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))
        logging.error(f'[TASKS]\ttdid_db: {tracking_data_db}')
        
        # NOTE: Which method is preferred?
        tracking_data_ = self.upload_td(client, tracking_data_db)  # uses the FSHandler, file is zipped before transfer
        # NOTE: This one doesn't work currently
        # tracking_data_ = self.upload_td_from_stream(client, tracking_data_db)  # uploads directly from the file stream

        # --------> RUN ANALYSER PLUGIN
        # NOTE: specify parameters for plugin execution -> needs to match call()-method of "/inference_ray/plugins/kinexon_convert.py"
        result = self.run_analyser(
            client,
            "kinexon_convert",
            parameters={"tracking_data_id": parameters.get("tracking_data_id")},  # NOTE: specify more params if needed  
            inputs={"tracking_data": tracking_data_},
            outputs=["pos_data"],   # this only outputs the reference (id)
            downloads=["pos_data"]  # this actually transfers "real" data
        )
        logging.error(f'[TASKS]\tresult: {result}')
        
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
            with result[1]["pos_data"] as pos_data:
                # saves analyser results to the database (PluginRunResult)
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=pos_data.id,
                    name="pos_data",
                    type=PluginRunResult.TYPE_POS,
                )
        # output results to the backend
        return {
            "plugin_run": plugin_run.id.hex,
            "plugin_run_results": [plugin_run_result_db.id.hex],
            "data": {"pos_data": pos_data.id},
        }
