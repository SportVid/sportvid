import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity


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