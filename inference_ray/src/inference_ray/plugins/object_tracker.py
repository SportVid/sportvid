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
            ByteTrack
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
        
        # with inputs["video"] as input_data:
        #     with input_data.open_video() as f_video:
        #         video_decoder = VideoDecoder(
        #             f_video,
        #             fps=fps,
        #             extension=f".{input_data.ext}",
        #             ref_id=input_data.id,
        #         )
        #         image_size = video_decoder._size
        
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
                    batch_size=batch_size,
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

                track_results = self.tracker.state # NOTE: returns a list of per-frame tracking results

                # -------> build the required output format for consistency with other plugins
                tracklets = defaultdict(list)
                unique_player_ids = set()
                
                DEFAULT_BYSTANDER_TEAM_ID = 0
                DEFAULT_BALL_TEAM_ID = 1
                DEFAULT_REF_TEAM_ID = 2 
                DEFAULT_TEAM_ID = 3
                
                team_id_meta = {
                    DEFAULT_BYSTANDER_TEAM_ID: {
                        "name": "Bystander",
                    },
                    DEFAULT_BALL_TEAM_ID: {
                        "name": "Ball",
                    },
                    DEFAULT_REF_TEAM_ID: {
                        "name": "Referee"
                    },
                    DEFAULT_TEAM_ID: {
                        "name": "Team A"
                    },
                }
                
                # TODO: create a tracklet to detection class mapping for the default team assignment at this stage.
                
                for frame_id, track in enumerate(track_results, start=0): # [N,5]
                    for (track_id, track_score, track_xywh, team_id) in zip( # [5,]
                        track['track_ids'],
                        track['track_scores'],
                        track['track_boxes'],
                        track['team_ids']
                    ):
                        unique_player_ids.add(track_id)
                        frame_time = round((frame_id/fps)*1000.)
                        # coord normalization
                        x_norm = int(track_xywh[0]) / self.detector.w
                        y_norm = int(track_xywh[1]) / self.detector.h
                        w_norm = int(track_xywh[2]) / self.detector.w
                        h_norm = int(track_xywh[3]) / self.detector.h
                        # construction of tracklet element
                        tracklet = [
                            int(frame_id),
                            int(track_id),
                            int(DEFAULT_TEAM_ID),
                            float(track_xywh[0]), float(track_xywh[1]), float(track_xywh[2]), float(track_xywh[3]),
                            float(x_norm + (w_norm / 2)), float(y_norm + h_norm),
                            float(x_norm), float(y_norm), float(w_norm), float(h_norm),
                            float(track_score),
                        ]
                        tracklets[frame_time].append([tracklet])        
                
                player_id_meta = {
                    pid: {
                        "id": pid, 
                        "name": str(pid), 
                        "number": pid, 
                        "team_id": DEFAULT_TEAM_ID
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