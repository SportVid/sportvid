import logging

from typing import Dict, List, Callable

from data import DataManager, Data

from ..utils.analyser_client import TaskAnalyserClient

from backend.models import (
    PluginRun, 
    PluginRunResult,
    TrackingData
)
from backend.plugin_manager import PluginManager
from backend.utils import media_path_to_file
from backend.utils.parser import Parser
from backend.utils.task import Task

from django.db import transaction
from django.conf import settings

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager


@PluginManager.export_parser("floodlight_convert")
class FloodlightConvertParser(Parser):
    def __init__(self):
        self.valid_parameter = {
            "tracking_data_id": {"parser": str, "required": True},
            "provided_meta_data": {"parser": bool, "default": False},
            "format": {"parser": str, "required": True},
            "delimiter": {"parser": str, "required": False, "default": ";"}
        }


@PluginManager.export_plugin("floodlight_convert")
class FloodlightConvert(Task):
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
        tracking_data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))
        
        # TODO: rather use file transfer as binary?
        tracking_data_ = self.upload_td(client, tracking_data_db)  # uses the FSHandler, file is zipped before transfer

        if parameters.get("provided_meta_data"):
            meta_data_ = self.upload_td(client, tracking_data_db.meta_file.hex, tracking_data_db.meta_ext)
            input_dict.update({"meta_data": meta_data_})

        # --------> RUN ANALYSER PLUGIN
        # NOTE: specify parameters for plugin execution -> needs to match call()-method of "/inference_ray/plugins/kinexon_convert.py"
        result = self.run_analyser(
            client,
            "kinexon_convert",
            parameters={"tracking_data_id": parameters.get("tracking_data_id")},
            inputs={"tracking_data": tracking_data_},
            outputs=["fl_data"],   # outputs the reference (id)
            # downloads=["fl_data"]  # actually transfers "real" data
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
        # TODO: define output of FL conversion, is it dynamic?
        with transaction.atomic():
            with result[1]["fl_data"] as fl_data:
                # saves analyser results to the database (PluginRunResult)
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=fl_data.id,
                    name="fl_data",
                    type=PluginRunResult.TYPE_FL,
                )
        # output results to the backend
        return {
            "plugin_run": plugin_run.id.hex,
            "plugin_run_results": [plugin_run_result_db.id.hex],
            "data": {"fl_data": fl_data.id},
        }
