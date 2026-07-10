import logging
import argparse
from typing import Any, Callable, Dict, List, Tuple
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder, VideoBatcher
from .detector import (
    YoloX, 
    YoloUltralytics,
    RFDetr,
    RTDetr
) 
from .tracker import (
    ByteTrack,
)


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
    "fps": 30,
    "detector": "yolox",
    "detector_params": {},
    "tracker": "bytetrack",
    "tracker_params": {}
}

requires = {
    "video": VideoData,
}

provides = {
    "tracklets": BboxesData,
}

DETECTOR_MAP = {
    "yolox": YoloX,
    "yolov10": YoloUltralytics,
    "yolov11": YoloUltralytics,
    "yolov12": YoloUltralytics,
    "yolov26": YoloUltralytics,
    "rfdetr": RFDetr,
    "rtdetr": RTDetr,
}

TRACKER_MAP = {
    "bytetrack": ByteTrack
}


@AnalyserPluginManager.export("tracker")
class Tracker(
    AnalyserPlugin,
    config=default_config,
    parameters={},
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
    ):
        import json
        from collections import defaultdict
        
        # -------> decode video and pass it to detector
        with inputs["video"] as input_data:
            with input_data.open_video("r") as f_video:
                video_decoder = VideoBatcher(
                    VideoDecoder(
                        f_video, 
                        fps=parameters["detector_params"]["batch_size"], 
                        extension=f".{input_data.ext}"
                    ),
                    batch_size=parameters.get("batch_size"),
                )
                num_frames = (video_decoder.duration() * video_decoder.fps()) // parameters.get("batch_size")
                # -------> instantiate detector & tracker objects
                self.detector = DETECTOR_MAP[self.parameters.detector](
                    model_path=parameters["detector_params"]["model_path"],
                    batch_size=parameters["detector_params"]["batch_size"],
                    image_size=video_decoder._size,
                    detector_params=parameters["detector_params"],
                    device="cuda",
                )
                self.tracker = TRACKER_MAP[self.parameters.tracker](
                    tracker_params=parameters["tracker_params"],
                    device="cuda",
                )
                for i, frame in enumerate(video_decoder):
                    # -------> process detections
                    preproced_outputs = self.detector.preprocess(video_decoder)
                    raw_outputs = self.detector.run_inference(preproced_outputs)
                    logging.error(type(raw_outputs))
                    # -------> TOOD: process tracking       

        # -------> build required output format for consistency
        # TODO: use data schema below ... (team_id = 0 (inactive); 1 (ball); 2 (refs); >=3 (active teams)
        #       team_id will be re-assigned by 'team_assignment' plugin at some point anyways.
        bboxes_dict = defaultdict(list)
        meta_dict = defaultdict(list)
        """
        DEFAULT_TEAM_ID = 3
        bboxes_dict = defaultdict(list)
        unique_player_ids = set()
        for i, frame_info in enumerate(results):
            frame_time = round((i/args.fps)*1000.)
            for id, score, box in zip(
                frame_info["track_ids"],
                frame_info["track_scores"],
                frame_info["track_boxes"],
            ):
                # Normalize coordinates once
                x_norm = int(box[0]) / img_info["width"]
                y_norm = int(box[1]) / img_info["height"]
                w_norm = int(box[2]) / img_info["width"]
                h_norm = int(box[3]) / img_info["height"]

                bbox = [
                    id, DEFAULT_TEAM_ID, 0,
                    x_norm + (w_norm / 2), y_norm + h_norm,
                    f'{i}-{id}',
                    x_norm, y_norm, w_norm, h_norm,
                    score
                ]
                bboxes_dict[frame_time].append(bbox)
                unique_player_ids.add(id)

        # New schema: separate dicts per entity kind. ByteTrack populates only player_ids
        # (with team_id=3); ref_ids/ball_ids stay empty until a classification plugin runs.
        team_id_meta = {
            DEFAULT_TEAM_ID: {"id": DEFAULT_TEAM_ID, "name": "Team A"},
        }
        player_id_meta = {
            pid: {"id": pid, "name": str(pid), "number": pid, "team_id": DEFAULT_TEAM_ID}
            for pid in sorted(unique_player_ids)
        }
        meta_dict = {
            "team_ids": team_id_meta,
            "player_ids": player_id_meta,
            "ref_ids": {},
            "ball_ids": {},
        }
        """
        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(bboxes_dict)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}