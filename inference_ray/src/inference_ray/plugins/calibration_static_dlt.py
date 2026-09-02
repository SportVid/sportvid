from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

import logging
from data import ScalarData
from data import DataManager, Data

from typing import Callable, Dict

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}


default_parameters = {}

requires = {}

provides = {
    "homography": ScalarData, 
}


@AnalyserPluginManager.export("calibration_static_dlt")
class DltCalibrationStatic(
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
        
        import numpy as np
        import cv2
        import json

        # Single closed-form homography solve -- effectively instantaneous, so there's
        # no meaningful intermediate progress to report, just "started" and "done".
        self.update_callbacks(callbacks, progress=0.1)

        # Deserialize point_correspondences from JSON string
        logging.debug(f"Parameters: {parameters}")

        if "point_correspondences" not in parameters:
            raise ValueError("Point correspondences are required for calibration")
        
        point_correspondences = json.loads(parameters["point_correspondences"])
        if len(point_correspondences) < 4:
            raise ValueError("At least 4 point correspondences are required for calibration")

        src_points: np.ndarray = np.stack(
            [
                [point["src"]["x"], point["src"]["y"]]
                for point in point_correspondences
            ],
            axis=0,
        ) # (N, 2)
        dst_points: np.ndarray = np.stack(
            [
                [point["dst"]["x"], point["dst"]["y"]]
                for point in point_correspondences
            ],
            axis=0,
        ) # (N, 2)
        
        # TODO: colinear/degenerate point correspondences
        #   1) points tightly clustered
        #   2) near-colinear / line-like distribution
        #   3) convex hull area too small -> points nearly colinear
        #   4) too many points in a narrow strip 
    
        # https://docs.opencv.org/4.11.0/d9/d0c/group__calib3d.html#ga4abc2ece9fab9398f2e560d53c8c9780
        homography_matrix, _ = cv2.findHomography(
            src_points, 
            dst_points, 
            method=cv2.RANSAC, 
            ransacReprojThreshold=0.5 # ransac proj thresh. should be between [0.001-0.01] (very tight) or [0.01-0.05] (more forgiving but still reasonable)
        )
        
        logging.error(f"Homography matrix: {homography_matrix}")
        
        # 1) check if homography is None (estimation failed)
        if homography_matrix is None:
            logging.error("No homography matrix could be computed from the provided correspondences.")
            raise ValueError("Homography estimation failed")

        # 2) Check if homography is close to identity (calibration probably failed)
        if np.allclose(homography_matrix, np.eye(3), atol=0.1):
            logging.error("Homography matrix is too close to identity. Estimation is probably incorrect.")
            raise ValueError("Homography estimation is probably incorrect (close to identity)")

        # TODO: add information if returned homography matrix is valid or not (if checks failed -> it is bad and shouldn't be used for projection)
        with data_manager.create_data("ScalarData") as output_data:
            output_data.y = homography_matrix.tolist()
            output_data.name = "homography_matrix"
            output_data.time = [0.0]  # Required field
            output_data.delta_time = 1.0  # Required field
            
            self.update_callbacks(callbacks, progress=1.0)
            return {"homography": output_data}
