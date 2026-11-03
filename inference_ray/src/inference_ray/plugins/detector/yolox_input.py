"""Input conventions of YOLOX checkpoints.

    legacy:  RGB, /255, ImageNet mean/std  - YOLOX 0.0.1 release, ByteTrack / MixSort / SportsMOT weights
    bgr255:  BGR, 0-255                    - YOLOX 0.1.1rc0 release, the SoccerNet fine-tunes

A checkpoint fed the other convention does not fail: it yields hundreds of low-score boxes per frame. The
convention a checkpoint was trained with can be read from its stem BatchNorm: running_var holds the variance of
the stem conv output on the training data, ~(255 * std)^2 ~ 3400x larger for 0-255 input (``input_format``).
A legacy checkpoint can be converted by folding the normalisation into the stem conv and BatchNorm; such a
converter tags it ``input_format: bgr255``, and the tag takes precedence.

The architecture is read from the state dict as well (``architecture``): the stem width, the number of CSP
blocks in ``dark2`` (depth) and the classifier's output channels (number of classes).
"""
from typing import Dict, Tuple

import torch
import torch.nn.functional as F

STEM = "backbone.backbone.stem.conv."
CONV_W = STEM + "conv.weight"
BN_KEYS = ("bn.weight", "bn.bias", "bn.running_mean", "bn.running_var")
MEAN = torch.tensor([0.485, 0.456, 0.406], dtype=torch.float64)   # RGB
STD = torch.tensor([0.229, 0.224, 0.225], dtype=torch.float64)
BN_EPS = 1e-3            # YOLOX sets every BatchNorm's eps to 1e-3 (init_yolo)
FORMATS = ("legacy", "bgr255")


def stem_prefix(state: Dict[str, torch.Tensor]) -> str:
    """Key prefix of the stem conv; tolerates wrappers such as 'module.' from DDP."""
    hits = [k[: -len(CONV_W)] for k in state if k.endswith(CONV_W)]
    if len(hits) != 1:
        raise ValueError(f"expected one YOLOX stem conv ('*{CONV_W}'), found {len(hits)}")
    prefix = hits[0]
    weight = state[prefix + CONV_W]
    if weight.ndim != 4 or weight.shape[1] != 12:
        raise ValueError(f"stem conv weight has shape {tuple(weight.shape)}, expected (out, 12, k, k) after Focus")
    return prefix


def stem_tensors(state: Dict[str, torch.Tensor], prefix: str) -> Dict[str, torch.Tensor]:
    return {key: state[prefix + STEM + key].detach().cpu().double() for key in ("conv.weight", *BN_KEYS)}


def focus(x: torch.Tensor) -> torch.Tensor:
    """yolox.models.network_blocks.Focus: channel k = 3 * position + colour."""
    return torch.cat((x[..., ::2, ::2], x[..., 1::2, ::2], x[..., ::2, 1::2], x[..., 1::2, 1::2]), dim=1)


def stem_forward(t: Dict[str, torch.Tensor], x: torch.Tensor, bn: bool = True) -> torch.Tensor:
    w = t["conv.weight"]
    y = F.conv2d(focus(x), w, padding=w.shape[-1] // 2)
    if not bn:
        return y
    return F.batch_norm(y, t["bn.running_mean"], t["bn.running_var"], t["bn.weight"], t["bn.bias"],
                        training=False, eps=BN_EPS)


def test_image(size: int = 128) -> torch.Tensor:
    """Deterministic smooth RGB image in [0, 255], (1, 3, size, size), float64."""
    g = torch.Generator().manual_seed(0)
    coarse = torch.rand(1, 3, 8, 8, generator=g, dtype=torch.float64)
    smooth = F.interpolate(coarse, size=(size, size), mode="bicubic", align_corners=False)
    noise = 0.05 * torch.rand(1, 3, size, size, generator=g, dtype=torch.float64)
    return (255.0 * (smooth + noise)).clamp(0, 255)


def as_legacy(rgb: torch.Tensor) -> torch.Tensor:
    return (rgb / 255.0 - MEAN.view(1, 3, 1, 1)) / STD.view(1, 3, 1, 1)


def as_bgr255(rgb: torch.Tensor) -> torch.Tensor:
    return rgb.flip(1)


def input_format(t: Dict[str, torch.Tensor]) -> Tuple[str, float]:
    """The convention the stem was trained with: the one whose conv output on the test image has the variance
    closer to running_var, and the log10 margin between the two."""
    rgb = test_image()
    dist = {}
    for name, x in (("legacy", as_legacy(rgb)), ("bgr255", as_bgr255(rgb))):
        var = stem_forward(t, x, bn=False).var(dim=(0, 2, 3))
        dist[name] = (torch.log10(var / t["bn.running_var"]).abs()).median().item()
    best, other = sorted(dist, key=dist.get)
    return best, dist[other] - dist[best]


def state_input_format(state: Dict[str, torch.Tensor]) -> Tuple[str, float]:
    """input_format() of a YOLOX state dict: ('legacy' | 'bgr255', log10 margin)."""
    return input_format(stem_tensors(state, stem_prefix(state)))


def architecture(state: Dict[str, torch.Tensor]) -> Dict[str, float]:
    """``depth`` / ``width`` multipliers and ``num_classes`` of a YOLOX state dict (CSPDarknet: stem channels
    = 64 * width, CSP blocks per stage = round(3 * depth); yolox-s/m/l/x: 0.33/0.67/1.0/1.33 x 0.5/0.75/1.0/1.25)."""
    prefix = stem_prefix(state)
    width = state[prefix + CONV_W].shape[0] / 64.0
    dark2 = prefix + "backbone.backbone.dark2.1.m."
    blocks = {k[len(dark2):].split(".")[0] for k in state if k.startswith(dark2)}
    depth = {1: 0.33, 2: 0.67, 3: 1.0, 4: 1.33}.get(len(blocks), len(blocks) / 3.0)
    cls = [v for k, v in state.items() if k.endswith("head.cls_preds.0.weight")]
    if len(cls) != 1:
        raise ValueError(f"expected one YOLOX classifier ('*head.cls_preds.0.weight'), found {len(cls)}")
    return {"depth": depth, "width": width, "num_classes": int(cls[0].shape[0])}
