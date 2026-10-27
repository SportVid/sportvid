import json
import logging
from typing import Dict, List, Optional

from backend.models import PluginRun, Video
from backend.plugin_manager import PluginManager
from backend.utils.lens import angular_snapshot
from backend.utils.pitch import soccer_fits
from .calibration_static_dlt import CalibrationStaticDlt
from ..utils.analyser_client import TaskAnalyserClient


logger = logging.getLogger(__name__)

# solver parameters passed through to the calibration_lens_solve analyser plugin when set
SOLVER_PARAMETERS = ("num_frames", "rounds", "poly_degree", "outlier_px", "first_round_outlier_px")


@PluginManager.export_plugin("calibration_lens_solve")
class CalibrationLensSolve(CalibrationStaticDlt):
    """The static DLT calibration with a lens self-calibrated from the same clicks and the painted pitch markings,
    instead of a lens profile (inference_ray/calib, ported from trak's prior-free distortion solver).

    Needs a soccer calibration asset of markers on a static camera: the markings are detected in frames sampled
    across the video. The lens is stored on the calibration asset (``lens_intrinsics``, model ``angular``) and the
    homography is fitted on the clicks undistorted with it. The video's lens profile is not used.
    """

    dlt_progress_range = (0.9, 1.0)
    MIN_KEYPOINTS = 6

    # the lens solve runs first, then the inherited homography fit
    ray_plugins = ("calibration_lens_solve", "calibration_static_dlt")

    def __call__(self, parameters: Dict, **kwargs):
        self.solver_parameters = {k: parameters[k] for k in SOLVER_PARAMETERS if parameters.get(k) is not None}
        return super().__call__(parameters, **kwargs)

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
        if video_db is None or not video_db.width or not video_db.height:
            raise Exception("The lens solver needs the calibration asset's video and its resolution")
        if sport != "soccer":
            raise Exception(f"The lens solver only supports soccer pitches, not '{sport}'")
        if not soccer_fits(field_length, field_width):
            raise Exception(
                f"A {field_length} x {field_width} m pitch is too small for the standard markings the solver fits"
            )
        motion = video_db.camera_motion
        if motion in (Video.CAMERA_MOTION_PAN, Video.CAMERA_MOTION_ZOOM, Video.CAMERA_MOTION_PAN_ZOOM):
            raise Exception(f"The lens solver needs a static camera, the video was classified as '{motion}'")
        if motion != Video.CAMERA_MOTION_STATIC:
            logger.warning(
                f"Video {video_db.id}: camera motion is '{motion}', the lens solver assumes a static camera"
            )
        if len(keypoints) < self.MIN_KEYPOINTS:
            raise Exception(
                f"The lens solver needs at least {self.MIN_KEYPOINTS} clicked soccer keypoints, got {len(keypoints)}"
            )

        video_id = self.upload_video(client, video_db)
        result = self.run_analyser(
            client,
            "calibration_lens_solve",
            parameters={
                "keypoints": json.dumps(keypoints),
                "field_length": field_length,
                "field_width": field_width,
                **self.solver_parameters,
            },
            inputs={"video": video_id},
            downloads=["lens"],
            progress_range=(0.0, 0.9),
        )
        if result is None:
            raise Exception("Lens solver failed")
        with result[1]["lens"] as data:
            solver_result = json.loads(data.text)

        snapshot = angular_snapshot(solver_result, video_db.width, video_db.height)
        solver = snapshot["solver"]
        logger.info(
            f"Video {video_db.id}: lens solved in {len(solver['rounds'] or [])} round(s) from "
            f"{len(solver['markings'] or [])} marking(s) (dropped: {solver['dropped_markings'] or 'none'}), "
            f"line RMS {solver['line_rms_px']:.2f} px, pose RMSE {solver['pose_rmse_px']:.2f} px, "
            f"horizontal FoV {solver['horizontal_fov_deg']:.1f} deg"
        )
        return snapshot
