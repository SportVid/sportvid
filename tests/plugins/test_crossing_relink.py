"""Crossing cut and constrained re-linking of player tracklets (inference_ray plugins/tracker/crossings.py,
relink.py), and their configuration in GTA-Link (tracker/refine.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest

try:
    import gta_link  # noqa: F401  (the inference image installs it; the test environment uses the vendored copy)
except ImportError:
    sys.path.insert(0, str(Path(__file__).parents[2] / "inference_ray/third_party/gta_link"))

from inference_ray.plugins.tracker import crossings
from inference_ray.plugins.tracker.refine import GTALink
from inference_ray.plugins.tracker.relink import RelinkCfg, relink

N = 120                 # frames
CROSS = range(50, 70)   # the two players overlap here
EMB = {"A": np.r_[1.0, 0.0, 0.0, 0.0], "B": np.r_[0.0, 1.0, 0.0, 0.0]}


def boxes(player, f):
    """tlwh of a player: A walks right, B walks left, they overlap in CROSS."""
    x = 100 + 4 * f if player == "A" else 580 - 4 * f
    if f in CROSS:
        x = 300 + (f - 60) * 0.5 + (0 if player == "A" else 5)
    return np.array([x, 200.0, 20.0, 50.0])


def swapped_state():
    """The tracker's output: track 1 follows A until the crossing and B after it, track 2 the other way round."""
    state = []
    for f in range(N):
        a, b = (1, 2) if f < CROSS.start else (2, 1)
        state.append({"track_ids": np.array([a, b]), "track_boxes": np.stack([boxes("A", f), boxes("B", f)])})
    return state


def features(state, noise=0.01, seed=0):
    rng = np.random.default_rng(seed)
    feat = {}
    for f, fr in enumerate(state):
        for k, t in enumerate(fr["track_ids"]):
            e = EMB["A" if k == 0 else "B"] + rng.normal(0, noise, 4)
            feat[(f, int(t))] = e / np.linalg.norm(e)
    return feat


def players_of(groups):
    """Each output track -> the set of players its boxes belong to (A boxes come first in every frame)."""
    out = []
    for rows in groups.values():
        out.append({"A" if np.allclose(b, boxes("A", f)) else "B" for f, b in rows})
    return out


def test_overlap_rule_cuts_both_tracks_where_the_overlap_starts():
    state = swapped_state()
    cuts = crossings.overlap_cuts(state, 0.3, 10)
    assert cuts == {1: {CROSS.start}, 2: {CROSS.start}}
    assert crossings.overlap_cuts(state, 0.3, len(CROSS) + 1) == {}   # a shorter overlap does not cut


def test_neighbour_rule_cuts_where_a_neighbour_vanishes_for_long():
    state = swapped_state()
    for f in range(60, 80):     # track 2 lost behind track 1
        keep = state[f]["track_ids"] != 2
        state[f] = {"track_ids": state[f]["track_ids"][keep], "track_boxes": state[f]["track_boxes"][keep]}
    assert 60 in crossings.neighbour_cuts(state, 0.1, 10)[1]
    assert crossings.neighbour_cuts(state, 0.1, 21) == {}   # absent for 20 frames only


def test_cut_and_relink_undo_the_swap():
    state = swapped_state()
    feat = features(state)
    pieces, n = crossings.cut(state, 0.3, 10, 0.1, 10)
    assert n == 4
    groups = relink(crossings.build_pieces(state, pieces, feat), RelinkCfg(thres=0.4))
    assert sorted(map(sorted, players_of(groups))) == [["A"], ["B"]]
    # uncut, each track holds both players
    uncut = {t: [(f, fr["track_boxes"][k]) for f, fr in enumerate(state) for k, i in enumerate(fr["track_ids"]) if i == t]
             for t in (1, 2)}
    assert all(p == {"A", "B"} for p in players_of(uncut))


def test_tracks_sharing_a_frame_never_merge():
    state = swapped_state()
    feat = features(state)
    for k in feat:
        feat[k] = EMB["A"]          # identical appearance: only the no-overlap rule keeps them apart
    pieces, _ = crossings.cut(state, 0.3, 10)
    groups = relink(crossings.build_pieces(state, pieces, feat), RelinkCfg(thres=0.4, team=False, reassign=False))
    for rows in groups.values():
        frames = [f for f, _ in rows]
        assert len(frames) == len(set(frames))


