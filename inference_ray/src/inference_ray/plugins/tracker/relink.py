"""Constrained re-linking of the pieces of a crossing cut (``crossings.py``), 
in place of GTA-Link's connect step (``refine.GTALink``, ``gta_link.relink``).

GTA-Link's connect step (``gta_link.refine_tracklets.merge_tracklets``) is a greedy agglomerative clustering: the
closest pair of tracklet groups by mean cosine distance merges first, as long as it is below a threshold and the
two never share a frame. Its spatial check compares exit and entry points with the *whole image range* of all boxes
(``spatial_factor`` 1), so in practice it never rejects a pair. 

``relink`` keeps that clustering and adds:
- ``team``: a cannot-link rule. Each piece's team is a K=2 KMeans on the pieces' mean embeddings; a group's team is
  the length-weighted vote of its pieces, and groups whose votes disagree confidently (margin >= ``team_margin``)
  never merge.
- ``reassign``: the greedy merge leaves mixed leftover groups (pieces of several players chained together) that share
  frames with every player's main group, so the no-overlap rule keeps their pieces out of it. The groups of at least
  ``anchor_min_frames`` frames stay as anchors, the others are dissolved, and each of their pieces joins the closest
  anchor it may join (``_reassign``).

With both off, ``relink`` gives exactly GTA-Link's connect step (whose spatial check never rejects at
``spatial_factor`` >= 1, and is not reproduced).
"""

import heapq
from dataclasses import dataclass

import numpy as np


@dataclass
class RelinkCfg:
    thres: float = 0.4                  # appearance (mean cosine distance) threshold, GTA-Link's merge_dist_thres
    team: bool = True
    team_margin: float = 0.2            # vote margin (|w0 - w1| / (w0 + w1)) for a group's team to count
    team_min_frames: int = 15           # pieces shorter than this do not vote or fit the KMeans
    reassign: bool = True
    anchor_min_frames: int = 1000       # groups at least this long are kept; the others are dissolved into pieces
    reassign_thres: float = 0.5         # a piece joins the closest feasible anchor below this mean cosine distance


def piece_teams(tracklets: dict, min_frames: int) -> dict:
    """piece -> (team 0/1, weight): KMeans K=2 on the long pieces' mean embeddings, every piece assigned."""
    from sklearn.cluster import KMeans
    ids = list(tracklets)
    mean = np.stack([np.mean(tracklets[p].features, axis=0) for p in ids])
    mean /= np.linalg.norm(mean, axis=1, keepdims=True)
    n = np.array([len(tracklets[p].times) for p in ids])
    fit = n >= min_frames
    if fit.sum() < 2:  # too few pieces to tell two teams apart
        return {}
    km = KMeans(2, n_init=10, random_state=0).fit(mean[fit], sample_weight=n[fit])
    lab = km.predict(mean)
    return {p: (int(lab[i]), float(n[i]) if fit[i] else 0.0) for i, p in enumerate(ids)}


class _Group:
    __slots__ = ("pieces", "frames", "sum", "cnt", "votes")

    def __init__(self, p, t, team):
        self.pieces = [p]
        self.frames = set(int(f) for f in t.times)
        f = np.asarray(t.features, np.float64)
        self.sum = (f / np.linalg.norm(f, axis=1, keepdims=True)).sum(0)
        self.cnt = float(len(f))
        self.votes = np.zeros(2)
        if team is not None:
            self.votes[team[0]] += team[1]

    def team(self, margin):
        w = self.votes.sum()
        if w <= 0 or abs(self.votes[0] - self.votes[1]) / w < margin:
            return None
        return int(np.argmax(self.votes))


def _feasible(a: _Group, b: _Group, c: RelinkCfg) -> bool:
    if not a.frames.isdisjoint(b.frames):
        return False
    if c.team:
        ta, tb = a.team(c.team_margin), b.team(c.team_margin)
        if ta is not None and tb is not None and ta != tb:
            return False
    return True


def _absorb(a: _Group, b: _Group):
    """Merge group ``b`` into ``a`` (``b`` is dropped by the caller)."""
    a.pieces += b.pieces
    a.frames |= b.frames
    a.sum = a.sum + b.sum
    a.cnt += b.cnt
    a.votes = a.votes + b.votes


class _Candidates:
    """The pairs of one group ``i`` (built at merge step ``created``), sorted by (distance, partner), 
    held as a buffer of the next ``size`` entries and refilled from a fresh distance row when it runs out.

    A pair is valid while its partner is alive and unchanged since ``created`` (``changed[j] <= created``); the
    group's own candidates are void once it changes, as its distances do. The initial candidates of group i are
    the pairs (i, j > i), the candidates after a merge every other group, as GTA-Link pushes them."""
    __slots__ = ("i", "created", "initial", "d", "j", "pos", "last", "complete")

    def __init__(self, i: int, created: int, initial: bool):
        self.i, self.created, self.initial = i, created, initial
        self.last = None            # (distance, partner) of the last buffered entry: the refill starts after it
        self.complete = False       # the buffer holds every remaining pair


