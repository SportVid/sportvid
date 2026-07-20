import logging
from typing import Dict, List
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


@PluginManager.export_plugin("team_clustering")
class TeamClustering(Task):
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
        
        object_tracker_id = parameters.get("object_tracker_id")
        if not object_tracker_id:
            raise ValueError("object_tracker_id is required to run this plugin.")
        
        tracklets = PluginRunResult.objects.filter(
            plugin_run_id=object_tracker_id,
            type=PluginRunResult.TYPE_BBOXES,
        )
        
        if not tracklets.exists():
            raise ValueError(
                f"No tracklets (TYPE_BBOXES) found for object tracker run {object_tracker_id}."
            )
        
        prr = tracklets.first()
        tracklets_ = manager.load(prr.data_id)
        if tracklets_ is None:
            raise ValueError(f"Could not load BboxesData for ByteTrack run {object_tracker_id}.")
        
        logging.error(f'TASK PARAMS: {parameters}')
        reids = self.run_analyser(
            client,
            "team_clustering",
            parameters=parameters,
            inputs={
                "video": video_id,
                "tracklets": tracklets_ 
            },
            outputs=["reids"],
            downloads=["reids"],
        )

        if plugin_run is not None:
            plugin_run.progress = 1.0
            plugin_run.save()

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        with transaction.atomic():
            with reids[1]["reids"] as reids:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=reids.id,
                    name="reids",
                    type=PluginRunResult.TYPE_LIST,
                )
                return {
                    "plugin_run": plugin_run.id.hex,
                    "plugin_run_results": [plugin_run_result_db.id.hex],
                    "data": {"reids": reids[1]["reids"].id},
                }

