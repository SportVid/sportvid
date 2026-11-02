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

# entity id of detections written without tracking (ball candidates, detection-only runs)
UNTRACKED_ID = 0


def _class_entry(output_class_mapping: Mapping[Any, Mapping[str, Any]], cls_id) -> Mapping[str, Any]:
    """ ``output_class_mapping`` entry of a class id; keys are str once the parameters went through JSON. """
    entry = output_class_mapping.get(str(cls_id))
    if entry is None:
        entry = output_class_mapping.get(cls_id, {})
    return entry or {}


@AnalyserPluginManager.export("object_tracker")
class ObjectTracker(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.2",
    requires=requires,
    provides=provides
):
    """ Detector -> player tracker -> tracklets, in stages (see tracker/README.md):

    1. detection over the decoded video;
    2. routing: with a tracker, the classes ``output_class_mapping`` names ``entity_type: ball`` are split off
       and never reach the player tracker;
    3. player tracking (``Tracker.process``), then ``Tracker.finalize`` once over the whole clip;
    4. per-track class votes (``TrackClassMapper``) give each track its default team;
    5. output: player tracks, plus the untracked detections (the split-off ball candidates, or every detection
       when no tracker is set) with entity id 0.
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
        out_cls_map = parameters["detector_params"]["output_class_mapping"]

        with inputs["video"] as input_data:
            with input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )
                image_size = video_decoder._size
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
                # -------> 1) detect
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
                self.update_callbacks(callbacks, progress=0.9)

        # every detector reports boxes in frame pixels (detector contract, tracker/README.md)
        frame_h, frame_w = (int(v) for v in self.detector.frame_shape)
        detections = self.detector.state

        # -------> 2) route: ball candidates never reach the player tracker
        if self.tracker:
            ball_cls_ids = entity_class_ids(out_cls_map, "ball")
            player_dets, untracked_dets = split_detections(detections, ball_cls_ids)
        else:
            player_dets, untracked_dets = None, detections

        tracklets = defaultdict(list)

        # -------> 3) track players + 4) default team per track from its class votes
        if self.tracker:
            self.tracker.process({
                'detections': player_dets,
                'image_shape': (frame_h, frame_w),
                'det_shape': (frame_h, frame_w),
            })  # TODO: check performance for 90m+ video footage.
            self.tracker.finalize()
            trk_det_mapping = TrackClassMapper().map_tracks_to_detections(
                tracks=self.tracker.state,
                detections=player_dets,
                iou_thresh=0.3
            )
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

        # -------> 5) untracked detections: ball candidates, or everything in a detection-only run
        # TODO: replaced by the Kalman ball tracker in the next step (tracker/README.md).
        for frame_id, frame_dets in enumerate(untracked_dets):
            frame_time = frame_time_ms(frame_id, fps)
            for det in frame_dets:
                team_id = _class_entry(out_cls_map, det["cls_id"]).get("default_team", TeamId.TEAM_LEFT)
                tracklets[frame_time].append(
                    # detector xywh is (centre x, centre y, w, h)
                    tracklet_row(UNTRACKED_ID, team_id, center_to_tlwh(det["xywh"]), frame_w, frame_h, det["conf"])
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
