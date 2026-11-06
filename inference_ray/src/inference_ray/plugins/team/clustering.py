"""Team clustering of player tracks.

Per crop a feature (jersey colour, the ReID embedding, or both), per track the median of up to
``max_samples_per_track`` crops sampled evenly over the track, then KMeans / HDBSCAN over the tracks. The
``num_teams`` most populous clusters become the teams 0..num_teams-1 (ordered by size); the other clusters
(goalkeepers, referees, outliers) and HDBSCAN noise become -1.

The plugin (``team_clustering.py``) picks the samples from the box geometry, crops them and computes the
embeddings; this module holds the features and the clustering.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# the defaults; the backend serializer holds the same values
DEFAULTS = {
    "clustering_method": "KMEANS",
    "K": 3,
    "num_teams": 2,
    "min_cluster_size": 3,
    "cluster_selection_epsilon": 0.5,
    "use_pca": False,
    "pca_components": 16,
    "metric": "euclidean",
    "hsv_only": True,
    "embedding_only": True,
    "two_channel": True,
    "hist_h_bins": 16,
    "hist_s_bins": 4,
    "hist_v_bins": 4,
    "use_illumination_norm": True,
    "use_green_mask": True,
    "use_gray_mask": True,
    "use_torso_crop": True,
    "use_central_band": True,
    "min_pixels": 40,
    "min_crop_w": 8,
    "min_crop_h": 16,
    "min_samples_per_track": 2,
    "max_samples_per_track": 15,
    "random_state": 42,
    "n_init": 10,
    "color_weight": 1.0,
    "reid_weight": 0.1,
}


class TeamClusterer:
    """Per-crop features and per-track clustering. ``uses_color`` / ``uses_embeddings`` tell the caller what
    to compute per sampled crop."""

    def __init__(self, cfg: Dict[str, Any]):
        c = {**DEFAULTS, **{k: v for k, v in (cfg or {}).items() if v is not None}}
        self.clustering_method = str(c["clustering_method"]).upper()
        if self.clustering_method not in ("KMEANS", "HDBSCAN"):
            raise ValueError(f"Unsupported clustering method: {self.clustering_method}")
        self.K = int(c["K"])
        self.num_teams = int(c["num_teams"])
        self.min_cluster_size = int(c["min_cluster_size"])
        self.cluster_selection_epsilon = float(c["cluster_selection_epsilon"])
        self.use_pca = bool(c["use_pca"])
        self.pca_components = int(c["pca_components"])
        self.metric = c["metric"]
        self.hsv_only = bool(c["hsv_only"])
        # the ReID embeddings alone: a crop abstains only when it has no embedding (box below min_box_w / _h)
        self.embedding_only = bool(c["embedding_only"])
        self.two_channel = bool(c["two_channel"])
        self.hist_h_bins = int(c["hist_h_bins"])
        self.hist_s_bins = int(c["hist_s_bins"])
        self.hist_v_bins = int(c["hist_v_bins"])
        self.use_illumination_norm = bool(c["use_illumination_norm"])
        self.use_green_mask = bool(c["use_green_mask"])
        self.use_gray_mask = bool(c["use_gray_mask"])
        self.use_torso_crop = bool(c["use_torso_crop"])
        self.use_central_band = bool(c["use_central_band"])
        self.min_pixels = int(c["min_pixels"])
        self.min_crop_w = int(c["min_crop_w"])
        self.min_crop_h = int(c["min_crop_h"])
        self.min_samples_per_track = int(c["min_samples_per_track"])
        self.max_samples_per_track = int(c["max_samples_per_track"])
        self.random_state = int(c["random_state"])
        self.n_init = c["n_init"] if c["n_init"] == "auto" else int(c["n_init"])
        self.color_weight = float(c["color_weight"])
        self.reid_weight = float(c["reid_weight"])
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    @property
    def uses_color(self) -> bool:
        return not self.embedding_only

    @property
    def uses_embeddings(self) -> bool:
        return self.embedding_only or not self.hsv_only

    # ---- sampling

    def sample(self, track_occ: Dict[int, List[Any]]) -> List[Tuple[int, Any]]:
        """``(tid, occurrence)`` of up to max_samples_per_track occurrences per track, evenly spaced over the track,
        tracks in first-seen order (the KMeans input order follows it)."""
        tasks = []
        for tid, occ in track_occ.items():
            if len(occ) > self.max_samples_per_track:
                sel = np.linspace(0, len(occ) - 1, self.max_samples_per_track)
                occ = [occ[j] for j in sorted(set(sel.round().astype(int).tolist()))]
            tasks += [(tid, o) for o in occ]
        return tasks

    # ---- per-crop features

    def normalize_illumination(self, crop: np.ndarray) -> np.ndarray:
        """CLAHE on the L channel (LAB): evens out shadows and overexposure."""
        lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
        lab[:, :, 0] = self._clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.uint8)

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
            x1, x2 = int(0.20 * w), int(0.80 * w)
        else:
            x1, x2 = 0, w
        y1 = max(0, min(y1, h - 1))
        y2 = max(y1 + 1, min(y2, h))
        x1 = max(0, min(x1, w - 1))
        x2 = max(x1 + 1, min(x2, w))
        return crop[y1:y2, x1:x2]

    def _build_color_mask(self, hsv_crop: np.ndarray) -> np.ndarray:
        h, s, v = hsv_crop[:, :, 0], hsv_crop[:, :, 1], hsv_crop[:, :, 2]
        valid = np.ones(h.shape, dtype=bool)
        if self.use_green_mask:  # pitch green (critical on amateur pitches)
            valid &= ~((h >= 30) & (h <= 95) & (s >= 35) & (v >= 25))
        if self.use_gray_mask:   # low-saturation background (asphalt, grey stands)
            valid &= ~((s < 30) & (v > 40))
        valid &= ~(v < 20)
        return valid.astype(np.uint8)

    def _masked_histogram(self, hsv_crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        if mask is None or int(mask.sum()) < self.min_pixels:
            return None
        if self.two_channel:
            hist = cv2.calcHist([hsv_crop], [0, 1], mask, [self.hist_h_bins, self.hist_s_bins], [0, 180, 0, 256])
        else:
            hist = cv2.calcHist([hsv_crop], [0, 1, 2], mask, [self.hist_h_bins, self.hist_s_bins, self.hist_v_bins],
                                [0, 180, 0, 256, 0, 256])
        hist = hist.astype(np.float32).flatten()
        hist /= np.linalg.norm(hist) + 1e-12
        return hist

    def _dominant_color_stats(self, hsv_crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        ys, xs = np.where(mask > 0)
        if len(xs) < self.min_pixels:
            return None
        vals = hsv_crop[ys, xs].astype(np.float32)
        return np.array([
            np.mean(vals[:, 0]) / 180.0, np.mean(vals[:, 1]) / 255.0, np.mean(vals[:, 2]) / 255.0,
            np.std(vals[:, 0]) / 180.0, np.std(vals[:, 1]) / 255.0, np.std(vals[:, 2]) / 255.0,
        ], dtype=np.float32)

    def color_feature(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """HSV histogram + colour statistics of the torso of an HWC uint8 RGB crop, or None (too few pixels)."""
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
        hsv = cv2.cvtColor(torso, cv2.COLOR_RGB2HSV)
        mask = self._build_color_mask(hsv)
        hist = self._masked_histogram(hsv, mask)
        if hist is None:
            return None
        stats = self._dominant_color_stats(hsv, mask)
        if stats is None:
            return None
        feat = np.concatenate([hist, stats], axis=0).astype(np.float32)
        feat /= np.linalg.norm(feat) + 1e-12
        return feat

    @staticmethod
    def _reid_feature(embedding: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if embedding is None:
            return None
        embedding = np.asarray(embedding)
        if embedding.size == 0:
            return None
        if embedding.ndim == 2 and embedding.shape[0] == 1:
            embedding = embedding[0]
        elif embedding.ndim > 1:
            embedding = np.mean(embedding, axis=0)
        embedding = embedding.astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm < 1e-6:
            return None
        return embedding / norm

    def crop_feature(self, color: Optional[np.ndarray], embedding: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """The clustering feature of one crop from its ``color_feature`` and ReID embedding. A crop
        whose colour feature failed abstains in the mixed mode too (its embedding is not used alone)."""
        if self.embedding_only:
            return self._reid_feature(embedding)
        if color is None or self.hsv_only:
            return color
        reid = self._reid_feature(embedding)
        if reid is None:
            # KMeans keeps the colour weight here, HDBSCAN does not
            return color * self.color_weight if self.clustering_method == "KMEANS" else color
        merged = np.concatenate([color * self.color_weight, reid * self.reid_weight], axis=0).astype(np.float32)
        merged /= np.linalg.norm(merged) + 1e-12
        return merged

    # ---- per-track features and clustering

    def track_features(self, results: List[Tuple[int, Optional[np.ndarray]]]) -> Dict[int, np.ndarray]:
        """Median feature per track from ``(tid, feature)`` in sample order; tracks with fewer than
        min_samples_per_track features are left out."""
        bank: Dict[int, list] = defaultdict(list)
        for tid, feat in results:
            if feat is not None:
                bank[tid].append(feat)
        out = {}
        for tid, feats in bank.items():
            if len(feats) < self.min_samples_per_track:
                continue
            agg = np.median(np.stack(feats, axis=0), axis=0).astype(np.float32)
            agg /= np.linalg.norm(agg) + 1e-12
            out[tid] = agg
        return out

    def cluster_features(self, features: np.ndarray) -> np.ndarray:
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA

        if features is None or len(features) == 0:
            return np.array([], dtype=np.int32)
        X = np.asarray(features, dtype=np.float32)
        if self.use_pca and X.shape[0] > 2 and X.shape[1] > self.pca_components:
            n_comp = min(self.pca_components, X.shape[0] - 1, X.shape[1])
            if n_comp >= 2:
                X = PCA(n_components=n_comp, random_state=self.random_state).fit_transform(X)

        if self.clustering_method == "KMEANS":
            n_clusters = min(self.K, len(X))
            if n_clusters <= 1:
                return np.zeros(len(X), dtype=np.int32)
            km = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=self.n_init)
            return km.fit_predict(X).astype(np.int32)

        from sklearn.cluster import HDBSCAN
        return HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric=self.metric,
            alpha=1.0,
            algorithm="auto",
            leaf_size=40,
            n_jobs=None,
            cluster_selection_method="eom",
        ).fit(X).labels_.astype(np.int32)

    def track_teams(self, track_features: Dict[int, np.ndarray]) -> Dict[int, int]:
        """Track id -> team 0..num_teams-1 (the most populous clusters, largest first) or -1."""
        if not track_features:
            return {}
        track_ids = list(track_features.keys())
        labels = self.cluster_features(np.stack([track_features[t] for t in track_ids], axis=0))

        n_teams = max(1, min(self.num_teams, len(set(int(l) for l in labels if l >= 0)) or 1))
        pos = labels[labels >= 0]
        if pos.size == 0:
            return {tid: -1 for tid in track_ids}
        counts = np.bincount(pos)
        ranked = [int(c) for c in np.argsort(counts)[::-1] if counts[c] > 0][:n_teams]
        remap = {old: new for new, old in enumerate(ranked)}
        n_dropped = sum(1 for l in labels if int(l) not in remap)
        if n_dropped:
            logger.info(f"team clustering: {len(ranked)} team cluster(s) kept (sizes {[int(counts[c]) for c in ranked]}), "
                        f"{n_dropped} track(s) -> -1 (keeper / referee / outlier).")
        return {tid: remap.get(int(l), -1) for tid, l in zip(track_ids, labels)}
