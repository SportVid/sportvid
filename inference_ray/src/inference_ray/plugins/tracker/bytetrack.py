import logging
import numpy as np
from typing import Dict, Any, List

from .tracker import Tracker, track_frame, detections_xyxy_conf


class ByteTrack(Tracker):
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
        super().__init__(tracker_params, device, **kwargs)
        from types import SimpleNamespace
        self.args = SimpleNamespace(**self.tracker_params)
        self._build()

    def _build(self):
        from yolox.tracker.basetrack import BaseTrack
        from yolox.tracker.byte_tracker import BYTETracker
        # track ids come from a class-level counter: reset it, or a second run in the same Ray replica would
        # continue the numbering of the first (and the analyser cache assumes one input gives one output)
        BaseTrack._count = 0
        # track_buffer is given in frames at 30 fps (upstream's convention): BYTETracker keeps a lost track for
        # frame_rate / 30 * track_buffer decoded frames, i.e. the same time at any decoding rate
        frame_rate = float(getattr(self.args, "frame_rate", 30) or 30)
        self.tracker = BYTETracker(args=self.args, frame_rate=frame_rate)
        # at least one frame: at low rates the scaled buffer rounds down to 0 (a lost track would be dropped at once)
        self.tracker.buffer_size = self.tracker.max_time_lost = max(1, self.tracker.buffer_size)
        logging.info(f"ByteTrack: lost tracks kept for {self.tracker.max_time_lost} frames "
                     f"({self.tracker.max_time_lost / frame_rate:.1f} s at {frame_rate:g} fps).")

    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        """ Brings the detections into the (N, 5) [x1, y1, x2, y2, conf] arrays BYTE consumes. """
        dets = inputs.get('detections') or []
        return {
            'detections': [detections_xyxy_conf(d) for d in dets],
            'frames': inputs.get('frames') or [None] * len(dets),   # BYTE needs no pixels; GTA-Link does
            'shape': inputs['image_shape'],
            'det_shape': inputs['det_shape'],
        }

    def process(self, inputs: Dict[Any, Any], **kwargs) -> List[Dict[str, Any]]:
        prep = self.preprocess(inputs, **kwargs)
        img_shape = prep['shape']
        det_shape = prep['det_shape']

        for detection, frame in zip(prep['detections'], prep['frames']):
            # a frame without detections still goes through update, so lost tracks age there
            online_targets = self.tracker.update(
                detection,      # [N,x1,y1,x2,y2,conf]
                img_shape,      # original image shape [H,W]
                det_shape       # (H_model, W_model) -> detections coordinate space
            )

            tlwhs, ids, scores = [], [], []
            for tar in online_targets:
                tlwh = tar.tlwh
                vertical = tlwh[2] / tlwh[3] > self.args.aspect_ratio_thresh
                if tlwh[2] * tlwh[3] > self.args.min_box_area and not vertical:
                    tlwhs.append(tlwh)
                    ids.append(tar.track_id)
                    scores.append(tar.score.item())
            self._record(track_frame(self.frame_id, tlwhs, ids, scores), frame)

        logging.debug(f"ByteTrack: {self.frame_id} frames tracked.")
        return self.state

    def reset_state(self):
        super().reset_state()
        self._build()
