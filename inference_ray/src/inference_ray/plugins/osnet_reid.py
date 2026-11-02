import json
import logging
import time
from typing import Callable, Dict

from data import (
    Data, DataManager,
    VideoData,
    BboxesData,
    ReIDData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder
from .reid import GlobalIDManager, Gallery, ProtoGallery
from .tracker.tracklets import TeamId, frame_time_ms, video_meta


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

requires = {
    "video": VideoData,
    "tracklets": BboxesData,
}

provides = {
    "reids": ReIDData,
}

# the model when a request names none (the serializer always sets both)
DEFAULT_MODEL = {"model_name": "osnet_ain_x1_0", "checkpoint": "/models/reid/osnet_ain_ms_d_c.pth.tar"}


@AnalyserPluginManager.export("osnet_reid")
class OSNetReID(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.4",
    requires=requires,
    provides=provides
):
    """ Global identities for the player tracks (tracker/README.md):

    1. per decoded frame the player boxes of the tracklets (entity id 0, the ball and untracked detections, and the
       ball rows are left out);
    2. crops by ``roi_align`` (bilinear, ``crop_size_x`` x ``crop_size_y``), embedded by a torchreid model loaded
       strictly from the allowlisted checkpoint. Boxes below ``min_box_w`` x ``min_box_h`` px abstain: their
       embedding is zero, so they never match a prototype;
    3. ``gallery_mode: protos``: the prototype gallery with the global-id lifecycle (``GlobalIDManager``: active ->
       lost after ``active_ttl`` unseen frames -> retired after ``lost_ttl``; re-entry matches, spatial gate,
       ``keep_tracker_binding``), or ``tracks``: a plain gallery.

    Output: ``mapping = {frame_time_ms: {track_id: global_id}}`` (the frontend's ``mergeReid`` reads it), and per
    frame the arrays ``tracks`` (the player rows), ``reid_ids`` (int64) and ``features``.
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
        import numpy as np
        import torch
        from .tracker.appearance import ReIDEncoder, reid_input_size, roi_crops, roi_windows

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.cfg = cfg = parameters or {}

        model_name = cfg.get("model_name") or DEFAULT_MODEL["model_name"]
        checkpoint = cfg.get("checkpoint") or DEFAULT_MODEL["checkpoint"]
        crop_hw = (int(cfg.get("crop_size_y", 256)), int(cfg.get("crop_size_x", 128)))
        size = reid_input_size(model_name)
        if size and tuple(size) != crop_hw:
            raise ValueError(f"osnet_reid: {model_name} takes {size[1]}x{size[0]} crops "
                             f"(crop_size_x / _y are {crop_hw[1]}x{crop_hw[0]}).")
        offsets = tuple(float(cfg.get(k, 0.0)) for k in
                        ("crop_x1_offset", "crop_y1_offset", "crop_x2_offset", "crop_y2_offset"))
        # smaller boxes have too few pixels for the broadcast-trained models
        min_box_w, min_box_h = float(cfg.get("min_box_w", 16)), float(cfg.get("min_box_h", 32))

        self.gallery_mode = cfg.get("gallery_mode", "protos")
        # the serializer's key is match_thresh (it used to be read as match_threshold, so it never applied)
        match_threshold = float(cfg.get("match_thresh", cfg.get("match_threshold", 0.6)))
        max_missed = int(cfg.get("max_missed", 150))

        self.encoder = ReIDEncoder(checkpoint, self.device, model_name=model_name)
        self.global_id_manager = None
        self.tracker_binding = {}  # tracks mode: tracker id -> its last global id
        if self.gallery_mode == "tracks":
            self.gallery = Gallery(threshold=match_threshold, max_missed=max_missed)
        elif self.gallery_mode == "protos":
            self.gallery = ProtoGallery(
                match_threshold=match_threshold,
                update_threshold=float(cfg.get("update_threshold", 0.88)),
                max_missed=max_missed,
                ema_alpha=float(cfg.get("ema_alpha", 0.99)),
                cache_size=int(cfg.get("cache_size", 10)),
                margin=float(cfg.get("margin", 0.06)),
                prototype_weight=float(cfg.get("prototype_weight", 0.7)),
                cache_weight=float(cfg.get("cache_weight", 0.3)),
            )
            self.global_id_manager = GlobalIDManager(
                gallery=self.gallery,
                active_ttl=int(cfg.get("active_ttl", 30)),
                lost_ttl=int(cfg.get("lost_ttl", 300)),
                reentry_threshold=float(cfg.get("reentry_threshold", 0.55)),
                spatial_gate_px=float(cfg.get("spatial_gate_px", 150.0)),
                use_spatial_gate=bool(cfg.get("use_spatial_gate", True)),
                keep_tracker_binding=bool(cfg.get("keep_tracker_binding", True)),
            )
        else:
            raise ValueError(f"Unknown gallery_mode: {self.gallery_mode}")

        with inputs["tracklets"] as tracklets_data:
            # frame size the tracklet boxes are normalised by (object_tracker writes video.h / video.w)
            self.fps, frame_h, frame_w = video_meta(json.loads(tracklets_data.meta_data or "{}"))
            tracklets_by_time = json.loads(tracklets_data.bboxes)
        scale = np.array([frame_w, frame_h, frame_w, frame_h], dtype=np.float64)
        dim = self.encoder.feature_dim

        mapping = {}
        n_boxes = n_abstained = 0
        with inputs["video"] as video_input_data:
            with video_input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=self.fps,
                    extension=f".{video_input_data.ext}",
                    ref_id=video_input_data.id,
                )
                total_frames = len(video_decoder)
                last_reported = 0.0
                with data_manager.create_data("ReIDData") as reids:
                    for frame_id, _frame in enumerate(video_decoder):
                        frame_time = frame_time_ms(frame_id, self.fps)
                        # player rows: no ball, no untracked detections (entity 0)
                        rows = [r for r in tracklets_by_time.get(str(frame_time), [])
                                if int(r[0]) != 0 and int(r[1]) != TeamId.BALL]
                        if not rows:
                            mapping[frame_time] = {}
                            continue
                        img = _frame["frame"]  # HWC uint8 RGB
                        if img.shape[:2] != (frame_h, frame_w):
                            raise ValueError(f"osnet_reid: decoded frame {img.shape[:2]} != the tracklets' "
                                             f"frame {(frame_h, frame_w)}.")
                        tracklets_npy = np.asarray(rows, dtype=np.float64)
                        track_ids = tracklets_npy[:, 0].astype(np.int64).tolist()
                        boxes = (tracklets_npy[:, 5:9] * scale).astype(np.float32)   # tlwh px, float32 as tracker states

                        windows, valid = roi_windows(boxes, (frame_h, frame_w), offsets, min_box_w, min_box_h)
                        feats = np.zeros((len(rows), dim), dtype=np.float32)
                        if valid.any():
                            feats[valid] = self.encoder.embed_crops(roi_crops(img, windows[valid], crop_hw, self.device))
                        n_boxes += len(rows)
                        n_abstained += int((~valid).sum())

                        global_ids = self._assign(frame_id, track_ids, feats, boxes, valid)
                        reid_ids = np.array([-1 if g is None else int(g) for g in global_ids], dtype=np.int64)
                        mapping[frame_time] = dict(zip(track_ids, reid_ids.tolist()))
                        reids.add_array(str(frame_id), "tracks", tracklets_npy)
                        reids.add_array(str(frame_id), "reid_ids", reid_ids)
                        reids.add_array(str(frame_id), "features", feats)

                        now = time.time()
                        if total_frames and now - last_reported >= 1.0:
                            last_reported = now
                            self.update_callbacks(callbacks, progress=min((frame_id + 1) / total_frames, 1.0) * 0.98)

                    n_ids = len({g for m in mapping.values() for g in m.values()})
                    n_tracks = len({t for m in mapping.values() for t in m})
                    logging.info(f"osnet_reid: {n_tracks} tracker ids -> {n_ids} global ids ({self.gallery_mode}, "
                                 f"{model_name}); {n_abstained} of {n_boxes} boxes below {min_box_w:g}x{min_box_h:g} px.")
                    reids.mapping = mapping
                    self.update_callbacks(callbacks, progress=1.0)

        return {"reids": reids}

    def _assign(self, frame_id: int, track_ids, feats, boxes, valid):
        """ Global id per box. In ``tracks`` mode a box without an embedding continues its tracker id's last global
        id; its zero embedding would register a new id in every frame. """
        if self.gallery_mode == "protos":
            global_ids, _, _ = self.global_id_manager.update(
                frame_id=frame_id,
                track_ids=track_ids,
                feats=feats,
                boxes_xywh=boxes,
            )
            return global_ids
        global_ids = [None] * len(track_ids)
        idx = [i for i in range(len(track_ids)) if valid[i]]
        if idx:
            matched_ids, _ = self.gallery.match(feats[idx], frame_id)
            for i, pid in zip(idx, matched_ids):
                global_ids[i] = pid if pid is not None else self.gallery.register(feats[i], frame_id)
        for i, tid in enumerate(track_ids):
            if global_ids[i] is None:
                global_ids[i] = self.tracker_binding.get(tid)
                if global_ids[i] is None:
                    global_ids[i] = self.gallery.next_id
                    self.gallery.next_id += 1
            self.tracker_binding[tid] = global_ids[i]
        self.gallery.prune(frame_id)
        return global_ids
