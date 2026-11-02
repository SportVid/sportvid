import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Tracker(ABC):
    """ Interface of the player trackers run by ``object_tracker`` (same as trak's ``trak.tracker.tracker``).

    - ``process`` tracks a sequence of frames and appends one ``track_frame`` dict per input frame to ``self.state``.
    - ``finalize`` runs once after the last frame: offline refinement over the whole clip (e.g. GTA-Link,
      interpolation) replaces ``self.state`` there. The base implementation changes nothing.
    """

    def __init__(self, tracker_params: Dict[Any, Any], device: str = "cuda", **kwargs):
        import torch
        self.device = device if torch.cuda.is_available() else "cpu"
        self.tracker_params = dict(tracker_params)
        self.state: List[Dict[str, Any]] = list()
        self.frame_id = 0

    @abstractmethod
    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Bring the detections into the format the tracker consumes. """

    @abstractmethod
    def process(self, inputs: Dict[Any, Any], **kwargs) -> List[Dict[str, Any]]:
        """ Track the given frames; appends one ``track_frame`` per input frame to ``self.state``.

        Args: Dict[str, Any]
            'detections': per-frame lists of detector dicts ({'xyxy', 'xywh', 'cls_id', 'conf'})
            'image_shape': (H, W) of the video frames
            'det_shape': (H, W) of the detector's coordinate space
        """

    def finalize(self) -> List[Dict[str, Any]]:
        """ Post-hoc refinement after the last frame (the caller runs it once). """
        return self.state

    def _record(self, track_results: Dict[str, Any]) -> None:
        self.state.append(track_results)
        self.frame_id += 1

    def reset_state(self) -> None:
        self.state = list()
        self.frame_id = 0


def track_frame(frame_id: int, tlwhs, ids, scores) -> Dict[str, Any]:
    """ One frame of the tracker state; boxes are tlwh in image pixels. """
    return {
        "frame_id": frame_id,
        "track_ids": [int(i) for i in ids],
        "track_scores": [float(s) for s in scores],
        "track_boxes": np.asarray(tlwhs, dtype=np.float32).reshape(-1, 4),
    }


def detections_xyxy_conf(frame_dets) -> np.ndarray:
    """ One frame's detector dicts as (N, 5) [x1, y1, x2, y2, conf] in the detector's coordinate space. """
    if not frame_dets:
        # np.array([]) of an empty list comes out 1-D and breaks the hstack below
        return np.empty((0, 5), dtype=np.float64)
    # float64 like the arrays BYTETracker got before (float32 boxes promoted by the Python-float scores)
    boxes = np.array([np.asarray(d['xyxy']).reshape(4) for d in frame_dets], dtype=np.float64)
    scores = np.array([d['conf'] for d in frame_dets], dtype=np.float64)
    return np.hstack([boxes, scores[:, np.newaxis]])
