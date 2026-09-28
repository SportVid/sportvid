import logging
from django.conf import settings
from typing import Dict

from backend.models import PluginRun, Video
from backend.plugin_manager import PluginManager
from backend.utils.task import Task
from data import DataManager
from ..utils.analyser_client import TaskAnalyserClient


logger = logging.getLogger(__name__)


@PluginManager.export_plugin("camera_motion_classification")
class CameraMotionClassifier(Task):
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
        **kwargs,
    ):
        manager = DataManager(self.config["output_path"])
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )
        video_id = self.upload_video(client, video)
        result = self.run_analyser(
            client,
            "camera_motion_classifier",
            inputs={"video": video_id},
            downloads=["camera_motion"],
            parameters={"fps": parameters.get("fps")},
        )

        if result is None: raise Exception

        with result[1]["camera_motion"] as data:
            camera_motion = data.text

        if camera_motion not in Video.CAMERA_MOTION:
            raise Exception(f"Unknown camera motion category '{camera_motion}'")

        if dry_run or plugin_run is None:
            logging.warning("dry_run or plugin_run is None")
            return {}

        # save() (not .update()) so the video change is pushed to the frontend via post_save
        video.camera_motion = camera_motion
        video.save(update_fields=["camera_motion"])
        logger.info(f"Classified camera motion of video {video.id} as '{camera_motion}'")

        return {
            "plugin_run": plugin_run.id.hex,
            "camera_motion": camera_motion,
        }
