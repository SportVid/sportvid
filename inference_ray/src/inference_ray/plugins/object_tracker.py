import logging
import argparse
from pprint import pprint
from enum import IntEnum
from typing import Any, Callable, Dict, List, Tuple, Optional
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder, VideoBatcher


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

requires = {
    "video": VideoData,
}

provides = {
    "tracklets": BboxesData,
}


class TeamId(IntEnum):
    UNKNOWN = (-1, "Unknown")
    BALL = (0, "Ball")
    BYSTANDER = (1, "Bystander")
    REFEREE = (2, "Referee")
    TEAM_LEFT = (3, "Team A")
    TEAM_RIGHT = (4, "Team B")

    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj


@AnalyserPluginManager.export("object_tracker")
class ObjectTracker(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.1",
    requires=requires,
    provides=provides
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
        import time
        from collections import defaultdict
        from .detector import (
            YoloX, 
            YoloUltralytics,
            RFDetr,
            RTDetr
        )
        from .tracker import (
            ByteTrack,
            TrackClassMapper
        )
        
        DETECTOR_MAP = {
            "yolox": YoloX,
            "yolo10": YoloUltralytics,
            "yolo11": YoloUltralytics,
            "yolo12": YoloUltralytics,
            "yolo26": YoloUltralytics,
            "rfdetr": RFDetr,
            "rtdetr": RTDetr,
        }
        TRACKER_MAP = {
           "bytetrack": ByteTrack
        }
    
        # -------> decode video and pass it to detector
        # TODO: Implement VideoBatcher for more efficient mini-batch processing.
        batch_size = parameters["detector_params"]["batch_size"]
        
        fps = parameters["fps"]
        parameters["tracker_params"].update({"frame_rate" : fps})
        self.tracker = parameters.get("tracker", None)
        if self.tracker in [None, "", "None"]: self.tracker = None
        
        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
                image_size = video_decoder._size
                # s = time.time()
                # -------> instantiate detector & tracker objects
                self.detector = DETECTOR_MAP[parameters["detector"]](
                    model_path=parameters["detector_params"]["model_path"],
                    image_size=image_size,
                    detector_params=parameters["detector_params"],
                    device="cuda",
                )
                if self.tracker:
                    self.tracker = TRACKER_MAP[parameters["tracker"]](
                        tracker_params=parameters["tracker_params"],
                        device="cuda",
                    )
                # -------> detect & track
                total_frames = len(video_decoder)
                last_reported = 0.0

                for frame_id, _frame in enumerate(video_decoder):
                    preproced_outputs = self.detector.preprocess(_frame)
                    _ = self.detector.run_inference(preproced_outputs)
                    # NOTE: Since detection dominates the runtime, it owns almost the whole progress bar.
                    if total_frames:
                        now = time.time()
                        if now - last_reported >= 1.0: # reported at most once a second
                            last_reported = now
                            # every write crosses into the shared-memory dict the analyser server polls
                            self.update_callbacks(
                                callbacks,
                                progress=min((frame_id + 1) / total_frames, 1.0) * 0.9,
                            )

                tracker_inputs = {
                    'detections': self.detector.state,
                    'image_shape': (self.detector.h, self.detector.w), 
                    'det_shape': self.detector.det_shape,
                }
                self.update_callbacks(callbacks, progress=0.9)
                if self.tracker:
                    _ = self.tracker.process(tracker_inputs)  # TODO: check performance for 90m+ video footage.
                    # NOTE: Creates a tracklet to detection class mapping.
                    # We'll use it for the default team assignment at this stage.
                    trk_det_mapping = TrackClassMapper().map_tracks_to_detections(
                        tracks=self.tracker.state,
                        detections=self.detector.state,
                        iou_thresh=0.3
                    )
                    """
                    {
                        "0":{
                            "entity_type": "athlete",
                            "default_team": "3"
                        }, ...
                    }                
                    """
                
                # e = time.time()
                # logging.error(f"object_tracker.py took: {e-s}")
                
                # -------> build the required output format for consistency with other plugins
                tracklets = defaultdict(list)
                unique_player_ids = set()
                
                # TODO: This is specific to team-based sports, need a generic solution at some point...!
                team_id_meta = {
                    TeamId.UNKNOWN: {"name": "Unknown"},
                    TeamId.BYSTANDER: {"name": "Bystander"},
                    TeamId.BALL: {"name": "Ball"},
                    TeamId.REFEREE: {"name": "Referee"},
                    TeamId.TEAM_LEFT: {"name": "Team A"},
                    TeamId.TEAM_RIGHT: {"name": "Team B"},
                }
                out_cls_map = parameters["detector_params"]["output_class_mapping"]
                
                # --------------------------------------------------
                # ----------- NOTE: output of this plugin run returns tracklets
                if self.tracker:
                    for frame_id, track in enumerate(self.tracker.state, start=0): # [N,5]
                        for (track_id, track_score, track_xywh, team_id) in zip( # [5,]
                            track['track_ids'],
                            track['track_scores'],
                            track['track_boxes'],
                            track['team_ids']
                        ):
                            frame_time = round((frame_id/fps)*1000.)
                            unique_player_ids.add(track_id)
                            # NOTE: Mapping of class_id to team_id.
                            # Detectors have varying output heads, so we need some mapping dict from cls_id to real-world entity.
                            class_id = trk_det_mapping[frame_id][track_id]['class']
                            assigned_cls_id = out_cls_map.get(str(class_id), {})
                            default_team_assgn = assigned_cls_id.get("default_team", 3)
                            # coord normalization
                            x_norm = int(track_xywh[0]) / self.detector.w
                            y_norm = int(track_xywh[1]) / self.detector.h
                            w_norm = int(track_xywh[2]) / self.detector.w
                            h_norm = int(track_xywh[3]) / self.detector.h
                            # construction of tracklet element
                            tracklet = [
                                int(track_id),
                                int(default_team_assgn),
                                0,
                                float(x_norm + (w_norm / 2)), float(y_norm + h_norm),
                                float(x_norm), float(y_norm), float(w_norm), float(h_norm),
                                float(track_score)
                            ]
                            tracklets[frame_time].append(tracklet)
                else:
                # ----------- NOTE: output of this plugin run returns detections only.
                # TODO: currently hard-coded for ball detections...!
                    for frame_id, detections in enumerate(tracker_inputs['detections']):
                        frame_time = round((frame_id / fps) * 1000.0)
                        for det in detections:
                            class_id = det["cls_id"]
                            track_id = 0 # NOTE: always assigning 0 to all detections here.
                            assigned_cls = out_cls_map.get(str(class_id), {})
                            default_team_assgn = assigned_cls.get("default_team", 3)

                            x, y, w, h = det["xywh"]
                            x_norm = x / self.detector.w
                            y_norm = y / self.detector.h
                            w_norm = w / self.detector.w
                            h_norm = h / self.detector.h

                            track_score = det["conf"]

                            tracklet = [
                                int(track_id),
                                int(default_team_assgn),
                                0,
                                float(x_norm + (w_norm / 2)),
                                float(y_norm + h_norm),
                                float(x_norm),
                                float(y_norm),
                                float(w_norm),
                                float(h_norm),
                                float(track_score),
                            ]
                            tracklets[frame_time].append(tracklet)
                # --------------------------------------------------
                player_id_meta = {
                    pid: {
                        "id": pid, 
                        "name": str(pid), 
                        "number": pid, 
                        "team_id": int(default_team_assgn)
                    }
                    for pid in sorted(unique_player_ids)
                }     
                meta_dict = {
                    "team_ids": team_id_meta,
                    "player_ids": player_id_meta,
                    "video": dict(
                        fps=fps,
                        h=int(self.detector.h),
                        w=int(self.detector.w)
                    )
                }
        
        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(tracklets)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}