import logging
import json
from django.db import transaction
from django.conf import settings
from typing import Dict, List, Optional

from backend.models import (
    Calibration,
    CalibrationAssets,
    PluginRun,
    Video,
)
from backend.plugin_manager import PluginManager
from backend.utils.task import Task, TaskFailure
from backend.utils.lens import (
    camera_pose_from_homography,
    lens_intrinsics_snapshot,
    reprojection_rmse,
    undistort_with_snapshot,
    undistorted_camera_matrix,
)
from backend.utils.pitch import normalize_sport, object_pitch_positions
from data import DataManager
from ..utils.analyser_client import TaskAnalyserClient

@PluginManager.export_plugin("calibration_static_dlt")
class CalibrationStaticDlt(Task):
    # progress share of the homography fit; subclasses that run another analyser first move it to the end
    dlt_progress_range = None

    ray_plugins = ("calibration_static_dlt",)

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

        if len(point_correspondences) < 4:
            raise TaskFailure(
                "not_enough_point_correspondences",
                f"The calibration needs at least 4 placed points, got {len(point_correspondences)}",
                count=len(point_correspondences),
                required=4,
            )
        
        video_db = data_db.video or video
        field_length = (video_db.field_length if video_db else None) or 105.0
        field_width = (video_db.field_width if video_db else None) or 68.0
        sport = normalize_sport(data_db.sport, video_db.sport if video_db else None)

        # The asset may be annotated on several frames (one row per object and frame). All of them are
        # fitted into a single homography, so a marker hidden behind a player in one frame can simply be
        # placed in another. That pooling assumes the camera stands still between the annotated frames --
        # with a pan or a zoom in between, every frame would need its own homography.
        annotated_times = sorted({p.time for p in point_correspondences if p.time is not None})
        if len(annotated_times) > 1:
            motion = video_db.camera_motion if video_db else None
            logging.info(
                f"Calibration asset {data_db.id}: {len(point_correspondences)} point(s) clicked on "
                f"{len(annotated_times)} frame(s) ({', '.join(f'{t:.0f} ms' for t in annotated_times)})"
            )
            if motion in (Video.CAMERA_MOTION_PAN, Video.CAMERA_MOTION_ZOOM, Video.CAMERA_MOTION_PAN_ZOOM):
                logging.warning(
                    f"Calibration asset {data_db.id}: the points of {len(annotated_times)} frames are fitted "
                    f"into one homography, but the camera is classified as '{motion}' -- if it moved between "
                    f"those frames, the fit mixes incompatible views"
                )

        # convert point correspondences; markers get their metric position on this pitch by name (the
        # template's relative position is only right on a pitch of the template's reference size)
        point_correspondences_dict = []
        keypoints = []      # markers placed by the pitch model: {"name", "video" (relative), "pitch" (metres)}
        for point in point_correspondences:
            keypoint, positions = object_pitch_positions(
                sport, data_db.object_type, point.name, point.comp_area_coords_rel, field_length, field_width
            )
            dst = positions[0]
            if keypoint is not None:
                keypoints.append({
                    "name": keypoint,
                    "video": [point.video_coords_rel[0]["x"], point.video_coords_rel[0]["y"]],
                    "pitch": [dst[0] * field_length, dst[1] * field_width],
                })
            point_correspondences_dict.append({
                "dst": {"x": dst[0], "y": dst[1]},
                "src": {
                    "x": point.video_coords_rel[0]["x"],
                    "y": point.video_coords_rel[0]["y"]
                }
            })
        # With several annotated frames the same marker can be clicked more than once. Those repeats
        # average out click noise, but they are one point on the pitch -- a homography needs 4 of them
        # in general position, so that is what the minimum counts.
        distinct_positions = {
            (round(p["dst"]["x"], 9), round(p["dst"]["y"], 9)) for p in point_correspondences_dict
        }
        if len(distinct_positions) < 4:
            raise TaskFailure(
                "not_enough_distinct_points",
                f"The calibration needs placed points at 4 different pitch positions, got "
                f"{len(distinct_positions)} ({len(point_correspondences_dict)} click(s) in total)",
                count=len(distinct_positions),
                required=4,
            )
        logging.info(
            f"Calibration asset {data_db.id}: {len(keypoints)}/{len(point_correspondences_dict)} point(s) placed by the "
            f"{sport or 'unknown'} pitch model on {field_length} x {field_width} m, the rest by template position"
        )
        manager = DataManager(self.config["output_path"])
        client = TaskAnalyserClient(
            host=self.config["analyser_host"],
            port=self.config["analyser_port"],
            plugin_run_db=plugin_run,
            manager=manager,
        )

        # with a lens the homography is fitted on undistorted video coordinates
        self.lens_notice = None
        lens_intrinsics = self.lens_intrinsics(
            client, video_db, keypoints, field_length, field_width, sport, plugin_run
        )
        if lens_intrinsics is not None:
            try:
                point_correspondences_dict = self.undistort_points(point_correspondences_dict, lens_intrinsics)
            except TaskFailure as failure:
                self.lens_notice = self.lens_unusable(failure, video_db, plugin_run)
                lens_intrinsics = None

        # all parameters are serialized based on strings when calling run_analyser
        plugin_parameters = {
            "point_correspondences": json.dumps(point_correspondences_dict),
        }
        result = self.run_analyser(
            client,
            "calibration_static_dlt",
            parameters=plugin_parameters,
            inputs={},
            downloads=["homography"],
            progress_range=self.dlt_progress_range,
        )

        if result is None:
            raise TaskFailure("homography_fit_failed", "The homography could not be fitted to the placed points")

        with transaction.atomic():
            with result[1]["homography"] as homography_data:
                homography_matrix = homography_data.y.tolist()
                reprojection_error = reprojection_rmse(
                    homography_matrix,
                    [[p["src"]["x"], p["src"]["y"]] for p in point_correspondences_dict],
                    [[p["dst"]["x"], p["dst"]["y"]] for p in point_correspondences_dict],
                    field_length,
                    field_width,
                )
                camera_pose = None
                if lens_intrinsics is not None:
                    try:
                        camera_pose = camera_pose_from_homography(
                            homography_matrix,
                            undistorted_camera_matrix(lens_intrinsics),
                            lens_intrinsics["width"],
                            lens_intrinsics["height"],
                            field_length=field_length,
                            field_width=field_width,
                        )
                    except Exception:
                        logging.exception(f"Camera pose estimation failed for calibration asset {data_db.id}")

                # Every run keeps its own calibration, so the variants (with a lens profile, with a solved
                # lens, with none) can be compared and switched between afterwards. The asset mirrors the
                # active one -- that is what the overlay, KPI computation and position data read.
                calibration = Calibration.objects.create(
                    calibration_asset=data_db,
                    plugin_run=plugin_run,
                    plugin=getattr(self, "plugin_name", ""),
                    homography_matrix=homography_matrix,
                    lens_intrinsics=lens_intrinsics,
                    camera_pose=camera_pose,
                    reprojection_error=reprojection_error,
                    lens_notice=self.lens_notice if lens_intrinsics is None else None,
                )
                data_db.apply_calibration(calibration)
                logging.debug(f"Updated homography matrix {homography_matrix} for calibration asset {data_db.id}")

        return {
            "plugin_run": plugin_run.id.hex,
            # "plugin_run_results": [plugin_run_result_db.id.hex],
            # "data": {"homography": result[1]["homography"].id},
        }

    def lens_intrinsics(
        self,
        client: TaskAnalyserClient,
        video_db: Optional[Video],
        keypoints: List[Dict],
        field_length: float,
        field_width: float,
        sport: Optional[str],
        plugin_run: Optional[PluginRun],
    ) -> Optional[Dict]:
        """The lens the clicks are undistorted with before the homography fit: the video's lens profile, if any.

        Returning None fits the homography on the raw clicks (pinhole); a subclass that does so because its lens
        could not be determined sets ``self.lens_notice`` to say why (see ``lens_unusable``).
        """
        if video_db is None or video_db.lens_profile is None:
            return None
        return lens_intrinsics_snapshot(video_db.lens_profile, video_db.width, video_db.height, crop=video_db.lens_crop)

    @staticmethod
    def undistort_points(point_correspondences: List[Dict], lens_intrinsics: Dict) -> List[Dict]:
        """The correspondences with their video side undistorted with the lens, dropping the points beyond the lens
        model's valid range. Raises TaskFailure when fewer than 4 remain. Doesn't modify its input."""
        undistorted = undistort_with_snapshot(
            [[p["src"]["x"], p["src"]["y"]] for p in point_correspondences], lens_intrinsics
        )
        valid = [
            {**point, "src": {"x": float(x), "y": float(y)}}
            for point, (x, y) in zip(point_correspondences, undistorted)
            if x == x and y == y  # NaN: beyond the lens model's valid range
        ]
        if len(valid) < 4:
            raise TaskFailure(
                "not_enough_points_after_undistortion",
                f"Only {len(valid)} placed point(s) lie within the lens model's valid range, at least 4 are needed",
                count=len(valid),
                required=4,
            )
        return valid

    def lens_unusable(
        self, failure: TaskFailure, video_db: Optional[Video], plugin_run: Optional[PluginRun]
    ) -> Dict:
        """Called when the lens can't be used for this fit. A subclass that would rather fit without lens correction
        returns the ``lens_notice`` to record for it; a lens profile the user picked is not silently dropped, so
        here the run fails."""
        raise failure
