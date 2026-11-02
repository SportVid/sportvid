"""Offline refinement of a finished player-track state (``Tracker.finalize``), ported from trak's
``trak/tracker/refine.py``. Both work on top of any player tracker and are configured in its parameters
(``gta_link`` / ``interpolation``, each with ``enabled``).

- ``GTALink``: GTA-Link (Sun et al., ACCV-W 2024, MIT, vendored in ``third_party/gta_link``) splits tracklets whose
  appearance clusters into several identities and connects tracklets of the same identity.
- ``Interpolation``: linear interpolation of short gaps, re-implementing the behaviour of Deep-EIoU's
  ``tools/sport_interpolation.py`` (that repository has no license, so none of its code is used).
"""

import logging
from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .tracker import track_frame

logger = logging.getLogger(__name__)


def build_refiners(params: Dict[str, Any], device: str) -> Tuple[Optional["GTALink"], Optional["Interpolation"]]:
    gta_cfg = dict(params.get('gta_link') or {})
    interp_cfg = dict(params.get('interpolation') or {})
    gta = GTALink(gta_cfg, device) if gta_cfg.pop('enabled', False) else None
    interp = Interpolation(interp_cfg) if interp_cfg.pop('enabled', False) else None
    return gta, interp


def _frames_from_tracks(tracks: Dict[int, List], num_frames: int, scores=None) -> List[Dict[str, Any]]:
    """ {track_id: [(frame, tlwh), ...]} -> per-frame track dicts (ids ascending within a frame). """
    per_frame = defaultdict(list)
    for tid, rows in tracks.items():
        for frame, box in rows:
            per_frame[int(frame)].append((tid, box))
    state = []
    for f in range(num_frames):
        rows = sorted(per_frame.get(f, []), key=lambda r: r[0])
        ids = [r[0] for r in rows]
        sc = [scores.get((f, tid), 1.0) if scores else 1.0 for tid in ids]
        state.append(track_frame(f, [r[1] for r in rows], ids, sc))
    return state


