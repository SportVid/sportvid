import logging
import torch
import json
import numpy as np
import cv2
from typing import Any, Callable, Dict, List, Tuple, Optional
from PIL import Image
from data import (
    Data, DataManager,
    VideoData,
    BboxesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder, VideoBatcher
from .reid import GlobalIDManager, Gallery, ProtoGallery


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


def l2_normalize(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        return x / (np.linalg.norm(x) + eps)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + eps)


def _crop_tracks(
    img: np.ndarray,
    track_boxes: np.ndarray,
    track_ids: List[int],
    crop_size: List[int] = [128, 256],
    x1_offset: float = 0.0,
    y1_offset: float = 0.0,
    x2_offset: float = 0.0,
    y2_offset: float = 0.0
) -> List[Image.Image]:
    """Crops track boxes and converts them to PIL RGB (H,W,C)."""

    def torch_to_npy(img):
        if isinstance(img, torch.Tensor):
            img_npy = img.permute(1, 2, 0).cpu().numpy()
            if img_npy.max() <= 1.0:
                img_npy = (img_npy * 255).astype(np.uint8)
            return img_npy
        return img

    img_npy = torch_to_npy(img)
    logging.debug(f"img shape: {img_npy.shape}")

    h_img, w_img = img_npy.shape[:2]
    crops = []

    for i, (tid, box) in enumerate(zip(track_ids, track_boxes)):
        x1, y1, w, h = box.astype(float)

        if w <= 0 or h <= 0:
            logging.debug(f"Raw box: x1={x1}, y1={y1}, w={w}, h={h}")
            logging.debug(f"Skipping invalid box {box}")
            continue

        x1 += w * x1_offset
        y1 += h * y1_offset
        x2 = x1 + w * (1.0 + x2_offset)
        y2 = y1 + h * (1.0 + y2_offset)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_img, x2), min(h_img, y2)

        if x2 <= x1 or y2 <= y1:
            logging.debug(f"Skipping degenerate clipped box: {(x1, y1, x2, y2)}")
            continue

        crop_bgr = img_npy[int(y1):int(y2), int(x1):int(x2)]
        if crop_bgr.size == 0:
            continue

        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        crop_pil = Image.fromarray(crop_rgb)
        crop_pil = crop_pil.resize(crop_size, Image.Resampling.LANCZOS)
        crops.append(crop_pil)

    return crops


