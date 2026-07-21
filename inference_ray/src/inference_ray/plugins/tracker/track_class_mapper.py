import logging
import numpy as np


class TrackClassMapper:
    def __init__(self, *args, **kwargs):
        """ Persistent state across frames:
        track_id -> {
           'class': int | None,
           'class_weights': {cls_id: cumulative_weight},
        }
        """ 
        super().__init__(*args, **kwargs)
        
        self._track_class_votes = {} # track_id -> {cls_id: cumulative_weight}
        self._track_last_class = {}  # track_id -> best class so far

    def compute_iou(self, track_boxes, det_boxes):  # [N,4], [M,4] -> [N,M]
        """
        IoU matrix [N_tracks, M_dets] for multiple vs multiple boxes.
        
        Args:
            track_boxes_xyxy: [N,4] x1,y1,x2,y2
            det_boxes_xyxy: [M,4] x1,y1,x2,y2
        
        Returns:
            ious: [N,M] IoU matrix
        """
        track_boxes = np.asarray(track_boxes, dtype=np.float32)
        det_boxes = np.asarray(det_boxes, dtype=np.float32)

        if track_boxes.size == 0 or det_boxes.size == 0:
            return np.zeros((len(track_boxes), len(det_boxes)), dtype=np.float32)

        # Broadcasting: track[N,1,4] --vs.-- det[1,M,4]
        track = track_boxes[:, None, :]  # [N,1,4]
        dets = det_boxes[None, :, :]     # [1,M,4]
        
        # intersection corners
        x1 = np.maximum(track[..., 0], dets[..., 0])  # [N,M]
        y1 = np.maximum(track[..., 1], dets[..., 1])
        x2 = np.minimum(track[..., 2], dets[..., 2])
        y2 = np.minimum(track[..., 3], dets[..., 3])
        
        # intersection area
        inter_area = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)  # [N,M]
        
        # union area
        track_area = np.maximum(0.0, track[..., 2] - track[..., 0]) * np.maximum(0.0, track[..., 3] - track[..., 1])  # [N,1]
        det_area = np.maximum(0.0, dets[..., 2] - dets[..., 0]) * np.maximum(0.0, dets[..., 3] - dets[..., 1])        # [1,M]
        union_area = track_area + det_area - inter_area
        
        return inter_area / (union_area + 1e-6)  # [N,M]

    def map_tracks_to_detections(self, tracks, detections, iou_thresh=0.3):
        """ Match each track bbox to best-overlapping detection. """
        mapping = dict()
        
        for track, det in zip(tracks, detections):
            frame_id = track['frame_id']
            track_ids = track['track_ids']
            
            track_boxes_xywh = np.array(track['track_boxes'], dtype=np.float32)  # [[x1,y1,w,h],[....],]
            track_boxes_xyxy = track_boxes_xywh.copy()        # conversion (x1,y1,w,h) -> (x1,y1,x2,y2)!
            if track_boxes_xyxy.size > 0:
                track_boxes_xyxy[:, 2] += track_boxes_xywh[:, 0]  # x2 = x1 + w
                track_boxes_xyxy[:, 3] += track_boxes_xywh[:, 1]  # y2 = y1 + h
            
            if len(track_ids) == 0 or not detections:
                logging.error(f"Returning empty list since no detections are available.")
                return [{'track_id': tid, 'class': -1, 'det_idx': -1, 'iou': 0.0} for tid in track_ids]
            
            if len(det) == 0:
                per_frame_td_map = dict()
                for track_id in track_ids:
                    per_frame_td_map.update({track_id: {
                        'class': self._track_last_class.get(track_id, -1),
                        'det_idx': -1,
                        'iou': 0.0
                    }})
                mapping.update({frame_id: per_frame_td_map})
                logging.error(f"Matched 0/{len(track_ids)} tracks.")
                continue
            
            det_boxes_xyxy = np.array([det_['xyxy'] for det_ in det],  dtype=np.float32)  # [M_dets, 4]

            ious = self.compute_iou(track_boxes_xyxy, det_boxes_xyxy)  # compute IoU matrix: tracks --vs.-- dets
            
            # ----> Hungarian matching
            from scipy.optimize import linear_sum_assignment

            cost_matrix = -ious  # [35,69] # convert IoU to cost matrix (higher IoU = lower cost)
            row_ind, col_ind = linear_sum_assignment(cost_matrix)  # find optimal pairs

            # filter valid matches
            match_ious  = ious[row_ind, col_ind]
            valid_mask = match_ious > iou_thresh
            matched_tracks = row_ind[valid_mask]
            matched_dets = col_ind[valid_mask]
            
            track_to_det = {track_idx: det_idx for track_idx, det_idx in zip(matched_tracks, matched_dets)}
            
            per_frame_td_map = dict()
            for i, track_id in enumerate(track_ids):
                if track_id not in self._track_class_votes:
                    self._track_class_votes[track_id] = {}
                
                if i in track_to_det:
                    det_idx = track_to_det[i]
                    iou_val = float(ious[i, det_idx])
                    cls_id = det[det_idx].get('cls_id', -1)
                    det_score = float(det[det_idx].get('score', det[det_idx].get('conf', 1.0)))
                    
                    if cls_id is not None:
                        vote_weight = det_score * iou_val
                        prev_weight = self._track_class_votes[track_id].get(cls_id, 0.0)
                        self._track_class_votes[track_id][cls_id] = prev_weight + vote_weight

                        voted_class = max(
                            self._track_class_votes[track_id].items(),
                            key=lambda kv: kv[1]
                        )[0]
                        self._track_last_class[track_id] = voted_class
                    else:
                        voted_class = self._track_last_class.get(track_id, None)
                        
                    per_frame_td_map.update({track_id: {
                        'class': voted_class,
                        'det_idx': det_idx,
                        'iou': iou_val
                    }})    
                else:  # default values for unmatched tracks
                    per_frame_td_map.update({track_id: {
                        'class': self._track_last_class.get(track_id, -1),
                        'det_idx': -1,
                        'iou': 0.0
                    }})
            mapping.update({frame_id : per_frame_td_map})
            logging.error(f"Matched {len(matched_tracks)}/{len(track_ids)} tracks.")
            
        return mapping
