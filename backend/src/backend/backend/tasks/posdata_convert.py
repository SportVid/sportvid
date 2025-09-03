import logging
import os

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
from backend.utils import media_path_to_file
from backend.utils.parser import Parser
from backend.utils.task import Task

from django.db import transaction
from django.conf import settings

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager


@PluginManager.export_parser("posdata_convert")
class PosDataConvertParser(Parser):
    def __init__(self):
        self.valid_parameter = {
            "tracking_data_id": {"parser": str, "required": True},
            "format": {"parser": str, "required": True},
            "fps": {"parser": int, "required": False, "default": -1},
            "delimiter": {"parser": str, "required": False, "default": ";"},
            "origin": {"parser": str, "required": False, "default": "kickoff"},
            "field_length": {"parser": float, "required": False, "default": 105.0},
            "field_width": {"parser": float, "required": False, "default": 68.0},
            "team_id_ball": {"parser": str, "required": False, "default": "ball"}
        }


@PluginManager.export_plugin("posdata_convert")
class PosDataConvert(Task):
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
        
        if parameters.get("format") not in ['dfl', 'kinexon']:
            raise ValueError("'format' has to be either one of ['dfl', 'kinexon'], other formats are not supported yet for conversion.")
        
        # obtain ref. object from DB to position data table
        tracking_data_db = TrackingData.objects.get(id=parameters.get("tracking_data_id"))
        
        # TODO: should we rather transfer binaries instead of using the FSHandler?
        tracking_data_ = self.upload_td(client, tracking_data_db.file.hex, tracking_data_db.ext)  # uses the FSHandler, file is zipped before transfer

        input_dict = {"tracking_data": tracking_data_}
        if tracking_data_db.meta_ext != "":
            meta_data_ = self.upload_td(client, tracking_data_db.meta_file.hex, tracking_data_db.meta_ext)
            input_dict.update({"meta_data": meta_data_})

        # --------> RUN
        result = self.run_analyser(
            client,
            "posdata_convert",
            parameters={
                "format": parameters.get("format"),
                "fps": parameters.get("fps"),
                "delimiter": parameters.get("delimiter"),
                "tracking_data_id": parameters.get("tracking_data_id"),
                "origin": parameters.get("origin"),
                "field_length": parameters.get("field_length"),
                "field_width" : parameters.get("field_width"),
                "team_id_ball": parameters.get("team_id_ball")
            },
            inputs={**input_dict},
            outputs=["pos_data"],   # this only outputs the reference (id)
            downloads=["pos_data"]  # this actually transfers "real" data
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
            with result[1]["pos_data"] as pos_data:       
                td_id = parameters.get("tracking_data_id")
                if pos_data.pos == {}: # no result, so clean up
                    # manager.delete(tracking_data_db.pk)
                    cache_path = os.path.join(settings.DATA_CACHE_ROOT, f"{tracking_data_db.pk}.json")
                    if os.path.exists(cache_path): os.remove(cache_path)
                    count, _ = TrackingData.objects.filter(
                        id=parameters.get("tracking_data_id")
                    ).delete()
                    plugin_run.status = "ERROR"
                    plugin_run.save()
                    if count:
                        logging.info(f"Successfully updated DB and deleted old data with id {parameters.get('tracking_data_id')}.")
                    td_id = None
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
            "tracking_data_id": td_id
        }