@AnalyserPluginManager.export("osnet_reid")
class OSNetReID(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.2",
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
        from torchreid.utils.feature_extractor import FeatureExtractor
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.cfg = parameters or {}

        self.model_name = self.cfg.get("model_name", "osnet_x1_0")
        self.checkpoint = self.cfg.get("checkpoint", "/models/reid/osnet_x1_0_ms_d_c.pth.tar")

        self.gallery_mode = self.cfg.get("gallery_mode", "tracks")
        self.match_threshold = self.cfg.get("match_threshold", 0.6)
        self.update_threshold = self.cfg.get("update_threshold", 0.82)
        self.ema_alpha = self.cfg.get("ema_alpha", 0.95)
        self.cache_size = self.cfg.get("cache_size", 20)
        self.margin = self.cfg.get("margin", 0.03)
        self.prototype_weight = self.cfg.get("prototype_weight", 0.7)
        self.cache_weight = self.cfg.get("cache_weight", 0.3)

        self.max_missed = self.cfg.get("max_missed", 30)
        self.reid_cls = self.cfg.get("reid_cls", [])

        self.crop_size_x = self.cfg.get("crop_size_x", 128)
        self.crop_size_y = self.cfg.get("crop_size_y", 256)
        self.crop_x1_offset = self.cfg.get("crop_x1_offset", 0)
        self.crop_y1_offset = self.cfg.get("crop_y1_offset", 0)
        self.crop_x2_offset = self.cfg.get("crop_x2_offset", 0)
        self.crop_y2_offset = self.cfg.get("crop_y2_offset", 0)

        self.feat_extr = FeatureExtractor(
            model_name=self.model_name,
            model_path=self.checkpoint,
            device=self.device
        )

        self.gallery = None
        self.global_id_manager = None

        if self.gallery_mode == "tracks":
            self.gallery = Gallery(
                threshold=self.match_threshold,
                max_missed=self.max_missed,
            )

        elif self.gallery_mode == "protos":
            self.gallery = ProtoGallery(
                match_threshold=self.match_threshold,
                update_threshold=self.update_threshold,
                max_missed=self.max_missed,
                ema_alpha=self.ema_alpha,
                cache_size=self.cache_size,
                margin=self.margin,
                prototype_weight=self.prototype_weight,
                cache_weight=self.cache_weight,
            )

            self.global_id_manager = GlobalIDManager(
                gallery=self.gallery,
                active_ttl=30,
                lost_ttl=300,
                reentry_threshold=0.68,
                spatial_gate_px=150.0,
                use_spatial_gate=True,
            )
        else:
            raise ValueError(f"Unknown gallery_mode: {self.gallery_mode}")

        with inputs["video"] as video_input_data, inputs["tracklets"] as tracklets_data:
            with video_input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    extension=f".{video_input_data.ext}",
                    ref_id=video_input_data.id,
                )
    
        self.frame_id = 0
        with inputs["tracklets"] as tracklets_data:
            # data unpacking
            tracklets_meta = json.loads(tracklets_data.meta_data)
            tracklets_meta = tracklets_meta.get('video', {})
            self.fps = tracklets_meta.get('fps', 30)
            self.detector_h = tracklets_meta.get('detector_h', 1080)
            self.detector_w = tracklets_meta.get('detector_w', 1920)
            
            tracklets_data = json.loads(tracklets_data.bboxes)
            # video decoding
            with inputs["video"] as video_input_data: 
                with video_input_data.open_video() as f_video:
                    video_decoder = VideoDecoder(
                        f_video,
                        fps=self.fps,
                        extension=f".{video_input_data.ext}",
                        ref_id=video_input_data.id,
                    )
                    total_frames = (
                        len(video_decoder) if hasattr(video_decoder, "__len__") else None
                    )
                    # main processing loop
                    with data_manager.create_data("ReIDData") as reids:
                        mapping = {}
                        for frame_id, _frame in enumerate(video_decoder):
                            self.frame_id = frame_id
                            frame_time = round((frame_id/self.fps)*1000.)
                            _tracklets = tracklets_data.get(f'{frame_time}', [])
                            per_frame_reids = self.process(
                                inputs={
                                    "tracklets": _tracklets,
                                    "image": _frame["frame"],
                                }
                            )
                            # logging.error(per_frame_reids)
                            for name, arr in per_frame_reids.items():
                                if type(arr) is np.ndarray:
                                    reids.add_array(str(frame_id), name, arr)
                            mapping[frame_time] = per_frame_reids['mapping']
                            if total_frames:
                                self.update_callbacks(
                                    callbacks,
                                    progress=min((frame_id + 1) / total_frames, 1.0) * 0.98,
                                )
                        reids.mapping = mapping
                        self.update_callbacks(callbacks, progress=1.0)

                    return { "reids" : reids }

    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Encode tracklet crops using the feature extractor. """
        # NOTE: Expects single tracklet/image pair as inputs.
        tracklets = inputs.get('tracklets', []) # [[track_id, team_id, game_section, x_center, y_bottom,
                                                 #   x_norm, y_norm, w_norm, h_norm, score], ...] (N,10)
        img = inputs.get('image')               # full frame numpy BGR (H,W,C)
        if not tracklets:
            # Empty-frame shape must match the normal-path return below, since process()
            # unconditionally reads preproc_inputs['inputs'] -- its own len(tracks)==0 branch
            # (further down) is what actually handles the "no detections this frame" case.
            return {'inputs': [{
                'tracks': np.empty((0, 10), dtype=np.float32),
                'features': np.empty((0, 512), dtype=np.float32),
                'crops': [],
            }]}
        tracklets_npy = np.array(tracklets)

        # undo normalization of coords using in-place mul
        tracklets_npy[:,5] *= self.detector_w  # x_n
        tracklets_npy[:,6] *= self.detector_h  # y_n
        tracklets_npy[:,7] *= self.detector_w  # w_n
        tracklets_npy[:,8] *= self.detector_h  # h_n
        
        track_ids = tracklets_npy[:,0]    # [N,]
        track_xywh = tracklets_npy[:,5:9] # [N,4] [x1,y1,w,h]
        
        # TODO: revert coordinate normalization of track_boxes using detector W/H
        crops = _crop_tracks( # crops track boxes
            img, 
            track_xywh, 
            track_ids,
            (self.crop_size_x, self.crop_size_y),
            self.crop_x1_offset,
            self.crop_y1_offset,
            self.crop_x2_offset,
            self.crop_y2_offset
        ) 
        if not crops: crops = []
        
        crop_arrays_rgb = []
        # NOTE: seems very inefficient, however feature extractor requires a list of PIL numpy arrays..
        for crop_pil in crops:
            crop_rgb_npy = np.array(crop_pil)  # PIL -> RGB numpy HWC uint8
            crop_arrays_rgb.append(crop_rgb_npy)
            
        if len(crop_arrays_rgb) > 0:
            features = self.feat_extr(crop_arrays_rgb).cpu().numpy() # extract features: PIL list of image bboxes -> [N,512] normalized
        else:
            features = np.empty((0,512), dtype=np.float32)
        
        # NOTE: returning per-frame processed input.
        return { 
            'inputs' : [{
                'tracks': tracklets_npy,    # [N,10]
                'features': features,       # [N,512] 
                'crops': crop_arrays_rgb    # [N,H,W,C]
            }]
        }

    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """
            1) Extract ReID features
            2) Associate detections to identities
            3) In ProtoGallery mode, use global-ID lifecycle management
        """
        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs['inputs']
        
        tracks = {}
        for frame_data in per_frame_data:
            tracklets = frame_data['tracks']    # expected: np.ndarray (N, 10)
            feats = frame_data['features']      # expected: np.ndarray (N, F_DIM) or None
            crops = frame_data['crops']
            
            # frame_id = tracks["frame_id"]
            track_ids = list(tracks.get("track_ids", []))
            track_boxes = list(tracks.get("track_boxes", []))

            if tracklets is None or len(tracklets) == 0:
                tracks.update({
                    "tracks": tracklets,
                    "reid_ids": np.array([], dtype=np.int_),
                    "mapping": {},
                    "crops": crops,
                    "features": feats,
                })
                self.frame_id += 1
                continue
            
            old_ids = tracklets[:, 0].astype(np.int_)
            track_ids = old_ids.tolist()

            # adjust this slice if your old tracklet layout stores boxes elsewhere
            track_boxes = tracklets[:, 5:9] if tracklets.shape[1] >= 5 else None

            if feats is None or len(feats) == 0 or len(track_ids) == 0:
                updated_ids = np.array([], dtype=np.int_)
                mapping = {}
                tracks.update({
                    "tracks": tracklets,
                    "reid_ids": updated_ids,
                    "mapping": mapping,
                    "crops": crops,
                    "features": feats,
                })
                self.frame_id += 1
                continue

            if self.gallery_mode == "protos":
                global_ids, reid_scores, reid_status = self.global_id_manager.update(
                    frame_id=self.frame_id,
                    track_ids=track_ids,
                    feats=feats,
                    boxes_xywh=track_boxes,
                )
                updated_ids = np.array(global_ids, dtype=object)
            else:
                matched_ids, matched_scores = self.gallery.match(feats, self.frame_id)

                global_ids = list(matched_ids)
                reid_scores = list(matched_scores)
                reid_status = []

                for i, pid in enumerate(global_ids):
                    if pid is None:
                        pid = self.gallery.register(feats[i], self.frame_id)
                        global_ids[i] = pid
                        reid_scores[i] = None
                        reid_status.append("new")
                    else:
                        reid_status.append("matched")

                self.gallery.prune(self.frame_id)
                updated_ids = np.array(global_ids, dtype=object)

            mapping = dict(zip(old_ids.tolist(), updated_ids.tolist()))

            tracks.update({
                "tracks": tracklets,
                "reid_ids": updated_ids,
                "mapping": mapping,
                "crops": crops,
                "features": feats,
            })

            logging.error(
                f"Frame {self.frame_id}: tracks={len(track_ids)}, "
                f"unique_global={len({gid for gid in updated_ids.tolist() if gid is not None})}, "
                f"mapping={mapping}"
            )
            logging.error(f"Old tracker IDs: {old_ids.tolist()}")
            logging.error(f"Global IDs: {updated_ids.tolist()}")

            if self.gallery_mode == "protos":
                logging.error(f"Status: {reid_status}")
                logging.error(f"Scores: {reid_scores}")
                tracks.update({
                    "reid_status": reid_status,
                    "reid_scores": reid_scores
                })

            self.frame_id += 1

        return tracks