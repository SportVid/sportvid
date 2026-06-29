import argparse
import logging

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from data import (
    Data, DataManager, 
    VideoData, 
    # BBoxData,
    BboxesData
)
from utils import VideoDecoder
from typing import Any, Callable, Dict, List, Tuple

"""ByteTrack, see original repo: https://github.com/ifzhang/ByteTrack

TODO: Replace with ONNX version, see https://github.com/ifzhang/ByteTrack/tree/main/deploy/ONNXRuntime
TODO: stream output_data to avoid memory issues in future plugins?
"""

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
    "model_name": "bytetrack",
    "model_file": "/models/bytetrack/bytetrack_x_mot17.pth.tar",
}

# args from tools/demo_track.py
default_parameters = {
    "fps": 30,
    "track_thresh": 0.6,    # tracking confidence threshold
    "track_buffer": 30,     # the frames for keep lost tracks
    "match_thresh": 0.8,    # matching threshold for tracking
    "fp16": False,          # TODO True does not work
    "fuse": True,
    "aspect_ratio_thresh": 1.6,
    "min_box_area": 10,
    "mot20": False,
    "num_classes": 1,
    "depth": 1.33,
    "width": 1.25,
}

requires = {
    "video": VideoData,
}

provides = {
    "tracklets": BboxesData,
}


class Predictor(object):
    def __init__(self, model, exp, decoder=None, device='cpu', fp16=False):
        self.model = model
        self.decoder = decoder
        self.num_classes = exp.num_classes
        self.confthre = exp.test_conf
        self.nmsthre = exp.nmsthre
        self.test_size = exp.test_size
        self.device = device
        self.fp16 = fp16

        if fp16:
            self.model = model.half()

        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

    def inference(self, img):
        import torch
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        from yolox.data.data_augment import preproc
        from yolox.utils import postprocess

        img_info = {"id": 0}

        height, width = img.shape[:2]
        img_info["height"] = height
        img_info["width"] = width
        img_info["raw_img"] = img
        img, ratio = preproc(img, self.test_size, self.rgb_means, self.std)
        img_info["ratio"] = ratio
        img = torch.from_numpy(img).unsqueeze(0).float().to(self.device)
        if self.fp16:
            img = img.half()  # to FP16

        with torch.no_grad():
            outputs = self.model(img)
            if self.decoder is not None:
                outputs = self.decoder(outputs, dtype=outputs.type())
            outputs = postprocess(
                outputs, self.num_classes, self.confthre, self.nmsthre
            )
        return outputs, img_info


@AnalyserPluginManager.export("bytetrack")
class ByteTrack(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.model = None
        self.model_name = self.config.get("model_name")

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:        
        import json
        from collections import defaultdict
        
        import torch
        from yolox.exp import get_exp

        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )

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

                # New entity-classification scheme (see posdata_convert): team_id=1 ball, =2 refs,
                # =0 inactive, ≥3 active teams. ByteTrack only knows "person" detections — assign
                # all to team_id=3 (single team). A future classification plugin will reassign.
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

                with data_manager.create_data("BboxesData") as output_data:
                    output_data.bboxes = json.dumps(bboxes_dict)
                    output_data.meta_data = json.dumps(meta_dict)
                    self.update_callbacks(callbacks, progress=1.0)

                return {"tracklets": output_data}

    def track(
        self,
        video_decoder: VideoDecoder,
        predictor: Predictor,
        args: argparse.Namespace,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Performs object tracking

        Result dictionary format for each frame:
        {
            "frame_id": int,
            "track_ids": [int],
            "track_scores": [float],
            "track_boxes": [np.array(top left x, top left y, width, height)],
        }

        Args:
            video_decoder (VideoDecoder): Iterator over video
            predictor (Predictor): Predictor model
            args (argparse.Namespace): Parameters / arguments

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Results with dictionary per frame, image info
        """
        from yolox.tracker.byte_tracker import BYTETracker

        tracker = BYTETracker(args, frame_rate=args.fps)

        results = []
        for frame_id, _frame in enumerate(video_decoder):
            outputs, img_info = predictor.inference(_frame["frame"])

            online_tlwhs = []
            online_ids = []
            online_scores = []

            if outputs[0] is not None:
                online_targets = tracker.update(
                    outputs[0],
                    [img_info["height"], img_info["width"]],
                    predictor.test_size,
                )

                for t in online_targets:
                    tlwh = t.tlwh
                    tid = t.track_id
                    vertical = tlwh[2] / tlwh[3] > args.aspect_ratio_thresh
                    if tlwh[2] * tlwh[3] > args.min_box_area and not vertical:
                        online_tlwhs.append(tlwh)
                        online_ids.append(tid)
                        online_scores.append(t.score.item())
            results.append(
                {
                    "frame_id": frame_id,
                    "track_ids": online_ids,
                    "track_scores": online_scores,
                    "track_boxes": online_tlwhs,
                }
            )
        return results, img_info
