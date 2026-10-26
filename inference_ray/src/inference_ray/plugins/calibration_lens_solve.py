import json
import logging
from typing import Callable, Dict

import numpy as np

from data import Data, DataManager, StringData, VideoData
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder

logger = logging.getLogger(__name__)

default_config = {
    "data_dir": "/data",
}

default_parameters = {
    # JSON list of {"name", "video": [x, y] relative video coordinates, "pitch": [x, y] metres from the lower-left
    # pitch corner}: the clicked keypoints with their metric positions
    "keypoints": "[]",
    "field_length": 105.0,
    "field_width": 68.0,
    # frames sampled evenly between 5 % and 95 % of the video (static camera) to detect the markings in
    "num_frames": 8,
    # see inference_ray/calib/solver.py:DEFAULT_PARAMETERS
    "rounds": 5,
    "poly_degree": 6,
    "outlier_px": 3.0,
    "first_round_outlier_px": 15.0,
}

requires = {
    "video": VideoData,
}

provides = {
    "lens": StringData,
}


@AnalyserPluginManager.export("calibration_lens_solve")
class CalibrationLensSolve(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    """Self-calibrates the lens distortion of a static camera from clicked pitch keypoints and the painted pitch
    markings (prior-free angular-polynomial solver ported from trak, see inference_ray/calib). Returns the lens in
    physical units as JSON, with the solver rounds, the pose fit under the lens and the frames used."""

    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:
        from inference_ray.calib.pitch import SoccerPitch, corner_to_pitch
        from inference_ray.calib.solver import calibrate, measure_content_rect

        keypoints = json.loads(parameters.get("keypoints"))
        length, width = float(parameters.get("field_length")), float(parameters.get("field_width"))
        num_frames = max(1, int(parameters.get("num_frames")))
        if len(keypoints) < 4:
            raise ValueError("At least 4 keypoints with a metric pitch position are required")

        self.update_callbacks(callbacks, progress=0.0)
        with inputs["video"] as input_data:
            f_video = input_data.open_video()
            try:
                decoder = VideoDecoder(f_video, extension=f".{input_data.ext}", ref_id=input_data.id)
                duration_s = decoder.duration() / 1000.0
                times = np.linspace(0.05, 0.95, num_frames) * duration_s if duration_s > 0 else [0.0]
                sampled = list(decoder.sample(times))
            finally:
                if hasattr(f_video, "close"):
                    try:
                        f_video.close()
                    except Exception:
                        logger.exception("Error closing video object")
        if not sampled:
            raise ValueError("Could not decode any frame of the video")
        frames = [s["frame"] for s in sampled]
        frame_h, frame_w = frames[0].shape[:2]
        self.update_callbacks(callbacks, progress=0.1)

        # relative video coordinates -> frame px with pixel centers at integers (the solver's convention)
        raw = np.array([k["video"] for k in keypoints], dtype=np.float64) * [frame_w, frame_h] - 0.5
        pitch_xy = corner_to_pitch([k["pitch"] for k in keypoints], length, width)
        rect = measure_content_rect(frames)
        logger.info(
            f"Lens solver: {len(keypoints)} keypoint(s), {len(frames)} frame(s) of {frame_w}x{frame_h}, "
            f"content rect {rect}, pitch {length} x {width} m"
        )

        solver_params = {
            "rounds": int(parameters.get("rounds")),
            "poly_degree": int(parameters.get("poly_degree")),
            "outlier_px": float(parameters.get("outlier_px")),
            "first_round_outlier_px": float(parameters.get("first_round_outlier_px")),
        }
        result = calibrate(
            frames, raw, pitch_xy, SoccerPitch(length, width), rect, solver_params,
            progress=lambda p: self.update_callbacks(callbacks, progress=0.1 + 0.85 * p),
        )
        # camera position in sportvid's frame: metres from the lower-left corner, height above the pitch
        cx, cy, cz = result["pose"].pop("camera_position")
        result["pose"]["position"] = {"x": cx + length / 2.0, "y": width / 2.0 - cy}
        result["pose"]["height"] = -cz
        result.update(
            frame_size=[frame_w, frame_h],
            frame_times_ms=[s["time"] for s in sampled],
            keypoints=[k["name"] for k in keypoints],
            parameters=solver_params,
        )

        with data_manager.create_data("StringData") as output_data:
            output_data.text = json.dumps(result)
            self.update_callbacks(callbacks, progress=1.0)
            return {"lens": output_data}