@pytest.mark.parametrize("team", [True, False])
@pytest.mark.parametrize("reassign", [True, False])
def test_relink_switches(team, reassign):
    state = swapped_state()
    pieces, _ = crossings.cut(state, 0.3, 10)
    groups = relink(crossings.build_pieces(state, pieces, features(state)),
                    RelinkCfg(thres=0.4, team=team, reassign=reassign, anchor_min_frames=50))
    assert sorted(map(sorted, players_of(groups))) == [["A"], ["B"]]


def test_gta_link_reads_cut_and_relink():
    cut, rl = GTALink._parse_cut_relink({"enabled": True, "iou": 0.3, "min_frames": 10, "near_iou": None},
                                        {"enabled": True, "team": False}, 0.35)
    assert cut == {"thr": 0.3, "min_frames": 10, "near": None, "min_absent": 1}
    assert rl == RelinkCfg(thres=0.35, team=False)
    assert GTALink._parse_cut_relink({"enabled": False}, {"enabled": False}, 0.4) == (None, None)
    with pytest.raises(ValueError, match="merge_dist_thres"):
        GTALink._parse_cut_relink(None, {"enabled": True, "thres": 0.5}, 0.4)


def _heap_agglomerate(G, cfg, thres, feasible, absorb):
    """GTA-Link's merge as written upstream: every pair below the threshold on one heap (the reference)."""
    import heapq
    n = len(G)
    alive, version = [True] * n, [0] * n
    sums = np.stack([g.sum for g in G])
    cnts = np.array([g.cnt for g in G])

    def dist_row(i):
        return 1.0 - (sums @ sums[i]) / (cnts * cnts[i])

    heap = []
    for i in range(n):
        d = dist_row(i)
        heap += [(float(d[j]), i, int(j), 0, 0) for j in np.nonzero(d < thres)[0] if j > i]
    heapq.heapify(heap)
    order = []
    while heap:
        d, i, j, vi, vj = heapq.heappop(heap)
        if not (alive[i] and alive[j] and version[i] == vi and version[j] == vj) or not feasible(G[i], G[j], cfg):
            continue
        absorb(G[i], G[j])
        order.append((i, j))
        sums[i], cnts[i] = G[i].sum, G[i].cnt
        alive[j] = False
        version[i] += 1
        di = dist_row(i)
        for k in np.nonzero(di < thres)[0]:
            k = int(k)
            if k != i and alive[k]:
                lo, hi = (i, k) if i < k else (k, i)
                heapq.heappush(heap, (float(di[k]), lo, hi, version[lo], version[hi]))
    return order


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("buffer", [1, 3, 64])
def test_buffered_merge_equals_the_heap_merge(seed, buffer):
    from inference_ray.plugins.tracker import relink as rl
    from gta_link.Tracklet import Tracklet

    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(6, 8))           # 6 players, close embeddings as within a team
    tracklets = {}
    for p in range(1, 121):
        start, length = int(rng.integers(0, 400)), int(rng.integers(5, 60))
        t = Tracklet(p, start, 1.0, [0.0, 0.0, 1.0, 1.0])
        for f in range(start + 1, start + length):
            t.append_det(f, 1.0, [0.0, 0.0, 1.0, 1.0])
        c = centres[rng.integers(6)]
        for _ in range(length):
            t.append_feat(c + rng.normal(0, 0.6, 8))
        tracklets[p] = t
    cfg = RelinkCfg(thres=0.4, team=bool(seed % 2), reassign=False)
    teams = rl.piece_teams(tracklets, cfg.team_min_frames) if cfg.team else {}

    def groups():
        return [rl._Group(p, tracklets[p], teams.get(p)) for p in tracklets]

    def merged(G):
        return sorted(tuple(sorted(g.pieces)) for g in G)

    reference = groups()
    order = _heap_agglomerate(reference, cfg, cfg.thres, rl._feasible, rl._absorb)
    alive = set(range(len(reference))) - {j for _, j in order}
    buffered = rl._agglomerate(groups(), cfg, cfg.thres, buffer=buffer)
    assert len(order) > 20                      # the case exercises the merge
    assert merged(buffered) == merged([reference[i] for i in alive])
