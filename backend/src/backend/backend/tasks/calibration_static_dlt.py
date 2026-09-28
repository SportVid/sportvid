import logging
import json
from django.db import transaction
from django.conf import settings
from typing import Dict

from backend.models import (
    CalibrationAssets,
    PluginRun,
    Video,
)
from backend.plugin_manager import PluginManager
from backend.utils.task import Task
from backend.utils.lens import (
    camera_pose_from_homography,
    lens_intrinsics_snapshot,
    undistort_with_snapshot,
)
from data import DataManager
from ..utils.analyser_client import TaskAnalyserClient

@PluginManager.export_plugin("calibration_static_dlt")
class CalibrationStaticDlt(Task):
    def __init__(self):
        self.config = {
            "output_path": None, # "/predictions/", 
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
        # get point correspondences from database and pass them as plugin parameters
        data_db = CalibrationAssets.objects.get(id=parameters.get("calibration_id"))
        if plugin_run is not None:
            plugin_run.calibration_asset = data_db
            plugin_run.save()
        point_correspondences = [
            p for p in data_db.object_data.all()
            if (
                p.video_coords_rel
                and p.video_coords_rel[0].get("x") is not None
                and p.video_coords_rel[0].get("y") is not None
                and p.comp_area_coords_rel
                and p.comp_area_coords_rel[0].get("x") is not None
                and p.comp_area_coords_rel[0].get("y") is not None
            )
        ]

        if len(point_correspondences) == 0:
            raise Exception("No point correspondences fetched")
        if len(point_correspondences) < 4:
            raise Exception("Not enough valid point correspondences (min 4 required)")
        
        # convert point correspondences
        point_correspondences_dict = []
        for point in point_correspondences:
            point_correspondences_dict.append({
                "dst": {
                    "x": point.comp_area_coords_rel[0]["x"],
                    "y": point.comp_area_coords_rel[0]["y"]
                },
                "src": {
                    "x": point.video_coords_rel[0]["x"],
                    "y": point.video_coords_rel[0]["y"]
                }
            })
        # with a lens profile the homography is fitted on undistorted video coordinates
        video_db = data_db.video or video
        lens_intrinsics = None
        if video_db is not None and video_db.lens_profile is not None:
            lens_intrinsics = lens_intrinsics_snapshot(video_db.lens_profile, video_db.width, video_db.height)
            undistorted = undistort_with_snapshot(
                [[p["src"]["x"], p["src"]["y"]] for p in point_correspondences_dict], lens_intrinsics
            )
            valid = []
            for point, (x, y) in zip(point_correspondences_dict, undistorted):
                # NaN: beyond the lens model's valid range
                if x == x and y == y:
                    point["src"] = {"x": float(x), "y": float(y)}
                    valid.append(point)
            if len(valid) < 4:
                raise Exception("Not enough valid point correspondences after undistortion (min 4 required)")
            point_correspondences_dict = valid

        # all parameters are serialized based on strings when calling run_analyser
        plugin_parameters = {
            "point_correspondences": json.dumps(point_correspondences_dict),
        }
        manager = DataManager(self.config["output_path"]) 
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )
        result = self.run_analyser(
            client,
            "calibration_static_dlt",
            parameters=plugin_parameters,
            inputs={},
            downloads=["homography"],
        )

        if result is None: raise Exception

        with transaction.atomic():
            with result[1]["homography"] as homography_data:
                homography_matrix = homography_data.y.tolist()
                data_db.homography_matrix = homography_matrix
                data_db.lens_intrinsics = lens_intrinsics
                data_db.camera_pose = None
                if lens_intrinsics is not None:
                    try:
                        data_db.camera_pose = camera_pose_from_homography(
                            homography_matrix,
                            lens_intrinsics["camera_matrix"],
                            lens_intrinsics["width"],
                            lens_intrinsics["height"],
                            field_length=video_db.field_length or 105.0,
                            field_width=video_db.field_width or 68.0,
                            src_points_rel=[[p["src"]["x"], p["src"]["y"]] for p in point_correspondences_dict],
                            dst_points_rel=[[p["dst"]["x"], p["dst"]["y"]] for p in point_correspondences_dict],
                        )
                    except Exception:
                        logging.exception(f"Camera pose estimation failed for calibration asset {data_db.id}")
                data_db.save()
                logging.debug(f"Updated homography matrix {homography_matrix} for calibration asset {data_db.id}")

        return {
            "plugin_run": plugin_run.id.hex,
            # "plugin_run_results": [plugin_run_result_db.id.hex],
            # "data": {"homography": result[1]["homography"].id},
        }
