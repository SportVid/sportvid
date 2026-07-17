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
    
        # -------> decode video and pass it to detector
        batch_size = parameters["detector_params"]["batch_size"]
        fps = parameters["fps"]
        parameters["tracker_params"].update({"frame_rate" : fps})
        
        with inputs["video"] as input_data:
            with input_data.open_video("r") as f_video:
                video_batcher = VideoBatcher(
                    VideoDecoder(
                        f_video, 
                        fps=fps, 
                        extension=f".{input_data.ext}"
                    ),
                    batch_size=batch_size,
                )
                num_frames = (video_batcher.duration() * video_batcher.fps()) // batch_size
                image_size = video_batcher.video_decoder._size

                # -------> instantiate detector & tracker objects
                self.detector = DETECTOR_MAP[parameters["detector"]](
                    model_path=parameters["detector_params"]["model_path"],
                    image_size=image_size,
                    detector_params=parameters["detector_params"],
                    device="cuda",
                )
                self.tracker = TRACKER_MAP[parameters["tracker"]](
                    tracker_params=parameters["tracker_params"],
                    device="cuda",
                )
                # -------> detect & track
                for frame_id, frame in enumerate(video_batcher, start=0):
                    preproced_outputs = self.detector.preprocess(frame)
                    _ = self.detector.run_inference(preproced_outputs)
                # TODO: check performance for 90m+ video footage.
                _ = self.tracker.process(
                        inputs = {
                            'detections': self.detector.state,
                            'image_shape': (self.detector.h, self.detector.w), 
                            'det_shape': self.detector.det_shape,
                        }
                    )
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
                
                # NOTE: creates a tracklet to detection class mapping.
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
                out_cls_mapping = parameters["detector_params"]["output_class_mapping"]
                
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
                        default_team_assignment = out_cls_mapping.get(str(class_id), -1).get('default_team', -1)
                        # coord normalization
                        x_norm = int(track_xywh[0]) / self.detector.w
                        y_norm = int(track_xywh[1]) / self.detector.h
                        w_norm = int(track_xywh[2]) / self.detector.w
                        h_norm = int(track_xywh[3]) / self.detector.h
                        # construction of tracklet element
                        # TODO: maybe get rid of some values here to save on memory/transfer?
                        tracklet = [
                            int(frame_id),
                            int(track_id),
                            int(default_team_assignment),
                            float(x_norm + (w_norm / 2)), float(y_norm + h_norm),
                            float(x_norm), float(y_norm), float(w_norm), float(h_norm),
                            float(track_xywh[0]), float(track_xywh[1]), float(track_xywh[2]), float(track_xywh[3]),
                            float(track_score)
                        ]
                        tracklets[frame_time].append([tracklet])        
                
                player_id_meta = {
                    pid: {
                        "id": pid, 
                        "name": str(pid), 
                        "number": pid, 
                        "team_id": default_team_assignment
                    }
                    for pid in sorted(unique_player_ids)
                }
                
                meta_dict = {
                    "team_ids": team_id_meta,
                    "player_ids": player_id_meta
                }
        
        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(tracklets)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}