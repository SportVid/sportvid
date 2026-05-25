from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData
)
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

from typing import Any, Callable, Dict, List, Tuple
import argparse

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
    "detector": "yolox",
    "tracker": "bytetrack"
}

default_yolox_params = {
    "batch_size": 2,
    "conf_thresh": 0.25,
    "nms_thresh": 0.65,
    "fp16": False,
    "num_classes": 2, 
    "decode": True,             # whether to decode the model outputs into bounding boxes during inference. If False, raw model outputs will be returned.
    "test_size": [576, 1024]
}

default_yoloultra_params = {
    "batch_size": 2,
    "conf": 0.1,                # min confidence threshold [0.1 - 0.6]
    "iou": 0.3,                 # threshold for NMS; lower values -> less detections [0.3 - 0.6]
    "agnostic_nms": False,      # class-agnostic NMS; merge overlapping boxes of different classes
    "classes": [0, 32],         # filters predictions to specified class set: 'person','sports_ball' for COCO dataset
    "half": False,
    "imgsz": None,              # e.g. [640, 1280] or null to use img dims
    "max_det": 100,             # max amount of detections per frame
    "embed": None,              # specify layers from which to extract feature vectors or embeddings
    "verbose": False,
}

default_rfdetr_params = {
    "batch_size": 2,
    "conf": 0.2,               
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    # "classes": ['ball', 'player', 'referee', 'goalkeeper'], # specific checkpoint
    "max_det": 100,
    "resolution": 672,          # has to be divisible by 56: [672,728,784,896,1008,1064,1120]
    "verbose": False,
}

default_rtdetr_params = {
    "batch_size": 2,
    "conf": 0.25,
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    "verbose": False,
}

default_bytetrack_params = {
    "track_thresh": 0.4,        # tracking confidence threshold (0.6 = default)
    "track_buffer": 300,        # num of frames to keep lost tracks
    "match_thresh": 0.8,        # [0.8, 0.6, 0.4]; high = fewer ID switches, low -> More MOTA; IoU matching threshold for associating detections to existing tracks
    "mot20": False,             # 'True' skips fusing scores?
    "aspect_ratio_thresh": 5.0, # reject tracking artifacts / FPs of unrealistic shape
    "min_box_area": 0,          # min box area thresholds (px^2)
}

# TODO: dynamic checkpoint loading for default value!

DETECTOR_MAP = {
    "yolox": YoloX,
    "yolov10": YoloUltralytics,
    "yolov11": YoloUltralytics,
    "yolov26": YoloUltralytics,
    "rfdetr": RFDetr,
    "rtdetr": RTDetr,
}

TRACKER_MAP = {
    "bytetrack": ByteTrack
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
        
        self.detector_cls = DETECTOR_MAP[config["detector"]]
        self.tracking_cls = TRACKER_MAP[config["tracker"]]

    
    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ):
        import json
        from collections import defaultdict
    
        # ------> decode video and pass it to detector
        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
        # ------> detection
        """ NOTE: Old logic for both
            args = argparse.Namespace(**parameters)
            exp = get_exp(None, "yolox-x")
            exp.num_classes = args.num_classes
            exp.depth = args.depth
            exp.width = args.width

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            model = exp.get_model().to(self.device)
            checkpoint = torch.load(
                default_config["model_file"], map_location="cpu"
            )
            model.load_state_dict(checkpoint["model"])
            model.eval()
            predictor = Predictor(model, exp, None, self.device, fp16=args.fp16)

            results, img_info = self.track(video_decoder, predictor, args)
        """
        # ------> tracking
                
        # TODO: 1) process by detector
        # TODO: 2) process detections by tracker
        # TODO: 3) return correct struct
        
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

        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(bboxes_dict)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}
    
    @abstractmethod
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Anything that needs to be done before processing the input. """
        return inputs
        
    @abstractmethod
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Processing logic of this class. """
        prep_inputs = self.preprocess(inputs, **kwargs)
        return prep_inputs
    
    @abstractmethod
    def track(self, inputs: Dict[Any, Any], **kwargs):
        """ Return tracklets based on detection inputs. """
        return self.state


class Detector():
    def __init__(
        self,
        model_path: str,
        batch_size: int,
        image_size: tuple[int, int],
        detector_params: Dict[Any, Any],
        device: str = "cuda",
        **kwargs
    ):
        import torch
        self.device = device if torch.cuda.is_available() else 'cpu'
        

        
        self.detector_params = 
        
        self.batch_size = batch_size
        self.exp = get_exp(None, model_path)
        self.model_chkpt = kwargs.get("model_chkpt", None)
        self.w, self.h = image_size
        
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        """ Anything that needs to be done before processing the input. """
        input = inputs['frame']
        input = input.to(self.device).float()
        input_shape = input.shape
        
        return dict({
            'inputs' : inputs,
            'shape' : input_shape
        })
        
    @abstractmethod
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Processing logic of this class. """
        prep_inputs = self.preprocess(inputs, **kwargs)
        mode = kwargs.get('mode', 'inference')
        
        results = {}
        if mode == 'inference': results = self.run_inference(prep_inputs)
        if mode == 'finetune':  results = self.run_finetune(prep_inputs)
        
        return results