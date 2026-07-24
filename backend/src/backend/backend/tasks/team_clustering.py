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
        
        object_tracker_id = parameters.get("object_tracker_id", None)
        osnet_reid_id = parameters.get("osnet_reid_id", None)
        
        reid_id = None
        if osnet_reid_id:
            reids = PluginRunResult.objects.filter(
                    plugin_run_id=osnet_reid_id,
                    type=PluginRunResult.TYPE_REID_DATA,
            )
            if not reids.exists():
                raise ValueError(
                    f"No reids (TYPE_REID_DATA) found for osnet_reid run {osnet_reid_id}."
                )
            prr = tracklets.first()
            reids_ = manager.load(prr.data_id)
            if reids_ is None:
                raise ValueError(f"Could not load REID_DATA for osnet_reid run {osnet_reid_id}.")
            reid_id = client.upload_data(reids_)
        else:
            if object_tracker_id:
                tracklets = PluginRunResult.objects.filter(
                    plugin_run_id=object_tracker_id,
                    type=PluginRunResult.TYPE_BBOXES,
                )
                if not tracklets.exists():
                    raise ValueError(
                        f"No tracklets (TYPE_BBOXES) found for object_tracker run {object_tracker_id}."
                    )
                prr = tracklets.first()
                tracklets_ = manager.load(prr.data_id)
                if tracklets_ is None:
                    raise ValueError(f"Could not load BBOXES for object_tracker run {object_tracker_id}.")
                tracklets_id = client.upload_data(tracklets_)

        logging.error(f'TASK PARAMS: {parameters}')
        reids = self.run_analyser(
            client,
            "osnet_reid",
            parameters=parameters,
            inputs={
                "video": video_id,
                "tracklets": None if reid_id else tracklets_id,
                "reids": reid_id if reid_id else None
            },
            outputs=["teams"],
            downloads=["teams"],
        )

        if plugin_run is not None:
            plugin_run.progress = 1.0
            plugin_run.save()

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        with transaction.atomic():
            with reids[1]["teams"] as teams:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=reids.id,
                    name="teams",
                    type=PluginRunResult.TYPE_TEAM_DATA,
                )
                return {
                    "plugin_run": plugin_run.id.hex,
                    "plugin_run_results": [plugin_run_result_db.id.hex],
                    "data": {
                        "teams": teams.id,
                        "teams": teams.mapping    
                    },
                }

