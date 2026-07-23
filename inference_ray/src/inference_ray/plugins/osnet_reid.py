import logging
import torch
import numpy as np
import cv2
from typing import Any, Callable, Dict, List, Tuple, Optional
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
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


@AnalyserPluginManager.export("osnet_reid")
class OSNetReID(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.1",
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

        self.cfg = parameters
        
        self.reid_threshold = self.cfg.get('reid_thresh', 0.6)
        self.max_missed = self.cfg.get('max_missed', 30) # prune stale tracks
        
        # resizing to (H,W) for feature extractor
        self.crop_size_x = self.cfg.get('crop_size_x', 128) 
        self.crop_size_y = self.cfg.get('crop_size_y', 256)
        self.crop_x1_offset = self.cfg.get('crop_x1_offset', 0)
        self.crop_y1_offset = self.cfg.get('crop_y1_offset', 0)
        self.crop_x2_offset = self.cfg.get('crop_x2_offset', 0)
        self.crop_y2_offset = self.cfg.get('crop_y2_offset', 0)
    
        self.feat_extr = FeatureExtractor( # wraps preprocessing and model forward
            model_name=self.cfg.get('model_name'),
            model_path=self.cfg.get('checkpoint', None), # NOTE: checkpoint -> if we provide 'None': model uses default weights.
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        
        self.gallery = Gallery(
            threshold=parameters["reid_threshold"], 
            max_missed=parameters["max_missed"]
        )
        
        self.state = list()
        self.frame_id = 0
        with inputs["video"] as video_input_data, inputs["tracklets"] as tracklets_data:
            with video_input_data.open_video() as f_video:
                video_decoder = VideoDecoder(
                    f_video,
                    extension=f".{video_input_data.ext}",
                    ref_id=video_input_data.id,
                )
                tracklets_meta = tracklets_data.meta_data.get('video', {}),
                logging.error(tracklets_meta)
                self.fps = tracklets_meta.get('fps', 30)
                self.detector_h = tracklets_meta.get('detector_h', 1080)
                self.detector_w = tracklets_meta.get('detector_w', 1920)
                tracklets_data = tracklets_data.bboxes
                
                for frame_id, _frame in enumerate(video_decoder):
                    frame_time = round((frame_id/self.fps)*1000.)
                    _tracklets = tracklets_data[frame_time]
                    _preproc = self.preprocess(
                        inputs={
                            "tracklets": _tracklets,
                            "image": _frame,
                        }
                    )
                    self.process(_preproc)
                        

    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Encode tracklet crops using the feature extractor. """
        # NOTE: Expects single tracklet/image pair as inputs.
        tracklets = inputs.get('tracklets', {})    # {'track_ids':[], 'track_boxes':[N,4] xywh}
        img = inputs.get('image')                 # full frame numpy BGR
    
        logging.debug(f'{tracklets}')
        
        if not tracklets: return inputs
        
        proc = []
        
        # for i, (track, img) in enumerate(zip(tracks, imgs['frame'])):
        track_ids = tracklets['track_ids']
        track_boxes = tracklets['track_boxes'] # [N,4] [x1,y1,w,h]
        # TODO: revert coordinate normalization of track_boxes using detector W/H
        crops = _crop_tracks( # crops track boxes
            img, 
            track_boxes, 
            track_ids,
            (self.crop_size_x, self.crop_size_y),
            self.crop_x1_offset,
            self.crop_y1_offset,
            self.crop_x2_offset,
            self.crop_y2_offset
        ) 
        if not crops: crops = []
        
        crop_arrays_rgb = []
        for crop_pil in crops:
            crop_np_rgb = np.array(crop_pil)  # PIL -> RGB numpy HWC uint8
            crop_arrays_rgb.append(crop_np_rgb)

        features = self.feat_extr(crop_arrays_rgb).cpu().numpy() # extract features: PIL list of image bboxes -> [N,512] normalized
    
        [dict(
                {
                    'tracks': tracklets,
                    'features': features,
                    'crops': crops
                }
        )]
    
        return { 'inputs': proc } 

    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ 
        1) Use feature extraction model
        2) Update embedding gallery
        3) Store updated ID for tracklets
        """
        preproc_inputs = self.preprocess(inputs, **kwargs)
        per_frame_data = preproc_inputs['inputs']
        
        for frame_data in per_frame_data:
            feats = frame_data['features']
            tracks = frame_data['tracks']
            crops = frame_data['crops']
            
            # update gallery & assign/update track IDs
            updated_ids = []
            tids = self.gallery.match(feats, tracks['frame_id'])
            if tids is None: 
                for feat in feats: # register single track into the gallery
                    tid = self.gallery.register(feat, tracks['frame_id'])
                    updated_ids.append(tid)
            else:
                updated_ids = tids
            
            self.frame_id += 1
            self.gallery.prune(self.frame_id)
            
            # store back in tracks
            tracks.update({ "reid_ids" : updated_ids}) # update ReID IDs
            tracks.update({ "crops": crops}) # append crops
            tracks.update({ "features": feats}) # append features
        
            logging.debug(f'Frame {self.frame_id}: {len(crops)} crops -> {len(set(updated_ids))} ReID IDs')
            logging.debug(f"Old IDs: {tracks['track_ids']}")
            logging.debug(f"New IDs: {tracks['reid_ids']}")
        
            self.state.append(tracks)
        return self.state
    

class Gallery:
    """ Stores encoded track feature vectors and matches new features against them. """
    def __init__(self, threshold=0.7, max_missed=100):
        self.threshold = threshold
        self.max_missed = max_missed
        self.next_id = 1
        self.features = {}       # pid -> list[features] (append history)
        self.last_seen = {}      # pid -> frame_idx

    def match(self, feats: np.ndarray, frame_id: int) -> Optional[int]:
        """ Given some feature vector, match it to the mean gallery features & return matched_id or None. """
        if not self.features: return None # (N,D)
        # compute cosine similarity between feat and the mean feature of each id
        gallery_means = np.array([np.mean(feats_, axis=0) for feats_ in self.features.values()])
        if len(gallery_means.shape) == 3: gallery_means = np.squeeze(gallery_means, axis=0)
        sims = cosine_similarity(feats, gallery_means) # (N, K)
        
        best_indices = np.argmax(sims, axis=1)  # (N,)
        best_sims = sims[np.arange(len(feats)), best_indices]
        
        matched_pids = []
        gallery_pids = list(self.features.keys())
        
        for i, (best_idx, best_sim) in enumerate(zip(best_indices, best_sims)):
            if best_sim >= self.threshold:
                pid = gallery_pids[best_idx]
                self.features[pid].append(feats[i])  # add new feature to the gallery
                self.last_seen[pid] = frame_id
                matched_pids.append(pid)
            else:
                matched_pids.append(None)
        
        return matched_pids
        
    def register(self, feat: np.ndarray, frame_id: int) -> int:
        """ Register new track ID. """
        pid = self.next_id
        self.next_id += 1
        self.features[pid] = [feat]
        self.last_seen[pid] = frame_id
        return pid

    def prune(self, frame_id: int):
        """ Removes stale tracks that have not been seen for more than max_missed frames. """
        stale = [pid for pid, last in self.last_seen.items()
                     if frame_id - last > self.max_missed]
        for pid in stale:
            del self.features[pid]
            del self.last_seen[pid]