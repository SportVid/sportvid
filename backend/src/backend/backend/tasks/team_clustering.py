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
        
        # osnet_reid_id = parameters.get("osnet_reid_id")
        # reid_input_id = ""
        # if osnet_reid_id:
        #     reid_results = PluginRunResult.objects.filter(
        #         plugin_run_id=osnet_reid_id,
        #         type=PluginRunResult.TYPE_REID_DATA,
        #     )
        #     if not reid_results.exists():
        #         raise ValueError(
        #             f"No reids (TYPE_REID_DATA) found for osnet_reid run {osnet_reid_id}."
        #         )

        #     prr = reid_results.first()
        #     reids_data = manager.load(prr.data_id)
        #     if reids_data is None:
        #         raise ValueError(f"Could not load REID_DATA for osnet_reid run {osnet_reid_id}.")
        #     reid_input_id = client.upload_data(reids_data)

        # parameters["osnet_reid_id"] = str(parameters["osnet_reid_id"])
        
        object_tracker_run_db = PluginRun.objects.get(id=object_tracker_id)
        if plugin_run is not None:
            plugin_run.source_plugin_run = object_tracker_run_db
            plugin_run.save()

        tracklet_results = PluginRunResult.objects.filter(
            plugin_run_id=object_tracker_id,
            type=PluginRunResult.TYPE_BBOXES,
        )
        if not tracklet_results.exists():
            raise ValueError(
                f"No tracklets (TYPE_BBOXES) found for object_tracker run {object_tracker_id}."
            )

        prr = tracklet_results.first()
        tracklets_data = manager.load(prr.data_id)
        if tracklets_data is None:
            raise ValueError(f"Could not load BBOXES for object_tracker run {object_tracker_id}.")

        tracklets_input_id = client.upload_data(tracklets_data)

        parameters["object_tracker_id"] = str(parameters["object_tracker_id"])
       

        logging.error(f"TASK PARAMS: {parameters}")

        analyser_result = self.run_analyser(
            client,
            "team_clustering",
            parameters=parameters,
            inputs={
                "video": video_id,
                "tracklets": tracklets_input_id,
                # "reids": reid_input_id,
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
            with analyser_result[1]["teams"] as teams_data:
                plugin_run_result_db = PluginRunResult.objects.create(
                    plugin_run=plugin_run,
                    data_id=teams_data.id,
                    name="teams",
                    type=PluginRunResult.TYPE_TEAMS_DATA,
                )
                return {
                    "plugin_run": plugin_run.id.hex,
                    "plugin_run_results": [plugin_run_result_db.id.hex],
                    "data": {
                        "teams": teams_data.id,
                        "teams_mapping": getattr(teams_data, "mapping", None),
                    },
                }