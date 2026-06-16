import logging
from django.db import transaction
from django.conf import settings
from typing import Dict, List, Callable

from backend.models import (
    PluginRun,
    PluginRunResult,
    TrackingData
)
from backend.plugin_manager import PluginManager
from backend.utils import media_path_to_file
from backend.utils.parser import Parser
from backend.utils.task import Task
from data import DataManager, Data
from ..utils.analyser_client import TaskAnalyserClient


@PluginManager.export_parser("floodlight_convert")
class FloodlightConvertParser(Parser):
    def __init__(self):
        self.valid_parameter = {
            "tracking_data_id": {"parser": str, "required": True},
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
        tracking_data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))

        tracking_data_ = self.upload_td(client, tracking_data_db.file.hex, tracking_data_db.ext)

        input_dict = {"tracking_data": tracking_data_}
        if tracking_data_db.meta_ext != "":
            meta_data_ = self.upload_td(client, tracking_data_db.meta_file.hex, tracking_data_db.meta_ext)
            input_dict.update({"meta_data": meta_data_})

        # --------> RUN
        result = self.run_analyser(
            client,
            "floodlight_convert",
            parameters={
                "format": parameters.get("format"),
                "delimiter": parameters.get("delimiter"),
                "tracking_data_id": parameters.get("tracking_data_id"),
            },
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
            "tracking_data_id": parameters.get("tracking_data_id"),
        }
