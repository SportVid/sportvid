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
        with inputs["video"] as input_data:
            with input_data.open_video("r") as f_video:
                video_batcher = VideoBatcher(
                    VideoDecoder(
                        f_video, 
                        fps=batch_size, 
                        extension=f".{input_data.ext}"
                    ),
                    batch_size=batch_size,
                )
                num_frames = (video_batcher.duration() * video_batcher.fps()) // batch_size
                # -------> instantiate detector & tracker objects
                self.detector = DETECTOR_MAP[parameters["detector"]](
                    model_path=parameters["detector_params"]["model_path"],
                    batch_size=batch_size,
                    image_size=video_batcher.video_decoder._size,
                    detector_params=parameters["detector_params"],
                    device="cuda",
                )
                self.tracker = TRACKER_MAP[parameters["tracker"]](
                    tracker_params=parameters["tracker_params"],
                    device="cuda",
                )
                for loop_ctr, frame in enumerate(video_batcher):
                    start = loop_ctr * batch_size
                    end = start + batch_size
                    # -------> detect & track
                    preproced_outputs = self.detector.preprocess(frame)
                    _ = self.detector.run_inference(preproced_outputs)
                    _ = self.tracker.process(
                            inputs = {
                                'detections': self.detector.state[start:end],
                                'image_shape': (self.detector.h, self.detector.w), 
                                'det_shape': self.detector.det_shape,
                            }
                        )
        track_results = self.tracker.state
        # -------> build required output format for consistency
        # TODO: use data schema below ... (team_id = 0 (inactive); 1 (ball); 2 (refs); >=3 (active teams)
        #       team_id will be re-assigned by 'team_assignment' plugin at some point anyways.
        bboxes_dict = defaultdict(list)
        meta_dict = defaultdict(list)
        unique_player_ids = set
        
        DEFAULT_TEAM_ID = 3
        team_id_meta = {
            DEFAULT_TEAM_ID: {"id": DEFAULT_TEAM_ID, "name": "Team A"},
        }
        
        for i, per_frame_track_results in enumerate(track_results):
            for (track_id, track_score, track_xywh, team_id) in zip(
                per_frame_track_results['track_ids'],
                per_frame_track_results['track_scores'],
                per_frame_track_results['track_boxes'],
                per_frame_track_results['team_ids']
            ):
                frame_time = round((i/batch_size)*1000.) # TODO: check if frame_time is correct, got rid of "fps" as param.
                logging.error(frame_time)
                # coord normalization
                x_norm = int(track_xywh[0]) / self.detector.w
                y_norm = int(track_xywh[1]) / self.detector.h
                w_norm = int(track_xywh[2]) / self.detector.w
                h_norm = int(track_xywh[3]) / self.detector.h
            
                for tracklet in zip(track_id, track_score, track_xywh, team_id):
                    logging.error(f'{track_id}, {track_score}, {track_xywh}, {team_id}')
                
                    # TODO: implement correct data struct, also keep in mind that i need another structure for reid & team assign.
                    # bbox = [
                    #     track_id, DEFAULT_TEAM_ID, 0,
                    #     x_norm + (w_norm / 2), y_norm + h_norm,
                    #     f'{i}-{id}',
                    #     x_norm, y_norm, w_norm, h_norm,
                    #     score
                    # ]
                    # TODO: why is this wrapped in a list?
                    # bboxes_dict[frame_time].append([bbox])
                unique_player_ids.add(id)
        
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
        
        raise Exception("ggwp")
        
        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(bboxes_dict)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}