class GTALink:
    """Embeds every output box while its frame is in memory (``observe``), then splits and connects the
    tracklets over the whole clip (``refine``), as GTA-Link's ``generate_tracklets.py`` + ``refine_tracklets.py``.

    As in trak: the boxes come from the tracker state instead of a MOT file; output IDs are renumbered 1..N in
    sorted order and every score is 1 (upstream's ``save_results``); upstream always runs the connect step.
    """

    DEFAULTS = {'use_split': True, 'min_len': 100, 'eps': 0.6, 'min_samples': 10, 'max_k': 3,
                'use_connect': True, 'spatial_factor': 1.0, 'merge_dist_thres': 0.4}

    def __init__(self, cfg: Dict[str, Any], device: str):
        from .appearance import ReIDEncoder
        cfg = dict(cfg)
        model_path = cfg.pop('model_path')
        model_name = cfg.pop('model_name', 'osnet_ain_x1_0')
        amp = cfg.pop('amp', False)
        self.encoder = ReIDEncoder(model_path, device, model_name=model_name, amp=amp)
        self.cfg = SimpleNamespace(**{**self.DEFAULTS, **cfg})
        if not (self.cfg.use_split or self.cfg.use_connect):
            raise ValueError("gta_link: use_split and use_connect are both false; upstream requires at least one.")
        self.reset()

    def reset(self):
        self.features = {}  # (frame, track_id) -> L2-normalised embedding

    def observe(self, frame_idx: int, track_results: Dict[str, Any], frame_rgb: np.ndarray):
        from .appearance import to_xyxy
        boxes = np.asarray(track_results['track_boxes'], dtype=np.float32).reshape(-1, 4)
        if len(boxes) == 0:
            return
        feats = self.encoder(frame_rgb, to_xyxy(boxes))
        for tid, feat in zip(track_results['track_ids'], feats):
            self.features[(frame_idx, int(tid))] = feat / np.linalg.norm(feat)

    def refine(self, state: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from gta_link.Tracklet import Tracklet
        from gta_link import refine_tracklets as rt

        tracklets = {}
        missing = 0
        for f, fr in enumerate(state):
            for tid, score, box in zip(fr['track_ids'], fr['track_scores'], fr['track_boxes']):
                feat = self.features.get((f, int(tid)))
                if feat is None:  # no pixels were available for this frame
                    missing += 1
                    continue
                tid = int(tid)
                bbox = [float(v) for v in box]
                if tid not in tracklets:
                    tracklets[tid] = Tracklet(tid, f, float(score), bbox)
                else:
                    tracklets[tid].append_det(f, float(score), bbox)
                tracklets[tid].append_feat(feat)
        if missing:
            logger.warning("[gta_link] %d track boxes had no embedding and were dropped.", missing)
        if not tracklets:
            return state

        c = self.cfg
        n_in = len(tracklets)
        max_x_range, max_y_range = rt.get_spatial_constraints(tracklets, c.spatial_factor)
        if c.use_split:
            tracklets = rt.split_tracklets(tracklets, eps=c.eps, max_k=c.max_k,
                                           min_samples=c.min_samples, len_thres=c.min_len)
        n_split = len(tracklets)
        dist = rt.get_distance_matrix(tracklets)
        merged = rt.merge_tracklets(tracklets, {}, dist, seq_name='sportvid', max_x_range=max_x_range,
                                    max_y_range=max_y_range, merge_dist_thres=c.merge_dist_thres)
        logger.info("[gta_link] tracklets: %d in, %d after split, %d after connect.", n_in, n_split, len(merged))

        out = {i + 1: list(zip(merged[tid].times, merged[tid].bboxes)) for i, tid in enumerate(sorted(merged))}
        return _frames_from_tracks(out, len(state))


class Interpolation:
    """Fills gaps shorter than ``n_dti`` frames in tracks with more than ``n_min`` boxes by linear interpolation of
    the tlwh box, unless the box centre moves more than ``distance_thres`` px across the gap. A (frame, id) pair
    that occurs more than once is dropped first (all its boxes). Existing boxes keep their score, interpolated
    ones get 1 (trak; Deep-EIoU's script writes -1 for every box)."""

    def __init__(self, cfg: Dict[str, Any]):
        self.n_min = int(cfg.get('n_min', 5))
        self.n_dti = int(cfg.get('n_dti', 20))
        self.distance_thres = float(cfg.get('distance_thres', 200))

    def refine(self, state: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = defaultdict(list)    # (frame, id) -> [(tlwh, score)]
        for f, fr in enumerate(state):
            for tid, score, box in zip(fr['track_ids'], fr['track_scores'], fr['track_boxes']):
                rows[(f, int(tid))].append((np.asarray(box, dtype=np.float64), float(score)))
        if not rows:
            return state
        tracks = defaultdict(list)  # id -> [(frame, tlwh)] in frame order
        scores = {}
        for (f, tid), entries in sorted(rows.items()):
            if len(entries) == 1:
                tracks[tid].append((f, entries[0][0]))
                scores[(f, tid)] = entries[0][1]

        n_before, n_far = len(scores), 0
        for tid, seq in tracks.items():
            if len(seq) <= self.n_min:
                continue
            filled = []
            for (f0, b0), (f1, b1) in zip(seq[:-1], seq[1:]):
                if not 1 < f1 - f0 < self.n_dti:
                    continue
                c0, c1 = b0[:2] + b0[2:] / 2, b1[:2] + b1[2:] / 2
                if np.linalg.norm(c1 - c0) > self.distance_thres:
                    n_far += 1
                    continue
                for f in range(f0 + 1, f1):
                    filled.append((f, (f - f0) * (b1 - b0) / (f1 - f0) + b0))
            seq.extend(filled)
        out = _frames_from_tracks(tracks, len(state), scores)
        logger.info("[interpolation] %d -> %d track boxes (%d gaps not filled: the box moved too far).",
                    n_before, sum(len(fr['track_ids']) for fr in out), n_far)
        return out
