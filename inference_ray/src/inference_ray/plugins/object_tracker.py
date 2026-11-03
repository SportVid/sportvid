import logging
from typing import Any, Callable, Dict, Mapping
from data import (
    Data, DataManager,
    VideoData,
    BboxesData,
    compute_bboxes_meta
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder
from .tracker.tracklets import (
    TeamId,
    DEFAULT_TEAM_META,
    frame_time_ms,
    tracklet_row,
    center_to_tlwh,
    entity_class_ids,
    split_detections,
)


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

# entity id of the ball, and of detections written without tracking (detection-only runs)
BALL_ID = 0
UNTRACKED_ID = 0


def _class_entry(output_class_mapping: Mapping[Any, Mapping[str, Any]], cls_id) -> Mapping[str, Any]:
    """ ``output_class_mapping`` entry of a class id; keys are str once the parameters went through JSON. """
    entry = output_class_mapping.get(str(cls_id))
    if entry is None:
        entry = output_class_mapping.get(cls_id, {})
    return entry or {}


def _is_set(value) -> bool:
    return value not in (None, "", "None")


@AnalyserPluginManager.export("object_tracker")
class ObjectTracker(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.4",
    requires=requires,
    provides=provides
):
    """ Detectors -> player tracker + ball tracker -> tracklets, in stages (see tracker/README.md):

    1. detection over the decoded video: the (player) detector, and the optional ball detector, a second
       detector instance with its own parameters (``ball_detector`` / ``ball_detector_params``); either can run
       sliced (``sahi``, SAHI-style tiles, ``detector/slicing.py``);
    2. routing by ``output_class_mapping``: the ``entity_type: ball`` classes never reach the player tracker. The
       ball candidates come from the ball detector when it runs (the player detector's ball class is dropped),
       else from the player detector;
    3. player tracking (``tracker``: ``bytetrack`` | ``deep_eiou``), frame by frame inside the detection loop
       with the frame's pixels (appearance embeddings), then ``Tracker.finalize`` once over the whole clip
       (GTA-Link, interpolation);
    4. per-track class votes (``TrackClassMapper``) give each track its default team;
    5. ball tracking (``ball_tracker``: ``kalman``) over the whole clip, with the player tracks as kick hints;
       without a ball tracker, or below its ``min_fps``, the candidates are written untracked;
    6. output: player tracks, the ball (entity id 0, team ``BALL``), and in detection-only runs (no tracker)
       the other detections untracked (entity id 0).
    """

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
            RTDetr,
            SliceConfig,
            SlicedDetector,
        )
        from .tracker import (
            ByteTrack,
            DeepEIoU,
            BallTracker,
            TrackClassMapper
        )

        DETECTOR_MAP = {
            "yolox": YoloX,
            "yolox_sn_player": YoloX,
            "yolox_sn_ball": YoloX,
            "yolo10": YoloUltralytics,
            "yolo11": YoloUltralytics,
            "yolo12": YoloUltralytics,
            "yolo26": YoloUltralytics,
            "rfdetr": RFDetr,
            "rtdetr": RTDetr,
        }
        TRACKER_MAP = {
           "bytetrack": ByteTrack,
           "deep_eiou": DeepEIoU,
        }
        BALL_TRACKER_MAP = {
            "kalman": BallTracker
        }

        # -------> decode video and pass it to detector
        # TODO: Implement VideoBatcher for more efficient mini-batch processing.
        batch_size = parameters["detector_params"]["batch_size"]

        fps = parameters["fps"]
        parameters["tracker_params"].update({"frame_rate" : fps})
        self.tracker = parameters.get("tracker", None)
        if not _is_set(self.tracker): self.tracker = None
        ball_detector_name = parameters.get("ball_detector")
        ball_tracker_name = parameters.get("ball_tracker")
        out_cls_map = parameters["detector_params"]["output_class_mapping"]
        ball_cls_ids = entity_class_ids(out_cls_map, "ball")

        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
                image_size = video_decoder._size
                # -------> instantiate detector(s) & tracker objects
                def build_detector(name, params):
                    detector = DETECTOR_MAP[name](
                        model_path=params["model_path"],
                        image_size=image_size,
                        detector_params=params,
                        device="cuda",
                    )
                    # SAHI-style sliced inference around any backend (detector/slicing.py)
                    slicing = SliceConfig.from_cfg(params.get("sahi"))
                    return detector if slicing is None else SlicedDetector(detector, slicing, params.get("batch_size", 1))

                self.detector = build_detector(parameters["detector"], parameters["detector_params"])
                # NOTE: the ball detector is another instance of a detector wrapper, with its own parameters
                self.ball_detector = None
                if _is_set(ball_detector_name):
                    self.ball_detector = build_detector(ball_detector_name, parameters["ball_detector_params"])
                if self.tracker:
                    self.tracker = TRACKER_MAP[parameters["tracker"]](
                        tracker_params=parameters["tracker_params"],
                        device="cuda",
                    )
                # -------> 1) detect + 3) track players, frame by frame: the trackers that embed boxes (Deep-EIoU,
                # GTA-Link) need the pixels, and no frame is kept after its iteration
                total_frames = len(video_decoder)
                last_reported = 0.0

                for frame_id, _frame in enumerate(video_decoder):
                    for detector in (self.detector, self.ball_detector):
                        if detector is not None:
                            detector.run_inference(detector.preprocess(_frame))
                    if self.tracker:
                        # every detector reports boxes in frame pixels (detector contract, tracker/README.md)
                        frame_shape = tuple(int(v) for v in self.detector.frame_shape)
                        # 2) route: ball candidates never reach the player tracker
                        player_dets, _ = split_detections(self.detector.state[-1:], ball_cls_ids)
                        self.tracker.process({
                            'detections': player_dets,
                            'frames': [_frame["frame"]],      # HWC uint8 RGB
                            'image_shape': frame_shape,
                            'det_shape': frame_shape,
                        })
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
                self.update_callbacks(callbacks, progress=0.9)

        # every detector reports boxes in frame pixels (detector contract, tracker/README.md)
        frame_h, frame_w = (int(v) for v in self.detector.frame_shape)
        detections = self.detector.state

        # -------> 2) route (as in the loop): ball candidates never reach the player tracker
        other_dets, ball_dets = split_detections(detections, ball_cls_ids)
        if self.ball_detector is not None:
            ball_out_cls_map = parameters["ball_detector_params"]["output_class_mapping"]
            if tuple(int(v) for v in self.ball_detector.frame_shape) != (frame_h, frame_w):
                raise RuntimeError(f"ball detector frame {self.ball_detector.frame_shape} != detector frame {(frame_h, frame_w)}")
            n_dropped = sum(map(len, ball_dets))
            _, ball_dets = split_detections(self.ball_detector.state, entity_class_ids(ball_out_cls_map, "ball"))
            logging.info(f"object_tracker: ball from '{ball_detector_name}' ({sum(map(len, ball_dets))} candidates); "
                         f"{n_dropped} ball-class detections of the player detector dropped.")

        tracklets = defaultdict(list)

        # -------> 3b) offline refinement (GTA-Link, interpolation) + 4) default team per track from its class votes
        player_tlwhs = None
        if self.tracker:
            self.tracker.finalize()
            trk_det_mapping = TrackClassMapper().map_tracks_to_detections(
                tracks=self.tracker.state,
                detections=other_dets,
                iou_thresh=0.3
            )
            player_tlwhs = [track['track_boxes'] for track in self.tracker.state]
            for track in self.tracker.state:
                frame_id = track['frame_id']
                frame_time = frame_time_ms(frame_id, fps)
                for track_id, track_score, track_tlwh in zip(
                    track['track_ids'],
                    track['track_scores'],
                    track['track_boxes'],
                ):
                    # NOTE: Mapping of class_id to team_id.
                    # Detectors have varying output heads, so we need some mapping dict from cls_id to real-world entity.
                    class_id = trk_det_mapping[frame_id][track_id]['class']
                    team_id = _class_entry(out_cls_map, class_id).get("default_team", TeamId.TEAM_LEFT)
                    tracklets[frame_time].append(
                        tracklet_row(track_id, team_id, track_tlwh, frame_w, frame_h, track_score)
                    )
        else:
            # -------> detection-only run: the non-ball detections are written untracked
            for frame_id, frame_dets in enumerate(other_dets):
                frame_time = frame_time_ms(frame_id, fps)
                for det in frame_dets:
                    team_id = _class_entry(out_cls_map, det["cls_id"]).get("default_team", TeamId.TEAM_LEFT)
                    tracklets[frame_time].append(
                        # detector xywh is (centre x, centre y, w, h)
                        tracklet_row(UNTRACKED_ID, team_id, center_to_tlwh(det["xywh"]), frame_w, frame_h, det["conf"])
                    )

        # -------> 5) ball
        ball_tracker = None
        if _is_set(ball_tracker_name):
            ball_tracker = BALL_TRACKER_MAP[ball_tracker_name](
                tracker_params=parameters.get("ball_tracker_params") or {},
                fps=fps,
            )
            if not ball_tracker.usable:
                logging.warning(f"object_tracker: ball tracking off at {fps} fps (min_fps {ball_tracker.min_fps:g}): "
                                f"the ball moves too far between frames; writing the ball candidates untracked.")
                ball_tracker = None
        if ball_tracker is not None:
            ball_state = ball_tracker.process({
                'detections': ball_dets,
                'players': player_tlwhs,     # kick hints at the players' feet (none in a ball-only run)
                'box_format': 'tlwh',
            })
            for frame_id, ball in enumerate(ball_state):
                if ball["ball_box"] is None:
                    continue
                # score: the detection confidence, 0 for interpolated boxes
                tracklets[frame_time_ms(frame_id, fps)].append(
                    tracklet_row(BALL_ID, TeamId.BALL, ball["ball_box"], frame_w, frame_h, ball["ball_score"])
                )
        else:
            for frame_id, frame_dets in enumerate(ball_dets):
                frame_time = frame_time_ms(frame_id, fps)
                for det in frame_dets:
                    tracklets[frame_time].append(
                        tracklet_row(BALL_ID, TeamId.BALL, center_to_tlwh(det["xywh"]), frame_w, frame_h, det["conf"])
                    )

        # -------> output: same entity scheme as after an edit in the bbox editor
        entity_meta = compute_bboxes_meta(tracklets)
        meta_dict = {
            # TODO: This is specific to team-based sports, need a generic solution at some point...!
            "team_ids": DEFAULT_TEAM_META,
            "player_ids": entity_meta["player_ids"],
            "ref_ids": entity_meta["ref_ids"],
            "ball_ids": entity_meta["ball_ids"],
            "video": dict(
                fps=fps,
                h=frame_h,
                w=frame_w
            )
        }
        logging.info(
            f"object_tracker: {len(entity_meta['player_ids'])} players, {len(entity_meta['ref_ids'])} referees, "
            f"{sum(len(rows) for rows in tracklets.values())} boxes in {len(detections)} frames."
        )

        with data_manager.create_data("BboxesData") as output_data:
            output_data.bboxes = json.dumps(tracklets)
            output_data.meta_data = json.dumps(meta_dict)
            self.update_callbacks(callbacks, progress=1.0)

        return {"tracklets": output_data}
