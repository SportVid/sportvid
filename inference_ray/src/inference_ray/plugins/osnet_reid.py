import logging
from collections import deque
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
        from torchreid.reid.utils.feature_extractor import FeatureExtractor

        self.cfg = parameters or {}

        self.reid_threshold = self.cfg.get("reid_threshold", 0.72)
        self.reid_update_threshold = self.cfg.get("reid_update_threshold", 0.82)
        self.reid_margin = self.cfg.get("reid_margin", 0.03)
        self.max_missed = self.cfg.get("max_missed", 30)
        self.ema_alpha = self.cfg.get("ema_alpha", 0.95)
        self.cache_size = self.cfg.get("cache_size", 20)
        self.proto_weight = self.cfg.get("proto_weight", 0.7)
        self.cache_weight = self.cfg.get("cache_weight", 0.3)

        self.crop_size_x = self.cfg.get("crop_size_x", 128)
        self.crop_size_y = self.cfg.get("crop_size_y", 256)
        self.crop_x1_offset = self.cfg.get("crop_x1_offset", 0.0)
        self.crop_y1_offset = self.cfg.get("crop_y1_offset", 0.0)
        self.crop_x2_offset = self.cfg.get("crop_x2_offset", 0.0)
        self.crop_y2_offset = self.cfg.get("crop_y2_offset", 0.0)

        self.feat_extr = FeatureExtractor(
            model_name=self.cfg.get("model_name"),
            model_path=self.cfg.get("model_path", None),
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        
        self.gallery = Gallery(
            match_threshold=self.cfg.reid_threshold,
            update_threshold=self.reid_update_threshold,
            max_missed=self.max_missed,
            ema_alpha=self.ema_alpha,
            cache_size=self.cache_size,
            margin=self.reid_margin,
            prototype_weight=self.proto_weight,
            cache_weight=self.cache_weight,
        )

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
                            per_frame_reids = self.process(inputs={
                                "tracklets": _tracklets,
                                "image": _frame["frame"],
                            })
                            
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
        features = self.feat_extr(crop_arrays_rgb).cpu().numpy() # extract features: PIL list of image bboxes -> [N,512] normalized
        features = l2_normalize(features)
        crop_arrays_rgb = np.array(crop_arrays_rgb)
        
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
        1) Use feature extraction model
        2) Update embedding gallery
        3) Store updated ID for tracklets
        """
        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs['inputs']
        
        tracks = {}
        for frame_data in per_frame_data:
            tracklets = frame_data['tracks']
            feats = frame_data['features']
            crops = frame_data['crops']
            # update gallery & assign/update track IDs
            updated_ids = []
            tids = self.gallery.match(feats, frame_id=self.frame_id)
            if tids is None: 
                for feat in feats:  # register single track into the gallery
                    tid = self.gallery.register(feat, frame_id=self.frame_id)
                    updated_ids.append(tid)
            else:
                updated_ids = tids
            updated_ids = np.array(updated_ids)
            
            self.frame_id += 1
            self.gallery.prune(self.frame_id)
            
            old_ids = tracklets[:, 0]
            old_ids = old_ids.astype(dtype=np.int_)
            mapping = dict(zip(old_ids.tolist(), updated_ids.tolist()))
            
            # logging.error(f'{type(tracklets)},{type(updated_ids)},{type(crops)},{type(feats)}')
            # logging.error(f'{tracklets.shape},{updated_ids.shape},{crops.shape},{feats.shape}')
            
            tracks.update({ "tracks" : tracklets})      # (N,10)
            tracks.update({ "reid_ids" : updated_ids})  # (N,)
            tracks.update({ "mapping": mapping})        # { 'old_id' : 'new_id' }
            tracks.update({ "crops": crops})            # (N,H,W,C)
            tracks.update({ "features": feats})         # (N,F_DIM)
             
            logging.error(f'Frame {self.frame_id}: {len(crops)} crops -> {len(set(updated_ids))} ReID IDs. Mapping: {mapping}')
        
        return tracks
    
class Gallery:
    """ Online ReID gallery with:
        - L2-normalized features.
        - One EMA prototype per identity.
        - One recent-feature cache per identity.
        - Conservative update policy with match/update thresholds.
        - Ambiguity margin on best vs second-best score.
    """
    def __init__(
        self,
        match_threshold: float = 0.72,
        update_threshold: float = 0.82,
        max_missed: int = 100,
        ema_alpha: float = 0.95,
        cache_size: int = 20,
        margin: float = 0.03,
        prototype_weight: float = 0.7,
        cache_weight: float = 0.3,
    ):
        self.match_threshold = match_threshold # rejects low-score matches
        self.update_threshold = update_threshold
        self.max_missed = max_missed
        self.ema_alpha = ema_alpha
        self.cache_size = cache_size
        self.margin = margin # rejects ambiguous matches when best and second-best are too close
        self.prototype_weight = prototype_weight
        self.cache_weight = cache_weight
        
        self.next_id = 1
        # self.features = {}       # pid -> list[features] (append history)
        self.prototype: Dict[int, np.ndarray] = {}
        self.cache: Dict[int, deque] = {}
        self.last_seen: Dict[int, int] = {}      # pid -> frame_idx

    def _similarity_to_pid(self, feat: np.ndarray, pid: int) -> Tuple[float, float, float]:
        proto = self.prototype[pid]
        proto_sim = float(np.dot(feat, proto))

        cached = self.cache[pid]
        if len(cached) > 0:
            cached_feats = np.stack(cached, axis=0)
            cache_sim = float(np.max(cached_feats @ feat))
        else:
            cache_sim = proto_sim

        score = self.prototype_weight * proto_sim + self.cache_weight * cache_sim
        return score, proto_sim, cache_sim

    def _update_identity(self, pid: int, feat: np.ndarray, frame_id: int):
        feat = l2_normalize(feat)

        new_proto = self.ema_alpha * self.prototype[pid] + (1.0 - self.ema_alpha) * feat
        self.prototype[pid] = l2_normalize(new_proto)
        self.cache[pid].append(feat)
        self.last_seen[pid] = frame_id

    def match_one(self, feat: np.ndarray, frame_id: int) -> Tuple[Optional[int], Optional[float]]:
        feat = l2_normalize(feat)

        if not self.prototype:
            return None, None

        pids = list(self.prototype.keys())
        scores = []

        for pid in pids:
            score, proto_sim, cache_sim = self._similarity_to_pid(feat, pid)
            scores.append(score)

        scores = np.asarray(scores, dtype=np.float32)
        order = np.argsort(-scores)
        best_idx = int(order[0])
        best_score = float(scores[best_idx])

        second_score = -1.0
        if len(order) > 1:
            second_score = float(scores[int(order[1])])

        if best_score < self.match_threshold:
            return None, best_score

        if (best_score - second_score) < self.margin:
            return None, best_score

        pid = pids[best_idx]

        if best_score >= self.update_threshold:
            self._update_identity(pid, feat, frame_id)

        return pid, best_score

    def match_batch(self, feats: np.ndarray, frame_id: int) -> Tuple[List[Optional[int]], List[Optional[float]]]:
        matched_pids: List[Optional[int]] = []
        matched_scores: List[Optional[float]] = []

        if feats is None or len(feats) == 0:
            return matched_pids, matched_scores

        feats = l2_normalize(feats)

        for feat in feats:
            pid, score = self.match_one(feat, frame_id)
            matched_pids.append(pid)
            matched_scores.append(score)

        return matched_pids, matched_scores

    def register(self, feat: np.ndarray, frame_id: int) -> int:
        feat = l2_normalize(feat)

        pid = self.next_id
        self.next_id += 1

        self.prototype[pid] = feat
        self.cache[pid] = deque([feat], maxlen=self.cache_size)
        self.last_seen[pid] = frame_id
        return pid

    def prune(self, frame_id: int):
        stale = [
            pid for pid, last in self.last_seen.items()
            if frame_id - last > self.max_missed
        ]
        for pid in stale:
            del self.prototype[pid]
            del self.cache[pid]
            del self.last_seen[pid]

    # NOTE: old gallery code.
    # ------------------------
    # def match(self, feats: np.ndarray, frame_id: int) -> Optional[int]:
    #     """ Given some feature vector, match it to the mean gallery features & return matched_id or None. """
    #     if not self.features: return None # (N,D)
    #     # compute cosine similarity between feat and the mean feature of each id
    #     gallery_means = np.array([np.mean(feats_, axis=0) for feats_ in self.features.values()])
    #     if len(gallery_means.shape) == 3: gallery_means = np.squeeze(gallery_means, axis=0)
    #     sims = cosine_similarity(feats, gallery_means) # (N, K)
        
    #     best_indices = np.argmax(sims, axis=1)  # (N,)
    #     best_sims = sims[np.arange(len(feats)), best_indices]
        
    #     matched_pids = []
    #     gallery_pids = list(self.features.keys())
        
    #     for i, (best_idx, best_sim) in enumerate(zip(best_indices, best_sims)):
    #         if best_sim >= self.threshold:
    #             pid = gallery_pids[best_idx]
    #             self.features[pid].append(feats[i])  # add new feature to the gallery
    #             self.last_seen[pid] = frame_id
    #             matched_pids.append(pid)
    #         else:
    #             matched_pids.append(None)
        
    #     return matched_pids
        
    # def register(self, feat: np.ndarray, frame_id: int) -> int:
    #     """ Register new track ID. """
    #     pid = self.next_id
    #     self.next_id += 1
    #     self.features[pid] = [feat]
    #     self.last_seen[pid] = frame_id
    #     return pid

    # def prune(self, frame_id: int):
    #     """ Removes stale tracks that have not been seen for more than max_missed frames. """
    #     stale = [pid for pid, last in self.last_seen.items()
    #                  if frame_id - last > self.max_missed]
    #     for pid in stale:
    #         del self.features[pid]
    #         del self.last_seen[pid]