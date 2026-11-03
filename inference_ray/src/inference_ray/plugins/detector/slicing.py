"""
SAHI-style sliced inference (Akyon et al., "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection",
https://arxiv.org/abs/2202.06934), independent of the detector backend.

A frame is cut into overlapping tiles. Each tile runs through the backend's own preprocess / run_inference, so a
tile of about the model's input size is detected at (close to) native resolution, instead of the whole frame being
shrunk to it (RF-DETR-L at 560 px turns a 13 px ball of a 1920 px frame into ~4 px). Tile boxes are shifted back
into frame pixels, optionally joined by a whole-frame pass that keeps large objects intact, and merged across
tiles. ``SlicedDetector`` wraps any detector wrapper of this package (``detector_params.sahi``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

import numpy as np

MERGE_MODES = ("nmm", "nms")
MATCH_METRICS = ("ios", "iou")


def xyxy_to_xywh(xyxy) -> np.ndarray:
    x1, y1, x2, y2 = np.asarray(xyxy, dtype=np.float64).reshape(4)
    return np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5, x2 - x1, y2 - y1])


def _pair(value: Any, name: str, cast: type) -> tuple:
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(f"sahi.{name} must be a scalar or [h, w], got {value!r}.")
        return cast(value[0]), cast(value[1])
    return cast(value), cast(value)


@dataclass(frozen=True)
class SliceConfig:
    slice_size: tuple[int, int] = (560, 560)    # (h, w) tile size in frame pixels
    overlap: tuple[float, float] = (0.2, 0.2)   # (h, w) overlap ratio of neighbouring tiles
    full_frame: bool = True                     # also detect on the whole frame (SAHI's standard prediction)
    tile_batch_size: int | None = None          # tiles per forward pass; None -> the detector's batch_size
    tile_classes: tuple[int, ...] | None = None # keep only these (raw) classes from the tiles; None -> all
    merge: str = "nmm"                          # nmm: union of matched boxes (SAHI default) | nms: keep the top box
    match_metric: str = "ios"                   # ios: intersection over the smaller box | iou
    match_threshold: float = 0.5
    class_agnostic: bool = False                # match boxes across classes

    @classmethod
    def from_cfg(cls, cfg: dict | None) -> SliceConfig | None:
        """The ``detector_params.sahi`` block as a SliceConfig, or None when it is missing or disabled."""
        if not cfg or not cfg.get("enabled", False):
            return None

        slice_size = _pair(cfg.get("slice_size", cls.slice_size), "slice_size", int)
        overlap = _pair(cfg.get("overlap", cls.overlap), "overlap", float)
        if min(slice_size) < 1:
            raise ValueError(f"sahi.slice_size must be positive, got {slice_size}.")
        if not all(0.0 <= o < 1.0 for o in overlap):
            raise ValueError(f"sahi.overlap must be in [0, 1), got {overlap}.")

        merge = str(cfg.get("merge", cls.merge)).lower()
        if merge not in MERGE_MODES:
            raise ValueError(f"sahi.merge must be one of {MERGE_MODES}, got {merge!r}.")
        metric = str(cfg.get("match_metric", cls.match_metric)).lower()
        if metric not in MATCH_METRICS:
            raise ValueError(f"sahi.match_metric must be one of {MATCH_METRICS}, got {metric!r}.")

        tile_batch_size = cfg.get("tile_batch_size")
        tile_classes = cfg.get("tile_classes")
        return cls(
            slice_size=slice_size,
            overlap=overlap,
            full_frame=bool(cfg.get("full_frame", cls.full_frame)),
            tile_batch_size=int(tile_batch_size) if tile_batch_size else None,
            tile_classes=tuple(int(c) for c in tile_classes) if tile_classes is not None else None,
            merge=merge,
            match_metric=metric,
            match_threshold=float(cfg.get("match_threshold", cls.match_threshold)),
            class_agnostic=bool(cfg.get("class_agnostic", cls.class_agnostic)),
        )


def _starts(size: int, tile: int, overlap: float) -> list[int]:
    """
    Tile offsets along one axis: as many tiles as SAHI uses for this overlap, spread evenly from border to border.
    SAHI instead steps by the nominal stride and shifts the last tile back onto the border, which can leave the
    last two tiles almost on top of each other (1920 px at 560 / 0.2: offsets 1344 and 1360); here `overlap` is
    a lower bound and the surplus is shared by all neighbours.
    """
    if tile >= size:
        return [0]
    step = max(1, tile - int(round(overlap * tile)))
    count = -(-(size - tile) // step) + 1
    return [round(k * (size - tile) / (count - 1)) for k in range(count)]


def slice_grid(
    height: int,
    width: int,
    slice_size: tuple[int, int],
    overlap: tuple[float, float],
) -> list[tuple[int, int, int, int]]:
    """
    Overlapping tiles covering a (height, width) image, as (x0, y0, x1, y1) in row-major order.

    All tiles have the same size, min(slice_size, image size) per axis, so they stack into one batch.
    """
    th, tw = min(slice_size[0], height), min(slice_size[1], width)
    return [
        (x, y, x + tw, y + th)
        for y in _starts(height, th, overlap[0])
        for x in _starts(width, tw, overlap[1])
    ]


def shift_detection(det: dict, x0: int, y0: int) -> dict:
    """A copy of a tile detection moved into frame pixels."""
    box = np.asarray(det["xyxy"], dtype=np.float64).reshape(4) + (x0, y0, x0, y0)
    return dict(det, xyxy=box, xywh=xyxy_to_xywh(box))


def _greedy_groups(boxes: np.ndarray, scores: np.ndarray, metric: str, threshold: float) -> Iterator[tuple[int, np.ndarray]]:
    """
    Greedy matching as in SAHI's greedy NMM: the best remaining box takes every remaining box that overlaps it
    by at least `threshold`. Yields (top index, member indices incl. the top).
    """
    areas = (boxes[:, 2] - boxes[:, 0]).clip(0) * (boxes[:, 3] - boxes[:, 1]).clip(0)
    free = np.ones(len(boxes), dtype=bool)
    for i in np.argsort(-scores, kind="stable"):
        if not free[i]:
            continue
        cand = np.flatnonzero(free)
        iw = (np.minimum(boxes[i, 2], boxes[cand, 2]) - np.maximum(boxes[i, 0], boxes[cand, 0])).clip(0)
        ih = (np.minimum(boxes[i, 3], boxes[cand, 3]) - np.maximum(boxes[i, 1], boxes[cand, 1])).clip(0)
        inter = iw * ih
        if metric == "ios":
            denom = np.minimum(areas[i], areas[cand])
        else:
            denom = areas[i] + areas[cand] - inter
        overlap = inter / np.maximum(denom, 1e-9)
        members = np.union1d(cand[overlap >= threshold], [i])
        free[members] = False
        yield i, members


def merge_detections(dets: list[dict], cfg: SliceConfig) -> list[dict]:
    """
    Merge the tile and whole-frame detections of one frame (all in frame pixels).

    A box cut by a tile border overlaps the full box mostly by its own area, hence the IoS default: with NMM
    the group becomes the union of its boxes (the uncut extent), with the top box's score and class; with NMS
    only the top box is kept.
    """
    if len(dets) < 2:
        return list(dets)

    boxes = np.stack([np.asarray(d["xyxy"], dtype=np.float64).reshape(4) for d in dets])
    scores = np.array([float(d["conf"]) for d in dets])
    if cfg.class_agnostic:
        classes = np.zeros(len(dets), dtype=np.int64)
    else:
        classes = np.array([-1 if d.get("cls_id") is None else int(d["cls_id"]) for d in dets])

    merged = []
    for c in np.unique(classes):
        idx = np.flatnonzero(classes == c)
        for top, members in _greedy_groups(boxes[idx], scores[idx], cfg.match_metric, cfg.match_threshold):
            det = dets[idx[top]]
            if cfg.merge == "nmm" and len(members) > 1:
                group = boxes[idx[members]]
                box = np.concatenate([group[:, :2].min(axis=0), group[:, 2:].max(axis=0)])
                det = dict(det, xyxy=box, xywh=xyxy_to_xywh(box))
            merged.append(det)

    merged.sort(key=lambda d: -float(d["conf"]))
    return merged


class SlicedDetector:
    """
    A detector wrapper (YoloX, YoloUltralytics, RFDetr, RTDetr) with sliced inference, behind the same interface:
    ``preprocess`` / ``run_inference`` append one list of detections per frame to ``state``, boxes in frame pixels
    (``frame_shape``). Every frame is cut into overlapping tiles that go through the backend's preprocess /
    run_inference like frames would, plus the whole frame when ``full_frame`` is set; the detections are moved
    into frame pixels and merged per frame.
    """

    def __init__(self, detector, cfg: SliceConfig, batch_size: int = 1):
        self.detector = detector
        self.slicing = cfg
        self.batch_size = max(1, int(batch_size or 1))
        self.state: List[List[dict]] = []
        self.img_id = 0
        self.frame_shape = getattr(detector, "frame_shape", None)
        self.det_shape = self.frame_shape
        logging.info(f"Detector sliced inference ({type(detector).__name__}): {cfg}")

    def __getattr__(self, name):
        # anything else (classes, model, ...) is the backend's
        return getattr(self.__dict__["detector"], name)

    def preprocess(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """ (N, H, W, C) uint8 RGB frames; the backend preprocesses each tile batch itself. """
        frames = inputs["frame"]
        if hasattr(frames, "detach"):
            frames = frames.detach().cpu().numpy()
        frames = np.asarray(frames)
        if frames.ndim == 3:
            frames = frames[None]
        if frames.ndim != 4 or frames.shape[-1] != 3:
            raise RuntimeError(f"Expected (H,W,C) or (N,H,W,C) RGB input, got {tuple(frames.shape)}")
        return {"frames": frames}

    def _detect_images(self, images: np.ndarray, batch_size: int) -> List[List[dict]]:
        """ Backend detections per image of an (N, H, W, C) batch, without adding them to the backend's state. """
        det = self.detector
        start, img_id = len(det.state), det.img_id
        for i in range(0, len(images), batch_size):
            det.run_inference(det.preprocess({"frame": np.ascontiguousarray(images[i:i + batch_size])}))
        dets = det.state[start:]
        del det.state[start:]
        det.img_id = img_id
        return dets

    def run_inference(self, inputs: Dict[str, Any]) -> List[List[dict]]:
        cfg = self.slicing
        frames = inputs["frames"]
        n, h, w, _ = frames.shape

        grid = slice_grid(h, w, cfg.slice_size, cfg.overlap)
        # frame-major: tile j of frame i sits at i * len(grid) + j
        tiles = np.stack([frames[i, y0:y1, x0:x1] for i in range(n) for x0, y0, x1, y1 in grid])
        tile_dets = self._detect_images(tiles, cfg.tile_batch_size or self.batch_size)
        full_dets = self._detect_images(frames, self.batch_size) if cfg.full_frame else [[] for _ in range(n)]

        # boxes are in frame pixels now, whatever input size the backend's preprocess left behind
        self.frame_shape = self.det_shape = (h, w)

        results = []
        for i in range(n):
            dets = list(full_dets[i])
            for (x0, y0, _, _), tile in zip(grid, tile_dets[i * len(grid):(i + 1) * len(grid)]):
                dets.extend(shift_detection(d, x0, y0) for d in tile
                            if cfg.tile_classes is None or d.get("cls_id") in cfg.tile_classes)
            merged = merge_detections(dets, cfg)
            self.state.append(merged)
            self.img_id += 1
            results.append(merged)
        return results
