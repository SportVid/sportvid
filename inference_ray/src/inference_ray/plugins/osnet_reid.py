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

        self.cfg = parameters or {}

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

        self.crop_size = self.cfg.get("crop_size", [128, 256])
        self.crop_x1_offset = self.cfg.get("crop_x1_offset", 0)
        self.crop_y1_offset = self.cfg.get("crop_y1_offset", 0)
        self.crop_x2_offset = self.cfg.get("crop_x2_offset", 0)
        self.crop_y2_offset = self.cfg.get("crop_y2_offset", 0)

        self.feat_extr = FeatureExtractor(
            model_name=model_name,
            model_path=model_path,
            device=self.device,
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
                    # main processing loop
                    with data_manager.create_data("ReIDData") as reids:
                        mapping = {}
                        for frame_id, _frame in enumerate(video_decoder):
                            frame_time = round((frame_id/self.fps)*1000.)
                            _tracklets = tracklets_data.get(f'{frame_time}', [])
                            per_frame_reids = self.process(
                                inputs={
                                    "tracklets": _tracklets,
                                    "image": _frame["frame"],
                                }
                            )
                            logging.error(per_frame_reids)
                            
                            for name, arr in per_frame_reids.items():
                                if type(arr) is np.ndarray:
                                    reids.add_array(str(frame_id), name, arr)
                            mapping[frame_time] = per_frame_reids['mapping']
                        reids.mapping = mapping
                        self.update_callbacks(callbacks, progress=1.0) 

                    return { "reids" : reids }

    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Encode tracklet crops using the feature extractor. """
        # NOTE: Expects single tracklet/image pair as inputs.
        tracklets = inputs.get('tracklets', []) # [track_id, *, *, *, *, x_norm, y_norm, w_norm, h_norm, *]
                                                # previous layout:  'track_ids':[], 'track_boxes':[N,4] xywh}
        img = inputs.get('image')               # full frame numpy BGR (H,W,C)
        if not tracklets: return inputs
        tracklets_npy = np.array(tracklets)
        tracklets_npy = np.squeeze(tracklets_npy, axis=1)
        
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
            tracklets = frame_data['tracks']
            feats = frame_data['features']
            crops = frame_data['crops']
            
            frame_id = tracks["frame_id"]
            track_ids = list(tracks.get("track_ids", []))
            track_boxes = list(tracks.get("track_boxes", []))

            if feats is None or len(feats) == 0 or len(track_ids) == 0:
                tracks.update({
                    "reid_ids": [],
                    "reid_scores": [],
                    "reid_status": [],
                    "crops": crops,
                    "features": feats,
                })
                continue

            if self.gallery_mode == "protos":
                global_ids, reid_scores, reid_status = self.global_id_manager.update(
                    frame_id=frame_id,
                    track_ids=track_ids,
                    feats=feats,
                    boxes_xywh=track_boxes,
                )
            else:
                matched_ids, matched_scores = self.gallery.match(feats, frame_id)
                global_ids = list(matched_ids)
                reid_scores = list(matched_scores)
                reid_status = []

                for i, pid in enumerate(global_ids):
                    if pid is None:
                        pid = self.gallery.register(feats[i], frame_id)
                        global_ids[i] = pid
                        reid_scores[i] = None
                        reid_status.append("new")
                    else:
                        reid_status.append("matched")

                self.gallery.prune(frame_id)

            tracks.update({
                "reid_ids": global_ids,
                "reid_scores": reid_scores,
                "reid_status": reid_status,
                "crops": crops,
                "features": feats,
            })

            logging.error(
                f"Frame {frame_id}: tracks={len(track_ids)}, "
                f"unique_global={len({gid for gid in global_ids if gid is not None})}, "
                f"new={sum(s == 'new' for s in reid_status)}, "
                f"continued={sum(s == 'continued' for s in reid_status)}, "
                f"matched_active={sum(s == 'matched_active' for s in reid_status)}, "
                f"reentry={sum(s == 'reid_reentry' for s in reid_status)}"
            )
            logging.error(f"Old tracker IDs: {track_ids}")
            logging.error(f"Global IDs: {global_ids}")
            logging.error(f"Scores: {reid_scores}")
            logging.error(f"Status: {reid_status}")

        return tracks