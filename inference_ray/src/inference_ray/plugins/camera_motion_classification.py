import logging
from typing import Callable, Dict

import numpy as np

from data import DataManager, Data, StringData, VideoData
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder

logger = logging.getLogger(__name__)

LABEL_STATIC = "static"
LABEL_PAN = "pan"
LABEL_ZOOM = "zoom"
LABEL_PAN_ZOOM = "pan_zoom"
LABEL_UNKNOWN = "unknown"

default_config = {
    "data_dir": "/data",
}

default_parameters = {
    "fps": 5.0,
    "max_dimension": 320, 
    "pan_threshold": 0.05, # smoothed camera translation of the image center, in frame widths per second
    "zoom_threshold": 0.03, # smoothed absolute log scale change per second (~0.03 => 3% zoom per second)
    "min_motion_ratio": 0.1, # fraction of valid frame pairs that must show motion for the video to count as moving
    "smoothing_window": 1.0, # length of the moving average in seconds; averages out hand-held/wind jitter
}

requires = {
    "video": VideoData,
}

provides = {
    "camera_motion": StringData,
}


def _estimate_similarity(prev_gray, gray):
    """Fit a similarity transform (rotation, uniform scale, translation) mapping prev_gray to gray.
    Returns (matrix, inlier_ratio) or (None, 0.0) if the pair is not usable (e.g. a hard cut).
    """
    import cv2

    prev_pts = cv2.goodFeaturesToTrack(prev_gray, maxCorners=400, qualityLevel=0.01, minDistance=8)
    if prev_pts is None or len(prev_pts) < 20:
        return None, 0.0

    next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, prev_pts, None)
    status = status.reshape(-1).astype(bool)
    if status.sum() < 20:
        return None, 0.0

    # RANSAC keeps the dominant (background) motion and rejects moving players/ball
    matrix, inliers = cv2.estimateAffinePartial2D(
        prev_pts[status], next_pts[status], method=cv2.RANSAC, ransacReprojThreshold=1.5
    )
    if matrix is None:
        return None, 0.0
    return matrix, float(inliers.sum()) / len(inliers)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or len(values) < window:
        return values
    kernel = np.ones(window) / window
    if values.ndim == 1:
        return np.convolve(values, kernel, mode="same")
    return np.stack([np.convolve(values[:, i], kernel, mode="same") for i in range(values.shape[1])], axis=1)


@AnalyserPluginManager.export("camera_motion_classifier")
class CameraMotionClassifier(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:
        import cv2

        fps = float(parameters.get("fps"))

        with inputs["video"] as input_data:
            f_video = input_data.open_video()
            try:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=fps,
                    max_dimension=int(parameters.get("max_dimension")),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
                total_frames = max(len(video_decoder), 1)

                # per frame pair: displacement of the image center (in frame widths) and log scale change
                translations = []
                log_scales = []

                prev_gray = None
                for i, frame in enumerate(video_decoder):
                    self.update_callbacks(callbacks, progress=(i + 1) / total_frames)
                    gray = cv2.cvtColor(frame["frame"], cv2.COLOR_RGB2GRAY)

                    if prev_gray is not None:
                        matrix, inlier_ratio = _estimate_similarity(prev_gray, gray)
                        # a low inlier ratio usually means a shot cut, skip those pairs
                        if matrix is not None and inlier_ratio >= 0.3:
                            h, w = gray.shape
                            center = np.array([w / 2, h / 2, 1.0])
                            shift = matrix @ center - center[:2]
                            scale = np.sqrt(matrix[0, 0] ** 2 + matrix[1, 0] ** 2)
                            translations.append(shift / w)
                            log_scales.append(np.log(scale))
                    prev_gray = gray
            finally:
                if hasattr(f_video, "close"):
                    try:
                        f_video.close()
                    except Exception:
                        logger.exception("Error closing video object")

        label = self.classify(np.asarray(translations), np.asarray(log_scales), fps, parameters)

        with data_manager.create_data("StringData") as output_data:
            output_data.text = label
            self.update_callbacks(callbacks, progress=1.0)
            return {"camera_motion": output_data}

    def classify(self, translations: np.ndarray, log_scales: np.ndarray, fps: float, parameters: Dict) -> str:
        if len(translations) == 0:
            logger.warning("No usable frame pairs for camera motion estimation")
            return LABEL_UNKNOWN

        window = max(int(round(float(parameters.get("smoothing_window")) * fps)), 1)
        # signed values are averaged before taking magnitudes, so oscillating jitter cancels out
        pan_speed = np.linalg.norm(_moving_average(translations, window), axis=1) * fps
        zoom_speed = np.abs(_moving_average(log_scales, window)) * fps

        pan_ratio = float(np.mean(pan_speed > float(parameters.get("pan_threshold"))))
        zoom_ratio = float(np.mean(zoom_speed > float(parameters.get("zoom_threshold"))))
        min_ratio = float(parameters.get("min_motion_ratio"))
        is_pan = pan_ratio > min_ratio
        is_zoom = zoom_ratio > min_ratio

        if is_pan and is_zoom:
            label = LABEL_PAN_ZOOM
        elif is_pan:
            label = LABEL_PAN
        elif is_zoom:
            label = LABEL_ZOOM
        else:
            label = LABEL_STATIC

        logger.info(
            f"Camera motion: {label} (pairs={len(translations)}, pan_ratio={pan_ratio:.3f}, "
            f"zoom_ratio={zoom_ratio:.3f}, median_pan={np.median(pan_speed):.4f}, "
            f"median_zoom={np.median(zoom_speed):.4f})"
        )
        return label