def _agglomerate(G: list, cfg: RelinkCfg, thres: float, buffer: int = 64) -> list:
    """GTA-Link's greedy merge (closest pair first, below ``thres``, ties to the first pair) with ``_feasible`` as the
    cannot-link test; an infeasible pair is out until one of the two changes, as in GTA-Link. 
    Returns the surviving groups.

    Pushing every pair below the threshold on one heap, as GTA-Link does, takes memory and time quadratic in the
    number of groups (teammates' embeddings are close, so most pairs are below it: tens of millions of pairs for a
    90-minute match). Here the heap holds one entry per group, the closest of its ``_Candidates``; the merge order
    and result are the same, because the pairs come off in the same (distance, lower index, higher index) order and
    every distance comes from the same full-matrix product."""
    n = len(G)
    if n < 2:
        return list(G)
    alive = np.ones(n, bool)
    changed = np.zeros(n, np.int64)   # merge step at which each group last changed
    sums = np.stack([g.sum for g in G])
    cnts = np.array([g.cnt for g in G])
    index = np.arange(n)

    def dist_row(i):
        return 1.0 - (sums @ sums[i]) / (cnts * cnts[i])

    def fill(c: _Candidates):
        d = dist_row(c.i)
        ok = (d < thres) & alive & (changed <= c.created) & (index != c.i)
        if c.initial:
            ok &= index > c.i
        if c.last is not None:
            ld, lj = c.last
            ok &= (d > ld) | ((d == ld) & (index > lj))
        cand = np.flatnonzero(ok)
        if len(cand) > buffer:          # the ``buffer`` closest, with every tie at the cut-off
            cand = cand[d[cand] <= np.partition(d[cand], buffer - 1)[buffer - 1]]
            c.complete = False
        else:
            c.complete = True
        order = np.lexsort((cand, d[cand]))
        c.d, c.j, c.pos = d[cand][order], cand[order], 0
        if len(cand):
            c.last = (c.d[-1], c.j[-1])

    def head(c: _Candidates):
        """The closest valid pair left (its position in the buffer), refilling as needed; None when there is none."""
        while True:
            rest = c.j[c.pos:]
            valid = np.flatnonzero(alive[rest] & (changed[rest] <= c.created))
            if len(valid):
                c.pos += int(valid[0])
                return c.pos
            if c.complete:
                return None
            fill(c)

    heap = []

    def push(c: _Candidates):
        if head(c) is not None:
            d, j = float(c.d[c.pos]), int(c.j[c.pos])
            heapq.heappush(heap, (d, min(c.i, j), max(c.i, j), c.i, c.created))

    cands = [_Candidates(i, 0, True) for i in range(n)]
    for c in cands:
        fill(c)
        push(c)
    step = 0
    while heap:
        _, lo, hi, i, created = heapq.heappop(heap)
        c = cands[i]
        if not alive[i] or changed[i] != created:
            continue                    # the group changed since: its candidates were rebuilt
        j = hi if lo == i else lo
        if not (alive[j] and changed[j] <= created):
            push(c)                     # the partner changed after this entry was pushed: next candidate
            continue
        c.pos += 1
        if not _feasible(G[lo], G[hi], cfg):
            push(c)
            continue
        _absorb(G[lo], G[hi])           # into the lower index, as GTA-Link: the indices order later ties
        sums[lo], cnts[lo] = G[lo].sum, G[lo].cnt
        alive[hi] = False
        step += 1
        changed[lo] = step
        cands[hi] = None
        cands[lo] = c = _Candidates(lo, step, False)
        fill(c)
        push(c)
    return [g for g, a in zip(G, alive) if a]


def _reassign(groups: list, singles: dict, cfg: RelinkCfg) -> list:
    """Keep the groups of at least ``anchor_min_frames`` frames as anchors, dissolve the others into their pieces and
    give each piece, longest first, to the closest anchor (mean cosine distance < ``reassign_thres``) it is feasible
    with. The pieces no anchor takes are clustered among themselves again (``_agglomerate`` at ``thres``)."""
    anchors = [g for g in groups if len(g.frames) >= cfg.anchor_min_frames]
    loose = [singles[p]() for g in groups if len(g.frames) < cfg.anchor_min_frames for p in g.pieces]
    if not anchors:
        return groups
    loose.sort(key=lambda g: -len(g.frames))
    A = np.stack([a.sum / a.cnt for a in anchors])  # anchor mean embeddings (unnormalised sums / n)
    left = []
    for s in loose:
        d = 1.0 - A @ (s.sum / s.cnt)
        placed = False
        for k in np.argsort(d):
            if d[k] >= cfg.reassign_thres:
                break
            if _feasible(anchors[k], s, cfg):
                _absorb(anchors[k], s)
                A[k] = anchors[k].sum / anchors[k].cnt
                placed = True
                break
        if not placed:
            left.append(s)
    return anchors + _agglomerate(left, cfg, cfg.thres)


def relink(tracklets: dict, cfg: RelinkCfg) -> dict:
    """Constrained agglomerative linking of {piece: gta_link Tracklet}, then the optional reassignment. 
    Returns {group: [(frame, tlwh), ...]}, groups numbered from 1."""
    teams = piece_teams(tracklets, cfg.team_min_frames) if cfg.team else {}
    singles = {p: (lambda p=p: _Group(p, tracklets[p], teams.get(p))) for p in tracklets}
    groups = _agglomerate([singles[p]() for p in tracklets], cfg, cfg.thres)
    if cfg.reassign:
        groups = _reassign(groups, singles, cfg)
    out = {}
    for g in groups:
        rows = [(f, b) for p in g.pieces for f, b in zip(tracklets[p].times, tracklets[p].bboxes)]
        out[len(out) + 1] = sorted(rows, key=lambda r: r[0])
    return out
