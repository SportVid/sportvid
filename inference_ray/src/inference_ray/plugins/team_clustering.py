import logging
import time
import torch
import numpy as np
import cv2
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple, Optional
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData,
    ReIDData,
    TeamsData
)
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
try:
    from sklearn.cluster import HDBSCAN
except Exception:
    HDBSCAN = None
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder, VideoBatcher
from .object_tracker import TeamId
from .osnet_reid import _crop_tracks


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

requires = {
    "video": VideoData,
    # "tracklets": BboxesData,
    # "reids": ReIDData
}

provides = {
    "teams": TeamsData
}


@AnalyserPluginManager.export("team_clustering")
class TeamClustering(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.1",
    requires=requires,
    provides=provides
):
    """ Team clustering via kMeans/HDBSCAN.
        - Build per-detection jersey-color features from player crops.
        - Aggregate features at track level for robustness.
        - Cluster track-level descriptors into team IDs.
        - Propagate team IDs back to all detections of the same track.

    Supported modes:
        - KMEANS: recommended for player-only, two-team soccer assignment.
        - HDBSCAN: optional for noisier/open-set clustering.
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
        self.cfg = parameters
        
        self.clustering_method = str(self.cfg.get("clustering_method", "KMEANS")).upper()

        self.crop_size = self.cfg.get("crop_size", [128, 256])  # (H, W)
        self.crop_x1_offset = self.cfg.get("crop_x1_offset", 0)
        self.crop_y1_offset = self.cfg.get("crop_y1_offset", 0)
        self.crop_x2_offset = self.cfg.get("crop_x2_offset", 0)
        self.crop_y2_offset = self.cfg.get("crop_y2_offset", 0)

        self.hsv_only = self.cfg.get("hsv_only", True)
        self.two_channel = self.cfg.get("two_channel", True)
        self.K = int(self.cfg.get("K", 2))

        self.min_cluster_size = int(self.cfg.get("min_cluster_size", 4))
        self.cluster_selection_epsilon = float(self.cfg.get("cluster_selection_epsilon", 0.5))
        self.use_pca = bool(self.cfg.get("use_pca", False))
        self.pca_components = int(self.cfg.get("pca_components", 16))
        self.metric = self.cfg.get("metric", "euclidean")

        self.hist_h_bins = int(self.cfg.get("hist_h_bins", 16))
        self.hist_s_bins = int(self.cfg.get("hist_s_bins", 4))
        self.hist_v_bins = int(self.cfg.get("hist_v_bins", 4))

        self.min_pixels = int(self.cfg.get("min_pixels", 40))
        self.min_crop_w = int(self.cfg.get("min_crop_w", 12))
        self.min_crop_h = int(self.cfg.get("min_crop_h", 24))
        self.min_samples_per_track = int(self.cfg.get("min_samples_per_track", 2))
        self.max_samples_per_track = int(self.cfg.get("max_samples_per_track", 20))

        self.use_illumination_norm = bool(self.cfg.get("use_illumination_norm", True))
        self.use_green_mask = bool(self.cfg.get("use_green_mask", True))
        self.use_gray_mask = bool(self.cfg.get("use_gray_mask", True))
        self.use_torso_crop = bool(self.cfg.get("use_torso_crop", True))
        self.use_central_band = bool(self.cfg.get("use_central_band", True))

        self.reid_weight = float(self.cfg.get("reid_weight", 0.10))
        self.color_weight = float(self.cfg.get("color_weight", 1.0))

        self.random_state = int(self.cfg.get("random_state", 42))
        self.n_init = int(self.cfg.get("n_init", 20))

        self.state = []
        self.frame_id = 0
        self.global_centers = None
        self.track_team_map = {}
        self.team_centroids = None
        
        if inputs["reids"]: # crops are there, allows the use of HDBSCAN.
            with inputs["reids"] as reids_data:
                reids_ = reids_.frames
                logging.error(reids_)
                self.reids = True
        else: # TODO: implement this as an alternative if not ReID data is provided! crop
            raise NotImplementedError('Please run this plugin with a valid ReID output.')

    
    @torch.no_grad()
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Encode tracklet crops using the feature extractor. """
        tracks = inputs.get('tracks', []) # {'track_ids':[], 'track_boxes':[N,4] xywh}
        imgs = inputs.get('images', []) # full frame numpy BGR
        
        if not tracks: return {"inputs": []}
        
        # check if tracks contains crops, if not create crops from tracklets here
        proc = []
        for i, (track, img) in enumerate(zip(tracks, imgs['frame'])):
            
            track_ids = track.get("track_ids", [])
            track_boxes = track.get("track_boxes", []) # [N,4] [x1,y1,w,h]
            features = track.get("features", [])
            crops = track.get("crops", [])
            
            if crops == []:
                crops = _crop_tracks(
                    img, 
                    track_boxes, 
                    track_ids,
                    self.crop_size,
                    self.crop_x1_offset,
                    self.crop_y1_offset,
                    self.crop_x2_offset,
                    self.crop_y2_offset
                )
                if not crops: crops = []
                track["crops"] = crops
                
            proc.append(
                dict(
                    {
                        'tracks': track,
                        'features': features,
                        'crops': crops
                    }
            ))

        return { 'inputs': proc }

    def normalize_illumination(self, crop: np.ndarray) -> np.ndarray:
        """
        Lighting normalization using CLAHE in LAB colorspace.
        Fixes shadows, overexposure, lighting variations.
        It increases image details that are too dark or too bright.
        """
        lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB) # LAB colorspace
        
        # CLAHE on L channel only (contrast limited adaptive histogram eq)
        clahe = cv2.createCLAHE(
            clipLimit=2.0,      # clipLimit (2.0 more natural, 3.0 high-contrast)
            tileGridSize=(8,8)  # local contrast adaptation on 8x8px tiles
        )
        lab[:,:,0] = clahe.apply(lab[:,:,0])  # normalize L channel
        
        # back to RGB
        crop_norm = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        
        return crop_norm.astype(np.uint8)

    def _valid_crop(self, crop: np.ndarray) -> bool:
        if crop is None or crop.size == 0:
            return False
        h, w = crop.shape[:2]
        return h >= self.min_crop_h and w >= self.min_crop_w

    def _extract_torso_region(self, crop: np.ndarray) -> np.ndarray:
        h, w = crop.shape[:2]

        y1 = int(0.12 * h)
        y2 = int(0.55 * h) if self.use_torso_crop else h

        if self.use_central_band:
            x1 = int(0.20 * w)
            x2 = int(0.80 * w)
        else:
            x1, x2 = 0, w

        y1 = max(0, min(y1, h - 1))
        y2 = max(y1 + 1, min(y2, h))
        x1 = max(0, min(x1, w - 1))
        x2 = max(x1 + 1, min(x2, w))

        return crop[y1:y2, x1:x2]

    def _build_color_mask(self, hsv_crop: np.ndarray) -> np.ndarray:
        h = hsv_crop[:, :, 0]
        s = hsv_crop[:, :, 1]
        v = hsv_crop[:, :, 2]

        valid_mask = np.ones(h.shape, dtype=bool)

        if self.use_green_mask:
            grass_mask = (
                (h >= 30) & (h <= 95) &
                (s >= 35) &
                (v >= 25)
            )
            valid_mask &= ~grass_mask

        if self.use_gray_mask:
            gray_mask = (s < 30) & (v > 40)
            valid_mask &= ~gray_mask

        dark_mask = v < 20
        valid_mask &= ~dark_mask

        return valid_mask.astype(np.uint8)

    def _masked_histogram(self, hsv_crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        if mask is None or int(mask.sum()) < self.min_pixels:
            return None

        if self.two_channel:
            hist = cv2.calcHist(
                [hsv_crop],
                [0, 1],
                mask,
                [self.hist_h_bins, self.hist_s_bins],
                [0, 180, 0, 256],
            )
        else:
            hist = cv2.calcHist(
                [hsv_crop],
                [0, 1, 2],
                mask,
                [self.hist_h_bins, self.hist_s_bins, self.hist_v_bins],
                [0, 180, 0, 256, 0, 256],
            )

        hist = hist.astype(np.float32).flatten()
        denom = np.linalg.norm(hist) + 1e-12
        hist /= denom
        
        return hist

    def _dominant_color_stats(self, hsv_crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        ys, xs = np.where(mask > 0)
        if len(xs) < self.min_pixels:
            return None

        vals = hsv_crop[ys, xs].astype(np.float32)
        h_mean = np.mean(vals[:, 0]) / 180.0
        s_mean = np.mean(vals[:, 1]) / 255.0
        v_mean = np.mean(vals[:, 2]) / 255.0

        h_std = np.std(vals[:, 0]) / 180.0
        s_std = np.std(vals[:, 1]) / 255.0
        v_std = np.std(vals[:, 2]) / 255.0

        return np.array([h_mean, s_mean, v_mean, h_std, s_std, v_std], dtype=np.float32)

    def _prepare_reid_feature(self, embeddings: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if embeddings is None:
            return None

        embeddings = np.asarray(embeddings)
        if embeddings.size == 0:
            return None

        if embeddings.ndim == 2 and embeddings.shape[0] == 1:
            embeddings = embeddings[0]
        elif embeddings.ndim > 1:
            embeddings = np.mean(embeddings, axis=0)

        embeddings = embeddings.astype(np.float32)
        norm = np.linalg.norm(embeddings) + 1e-12
        return embeddings / norm

    def preproc_features(self, crop: np.ndarray, embeddings: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        if crop is None or not self._valid_crop(crop):
            return None

        crop = np.asarray(crop)
        if crop.dtype != np.uint8:
            crop = np.clip(crop, 0, 255).astype(np.uint8)

        if self.use_illumination_norm:
            crop = self.normalize_illumination(crop)

        torso = self._extract_torso_region(crop)
        if not self._valid_crop(torso):
            return None

        hsv_crop = cv2.cvtColor(torso, cv2.COLOR_RGB2HSV)
        mask = self._build_color_mask(hsv_crop)

        color_hist = self._masked_histogram(hsv_crop, mask)
        if color_hist is None:
            return None

        stats = self._dominant_color_stats(hsv_crop, mask)
        if stats is None:
            return None

        color_feat = np.concatenate([color_hist, stats], axis=0).astype(np.float32)
        color_feat /= (np.linalg.norm(color_feat) + 1e-12)

        if self.clustering_method == "KMEANS":
            if self.hsv_only:
                return color_feat

            reid_feat = self._prepare_reid_feature(embeddings)
            if reid_feat is None:
                return color_feat * self.color_weight

            merged = np.concatenate(
                [
                    color_feat * self.color_weight,
                    reid_feat * self.reid_weight,
                ],
                axis=0,
            ).astype(np.float32)
            merged /= (np.linalg.norm(merged) + 1e-12)
            return merged

        if self.clustering_method == "HDBSCAN":
            if self.hsv_only:
                return color_feat

            reid_feat = self._prepare_reid_feature(embeddings)
            if reid_feat is None:
                return color_feat

            merged = np.concatenate(
                [
                    color_feat * self.color_weight,
                    reid_feat * self.reid_weight,
                ],
                axis=0,
            ).astype(np.float32)
            merged /= (np.linalg.norm(merged) + 1e-12)
            return merged

        return color_feat

    def _aggregate_track_features(
        self,
        per_frame_data: List[Dict[str, Any]],
    ) -> Tuple[Dict[int, np.ndarray], Dict[int, List[Tuple[int, int]]]]:
        track_feature_bank = defaultdict(list)
        track_occurrences = defaultdict(list)

        for frame_idx, frame_data in enumerate(per_frame_data):
            tracks = frame_data["tracks"]
            crops = frame_data.get("crops", [])
            raw_features = frame_data.get("features", [])

            track_ids = tracks.get("track_ids", [])

            if len(raw_features) == 0:
                raw_features = [None] * len(crops)

            for det_idx, (tid, crop, feat) in enumerate(zip(track_ids, crops, raw_features)):
                feat_vec = self.preproc_features(crop=np.array(crop), embeddings=feat)
                if feat_vec is None:
                    continue

                if len(track_feature_bank[tid]) < self.max_samples_per_track:
                    track_feature_bank[tid].append(feat_vec)
                    track_occurrences[tid].append((frame_idx, det_idx))

        track_features = {}
        for tid, feats in track_feature_bank.items():
            if len(feats) < self.min_samples_per_track:
                continue
            X = np.stack(feats, axis=0)
            agg = np.median(X, axis=0).astype(np.float32)
            agg /= (np.linalg.norm(agg) + 1e-12)
            track_features[tid] = agg

        return track_features, track_occurrences

    def cluster_features(self, features: np.ndarray) -> np.ndarray:
        if features is None or len(features) == 0:
            return np.array([], dtype=np.int32)

        X = np.asarray(features, dtype=np.float32)

        if self.use_pca and X.shape[0] > 2 and X.shape[1] > self.pca_components:
            n_comp = min(self.pca_components, X.shape[0] - 1, X.shape[1])
            if n_comp >= 2:
                pca = PCA(n_components=n_comp, random_state=self.random_state)
                X = pca.fit_transform(X)

        if self.clustering_method == "KMEANS":
            n_clusters = min(self.K, len(X))
            if n_clusters <= 1:
                return np.zeros(len(X), dtype=np.int32)

            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=self.random_state,
                n_init=self.n_init,
            )
            labels = kmeans.fit_predict(X).astype(np.int32)
            self.global_centers = kmeans.cluster_centers_
            self.team_centroids = kmeans.cluster_centers_
            return labels

        if self.clustering_method == "HDBSCAN":
            if HDBSCAN is None:
                raise ImportError("HDBSCAN is not available in the current environment.")
            hdbscan = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                cluster_selection_epsilon=self.cluster_selection_epsilon,
                metric=self.metric,
                alpha=1.0,
                algorithm="auto",
                leaf_size=40,
                n_jobs=None,
                cluster_selection_method="eom",
            ).fit(X)
            return hdbscan.labels_.astype(np.int32)

        raise ValueError(f"Unsupported clustering method: {self.clustering_method}")

    def _build_track_team_map(self, track_features: Dict[int, np.ndarray]) -> Dict[int, int]:
        if not track_features:
            return {}

        track_ids = list(track_features.keys())
        X = np.stack([track_features[tid] for tid in track_ids], axis=0)
        labels = self.cluster_features(X)

        track_team_map = {tid: int(lbl) for tid, lbl in zip(track_ids, labels)}
        return track_team_map

    def _assign_back_to_frames(
        self,
        per_frame_data: List[Dict[str, Any]],
        track_team_map: Dict[int, int],
    ) -> List[Dict[str, Any]]:
        output_state = []

        for frame_data in per_frame_data:
            tracks = frame_data["tracks"]
            track_ids = tracks.get("track_ids", [])
            team_ids = [int(track_team_map.get(tid, -1)) for tid in track_ids]

            tracks.update({"team_ids": team_ids})
            output_state.append(tracks)

            bincount_input = np.array([t for t in team_ids if t >= 0], dtype=np.int32)
            if len(bincount_input) > 0:
                logging.info(
                    f'Frame {tracks.get("frame_id", "N/A")}: '
                    f'{len(track_ids)} tracks -> team counts {np.bincount(bincount_input)}'
                )
            else:
                logging.info(
                    f'Frame {tracks.get("frame_id", "N/A")}: '
                    f'{len(track_ids)} tracks -> no valid team labels'
                )

        return output_state

    @torch.no_grad()
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        self.reset_state()

        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs["inputs"]

        if len(per_frame_data) == 0:
            return self.state

        t1 = time.time()

        track_features, track_occurrences = self._aggregate_track_features(per_frame_data)
        if not track_features:
            logging.warning("No valid track-level features available for team clustering.")
            self.state = self._assign_back_to_frames(per_frame_data, {})
            return self.state

        self.track_team_map = self._build_track_team_map(track_features)
        self.state = self._assign_back_to_frames(per_frame_data, self.track_team_map)

        valid_labels = [v for v in self.track_team_map.values() if v >= 0]
        if len(valid_labels) > 0:
            logging.info(
                f"Team clustering done for {len(self.track_team_map)} tracks: "
                f"{np.bincount(np.array(valid_labels, dtype=np.int32))} "
                f"after {time.time() - t1:.3f}s."
            )
        else:
            logging.info(
                f"Team clustering done for {len(self.track_team_map)} tracks with only noise/unassigned labels "
                f"after {time.time() - t1:.3f}s."
            )

        return self.state