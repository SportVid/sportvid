import logging
import numpy as np

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set, Any
from scipy.optimize import linear_sum_assignment
from .gallery import _vec, _l2_normalize


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
    Lifecycle manager on top of ProtoGallery.

    ProtoGallery acts as an appearance storage:
      - prototype: Dict[int, np.ndarray]
      - cache: Dict[int, deque]
      - last_seen: Dict[int, int]

    This manager adds:
      - tracker_id <-> global_id mapping
      - active / lost / retired states
      - re-entry matching to lost IDs
      - one-to-one assignment over candidate subsets
    """
    def __init__(
        self,
        gallery,
        active_ttl: int = 30,
        lost_ttl: int = 300,
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

        # 1) direct continuation by tracker_id -> global_id binding
        for i, track_id in enumerate(track_ids):
            global_id = self.tracker_to_global.get(track_id)
            if global_id is None:
                unmatched_idx.append(i)
                continue

            feat_i = feats[i]
            
            # NOTE: do not need to compute this for continued tracks...
            # score_i, proto_sim_i, cache_sim_i = self.gallery._similarity_to_pid(feat_i, global_id)

            global_ids[i] = global_id
            global_scores[i] = None
            statuses[i] = "continued"

            self._refresh_identity(
                global_id=global_id,
                track_id=track_id,
                feat=feat_i,
                frame_id=frame_id,
                box_xywh=None if boxes_xywh is None else boxes_xywh[i],
                allow_gallery_update=True,
            )
            seen_globals.add(global_id)

        # 2) unmatched -> active pool
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

        # 3) unmatched -> lost pool (re-entry)
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

        # 4) create new global IDs
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

        # physically remove retired identities from ProtoGallery
        for gid in list(self.retired_ids):
            self.gallery.prototype.pop(gid, None)
            self.gallery.cache.pop(gid, None)
            self.gallery.last_seen.pop(gid, None)