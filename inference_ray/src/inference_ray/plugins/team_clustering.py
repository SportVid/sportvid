import json
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple, Optional

import cv2
import numpy as np
import torch
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

try:
    from sklearn.cluster import HDBSCAN
except Exception:
    HDBSCAN = None

from data import Data, DataManager, VideoData, TeamsData
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder
from .osnet_reid import _crop_tracks


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

requires = {
    "video": VideoData,
    # "tracklets": BboxesData,
}

provides = {
    "teams": TeamsData,
}


@AnalyserPluginManager.export("team_clustering")
class TeamClustering(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.1",
    requires=requires,
    provides=provides,
):
    """
    Two-pass track-level team clustering using crop color only.

    Pass 1:
      - decode each frame
      - crop player detections
      - extract per-detection color feature
      - accumulate features by track_id over the whole video
      - store per-frame track ids

    Pass 2:
      - aggregate features per track_id
      - cluster track-level descriptors
      - assign final team labels back to each frame
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def _reset_state(self):
        self.frame_id = 0
        self.global_centers = None
        self.team_centroids = None
        self.track_team_map = {}

        self.track_feature_bank = defaultdict(list)     # tid -> [feat, feat, ...]
        self.track_occurrences = defaultdict(list)      # tid -> [(frame_key, det_idx), ...]
        self.frame_store = []                           # list of per-frame lightweight records

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ):
        self.cfg = parameters or {}

        self.clustering_method = str(self.cfg.get("clustering_method", "KMEANS")).upper()

        self.crop_size_x = int(self.cfg.get("crop_size_x", 128))
        self.crop_size_y = int(self.cfg.get("crop_size_y", 256))
        self.crop_x1_offset = float(self.cfg.get("crop_x1_offset", 0))
        self.crop_y1_offset = float(self.cfg.get("crop_y1_offset", 0))
        self.crop_x2_offset = float(self.cfg.get("crop_x2_offset", 0))
        self.crop_y2_offset = float(self.cfg.get("crop_y2_offset", 0))

        self.two_channel = bool(self.cfg.get("two_channel", True))
        self.K = int(self.cfg.get("K", 2))

        self.min_cluster_size = int(self.cfg.get("min_cluster_size", 4))
        self.cluster_selection_epsilon = float(self.cfg.get("cluster_selection_epsilon", 0.5))
        self.use_pca = bool(self.cfg.get("use_pca", False))
        self.pca_components = int(self.cfg.get("pca_components", 16))
        self.metric = self.cfg.get("metric", "euclidean")

        self.hist_h_bins = int(self.cfg.get("hist_h_bins", 16))
        self.hist_s_bins = int(self.cfg.get("hist_s_bins", 4))
        self.hist_v_bins = int(self.cfg.get("hist_v_bins", 4))

        self.min_pixels = int(self.cfg.get("min_pixels", 12))
        self.min_crop_w = int(self.cfg.get("min_crop_w", 12))
        self.min_crop_h = int(self.cfg.get("min_crop_h", 24))
        self.min_samples_per_track = int(self.cfg.get("min_samples_per_track", 2))
        self.max_samples_per_track = int(self.cfg.get("max_samples_per_track", 20))

        self.use_illumination_norm = bool(self.cfg.get("use_illumination_norm", False))
        self.use_green_mask = bool(self.cfg.get("use_green_mask", False))
        self.use_gray_mask = bool(self.cfg.get("use_gray_mask", False))
        self.use_torso_crop = bool(self.cfg.get("use_torso_crop", False))
        self.use_central_band = bool(self.cfg.get("use_central_band", False))

        self.random_state = int(self.cfg.get("random_state", 42))
        self.n_init = int(self.cfg.get("n_init", 20))

        self._reset_state()

        if "tracklets" not in inputs:
            raise ValueError("team_clustering requires 'tracklets' input.")
        if "video" not in inputs:
            raise ValueError("team_clustering requires 'video' input.")

        with inputs["tracklets"] as tracklets_data:
            tracklets_meta = json.loads(tracklets_data.meta_data or "{}")
            tracklets_meta = tracklets_meta.get("video", {})
            self.fps = tracklets_meta.get("fps", 30)
            self.detector_h = tracklets_meta.get("detector_h", 1080)
            self.detector_w = tracklets_meta.get("detector_w", 1920)
            tracklets_by_time = json.loads(tracklets_data.bboxes)

        with inputs["video"] as video_input_data:
            with video_input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=self.fps,
                    extension=f".{video_input_data.ext}",
                    ref_id=video_input_data.id,
                )

                frame_count = len(video_decoder) if hasattr(video_decoder, "__len__") else None

                # PASS 1: collect per-track features over whole video
                for frame_id, frame_obj in enumerate(video_decoder):
                    self.frame_id = frame_id
                    frame_time = round((frame_id / self.fps) * 1000.0)
                    raw_tracklets = tracklets_by_time.get(str(frame_time), [])

                    self.process(
                        inputs={
                            "tracklets": raw_tracklets,
                            "image": frame_obj["frame"],
                            "frame_time": frame_time,
                        }
                    )

                    if frame_count is not None:
                        self.update_callbacks(callbacks, progress=0.5 * ((frame_id + 1) / max(frame_count, 1)))

        # PASS 2: aggregate + cluster + assign back
        track_features = self._finalize_track_features()

        if not track_features:
            logging.warning("No valid track-level features available for team clustering.")
            teams_mapping = {
                frame_rec["frame_key"]: {
                    int(tid): -1 for tid in frame_rec["track_ids"].tolist()
                }
                for frame_rec in self.frame_store
            }
        else:
            self.track_team_map = self._build_track_team_map(track_features)
            teams_mapping = self._build_frame_team_mapping(self.track_team_map)

            valid_labels = [v for v in self.track_team_map.values() if v >= 0]
            if len(valid_labels) > 0:
                logging.info(
                    f"Team clustering done for {len(self.track_team_map)} tracks: "
                    f"{np.bincount(np.array(valid_labels, dtype=np.int32))}"
                )
            else:
                logging.info(
                    f"Team clustering done for {len(self.track_team_map)} tracks with only noise/unassigned labels"
                )

        with data_manager.create_data("TeamsData") as teams:
            teams.teams_data = json.dumps(teams_mapping)
            self.update_callbacks(callbacks, progress=1.0)
            return {"teams": teams}

    @torch.no_grad()
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        tracklets = inputs.get("tracklets", [])
        img = inputs.get("image", None)
        frame_time = inputs.get("frame_time", None)

        if img is None:
            logging.warning(f"[preprocess] frame={self.frame_id} image is None")
            return {"inputs": []}

        if tracklets is None or len(tracklets) == 0:
            return {"inputs": []}

        tracklets_npy = np.asarray(tracklets, dtype=np.float32)

        if tracklets_npy.ndim == 3 and tracklets_npy.shape[1] == 1:
            tracklets_npy = np.squeeze(tracklets_npy, axis=1)

        if tracklets_npy.ndim == 1:
            tracklets_npy = tracklets_npy[None, :]

        if tracklets_npy.size == 0 or tracklets_npy.shape[1] < 9:
            logging.warning(f"[preprocess] frame={self.frame_id} invalid tracklet shape={tracklets_npy.shape}")
            return {"inputs": []}

        tracklets_npy = tracklets_npy.copy()
        tracklets_npy[:, 5] *= self.detector_w
        tracklets_npy[:, 6] *= self.detector_h
        tracklets_npy[:, 7] *= self.detector_w
        tracklets_npy[:, 8] *= self.detector_h

        track_ids = tracklets_npy[:, 0].astype(np.int32)
        track_xywh = tracklets_npy[:, 5:9].astype(np.float32)

        crops = _crop_tracks(
            img,
            track_xywh,
            track_ids,
            (self.crop_size_x, self.crop_size_y),
            self.crop_x1_offset,
            self.crop_y1_offset,
            self.crop_x2_offset,
            self.crop_y2_offset,
        )
        if not crops:
            return {"inputs": []}

        crop_arrays = []
        valid_track_rows = []

        for row, crop_pil in zip(tracklets_npy, crops):
            if crop_pil is None:
                continue
            crop_arr = np.asarray(crop_pil, dtype=np.uint8)
            if crop_arr.size == 0:
                continue
            crop_arrays.append(crop_arr)
            valid_track_rows.append(row)

        if len(valid_track_rows) == 0:
            return {"inputs": []}

        track_arr = np.stack(valid_track_rows, axis=0).astype(np.float32)

        return {
            "inputs": [
                {
                    "frame_id": int(self.frame_id),
                    "frame_time": frame_time,
                    "tracks": track_arr,     # [N,10]
                    "crops": crop_arrays,    # list length N
                }
            ]
        }

    @torch.no_grad()
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs.get("inputs", [])

        if len(per_frame_data) == 0:
            return {}

        frame_data = per_frame_data[0]
        tracks = np.asarray(frame_data["tracks"], dtype=np.float32)
        crops = frame_data.get("crops", [])
        frame_time = frame_data.get("frame_time", None)
        frame_key = str(frame_time) if frame_time is not None else str(frame_data["frame_id"])

        if tracks.ndim == 1:
            tracks = tracks[None, :]

        track_ids = tracks[:, 0].astype(np.int32)

        self.frame_store.append(
            {
                "frame_id": int(frame_data["frame_id"]),
                "frame_key": frame_key,
                "track_ids": track_ids.copy(),
            }
        )

        valid_count = 0
        for det_idx, tid in enumerate(track_ids):
            crop = crops[det_idx] if det_idx < len(crops) else None
            feat_vec = self.preproc_features(crop)

            if feat_vec is None:
                continue

            tid = int(tid)
            if len(self.track_feature_bank[tid]) < self.max_samples_per_track:
                self.track_feature_bank[tid].append(feat_vec)
                self.track_occurrences[tid].append((frame_key, det_idx))
                valid_count += 1

        logging.info(
            f"[process] frame={self.frame_id} detections={len(track_ids)} "
            f"valid_features={valid_count} unique_tracks_seen={len(self.track_feature_bank)}"
        )

        return {
            "frame_key": frame_key,
            "track_ids": track_ids,
        }

    def normalize_illumination(self, crop: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
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

        return (valid_mask.astype(np.uint8) * 255)

    def _masked_histogram(self, hsv_crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        if mask is None or int((mask > 0).sum()) < self.min_pixels:
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
        hist /= (np.linalg.norm(hist) + 1e-12)
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

    def preproc_features(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if crop is None:
            return None

        if not self._valid_crop(crop):
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
        
        return color_feat

    def _finalize_track_features(self) -> Dict[int, np.ndarray]:
        track_features = {}

        for tid, feats in self.track_feature_bank.items():
            if len(feats) < self.min_samples_per_track:
                continue

            X = np.stack(feats, axis=0).astype(np.float32)
            agg = np.median(X, axis=0).astype(np.float32)
            agg /= (np.linalg.norm(agg) + 1e-12)
            track_features[int(tid)] = agg

        logging.info(
            f"[finalize] total_tracks_seen={len(self.track_feature_bank)} "
            f"tracks_after_min_samples={len(track_features)}"
        )
        return track_features

    def cluster_features(self, features: np.ndarray) -> np.ndarray:
        if features is None or len(features) == 0:
            return np.array([], dtype=np.int32)

        X = np.asarray(features, dtype=np.float32)

        if self.use_pca and X.ndim == 2 and X.shape[0] >= 2 and X.shape[1] >= 2:
            max_comp = min(self.pca_components, X.shape[0], X.shape[1])
            if max_comp >= 2:
                pca = PCA(n_components=max_comp, random_state=self.random_state)
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
        return {int(tid): int(lbl) for tid, lbl in zip(track_ids, labels)}

    def _build_frame_team_mapping(self, track_team_map: Dict[int, int]) -> Dict[str, Dict[int, int]]:
        teams_mapping = {}

        for frame_rec in self.frame_store:
            frame_key = frame_rec["frame_key"]
            track_ids = frame_rec["track_ids"]

            mapping = {
                int(tid): int(track_team_map.get(int(tid), -1))
                for tid in track_ids.tolist()
            }
            teams_mapping[frame_key] = mapping

            valid = [v for v in mapping.values() if v >= 0]
            if len(valid) > 0:
                logging.info(
                    f"[assign] frame={frame_key} tracks={len(mapping)} "
                    f"team_counts={np.bincount(np.array(valid, dtype=np.int32))}"
                )
            else:
                logging.info(
                    f"[assign] frame={frame_key} tracks={len(mapping)} no valid team labels"
                )

        return teams_mapping