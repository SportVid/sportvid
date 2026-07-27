import logging
import h5py
import torch
import numpy as np
import cv2
from pprint import pprint
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import deque
from omegaconf import OmegaConf, DictConfig
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image


def _l2_normalize(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1: 
        return x / max(np.linalg.norm(x), eps)
    elif x.ndim == 2:
        n = np.linalg.norm(x, axis=1, keepdims=True)
        return x / np.clip(n, eps, None)
    raise ValueError(f"Expected 1D or 2D array, got {x.shape}")


def _vec(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return x.reshape(-1)


@dataclass
class GlobalTrackState:
    global_id: int
    state: str = "active"   # active, lost, retired
    first_frame: int = -1
    last_frame: int = -1
    last_tracker_id: Optional[int] = None
    last_bbox_xywh: Optional[np.ndarray] = None
    hits: int = 0
    misses: int = 0
    age: int = 0
    
    
class GlobalIDManager:
    """
    Wraps an existing ProtoGallery and adds:
      - active / lost / retired lifecycle
      - tracker_id <-> global_id mapping
      - re-entry matching against lost IDs
      - one-to-one matching over subsets of gallery IDs
    """
    def __init__(
        self,
        gallery,                      # your existing ProtoGallery
        active_ttl: int = 30,        # frames until active -> lost
        lost_ttl: int = 300,         # frames until lost -> retired
        reentry_threshold: float = 0.68,
        spatial_gate_px: float = 150.0,
        use_spatial_gate: bool = True,
    ):
        self.gallery = gallery

        self.active_ttl = active_ttl
        self.lost_ttl = lost_ttl
        self.reentry_threshold = reentry_threshold
        self.spatial_gate_px = spatial_gate_px
        self.use_spatial_gate = use_spatial_gate

        self.track_states: Dict[int, GlobalTrackState] = {}

        self.active_ids: Set[int] = set()
        self.lost_ids: Set[int] = set()
        self.retired_ids: Set[int] = set()

        self.tracker_to_global: Dict[int, int] = {}
        self.global_to_tracker: Dict[int, int] = {}
        
    def _bind_tracker(self, track_id: int, global_id: int) -> None:
        prev_gid = self.tracker_to_global.get(track_id)
        if prev_gid is not None and prev_gid != global_id:
            self.global_to_tracker.pop(prev_gid, None)

        prev_tid = self.global_to_tracker.get(global_id)
        if prev_tid is not None and prev_tid != track_id:
            self.tracker_to_global.pop(prev_tid, None)

        self.tracker_to_global[track_id] = global_id
        self.global_to_tracker[global_id] = track_id

    def _unbind_global(self, global_id: int) -> None:
        tid = self.global_to_tracker.pop(global_id, None)
        if tid is not None:
            self.tracker_to_global.pop(tid, None)

    def _mark_lost(self, global_id: int) -> None:
        if global_id not in self.track_states:
            return
        st = self.track_states[global_id]
        if st.state == "lost":
            return
        st.state = "lost"
        self.active_ids.discard(global_id)
        self.lost_ids.add(global_id)
        self._unbind_global(global_id)

    def _mark_retired(self, global_id: int) -> None:
        if global_id not in self.track_states:
            return
        st = self.track_states[global_id]
        if st.state == "retired":
            return
        st.state = "retired"
        self.active_ids.discard(global_id)
        self.lost_ids.discard(global_id)
        self.retired_ids.add(global_id)
        self._unbind_global(global_id)

    def _create_identity(
        self,
        track_id: int,
        feat: np.ndarray,
        frame_id: int,
        box_xywh: Optional[np.ndarray] = None,
    ) -> int:
        global_id = self.gallery.register(feat, frame_id)

        self.track_states[global_id] = GlobalTrackState(
            global_id=global_id,
            state="active",
            first_frame=frame_id,
            last_frame=frame_id,
            last_tracker_id=track_id,
            last_bbox_xywh=None if box_xywh is None else np.asarray(box_xywh, dtype=np.float32).copy(),
            hits=1,
            misses=0,
            age=1,
        )
        self.active_ids.add(global_id)
        self._bind_tracker(track_id, global_id)
        return global_id

    def _refresh_identity(
        self,
        global_id: int,
        track_id: int,
        feat: np.ndarray,
        frame_id: int,
        box_xywh: Optional[np.ndarray] = None,
        allow_gallery_update: bool = True,
    ) -> None:
        st = self.track_states[global_id]
        st.last_frame = frame_id
        st.last_tracker_id = track_id
        st.last_bbox_xywh = None if box_xywh is None else np.asarray(box_xywh, dtype=np.float32).copy()
        st.hits += 1
        st.misses = 0
        st.age += 1

        if allow_gallery_update:
            feat = _l2_normalize(x=_vec(feat))
            score, _, _ = self.gallery._similarity_to_pid(feat, global_id)
            if score >= self.gallery.update_threshold:
                self.gallery._update_identity(global_id, feat, frame_id)
            else:
                self.gallery.last_seen[global_id] = frame_id

        if st.state == "lost":
            st.state = "active"
            self.lost_ids.discard(global_id)
            self.active_ids.add(global_id)

        self._bind_tracker(track_id, global_id)

    def _passes_spatial_gate(
        self,
        det_box_xywh: Optional[np.ndarray],
        global_id: int,
        frame_id: int,
    ) -> bool:
        if not self.use_spatial_gate:
            return True
        if det_box_xywh is None:
            return True
        if global_id not in self.track_states:
            return True

        st = self.track_states[global_id]
        if st.last_bbox_xywh is None:
            return True

        gap = frame_id - st.last_frame
        if gap > self.active_ttl:
            return True

        x1, y1, w1, h1 = det_box_xywh
        x2, y2, w2, h2 = st.last_bbox_xywh

        c1 = np.array([x1 + w1 / 2.0, y1 + h1 / 2.0], dtype=np.float32)
        c2 = np.array([x2 + w2 / 2.0, y2 + h2 / 2.0], dtype=np.float32)

        dist = float(np.linalg.norm(c1 - c2))
        return dist <= self.spatial_gate_px

    def _match_subset(
        self,
        feats: np.ndarray,
        boxes_xywh: Optional[List[np.ndarray]],
        candidate_ids: List[int],
        frame_id: int,
        threshold: float,
        margin: float,
        apply_spatial_gate: bool,
    ) -> Tuple[Dict[int, int], Dict[int, float]]:
        """ Subset matching against the gallery. """
        matches: Dict[int, int] = {}
        scores_out: Dict[int, float] = {}

        if feats is None or len(feats) == 0 or len(candidate_ids) == 0:
            return matches, scores_out

        feats = _l2_normalize(np.asarray(feats, dtype=np.float32))
        n = len(feats)
        m = len(candidate_ids)

        score_matrix = np.full((n, m), -1.0, dtype=np.float32)

        for i, feat in enumerate(feats):
            for j, gid in enumerate(candidate_ids):
                if apply_spatial_gate:
                    box_i = None if boxes_xywh is None else boxes_xywh[i]
                    if not self._passes_spatial_gate(box_i, gid, frame_id):
                        continue
                score, _, _ = self.gallery._similarity_to_pid(feat, gid)
                score_matrix[i, j] = score

        row_ind, col_ind = linear_sum_assignment(score_matrix, maximize=True)

        for i, j in zip(row_ind, col_ind):
            best_score = float(score_matrix[i, j])
            if best_score < threshold:
                continue

            second_score = -1.0
            if m > 1:
                row_scores = score_matrix[i].copy()
                row_scores[j] = -np.inf
                second_score = float(np.max(row_scores))

            if m > 1 and (best_score - second_score) < margin:
                continue

            matches[i] = candidate_ids[j]
            scores_out[i] = best_score

        return matches, scores_out

    def update(
        self,
        frame_id: int,
        track_ids: List[int],
        feats: np.ndarray,
        boxes_xywh: Optional[List[np.ndarray]] = None,
    ) -> Tuple[List[Optional[int]], List[Optional[float]], List[str]]:
        """ Main update logic -> this is the method the external process() calls. """
        if feats is None or len(feats) == 0:
            self.prune(frame_id)
            return [], [], []

        feats = _l2_normalize(np.asarray(feats, dtype=np.float32))
        n = len(feats)

        global_ids: List[Optional[int]] = [None] * n
        global_scores: List[Optional[float]] = [None] * n
        statuses: List[str] = ["unmatched"] * n

        seen_globals: Set[int] = set()
        unmatched_idx: List[int] = []

        # 1) Continue already-linked tracker IDs
        for i, track_id in enumerate(track_ids):
            global_id = self.tracker_to_global.get(track_id)
            if global_id is None:
                unmatched_idx.append(i)
                continue

            global_ids[i] = global_id
            global_scores[i] = None
            statuses[i] = "continued"

            self._refresh_identity(
                global_id=global_id,
                track_id=track_id,
                feat=feats[i],
                frame_id=frame_id,
                box_xywh=None if boxes_xywh is None else boxes_xywh[i],
                allow_gallery_update=True,
            )
            seen_globals.add(global_id)

        # 2) Match remaining detections to unused active identities
        active_candidates = [gid for gid in self.active_ids if gid not in seen_globals]

        if unmatched_idx and active_candidates:
            sub_feats = np.stack([feats[i] for i in unmatched_idx], axis=0)
            sub_boxes = None if boxes_xywh is None else [boxes_xywh[i] for i in unmatched_idx]

            matches, scores = self._match_subset(
                feats=sub_feats,
                boxes_xywh=sub_boxes,
                candidate_ids=active_candidates,
                frame_id=frame_id,
                threshold=self.gallery.match_threshold,
                margin=self.gallery.margin,
                apply_spatial_gate=True,
            )

            for local_i, global_id in matches.items():
                i = unmatched_idx[local_i]
                track_id = track_ids[i]

                global_ids[i] = global_id
                global_scores[i] = scores[local_i]
                statuses[i] = "matched_active"

                self._refresh_identity(
                    global_id=global_id,
                    track_id=track_id,
                    feat=feats[i],
                    frame_id=frame_id,
                    box_xywh=None if boxes_xywh is None else boxes_xywh[i],
                    allow_gallery_update=True,
                )
                seen_globals.add(global_id)

        unmatched_idx = [i for i in range(n) if global_ids[i] is None]

        # 3) Match remaining detections to lost identities (re-entry)
        lost_candidates = list(self.lost_ids)

        if unmatched_idx and lost_candidates:
            sub_feats = np.stack([feats[i] for i in unmatched_idx], axis=0)
            sub_boxes = None if boxes_xywh is None else [boxes_xywh[i] for i in unmatched_idx]

            matches, scores = self._match_subset(
                feats=sub_feats,
                boxes_xywh=sub_boxes,
                candidate_ids=lost_candidates,
                frame_id=frame_id,
                threshold=self.reentry_threshold,
                margin=self.gallery.margin,
                apply_spatial_gate=False,
            )

            for local_i, global_id in matches.items():
                i = unmatched_idx[local_i]
                track_id = track_ids[i]

                global_ids[i] = global_id
                global_scores[i] = scores[local_i]
                statuses[i] = "reid_reentry"

                self._refresh_identity(
                    global_id=global_id,
                    track_id=track_id,
                    feat=feats[i],
                    frame_id=frame_id,
                    box_xywh=None if boxes_xywh is None else boxes_xywh[i],
                    allow_gallery_update=True,
                )
                seen_globals.add(global_id)

        unmatched_idx = [i for i in range(n) if global_ids[i] is None]

        # 4) Create new global IDs for anything still unmatched
        for i in unmatched_idx:
            track_id = track_ids[i]
            global_id = self._create_identity(
                track_id=track_id,
                feat=feats[i],
                frame_id=frame_id,
                box_xywh=None if boxes_xywh is None else boxes_xywh[i],
            )
            global_ids[i] = global_id
            global_scores[i] = None
            statuses[i] = "new"
            seen_globals.add(global_id)

        self.prune(frame_id)
        return global_ids, global_scores, statuses

    def prune(self, frame_id: int) -> None:
        """ Manage lifecycle of track identities. """
        # active -> lost
        for gid in list(self.active_ids):
            st = self.track_states[gid]
            if frame_id - st.last_frame > self.active_ttl:
                self._mark_lost(gid)

        # lost -> retired
        for gid in list(self.lost_ids):
            st = self.track_states[gid]
            if frame_id - st.last_frame > self.lost_ttl:
                self._mark_retired(gid)

        # remove retired identities from ProtoGallery stores
        for gid in list(self.retired_ids):
            self.gallery.prototype.pop(gid, None)
            self.gallery.cache.pop(gid, None)
            self.gallery.last_seen.pop(gid, None)


class Gallery:
    """ Stores encoded track feature vectors and matches new features against them. """
    def __init__(self, threshold=0.7, max_missed=100):
        self.threshold = threshold
        self.max_missed = max_missed
        self.next_id = 1
        self.features = {}       # pid -> list[features] (append history)
        self.last_seen = {}      # pid -> frame_idx

    def match(self, feats: np.ndarray, frame_id: int) -> Optional[int]:
        """ Given some feature vector, match it othe mean gallery features & return matched_id or None. """
        if not self.features: return None # (N,D)
        # compute cosine similarity between feat and the mean feature of each id
        gallery_means = np.array([np.mean(feats_, axis=0) for feats_ in self.features.values()])
        if len(gallery_means.shape) == 3: gallery_means = np.squeeze(gallery_means, axis=0)
        # computes similarities for the whole batch
        sims = cosine_similarity(feats, gallery_means) # (N, K)
        
        best_indices = np.argmax(sims, axis=1)  # (N,)
        best_sims = sims[np.arange(len(feats)), best_indices]
        
        matched_pids = []
        gallery_pids = list(self.features.keys())
        
        for i, (best_idx, best_sim) in enumerate(zip(best_indices, best_sims)):
            # accept any best match above the threshold & append the feature immediately
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


class ProtoGallery:
    """ Online ReID gallery with:
        - L2-normalized features.
        - One EMA prototype per identity.
        - One recent-feature cache per identity.
        - Conservative update policy with match/update thresholds.
        - Ambiguity margin on best vs second-best score.
    """
    def __init__(
        self,
        match_threshold: float = 0.72,
        update_threshold: float = 0.82,
        max_missed: int = 100,
        ema_alpha: float = 0.95,
        cache_size: int = 20,
        margin: float = 0.03,
        prototype_weight: float = 0.7,
        cache_weight: float = 0.3,
    ):
        self.match_threshold = match_threshold # rejects low-score matches
        self.update_threshold = update_threshold
        self.max_missed = max_missed
        self.ema_alpha = ema_alpha
        self.cache_size = cache_size
        self.margin = margin # rejects ambiguous matches when best and second-best are too close
        self.prototype_weight = prototype_weight
        self.cache_weight = cache_weight
        
        self.next_id = 1
        
        self.prototype: Dict[int, np.ndarray] = {}
        self.cache: Dict[int, deque] = {}
        self.last_seen: Dict[int, int] = {}      # pid -> frame_idx

    def _similarity_to_pid(self, feat: np.ndarray, pid: int):
        feat = _vec(feat)
        proto = _vec(self.prototype[pid])
        proto_sim = float(np.dot(feat, proto))

        cached = self.cache[pid]
        if len(cached) > 0:
            cached_feats = np.stack([_vec(f) for f in cached], axis=0)
            cache_sim = float(np.max(cached_feats @ feat))
        else:
            cache_sim = proto_sim

        score = self.prototype_weight * proto_sim + self.cache_weight * cache_sim
        return score, proto_sim, cache_sim

    def _update_identity(self, pid: int, feat: np.ndarray, frame_id: int):
        feat = _l2_normalize(x=_vec(feat))
        new_proto = self.ema_alpha * self.prototype[pid] + (1.0 - self.ema_alpha) * feat
        self.prototype[pid] = _l2_normalize(_vec(new_proto))
        self.cache[pid].append(feat)
        self.last_seen[pid] = frame_id

    def match_one(self, feat: np.ndarray, frame_id: int):
        feat = _l2_normalize(x=_vec(feat))

        logging.error(f"feat shape={feat.shape}")
        logging.error(f"num ids in gallery={len(self.prototype)}")

        if not self.prototype:
            return None, None

        pids = list(self.prototype.keys())
        
        for pid in pids:
            score, proto_sim, cache_sim = self._similarity_to_pid(feat, pid)
            logging.error(
                f"pid={pid} score={score:.4f} proto={proto_sim:.4f} cache={cache_sim:.4f} "
                f"proto_shape={self.prototype[pid].shape}"
            )
        
        scores = np.array([self._similarity_to_pid(feat, pid)[0] for pid in pids], dtype=np.float32)

        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        second_score = -1.0
        if len(scores) > 1:
            tmp = scores.copy()
            tmp[best_idx] = -np.inf
            second_score = float(np.max(tmp))

        if best_score < self.match_threshold:
            return None, best_score

        if len(scores) > 1 and (best_score - second_score) < self.margin:
            return None, best_score

        pid = pids[best_idx]

        if best_score >= self.update_threshold:
            self._update_identity(pid, feat, frame_id)

        logging.error(
            f"best={best_score:.3f}, second={second_score:.3f}, "
            f"match_th={self.match_threshold:.3f}, margin={self.margin:.3f}"
        )

        return pid, best_score

    def match(self, feats: np.ndarray, frame_id: int) -> Tuple[List[Optional[int]], List[Optional[float]]]:
        matched_pids: List[Optional[int]] = []
        matched_scores: List[Optional[float]] = []

        if feats is None or len(feats) == 0:
            return matched_pids, matched_scores

        feats = _l2_normalize(np.asarray(feats, dtype=np.float32))
        n = len(feats)

        if not self.prototype:
            matched_pids = [None] * n
            matched_scores = [None] * n
            return matched_pids, matched_scores

        pids = list(self.prototype.keys())
        m = len(pids)

        score_matrix = np.full((n, m), -1.0, dtype=np.float32)
        proto_matrix = np.full((n, m), -1.0, dtype=np.float32)
        cache_matrix = np.full((n, m), -1.0, dtype=np.float32)

        for i, feat in enumerate(feats):
            for j, pid in enumerate(pids):
                score, proto_sim, cache_sim = self._similarity_to_pid(feat, pid)
                score_matrix[i, j] = score
                proto_matrix[i, j] = proto_sim
                cache_matrix[i, j] = cache_sim

        row_ind, col_ind = linear_sum_assignment(score_matrix, maximize=True)

        matched_pids = [None] * n
        matched_scores = [None] * n

        for i, j in zip(row_ind, col_ind):
            best_score = float(score_matrix[i, j])

            second_score = -1.0
            if m > 1:
                row_scores = score_matrix[i].copy()
                row_scores[j] = -np.inf
                second_score = float(np.max(row_scores))

            if best_score < self.match_threshold:
                continue

            if m > 1 and (best_score - second_score) < self.margin:
                continue

            pid = pids[j]
            matched_pids[i] = pid
            matched_scores[i] = best_score

            if best_score >= self.update_threshold:
                self._update_identity(pid, feats[i], frame_id)

        return matched_pids, matched_scores

    def assign(self, feat: np.ndarray, frame_id: int) -> Tuple[int, Optional[float], bool]:
        pid, score = self.match_one(feat, frame_id)
        if pid is None:
            pid = self.register(feat, frame_id)
            return pid, score, True
        return pid, score, False

    def register(self, feat: np.ndarray, frame_id: int):
        feat = _l2_normalize(x=_vec(feat))
        pid = self.next_id
        self.next_id += 1
        self.prototype[pid] = feat
        self.cache[pid] = deque([feat], maxlen=self.cache_size)
        self.last_seen[pid] = frame_id
        return pid

    def prune(self, frame_id: int):
        stale = [pid for pid, last in self.last_seen.items() if frame_id - last > self.max_missed]
        for pid in stale:
            del self.prototype[pid]
            del self.cache[pid]
            del self.last_seen[pid]