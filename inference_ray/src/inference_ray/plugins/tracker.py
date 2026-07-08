import logging
import argparse
from typing import Any, Callable, Dict, List, Tuple
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder
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
    "detector": "yolox",
    "detector_params": {},
    "tracker": "bytetrack",
    "tracker_params": {}
}

default_yolox_params = {
    "batch_size": 1,
    "conf_thresh": 0.2,
    "nms_thresh": 0.65,
    "fp16": True,
    "num_classes": 1, 
    "decode": True,             # whether to decode the model outputs into bounding boxes during inference. If False, raw model outputs will be returned.
    "test_size": [576, 1024],
    "model_path": "yolox-x",
    "model_checkpoint": "bytetrack/bytetrack_x_mot17.pth"
}

default_yoloultra_params = {
    "batch_size": 1,
    "conf": 0.1,                # min confidence threshold [0.1 - 0.6]
    "iou": 0.3,                 # threshold for NMS; lower values -> less detections [0.3 - 0.6]
    "agnostic_nms": False,      # class-agnostic NMS; merge overlapping boxes of different classes
    "classes": [0, 32],         # filters predictions to specified class set: 'person','sports_ball' for COCO dataset
    "half": False,
    "imgsz": None,              # e.g. [640, 1280] or null to use img dims
    "max_det": 100,             # max amount of detections per frame
    "embed": None,              # specify layers from which to extract feature vectors or embeddings
    "verbose": False,
    "checkpoint": "yolo_ultra/yolo11l.pt"
}

default_rfdetr_params = {
    "batch_size": 1,
    "conf": 0.2,               
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    # "classes": ['ball', 'player', 'referee', 'goalkeeper'], # specific checkpoint
    "max_det": 100,
    "resolution": 672,          # has to be divisible by 56: [672,728,784,896,1008,1064,1120]
    "verbose": False,
    "checkpoint": "detr/rf-detr-large.pth"
}

default_rtdetr_params = {
    "batch_size": 2,
    "conf": 0.25,
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    "verbose": False, 
    "checkpoint": "detr/rtdetr-x.pt"
}

default_bytetrack_params = {
    "track_thresh": 0.4,        # tracking confidence threshold (0.6 = default)
    "track_buffer": 300,        # num of frames to keep lost tracks
    "match_thresh": 0.8,        # [0.8, 0.6, 0.4]; high = fewer ID switches, low -> More MOTA; IoU matching threshold for associating detections to existing tracks
    "mot20": False,             # 'True' skips fusing scores?
    "aspect_ratio_thresh": 5.0, # reject tracking artifacts / FPs of unrealistic shape
    "min_box_area": 0,          # min box area thresholds (px^2)
}

DETECTOR_MAP = {
    "yolox": YoloX,
    "yolov10": YoloUltralytics,
    "yolov11": YoloUltralytics,
    "yolov26": YoloUltralytics,
    "rfdetr": RFDetr,
    "rtdetr": RTDetr,
}

DETECTOR_PARAMS_MAP = {
    "yolox": default_yolox_params,
    "yolov10": default_yoloultra_params,
    "yolov11": default_yoloultra_params,
    "yolov26": default_yoloultra_params,
    "rfdetr": default_rfdetr_params,
    "rtdetr": default_rtdetr_params, 
}

TRACKER_MAP = {
    "bytetrack": ByteTrack
}

TRACKER_PARAMS_MAP = {
    "bytetrack": default_bytetrack_params
}

requires = {
    "video": VideoData,
}

provides = {
    "tracklets": BboxesData,
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

        # -------> Load defaults based on selection
        self.detector_defaults = DETECTOR_PARAMS_MAP[config["detector"]]
        self.tracker_defaults = TRACKER_PARAMS_MAP[config["tracker"]]
        
        self.detector_name = config["detector"]
        self.tracker_name = config["tracker"]

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ):
        import json
        from collections import defaultdict
        
        # -------> Args check
        logging.error(parameters)
        # extend args by default values if they have not been passed to call().
        for default_arg_k, default_arg_v in zip(self.detector_defaults, self.tracker_defaults):
            logging.error(default_arg_k, default_arg_v)
            if default_arg_k not in parameters:
                parameters.update({default_arg_k : default_arg_v})
        logging.error(parameters)
        
        # -------> decode video and pass it to detector
        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
                # -------> Detector
                # ---> Instantiate objects
                self.detector = DETECTOR_MAP[self.detector_name](
                    model_path=parameters["model_path"],
                    batch_size=len(video_decoder),
                    image_size=video_decoder._size,
                    detector_cfg=parameters,
                    device="cuda",
                    **parameters
                )
                preproced_outputs = self.detector.preprocess(video_decoder)
                raw_outputs = self.detector.run_inference(preproced_outputs)
                logging.error(type(raw_outputs))
                
                # -------> Tracker
        
        # TODO: data schema below ... (team_id = 0 (inactive); 1 (ball); 2 (refs); >=3 (active teams)
        # team_id will be re-assigned by 'team_assignment' plugin at some point.
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

        # TODO: 3) return correct struct
        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(bboxes_dict)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}