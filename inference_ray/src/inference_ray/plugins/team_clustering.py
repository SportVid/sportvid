import logging
import time
import torch
import numpy as np
import cv2
from typing import Any, Callable, Dict, List, Tuple, Optional
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData,
    ReIDData,
    TeamsData
)
from PIL import Image
from sklearn.cluster import KMeans, HDBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
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
    """ This module either runs k-Means on tracklet crops or HDBSCAN clustering on the ReID embeddings for team assignment.
    - Each tracklet gets a team label assigned from [0, K-1].
    - For k-Means a color histogram of the player crops is computed that captures the color distribution.
    - HDBScan REuses the REID embeddings [N,512] with optional dim. reduction via PCA for clustering.
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
        
        self.clustering_method = self.cfg.get('clustering_method', 'KMEANS') # ['KMEANS', 'HDBSCAN']
        
        # crop sizes
        self.crop_size_x = self.cfg.get('crop_size_x', 128) 
        self.crop_size_y = self.cfg.get('crop_size_y', 256)
        self.crop_x1_offset = self.cfg.get('crop_x1_offset', 0)
        self.crop_y1_offset = self.cfg.get('crop_y1_offset', 0)
        self.crop_x2_offset = self.cfg.get('crop_x2_offset', 0)
        self.crop_y2_offset = self.cfg.get('crop_y2_offset', 0)
        
        self.hsv_only = self.cfg.get('hsv_only', True)
        self.two_channel = self.cfg.get('two_channel', True)
        self.K = self.cfg.get('K', 3)

        self.min_cluster_size = self.cfg.get('min_cluster_size', 4)
        self.cluster_selection_epsilon = self.cfg.get('cluster_selection_epsilon', 0.5)
        self.use_pca = self.cfg.get('use_pca', False)
        self.pca_components = self.cfg.get('pca_components', 50)
        self.metric = self.cfg.get('metric', 'euclidean')
        
        if inputs["reids"]: # crops are there, allows the use of HDBSCAN.
            with inputs["reids"] as reids_data:
                reids_ = reids_.frames
                logging.error(reids_)
                self.reids = True

    
    @torch.no_grad()
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Encode tracklet crops using the feature extractor. """
        tracks = inputs.get('tracks', []) # {'track_ids':[], 'track_boxes':[N,4] xywh}
        imgs = inputs.get('images', []) # full frame numpy BGR
        
        if not tracks: return inputs
        
        # check if tracks contains crops, if not create crops from tracklets here
        proc = []
        for i, (track, img) in enumerate(zip(tracks, imgs['frame'])):
            track_ids = track['track_ids']
            track_boxes = track['track_boxes'] # [N,4] [x1,y1,w,h]
            features = track.get('features', [])
            crops = track.get('crops', [])
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
                track.update({ 'crops' : crops })
                
            proc.append(
                dict(
                    {
                        'tracks': track,
                        'features': features,
                        'crops': crops
                    }
            ))

        return { 'inputs': proc }

    def normalize_illumination(self, crop):
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

    def dominant_color_filter(self, crop):
        """
        Remove grass/background -> keep dominant jersey pixels only.
        Returns clean HSV histogram of jersey colors.
        """
        # TODO: dominant color filtering to only provide jersey colors;
        # however if the jersey contains green that's a problem?
        pass

    @torch.no_grad()
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ 
        1) Extract HSV histograms, merge ReID embeddings with HSV histogram if available.
        2) Perform global k-Means clustering on (hybrid) features.
        3) Update tracks with team_ids. 
        """
        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs['inputs']
        t1 = time.time()
        # ----> feature extraction & merging
        all_frame_features = []
        for frame_data in per_frame_data:
            # tracks & crops always existing
            crops = frame_data['crops']
            # features might not ...
            reid_feats = frame_data.get('features', [])

            per_frame_features = []
            for crop_pil, reid_feat in zip(crops, reid_feats) if len(reid_feats) > 0 else zip(crops, [None] * len(crops)):
                crop = np.array(crop_pil)
                
                # pre-processing for clustering (HSV histogram, compute embeddings if required)
                clustering_features = self.preproc_features(crop, reid_feat)
                per_frame_features.append(clustering_features)
        
            # store HSV/hybrid features back in frame_data for downstream
            frame_data['features'] = np.array(per_frame_features)
            all_frame_features.extend(per_frame_features)
    
        # ----> global tracklet clustering
        all_features_np = np.array(all_frame_features)
        global_team_ids = self.cluster_features(all_features_np)
        global_team_ids = global_team_ids.astype(int)

        # ----> assign team_ids to each frame's tracks
        team_id_idx = 0
        for frame_data in per_frame_data:
            feats = frame_data['features']  # updated features
            tracks = frame_data['tracks']
            crops = frame_data['crops']
            
            frame_team_ids = global_team_ids[team_id_idx:team_id_idx + len(feats)]
            team_id_idx += len(feats)
            
            tracks.update({"team_ids": frame_team_ids.tolist()})
            tracks.update({"crops": crops})
            tracks.update({"features": feats})
            
            self.state.append(tracks)
            
            logging.info(f'Frame {tracks.get("frame_id", "N/A")}: {len(feats)} tracks -> {np.bincount(frame_team_ids)}')
        logging.info(f"Team clustering for {len(feats)} tracks is done: {np.bincount(global_team_ids)} after {time.time()-t1}s.")
        
        return self.state

    # TODO: test & adjust for input crops.
    def color_descriptor(
        self,
        crop,
        hist_bins=(4, 6, 6),
        use_torso=True,
        add_stats=True,
        mask_gray=True,
    ):
        """
        Compute a LAB-based color descriptor for jersey clustering.

        Args:
            crop (np.ndarray): RGB crop of a player, shape (H, W, 3).
            hist_bins (tuple): Number of bins for L, A, B histogram.
            use_torso (bool): Use upper-middle torso region instead of full crop.
            add_stats (bool): Append per-channel mean/std in LAB.
            mask_gray (bool): Mask low-chroma pixels that are less informative.

        Returns:
            np.ndarray: 1D L2-normalized feature vector.
        """
        if crop is None or crop.size == 0:
            return np.array([], dtype=np.float32)
        if crop.ndim != 3 or crop.shape[2] != 3:
            return np.array([], dtype=np.float32)
        h, w = crop.shape[:2]
        if h < 4 or w < 4:
            return np.array([], dtype=np.float32)
        roi = crop

        if use_torso: # focus on jersey region: upper-middle torso
            y1 = int(0.18 * h)
            y2 = int(0.60 * h)
            x1 = int(0.20 * w)
            x2 = int(0.80 * w)
            if y2 > y1 and x2 > x1:
                roi = crop[y1:y2, x1:x2]

        roi = cv2.GaussianBlur(roi, (3, 3), 0)  # smooth to reduce pixel noise
        lab = cv2.cvtColor(roi, cv2.COLOR_RGB2LAB)  # RGB -> LAB

        # optional mask to suppress low-chroma pixels
        mask = None
        if mask_gray:
            lab_f = lab.astype(np.float32)
            a = lab_f[:, :, 1] - 128.0
            b = lab_f[:, :, 2] - 128.0
            chroma = np.sqrt(a * a + b * b)
            # keep sufficiently colorful pixels
            mask = (chroma > 12).astype(np.uint8) * 255
            # fallback if mask is too small
            if np.count_nonzero(mask) < 0.05 * mask.size:
                mask = None
            
        hist = cv2.calcHist( # 3D histogram in LAB
            [lab],
            [0, 1, 2],
            mask,
            list(hist_bins),
            [0, 256, 0, 256, 0, 256]
        )
        hist = hist.astype(np.float32).flatten()

        # normalize histogram to sum=1 first
        hist_sum = hist.sum()
        if hist_sum > 0:
            hist /= hist_sum
        feats = [hist]

        if add_stats:
            if mask is not None:
                pixels = lab[mask > 0].reshape(-1, 3).astype(np.float32)
            else:
                pixels = lab.reshape(-1, 3).astype(np.float32)

            if len(pixels) > 0:
                mean = pixels.mean(axis=0)
                std = pixels.std(axis=0)
                stats = np.concatenate([  # scale to roughly comparable ranges
                    mean / 255.0,
                    std / 255.0
                ]).astype(np.float32)
                feats.append(stats)
    
        feat = np.concatenate(feats).astype(np.float32)
        # final L2 normalization
        feat = normalize(feat.reshape(1, -1), norm='l2').squeeze(0)
        return feat

    def preproc_features(self, crops, embeddings):
        if embeddings is None or not np.any(embeddings):
            # NOTE: in case there is no embeddings from the REID modules.
            # Computes a LAB-based color discriptor on-the-fly.
            return self.color_descriptor(crops)     
        
        # ---> L2-normalize feature vector
        if len(embeddings.shape) == 1: 
            embeddings = embeddings.reshape(1, -1)
        embeddings_norm = normalize(embeddings, norm='l2', axis=1)
        
        if self.clustering_method == 'KMEANS':
            # lighting invariance
            crops_norm = self.normalize_illumination(crops)
            # compute color histogram
            hsv_crops = cv2.cvtColor(crops_norm, cv2.COLOR_RGB2HSV)
            color_hist = cv2.calcHist(
                [hsv_crops], 
                [0, 1] if self.two_channel else [0, 1, 2],
                None, 
                [3, 3] if self.two_channel else [3, 3, 3], 
                [0, 180, 0, 256] if self.two_channel else [0, 180, 0, 256, 0, 256]
            )
            hsv_feat = cv2.normalize(color_hist, None).flatten()
            # hsv_feat = self.dominant_color_filter(crop_norm)
            
            if self.hsv_only: return hsv_feat
            if len(embeddings.shape) == 2: embeddings_norm = np.squeeze(embeddings_norm, axis=0)
            return np.concatenate([embeddings_norm, hsv_feat])
        if self.clustering_method == 'HDBSCAN':
            if self.use_pca:
                pca = PCA(n_components=self.pca_components)
                pca_features = pca.fit_transform(embeddings_norm)
                return pca_features
            return embeddings_norm
        
        return []

    def cluster_features(self, features):
        if self.clustering_method == 'KMEANS':
            if len(features) >= self.K:
                kmeans = KMeans(n_clusters=self.K, random_state=42, n_init=10)
                team_ids = kmeans.fit_predict(features)
                self.global_centers = kmeans.cluster_centers_ if len(features) >= self.K else None
            else:
                team_ids = np.zeros(len(features), dtype=np.int32)
            return team_ids
        if self.clustering_method == 'HDBSCAN':
            if len(features.shape) == 3: features = np.squeeze(features, axis=1)
            hdbscan = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                cluster_selection_epsilon=self.cluster_selection_epsilon,
                metric=self.metric,
                alpha=1.0, 
                algorithm='auto', 
                leaf_size=40,
                n_jobs=None,
                cluster_selection_method='eom'
            ).fit(features)    
            labels = np.add(hdbscan.labels_.astype(float), 1)
            return labels
        return []