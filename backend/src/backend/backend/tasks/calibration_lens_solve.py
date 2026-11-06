import json
import logging
from typing import Dict, List, Optional

from django.utils import timezone

from backend.models import PluginRun, Video
from backend.plugin_manager import PluginManager
from backend.utils.events import publish_plugin_run
from backend.utils.lens import angular_snapshot
from backend.utils.pitch import soccer_fits
from backend.utils.task import TaskFailure
from .calibration_static_dlt import CalibrationStaticDlt
from ..utils.analyser_client import TaskAnalyserClient


logger = logging.getLogger(__name__)

# solver parameters passed through to the calibration_lens_solve analyser plugin when set
SOLVER_PARAMETERS = ("num_frames", "rounds", "poly_degree", "outlier_px", "first_round_outlier_px")


@PluginManager.export_plugin("calibration_lens_solve")
class CalibrationLensSolve(CalibrationStaticDlt):
    """The static DLT calibration with the lens chosen in this order:

    1. the video's lens profile, when the user picked one (exactly as ``calibration_static_dlt``);
    2. otherwise a lens self-calibrated from the same clicks and the painted pitch markings (inference_ray/calib,
       a prior-free distortion solver). It wants a soccer calibration asset of markers on a camera classified as
       static: the markings are detected in frames sampled across the video. The lens is stored on the calibration
       (``lens_intrinsics``, model ``angular``) and the homography is fitted on the clicks undistorted with it;
    3. when no usable lens can be solved (whatever the solver needs and doesn't get, or a solved lens that leaves
       too few clicks inside its valid range), a plain DLT+RANSAC fit on the raw clicks, i.e. a pinhole camera
       without lens correction. The run still succeeds, but the calibration carries a ``lens_notice`` with the
       reason, so the user is told that no undistortion was applied and the calibration is probably less precise.

    That is what lets the frontend pick this plugin for every video without a lens profile (see usePluginParams.js
    calibrationParams): whether the solver can run on it is decided here.
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
        """The video's lens profile if it has one, else the lens solved from the video, else None (a pinhole fit)
        with ``self.lens_notice`` saying why no lens could be solved (see the class docstring). The fallback is
        not a failure of the run."""
        self.lens_from_profile = video_db is not None and video_db.lens_profile is not None
        if self.lens_from_profile:
            logger.info(f"Video {video_db.id}: using its lens profile, the lens solver is not run")
            return super().lens_intrinsics(
                client, video_db, keypoints, field_length, field_width, sport, plugin_run
            )
        try:
            return self.solve_lens(client, video_db, keypoints, field_length, field_width, sport, plugin_run)
        except TaskFailure as failure:
            self.lens_notice = self.lens_unusable(failure, video_db, plugin_run)
        except Exception:
            logger.exception(
                f"Calibration of video {video_db.id if video_db else None}: the lens solver crashed"
            )
            self.lens_notice = self.lens_unusable(
                TaskFailure("lens_solver_failed", "The lens solver could not fit a lens to this video"),
                video_db,
                plugin_run,
            )
        return None

    def lens_unusable(
        self, failure: TaskFailure, video_db: Optional[Video], plugin_run: Optional[PluginRun]
    ) -> Dict:
        """Fall back to a fit without lens correction; returns the ``lens_notice`` for it.

        A failed analyser call has already marked the run ERROR (its status is polled from the analyser) and may
        have recorded a failure_reason (e.g. ``analyser_timeout``). The run carries on, so it is put back to
        RUNNING and that reason becomes the notice instead. A run deleted meanwhile is cancelled, not fallen back,
        and a lens profile the user picked is not dropped silently either: then the run fails as in the plain DLT.
        """
        if getattr(self, "lens_from_profile", False):
            return super().lens_unusable(failure, video_db, plugin_run)
        if plugin_run is not None:
            if not PluginRun.objects.filter(id=plugin_run.id).exists():
                raise failure
            notice = plugin_run.failure_reason or failure.to_dict()
            if plugin_run.status == PluginRun.STATUS_ERROR or plugin_run.failure_reason:
                PluginRun.objects.filter(id=plugin_run.id).update(
                    status=PluginRun.STATUS_RUNNING, failure_reason=None, update_date=timezone.now()
                )
                plugin_run.status, plugin_run.failure_reason = PluginRun.STATUS_RUNNING, None
                try:
                    publish_plugin_run(plugin_run)
                except Exception:
                    logger.warning("Failed to publish plugin run RUNNING event", exc_info=True)
        else:
            notice = failure.to_dict()
        logger.warning(
            f"Calibration of video {video_db.id if video_db else None}: no usable lens ({notice['type']}: "
            f"{notice.get('message')}), falling back to a fit without lens correction"
        )
        return notice

    def solve_lens(
        self,
        client: TaskAnalyserClient,
        video_db: Optional[Video],
        keypoints: List[Dict],
        field_length: float,
        field_width: float,
        sport: Optional[str],
        plugin_run: Optional[PluginRun],
    ) -> Optional[Dict]:
        """The lens solved from the clicks and the painted markings; raises TaskFailure when it can't be."""
        if video_db is None or not video_db.width or not video_db.height:
            raise TaskFailure(
                "video_resolution_unknown", "The lens solver needs the calibration asset's video and its resolution"
            )
        if sport != "soccer":
            raise TaskFailure(
                "unsupported_sport", f"The lens solver only supports soccer pitches, not '{sport}'", sport=sport
            )
        if not soccer_fits(field_length, field_width):
            raise TaskFailure(
                "pitch_too_small",
                f"A {field_length} x {field_width} m pitch is too small for the standard markings the solver fits",
                field_length=field_length,
                field_width=field_width,
            )
        # The markings are detected in frames across the whole video, so only a camera confirmed as static
        # qualifies; one that isn't classified (yet) is not guessed at.
        motion = video_db.camera_motion
        if motion in (Video.CAMERA_MOTION_PAN, Video.CAMERA_MOTION_ZOOM, Video.CAMERA_MOTION_PAN_ZOOM):
            raise TaskFailure(
                "camera_not_static",
                f"The lens solver needs a static camera, the video was classified as '{motion}'",
                camera_motion=motion,
            )
        if motion != Video.CAMERA_MOTION_STATIC:
            raise TaskFailure(
                "camera_motion_unknown",
                f"The lens solver needs a static camera, the video's camera motion is '{motion}'",
                camera_motion=motion,
            )
        # Several annotated frames can carry the same keypoint more than once; those repeats are extra
        # observations of one pitch point, so the minimum counts the different keypoints.
        distinct_keypoints = {k["name"] for k in keypoints}
        if len(distinct_keypoints) < self.MIN_KEYPOINTS:
            raise TaskFailure(
                "not_enough_keypoints",
                f"The lens solver needs at least {self.MIN_KEYPOINTS} different clicked soccer keypoints, "
                f"got {len(distinct_keypoints)} ({len(keypoints)} click(s) in total)",
                count=len(distinct_keypoints),
                required=self.MIN_KEYPOINTS,
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
            # the analyser call itself failed (crash, timeout, gRPC error): it does not pass on why
            raise TaskFailure("lens_solver_failed", "The lens solver could not fit a lens to this video")
        with result[1]["lens"] as data:
            solver_result = json.loads(data.text)
        if solver_result.get("failure"):
            # the solver ran but found no usable lens; its message says what was missing
            failure = solver_result["failure"]
            raise TaskFailure(
                failure.get("type") or "lens_solver_failed",
                f"The lens solver could not fit a lens to this video: {failure.get('message')}",
                reason=failure.get("message"),
            )

        snapshot = angular_snapshot(solver_result, video_db.width, video_db.height)
        solver = snapshot["solver"]
        logger.info(
            f"Video {video_db.id}: lens solved in {len(solver['rounds'] or [])} round(s) from "
            f"{len(solver['markings'] or [])} marking(s) (dropped: {solver['dropped_markings'] or 'none'}), "
            f"line RMS {solver['line_rms_px']:.2f} px, pose RMSE {solver['pose_rmse_px']:.2f} px, "
            f"horizontal FoV {solver['horizontal_fov_deg']:.1f} deg"
        )
        return snapshot
