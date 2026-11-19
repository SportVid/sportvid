"""Cut player tracklets at crossings, the optional step between GTA-Link's split and 
connect (``refine.GTALink``, ``gta_link.cut``).

Where two players cross, a tracklet can continue on the other player; GTA-Link's split only catches the swaps it
sees in the appearance clusters. Two geometric rules cut every tracklet into pieces, which the connect step then
joins again by appearance:
    - *Overlap* (``iou``, ``min_frames``): every overlap episode (IoU > ``iou`` with any other box in the frame) lasting
    at least ``min_frames`` frames ends the tracklet's piece at its start.
    - *Neighbour change* (``near_iou``, off with ``None``): the detector's NMS often drops one of two crossing players,
    so a crossing shows as a box vanishing next to the track instead of a long overlap. A tracklet is cut at frame f
    when a box that overlapped it (IoU > ``near_iou``) in frame f-1 is gone in f, or when a box that was absent in f-1
    overlaps it in f (a player re-emerging, or a new track). Both the tracklet and the re-emerging one are cut. 
    The other box must stay absent for at least ``min_absent`` frames (after f-1, resp. before f), 
    so a single dropped detection between two separated players does not count.
"""

from collections import defaultdict

import numpy as np


def iou(a, B):
    """IoU of one tlwh box with each row of B."""
    x1, y1 = np.maximum(a[0], B[:, 0]), np.maximum(a[1], B[:, 1])
    x2, y2 = np.minimum(a[0] + a[2], B[:, 0] + B[:, 2]), np.minimum(a[1] + a[3], B[:, 1] + B[:, 3])
    i = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    return i / (a[2] * a[3] + B[:, 2] * B[:, 3] - i)


def overlap_cuts(state, thr: float, min_frames: int) -> dict:
    """track -> frames where an overlap episode of at least ``min_frames`` frames starts."""
    overlap = defaultdict(list)  # track -> [(frame, overlapping)]
    for fi, f in enumerate(state):
        B = np.asarray(f["track_boxes"], float).reshape(-1, 4)
        for k, t in enumerate(f["track_ids"]):
            o = np.delete(B, k, 0)
            overlap[int(t)].append((fi, bool(len(o) and iou(B[k], o).max() > thr)))
    cuts = defaultdict(set)
    for t, rows in overlap.items():
        fl = [r[1] for r in rows]
        k = 0
        while k < len(fl):
            e = k
            while e < len(fl) and fl[e]:
                e += 1
            if e - k >= min_frames:
                cuts[t].add(rows[k][0])
            k = max(e, k + 1)
    return cuts


def neighbour_cuts(state, near: float, min_absent: int) -> dict:
    """track -> frames where an overlapping box vanished since the previous frame, or one appeared next to it."""
    frames = [{int(t): np.asarray(b, float) for t, b in zip(f["track_ids"], np.asarray(f["track_boxes"]).reshape(-1, 4))}
              for f in state]
    present = defaultdict(set)
    for fi, f in enumerate(frames):
        for t in f:
            present[t].add(fi)

    def absent(t, lo, hi):  # t absent in every frame of [lo, hi]
        return not any(g in present[t] for g in range(max(lo, 0), hi + 1))

    cuts = defaultdict(set)
    for fi in range(1, len(frames)):
        prev, cur = frames[fi - 1], frames[fi]
        if not prev or not cur:
            continue
        P = np.stack(list(prev.values())); pid = list(prev)
        C = np.stack(list(cur.values())); cid = list(cur)
        vanished = [k for k, n in enumerate(pid) if n not in cur and absent(n, fi, fi + min_absent - 1)]
        appeared = [k for k, n in enumerate(cid) if n not in prev and absent(n, fi - min_absent, fi - 1)]
        for k in vanished:  # the tracks it overlapped that are still there
            ov = iou(P[k], P) > near
            for j in np.nonzero(ov)[0]:
                if j != k and pid[j] in cur:
                    cuts[pid[j]].add(fi)
        for k in appeared:  # cut both the re-emerging track and its neighbours
            ov = iou(C[k], C) > near
            ov[k] = False
            if ov.any():
                cuts[cid[k]].add(fi)
                for j in np.nonzero(ov)[0]:
                    cuts[cid[j]].add(fi)
    return cuts


def apply_cuts(state, cuts: dict):
    """New piece ids: a track's piece changes at each of its cut frames. Returns (state, number of pieces)."""
    first = {}
    for fi, f in enumerate(state):
        for t in f["track_ids"]:
            first.setdefault(int(t), fi)
    starts = {t: sorted({first[t], *(c for c in cuts.get(t, ()) if c > first[t])}) for t in first}
    piece_of, nxt = {}, 1
    for t in sorted(starts):
        for s in starts[t]:
            piece_of[(t, s)] = nxt
            nxt += 1
    out = []
    for fi, f in enumerate(state):
        ids = []
        for t in f["track_ids"]:
            s = starts[int(t)]
            ids.append(piece_of[(int(t), s[np.searchsorted(s, fi, side="right") - 1])])
        g = dict(f)
        g["track_ids"] = np.array(ids, dtype=np.int64)
        out.append(g)
    return out, nxt - 1


def cut(state, thr: float, min_frames: int, near: float | None = None, min_absent: int = 1):
    """Both rules (the neighbour-change rule only with ``near``). Returns (state with piece ids, number of pieces)."""
    cuts = overlap_cuts(state, thr, min_frames)
    if near is not None:
        for t, c in neighbour_cuts(state, near, min_absent).items():
            cuts[t] |= c
    return apply_cuts(state, cuts)


def build_pieces(src_state, pieces, feat: dict) -> dict:
    """piece id -> GTA-Link ``Tracklet`` (times, boxes, embeddings, score 1); ``pieces`` is ``src_state`` with the
    piece ids of ``cut``, ``feat`` maps (frame, source track id) to the box's embedding."""
    from gta_link.Tracklet import Tracklet
    tracklets = {}
    for fi, (src, pc) in enumerate(zip(src_state, pieces)):
        for t, p, box in zip(src["track_ids"], pc["track_ids"], src["track_boxes"]):
            p, bbox = int(p), [float(v) for v in box]
            if p not in tracklets:
                tracklets[p] = Tracklet(p, fi, 1.0, bbox)
            else:
                tracklets[p].append_det(fi, 1.0, bbox)
            tracklets[p].append_feat(feat[(fi, int(t))])
    return tracklets
