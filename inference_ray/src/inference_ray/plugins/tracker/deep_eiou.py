"""Deep-EIoU (Huang et al., "Iterative Scale-Up ExpansionIoU and Deep Features Association for Multi-Object
Tracking in Sports", WACV-W 2024), re-implemented for SportVid.
The upstream repository (hsiangwei0903/Deep-EIoU) has no license, so none of its code is used here.

* Association compares a track's *last detection box* with the detections, both enlarged by the expansion
  scale (Expansion IoU), not a motion prediction. High-score detections are matched in two iterations with
  growing expansion (0.7, then 0.8); the IoU cost is fused with the cosine distance of the appearance
  embeddings (halved, gated by ``appearance_thresh`` and by ``proximity_thresh`` on the EIoU cost).
* Low-score detections (``track_low_thresh`` < score < ``track_high_thresh``) are matched to the tracks still
  unmatched by EIoU alone (expansion 0.5, cost <= 0.5); tracks lost in the first round take no part in the
  second iteration or this round.
* Unconfirmed tracks (a new track from a frame other than the first) are confirmed by a match in the next
  frame or removed; new tracks start from unmatched detections >= ``new_track_thresh``.
* The constant-velocity Kalman filter (center x, y, width, height) is initiated on activation and corrected only
  when a lost track is re-found; no prediction step runs. Its box is used only to drop duplicate tracked / lost
  pairs (IoU > 0.85). Output boxes are the last detection boxes (``last_tlwh``).
* Expanded boxes grow by floor((2 e + 1) * size / 2) on each side, and IoU uses the inclusive pixel convention
  (+1 on widths and heights), as the evaluated version did.
* The appearance embedding of a track is an exponential moving average (0.9) of its L2-normalised detection
  embeddings.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import scipy.linalg
from scipy.spatial.distance import cdist

from .tracker import Tracker, track_frame, detections_xyxy_conf

logger = logging.getLogger(__name__)

TRACKED, LOST, REMOVED = 1, 2, 4


# ---------------------------------------------------------------------------------------------------------------
# geometry and assignment
def _expand_xyxy(boxes: np.ndarray, e: float) -> np.ndarray:
    """(N, 4) xyxy boxes enlarged on each side by floor((2 e + 1) * size / 2)."""
    out = np.empty_like(boxes)
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        w, h = x2 - x1, y2 - y1
        dx, dy = (2 * w * e + w) // 2, (2 * h * e + h) // 2
        out[i] = (x1 - dx, y1 - dy, x2 + dx, y2 + dy)
    return out


def _iou_inclusive(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(N, M) IoU of xyxy boxes with inclusive pixel coordinates (+1 on widths and heights)."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float64)
    iw = np.minimum(a[:, None, 2], b[None, :, 2]) - np.maximum(a[:, None, 0], b[None, :, 0]) + 1
    ih = np.minimum(a[:, None, 3], b[None, :, 3]) - np.maximum(a[:, None, 1], b[None, :, 1]) + 1
    inter = np.where((iw > 0) & (ih > 0), iw * ih, 0.0)
    area_a = (a[:, 2] - a[:, 0] + 1) * (a[:, 3] - a[:, 1] + 1)
    area_b = (b[:, 2] - b[:, 0] + 1) * (b[:, 3] - b[:, 1] + 1)
    union = area_a[:, None] + area_b[None, :] - inter
    return np.where(inter > 0, inter / union, 0.0)


def _boxes(tracks, attr: str) -> np.ndarray:
    return np.array([getattr(t, attr) for t in tracks], dtype=np.float64).reshape(-1, 4)


def _eiou_cost(tracks, dets, e: float) -> np.ndarray:
    """1 - EIoU of the last detection boxes."""
    if not tracks or not dets:
        return np.zeros((len(tracks), len(dets)), dtype=np.float64)
    a = _expand_xyxy(_boxes(tracks, "last_xyxy"), e)
    b = _expand_xyxy(_boxes(dets, "last_xyxy"), e)
    return 1.0 - _iou_inclusive(a, b)


def _emb_cost(tracks, dets) -> np.ndarray:
    """Cosine distance of the tracks' smoothed embeddings to the detections' embeddings (>= 0)."""
    if not tracks or not dets:
        return np.zeros((len(tracks), len(dets)), dtype=np.float64)
    t = np.asarray([tr.smooth_feat for tr in tracks], dtype=np.float64)
    d = np.asarray([de.curr_feat for de in dets], dtype=np.float64)
    return np.maximum(0.0, cdist(t, d, "cosine"))


def _assign(cost: np.ndarray, thresh: float):
    """Minimum-cost assignment with pairs above ``thresh`` excluded (LAPJV with cost_limit).
    Returns (matches [(row, col)], unmatched rows, unmatched cols)."""
    if cost.size == 0:
        return [], list(range(cost.shape[0])), list(range(cost.shape[1]))
    import lap
    _, x, y = lap.lapjv(cost, extend_cost=True, cost_limit=thresh)
    matches = [(i, int(j)) for i, j in enumerate(x) if j >= 0]
    return matches, [int(i) for i in np.where(x < 0)[0]], [int(j) for j in np.where(y < 0)[0]]


# ---------------------------------------------------------------------------------------------------------------
# Kalman filter on (center x, center y, width, height) + velocities; position / velocity noise relative to size
class _BoxKalman:
    POS, VEL = 1. / 20, 1. / 160

    def __init__(self):
        self.H = np.eye(4, 8)

    def initiate(self, xywh: np.ndarray):
        mean = np.r_[xywh, np.zeros(4)]
        w, h = xywh[2], xywh[3]
        std = np.array([2 * self.POS * w, 2 * self.POS * h, 2 * self.POS * w, 2 * self.POS * h,
                        10 * self.VEL * w, 10 * self.VEL * h, 10 * self.VEL * w, 10 * self.VEL * h])
        return mean, np.diag(std ** 2)

    def update(self, mean: np.ndarray, cov: np.ndarray, xywh: np.ndarray):
        w, h = mean[2], mean[3]
        R = np.diag(np.array([self.POS * w, self.POS * h, self.POS * w, self.POS * h]) ** 2)
        S = self.H @ cov @ self.H.T + R
        c, low = scipy.linalg.cho_factor(S, lower=True, check_finite=False)
        K = scipy.linalg.cho_solve((c, low), (cov @ self.H.T).T, check_finite=False).T
        mean = mean + (xywh - self.H @ mean) @ K.T
        cov = cov - K @ S @ K.T
        return mean, cov


def _tlwh_to_xywh(tlwh: np.ndarray) -> np.ndarray:
    out = np.asarray(tlwh, dtype=np.float64).copy()
    out[:2] += out[2:] / 2
    return out


# ---------------------------------------------------------------------------------------------------------------
class _Track:
    """A detection, and once activated a track (Deep-EIoU's STrack)."""

    EMA = 0.9

    def __init__(self, tlwh, score: float, feat: Optional[np.ndarray] = None):
        self.last_tlwh = np.asarray(tlwh, dtype=np.float64)
        self.score = score
        self.mean = self.cov = None
        self.track_id = 0
        self.state = 0
        self.is_activated = False
        self.frame_id = self.start_frame = 0
        self.curr_feat = self.smooth_feat = None
        if feat is not None:
            self._add_feat(feat)

    def _add_feat(self, feat: np.ndarray) -> None:
        feat = feat / np.linalg.norm(feat)
        self.curr_feat = feat
        if self.smooth_feat is None:
            self.smooth_feat = feat
        else:
            self.smooth_feat = self.EMA * self.smooth_feat + (1 - self.EMA) * feat
        self.smooth_feat = self.smooth_feat / np.linalg.norm(self.smooth_feat)

    @property
    def last_xyxy(self) -> np.ndarray:
        b = self.last_tlwh.copy()
        b[2:] += b[:2]
        return b

    @property
    def kalman_xyxy(self) -> np.ndarray:
        """The Kalman box (before activation: the detection box)."""
        if self.mean is None:
            b = self.last_tlwh.copy()
        else:
            b = self.mean[:4].copy()
            b[:2] -= b[2:] / 2
        b[2:] += b[:2]
        return b

    def activate(self, kf: _BoxKalman, track_id: int, frame_id: int) -> None:
        self.track_id = track_id
        self.mean, self.cov = kf.initiate(_tlwh_to_xywh(self.last_tlwh))
        self.state = TRACKED
        self.is_activated = frame_id == 1     # tracks of the first frame need no confirmation
        self.frame_id = self.start_frame = frame_id

    def update(self, det: "_Track", frame_id: int) -> None:
        """A matched track; the Kalman filter is not corrected (see the module docstring)."""
        self.frame_id = frame_id
        self.last_tlwh = det.last_tlwh.copy()
        if det.curr_feat is not None:
            self._add_feat(det.curr_feat)
        self.state = TRACKED
        self.is_activated = True
        self.score = det.score

    def re_activate(self, kf: _BoxKalman, det: "_Track", frame_id: int) -> None:
        """A lost track found again: the only Kalman correction."""
        self.mean, self.cov = kf.update(self.mean, self.cov, _tlwh_to_xywh(det.last_tlwh))
        self.update(det, frame_id)


class DeepEIoUAssociation:
    """The per-frame association (one ``update`` per frame with detections)."""

    def __init__(self, params, frame_rate: float = 30):
        p = params
        self.high = float(p.track_high_thresh)
        self.low = float(p.track_low_thresh)
        self.new = float(p.new_track_thresh)
        self.match_thresh = float(p.match_thresh)
        self.proximity = float(p.proximity_thresh)
        self.appearance = float(p.appearance_thresh)
        self.with_reid = bool(p.with_reid)
        # track_buffer is given in frames at 30 fps, at least one frame (as for ByteTrack, tracker/README.md)
        self.max_time_lost = max(1, int(frame_rate / 30.0 * p.track_buffer))
        self.kf = _BoxKalman()
        self.frame_id = 0
        self.next_id = 0
        self.tracked: List[_Track] = []
        self.lost: List[_Track] = []
        self.removed_ids = set()

    def _fused_cost(self, tracks, dets, e: float) -> np.ndarray:
        iou = _eiou_cost(tracks, dets, e)
        if not self.with_reid:
            return iou
        emb = _emb_cost(tracks, dets) / 2.0
        emb[emb > self.appearance] = 1.0
        emb[iou > self.proximity] = 1.0
        return np.minimum(iou, emb)

    def update(self, dets: np.ndarray, embs: Optional[np.ndarray]) -> List[_Track]:
        """``dets``: (N, 5) [x1, y1, x2, y2, score] in pixels; ``embs``: (N, D) or None. Returns the tracked
        tracks (unconfirmed new ones included)."""
        self.frame_id += 1
        fid = self.frame_id
        activated, refound, lost, removed = [], [], [], []

        keep = dets[:, 4] > self.low
        boxes, scores = dets[keep, :4], dets[keep, 4]
        feats = embs[keep] if self.with_reid else None
        tlwh = boxes.copy()
        tlwh[:, 2:] -= tlwh[:, :2]

        def make(mask):
            return [_Track(tlwh[i], scores[i], feats[i] if feats is not None else None) for i in np.flatnonzero(mask)]

        dets_high = make(scores > self.high)
        unconfirmed = [t for t in self.tracked if not t.is_activated]
        pool = _joint([t for t in self.tracked if t.is_activated], self.lost)

        # 1) high-score detections, two iterations with growing expansion
        for it in range(2):
            cost = self._fused_cost(pool, dets_high, 0.7 + 0.1 * it)
            matches, u_track, u_det = _assign(cost, self.match_thresh)
            for i, j in matches:
                tr = pool[i]
                if tr.state == TRACKED:
                    tr.update(dets_high[j], fid)
                    activated.append(tr)
                else:
                    tr.re_activate(self.kf, dets_high[j], fid)
                    refound.append(tr)
            pool = [pool[i] for i in u_track if pool[i].state == TRACKED]
            dets_high = [dets_high[j] for j in u_det]

        # 2) low-score detections, EIoU only (a score of exactly track_high_thresh is in neither round)
        dets_low = make(scores < self.high) if len(scores) else []
        matches, u_track, _ = _assign(_eiou_cost(pool, dets_low, 0.5), 0.5)
        for i, j in matches:
            pool[i].update(dets_low[j], fid)
            activated.append(pool[i])
        for i in u_track:
            tr = pool[i]
            if tr.state != LOST:
                tr.state = LOST
                lost.append(tr)

        # 3) unconfirmed tracks
        matches, u_unconf, u_det = _assign(self._fused_cost(unconfirmed, dets_high, 0.5), 0.7)
        for i, j in matches:
            unconfirmed[i].update(dets_high[j], fid)
            activated.append(unconfirmed[i])
        for i in u_unconf:
            unconfirmed[i].state = REMOVED
            removed.append(unconfirmed[i])

        # 4) new tracks
        for j in u_det:
            det = dets_high[j]
            if det.score < self.new:
                continue
            self.next_id += 1
            det.activate(self.kf, self.next_id, fid)
            activated.append(det)

        # 5) lost tracks past the buffer
        for tr in self.lost:
            if fid - tr.frame_id > self.max_time_lost:
                tr.state = REMOVED
                removed.append(tr)

        self.tracked = _joint(_joint([t for t in self.tracked if t.state == TRACKED], activated), refound)
        self.lost = _without(self.lost, {t.track_id for t in self.tracked})
        self.lost.extend(lost)
        # the ids removed in *earlier* frames: a track removed in this frame stays in the lost pool for one more
        # frame (with state REMOVED it can still be re-found there), as in the evaluated version
        self.lost = _without(self.lost, self.removed_ids)
        self.removed_ids.update(t.track_id for t in removed)
        self.tracked, self.lost = _drop_duplicates(self.tracked, self.lost)
        return list(self.tracked)


def _joint(a: List[_Track], b: List[_Track]) -> List[_Track]:
    seen = {t.track_id for t in a}
    out = list(a)
    for t in b:
        if t.track_id not in seen:
            seen.add(t.track_id)
            out.append(t)
    return out


def _without(a: List[_Track], ids: set) -> List[_Track]:
    out = {}
    for t in a:
        out[t.track_id] = t     # a repeated id keeps the first position, the last object
    return [t for tid, t in out.items() if tid not in ids]


def _drop_duplicates(tracked: List[_Track], lost: List[_Track]):
    """Tracked / lost pairs whose Kalman boxes overlap by IoU > 0.85: the younger one goes."""
    iou = _iou_inclusive(_boxes(tracked, "kalman_xyxy"), _boxes(lost, "kalman_xyxy"))
    drop_t, drop_l = set(), set()
    for p, q in zip(*np.where(1.0 - iou < 0.15)):
        if tracked[p].frame_id - tracked[p].start_frame > lost[q].frame_id - lost[q].start_frame:
            drop_l.add(q)
        else:
            drop_t.add(p)
    return ([t for i, t in enumerate(tracked) if i not in drop_t],
            [t for i, t in enumerate(lost) if i not in drop_l])


# ---------------------------------------------------------------------------------------------------------------
class DeepEIoU(Tracker):
    """Deep-EIoU behind the ``Tracker`` interface (SportsMOT setting).

    Detections with score > ``track_low_thresh`` are embedded (``appearance.ReIDEncoder``); frames without
    detections skip the association, so tracks do not age there and no boxes are written for them (as upstream's
    ``sport_track.py``). Output boxes are the last detection boxes, filtered by ``min_box_area`` only.
    """

    def __init__(self, tracker_params: Dict[Any, Any], device: str = "cuda", **kwargs):
        super().__init__(tracker_params, device, **kwargs)
        from types import SimpleNamespace
        self.args = SimpleNamespace(**self.tracker_params)
        self.encoder = None
        if self.args.with_reid:
            from .appearance import ReIDEncoder
            self.encoder = ReIDEncoder(self.args.reid_model_path, self.device, model_name=self.args.reid_model_name,
                                       amp=getattr(self.args, "reid_amp", False))
        self._build()

    def _build(self):
        self.association = DeepEIoUAssociation(self.args, frame_rate=float(getattr(self.args, "frame_rate", 30) or 30))
        logger.info(f"Deep-EIoU: lost tracks kept for {self.association.max_time_lost} frames.")

    def preprocess(self, inputs: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        dets = inputs.get('detections') or []
        frames = inputs.get('frames') or [None] * len(dets)
        return {'detections': [detections_xyxy_conf(d) for d in dets], 'frames': frames}

    def process(self, inputs: Dict[Any, Any], **kwargs) -> List[Dict[str, Any]]:
        prep = self.preprocess(inputs)
        a = self.args
        for dets, frame in zip(prep['detections'], prep['frames']):
            if a.remove_edge_dets and len(dets):
                dets = dets[~np.any(dets[:, 0:4] < 1, axis=1)]
            embs = None
            if self.encoder is not None:
                if frame is None:
                    raise ValueError("Deep-EIoU with ReID needs the frames.")
                # rows <= track_low_thresh are dropped before their embeddings are used: embed only the rest
                embs = np.zeros((len(dets), self.encoder.feature_dim), dtype=np.float32)
                keep = dets[:, 4] > a.track_low_thresh
                if keep.any():
                    embs[keep] = self.encoder(frame, dets[keep, :4])
            online = self.association.update(dets, embs) if len(dets) else []
            tlwhs, ids, scores = [], [], []
            for t in online:
                if t.last_tlwh[2] * t.last_tlwh[3] > a.min_box_area:
                    tlwhs.append(t.last_tlwh)
                    ids.append(t.track_id)
                    scores.append(float(t.score))
            self._record(track_frame(self.frame_id, tlwhs, ids, scores), frame)
        return self.state

    def reset_state(self):
        super().reset_state()
        self._build()
