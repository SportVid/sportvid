"""Sliced inference for players (inference_ray plugins/detector/slicing.py): running only some tiles (``tiles``) and
dropping the partial boxes at inner tile borders (``drop_border_px``)."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

# loaded by path: the detector package imports torch, which the test environment does not install
_spec = importlib.util.spec_from_file_location(
    "sahi_slicing", Path(__file__).parents[2] / "inference_ray/src/inference_ray/plugins/detector/slicing.py")
slicing = sys.modules["sahi_slicing"] = importlib.util.module_from_spec(_spec)   # registered: its dataclass needs it
_spec.loader.exec_module(slicing)
SliceConfig, SlicedDetector, at_inner_border, slice_grid = (
    slicing.SliceConfig, slicing.SlicedDetector, slicing.at_inner_border, slicing.slice_grid)

H, W = 1080, 1920
PLAYER_SAHI = {"enabled": True, "slice_size": [608, 1088], "overlap": [0.2, 0.2], "full_frame": True,
               "merge": "nms", "match_metric": "iou", "match_threshold": 0.45}


class StubBackend:
    """Records the input sizes it sees and returns the boxes ``boxes(image)`` gives, in that image's pixels."""

    def __init__(self, boxes):
        self.boxes, self.seen, self.state, self.img_id = boxes, [], [], 0

    def preprocess(self, inputs):
        return inputs

    def run_inference(self, inputs):
        for image in inputs["frame"]:
            self.seen.append(image.shape[:2])
            self.state.append([{"xyxy": np.asarray(b, float), "conf": c, "cls_id": 0} for b, c in self.boxes(image)])
            self.img_id += 1


def frame_with(marks):
    """A black frame with a white rectangle per (x0, y0, x1, y1) mark; the stub detects the marks it sees whole or cut."""
    f = np.zeros((H, W, 3), np.uint8)
    for x0, y0, x1, y1 in marks:
        f[y0:y1, x0:x1] = 255
    return f


def detect_marks(image):
    """Boxes of the white pixels per connected column run (enough for separated rectangles), clipped to the image."""
    ys, xs = np.nonzero(image[..., 0])
    if not len(xs):
        return []
    out, cols = [], np.unique(xs)
    runs = np.split(cols, np.nonzero(np.diff(cols) > 1)[0] + 1)
    for r in runs:
        m = (xs >= r[0]) & (xs <= r[-1])
        out.append(([r[0], ys[m].min(), r[-1] + 1, ys[m].max() + 1], 0.9))
    return out


def run(sahi, frame, batch_size=2):
    backend = StubBackend(detect_marks)
    det = SlicedDetector(backend, SliceConfig.from_cfg(sahi), batch_size)
    det.run_inference(det.preprocess({"frame": frame}))
    return det, backend


def test_grid_is_two_by_two_with_the_top_row_first():
    grid = slice_grid(H, W, (608, 1088), (0.2, 0.2))
    assert grid == [(0, 0, 1088, 608), (832, 0, 1920, 608), (0, 472, 1088, 1080), (832, 472, 1920, 1080)]


def test_only_the_selected_tiles_run():
    det, backend = run({**PLAYER_SAHI, "tiles": [0, 1]}, frame_with([]))
    # two tiles and the whole frame
    assert backend.seen == [(608, 1088), (608, 1088), (H, W)]
    _, backend = run(PLAYER_SAHI, frame_with([]))
    assert backend.seen == [(608, 1088)] * 4 + [(H, W)]


def test_tile_outside_the_grid_is_an_error():
    with pytest.raises(ValueError, match="tiles"):
        run({**PLAYER_SAHI, "tiles": [4]}, frame_with([]))


def test_border_fragment_is_dropped_and_the_whole_player_kept():
    # a player across tile 0's right border (x 1088) but inside tile 1 (x from 832): tile 0 sees an 8 px fragment
    # ending on its border, tile 1 and the whole frame see the player whole
    player = (1080, 100, 1110, 160)
    with_rule, _ = run({**PLAYER_SAHI, "tiles": [0, 1], "drop_border_px": 3}, frame_with([player]))
    boxes = [tuple(np.round(d["xyxy"]).astype(int)) for d in with_rule.state[-1]]
    assert boxes == [player]
    without, _ = run({**PLAYER_SAHI, "tiles": [0, 1]}, frame_with([player]))
    # without the rule NMS keeps the fragment: its IoU with the whole box is below 0.45
    assert len(without.state[-1]) == 2


def test_border_on_the_frame_edge_does_not_count():
    tile = (0, 0, 1088, 608)
    at_left_frame_edge = {"xyxy": [0, 100, 20, 160]}
    at_inner_right_border = {"xyxy": [1060, 100, 1088, 160]}
    assert not at_inner_border(at_left_frame_edge, tile, (H, W), 3)
    assert at_inner_border(at_inner_right_border, tile, (H, W), 3)
    assert not at_inner_border({"xyxy": [1060, 100, 1080, 160]}, tile, (H, W), 3)   # 8 px off the border


def test_slice_config_parses_and_checks_the_player_keys():
    cfg = SliceConfig.from_cfg({**PLAYER_SAHI, "tiles": [1, 0, 1], "drop_border_px": 3})
    assert cfg.tiles == (0, 1) and cfg.drop_border_px == 3.0
    assert SliceConfig.from_cfg(PLAYER_SAHI).tiles is None and SliceConfig.from_cfg(PLAYER_SAHI).drop_border_px is None
    for bad in ({"tiles": []}, {"tiles": [-1]}, {"drop_border_px": -1}):
        with pytest.raises(ValueError):
            SliceConfig.from_cfg({**PLAYER_SAHI, **bad})
