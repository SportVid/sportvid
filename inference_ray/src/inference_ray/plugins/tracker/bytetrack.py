import logging
import numpy as np

from pprint import pprint
from typing import Dict, Any


class ByteTrack():
    """ BYTE:
    - Matches the high score detection boxes to the tracklets based on motion similarity or appearance similarity.
    - Adopts Kalman filter to predict future location of tracklets in the next frame.
    - Similarity can be computed by the IoU or Re-ID feature distance of the predicted box and the detection box.
    - First matching is performed, then second matching between unmatched tracklets, and low score detection boxes using same motion similarity.
    - Removes false-positives with no association.
    
    - Detection by tracking: Fuses the predicted boxes with the detection boxes to enhance the detection results.
        - Many occluded objects can be correctly detected but have low scores. 
        - To reduce missing detections and keep the persistence of trajectories, keep all detection boxes and associate across every of them.
    
    - Location and motion similarity are accurate in the short-range matching.
    - Appearance similarity are helpful in the long-range matching -> ReID when object was occluded
        - can be measured by the cosine similarity of the Re-ID features
        - e.g. DeepSORT -> extracts appearance features from detection boxes
        - After similarity computation, matching strategy assigns identities to the objects
    """
    
    def __init__(
        self, 
        tracker_params: Dict [Any, Any],
        device: str = "cuda",
        **kwargs
    ):
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.state = list()
        
        self.tracker_params = tracker_params
        
        from yolox.tracker.byte_tracker import BYTETracker
        self.tracker = BYTETracker(args=self.tracker_params)
        
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Brings the detection into the correct format required by BYTE. """
        if not inputs or not inputs['detections']: 
            detections = np.empty((0, 5))
        else:
            detections = []
            for det in inputs['detections']:
                det_bbox = np.array([det_['xyxy']for det_ in det]) # [N,4]
                det_scores = np.array([det_['conf'] for det_ in det]) # [N,1]
                det_merged = np.hstack([det_bbox, det_scores[:, np.newaxis]]) # [N,5]
                
                detections.append(det_merged)
        
        return dict({
            'detections': detections,
            'shape': inputs['image_shape'],
            'det_shape': inputs['det_shape']
        })
    
    def process(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        detections = self.preprocess(inputs, **kwargs)
        return self.track(detections, **kwargs)
    
    def track(self, inputs, **kwargs):
        """Runs the BYTE object tracker.

        Args: Dict[str, Any]
            'detections': np.ndarray: Shape exactly (N, 5), dtype=float32
            'shape': [int, int]
            'det_shape: [int, int]

        Returns:
            Result is a dictionary for the input detections:
                {
                    "frame_id": int,
                    "track_ids": [int],
                    "track_scores": [float],
                    "track_boxes": [np.array(top left x, top left y, width, height)],
                }
        """
        detections = inputs['detections']
        img_shape = inputs['shape']
        det_shape = inputs['det_shape']

        # logging.debug(len(detections)); logging.debug(detections[0].shape)
        # logging.info(f'img dim: {img_shape}, det dim: {det_shape}')
        
        for detection in detections:
            # reset to prevent accumulation
            online_tlwhs = []
            online_ids = []
            online_scores = []
            
            online_targets = self.tracker.update(
                detection,      # [N,x1,y1,x2,y2,conf] or [N,x1,y1,x2,y2,cls_conf,obj_conf]
                img_shape,      # original image shape [H,W]
                det_shape       # (H_model, W_model) -> detections coordinate space
            )
            # logging.debug(online_targets)

            for tar in online_targets:
                track_lwh = tar.tlwh
                track_id = tar.track_id
                
                vertical = track_lwh[2] / track_lwh[3] > self.cfg_args_dict.aspect_ratio_thresh
                if track_lwh[2] * track_lwh[3] > self.cfg_args_dict.min_box_area and not vertical:
                    online_tlwhs.append(track_lwh)
                    online_ids.append(track_id)
                    online_scores.append(tar.score.item())
            
            xywh = np.array(online_tlwhs, dtype=np.float32)
            # logging.debug(xywh.min(axis=0, keepdims=True))
            # logging.debug(xywh.max(axis=0, keepdims=True))
            
            team = np.zeros(len(online_ids), dtype=np.int8)

            track_results = {
                "frame_id": self.frame_id,
                "track_ids": online_ids,
                "track_scores": online_scores,
                "track_boxes": xywh,
                "team_ids": team
            }
            self.state.append(track_results)
            self.frame_id += 1

        return self.state
