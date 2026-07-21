import logging
from typing import Any, Callable, Dict, List, Tuple, Optional
from data import (
    Data, DataManager, 
    VideoData,
    BboxesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder, VideoBatcher

import time
import torch
import numpy as np
import cv2
from PIL import Image
from sklearn.cluster import KMeans, HDBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


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
    """ Crops track boxes and converts them to PIL RGB (H,W,C). """

    def torch_to_npy(img):
        if isinstance(img, torch.Tensor):
            img_npy = img.permute(1, 2, 0).cpu().numpy()  # CHW -> HWC
            if img_npy.max() <= 1.0:  # normalize
                img_npy = (img_npy * 255).astype(np.uint8)
            return img_npy
        else:
            return img  

    img_npy = torch_to_npy(img)
    logging.debug(f"img shape: {img_npy.shape}") # (H,W,C)

    h_img, w_img = img_npy.shape[:2]
    
    crops = []
    for i, (tid, box) in enumerate(zip(track_ids, track_boxes)):
        x1, y1, w, h = box.astype(float)

        if w <= 0 or h <= 0: # sanity check raw box
            logging.debug(f"Raw box: x1={x1}, y1={y1}, w={w}, h={h}")
            logging.debug(f"Skipping invalid box {box}")
            continue

        # apply fractional offsets
        x1 += w * x1_offset
        y1 += h * y1_offset
        x2 = x1 + w * (1.0 + x2_offset)
        y2 = y1 + h * (1.0 + y2_offset)
        
        # clipping
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_img, x2), min(h_img, y2)
        
        crop_bgr = img_npy[int(y1):int(y2), int(x1):int(x2)]
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        crop_pil = Image.fromarray(crop_rgb)
        crop_pil = crop_pil.resize(crop_size, Image.Resampling.LANCZOS) # resize to OSNet crop_size
        crops.append(crop_pil)

    return crops  


class Clustering:
    """
    This module either runs k-Means or HDBSCAN clustering on tracklet crops or ReID embeddings for team assignment.
    - Each tracklet gets a team label assigned from [0,K-1].
    - For k-Means a color histogram of the player crops is computed that captures the color distribution.
    - HDBScan uses the ReID embeddings [N,512] with optional dim. reduction via PCA for clustering.
    """

    def __init__(
        self, 
        model_name: str = "team_clustering",
        model_path: Optional[str] = None,
        device: str = "cuda",
        **kwargs
    ):
        self.device = device if torch.cuda.is_available() else 'cpu'
        logging.info(f'Team cfg: {self.cfg}')
        
        self.clustering_method = self.cfg.get('clustering_method', 'KMEANS') # ['KMEANS', 'HDBSCAN']
        
        self.crop_size = self.cfg.get('crop_size', [128, 256]) # resizing to (H,W)
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

        self.state = list()
        self.frame_id = 0

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

    def preproc_features(self, crop, embeddings):
        if not np.any(embeddings):
            # TODO: in case there exist no embeddings, compute them on-the-fly ???
            return []
        
        # ---> L2-normalize feature vector
        if len(embeddings.shape) == 1: 
            embeddings = embeddings.reshape(1, -1)
        embeddings_norm = normalize(embeddings, norm='l2', axis=1)
        
        if self.clustering_method == 'KMEANS':
            # lighting invariance
            crop_norm = self.normalize_illumination(crop)
            # compute color histogram
            hsv_crop = cv2.cvtColor(crop_norm, cv2.COLOR_RGB2HSV)
            color_hist = cv2.calcHist(
                [hsv_crop], 
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