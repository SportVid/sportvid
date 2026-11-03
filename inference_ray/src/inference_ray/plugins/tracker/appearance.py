"""Appearance embeddings for the trackers (Deep-EIoU, GTA-Link), team clustering and ReID."""

import logging
from typing import Optional, Tuple

import numpy as np
import torch

from utils.model_paths import checked_model_path

logger = logging.getLogger(__name__)

# torchvision < 0.12 named the ViT MLP layers linear_1 / linear_2 (the sportsreid ViT-B checkpoint); now 0 / 3
_LEGACY_KEYS = ((".mlp.linear_1.", ".mlp.0."), (".mlp.linear_2.", ".mlp.3."))


def reid_input_size(model_name: str) -> Optional[Tuple[int, int]]:
    """The (h, w) input an architecture requires, or None for any size (OSNet, trained at 256x128). The sportsreid
    DeiTs / ViTs were trained at 224x224 (position embeddings of 14x14 patches)."""
    return (224, 224) if model_name.startswith(("deit", "vit")) else None


def load_reid_weights(model: torch.nn.Module, model_path: str) -> None:
    """Load a torchreid checkpoint into ``model``. Unlike torchreid's ``load_pretrained_weights``, which silently
    keeps the initial (ImageNet) weights of every layer whose name or shape differs, this fails unless every layer
    but the identity classifier (trained on another dataset's ids) is loaded."""
    from torchreid.utils import load_checkpoint
    ckpt = load_checkpoint(model_path)
    state = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
    own = model.state_dict()
    loaded = {}
    for k, v in state.items():
        k = k[7:] if k.startswith("module.") else k
        for old, new in _LEGACY_KEYS:
            k = k.replace(old, new)
        if k in own and own[k].shape == v.shape:
            loaded[k] = v
    missing = [k for k in own if k not in loaded and not k.startswith("classifier.")]
    if missing:
        raise ValueError(f"[reid] {model_path} does not fit {type(model).__name__}: {len(missing)} of {len(own)} "
                         f"tensors not loaded, e.g. {missing[:3]} (wrong model_name?)")
    own.update(loaded)
    model.load_state_dict(own)


class ReIDEncoder:
    """A torchreid model (OSNet-AIN by default) embedding boxes of an RGB frame.

    Preprocessing as Deep-EIoU's SportsMOT embeddings and GTA-Link's ``generate_tracklets.py``: a PIL crop of the
    RGB frame (boxes reaching outside the image are padded black), resize to 256x128 (224x224 for DeiT / ViT),
    ImageNet normalisation, no feature normalisation (the trackers L2-normalise). Resizing is a per-crop PIL op;
    ToTensor + Normalize run batched on the device.
    """

    def __init__(self, model_path: str, device: str = "cuda", model_name: str = "osnet_ain_x1_0",
                 batch_size: int = 64, amp: bool = False):
        import torchvision.transforms as T
        from torchreid.models import build_model

        self.device = device if torch.cuda.is_available() else "cpu"
        self.batch_size = batch_size
        size = reid_input_size(model_name)
        self.resize = T.Resize(list(size or (256, 128)))
        self.mean = torch.tensor([0.485, 0.456, 0.406], device=self.device).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225], device=self.device).view(1, 3, 1, 1)
        model_path = checked_model_path(model_path)
        model = build_model(model_name, num_classes=1, pretrained=False, use_gpu=self.device.startswith("cuda"),
                            **({"img_size": size} if size else {}))
        load_reid_weights(model, model_path)
        self.model = model.eval().to(self.device)
        self.feature_dim = int(getattr(self.model, "feature_dim", 512))
        # fp16 autocast (CUDA only)
        self.amp = bool(amp) and self.device.startswith("cuda")
        logger.info(f"ReIDEncoder: {model_name} from {model_path} on {self.device} (amp={self.amp}).")

    @torch.no_grad()
    def __call__(self, frame_rgb: np.ndarray, boxes_xyxy: np.ndarray) -> np.ndarray:
        """(N, D) float32 embeddings of ``boxes_xyxy`` (frame pixels) in an HWC uint8 RGB frame."""
        from PIL import Image

        boxes_xyxy = np.asarray(boxes_xyxy, dtype=np.float64).reshape(-1, 4)
        if len(boxes_xyxy) == 0:
            return np.empty((0, self.feature_dim), dtype=np.float32)
        img = Image.fromarray(frame_rgb)
        crops = np.stack([np.asarray(self.resize(img.crop(tuple(b)).convert("RGB"))) for b in boxes_xyxy])
        crops = torch.from_numpy(crops).to(self.device).permute(0, 3, 1, 2).float().div_(255.0)
        crops = (crops - self.mean) / self.std
        return self.embed_crops(crops, normalized=True)

    @torch.no_grad()
    def embed_crops(self, crops: torch.Tensor, normalized: bool = False) -> np.ndarray:
        """(N, D) float32 embeddings of an (N, 3, H, W) RGB crop batch on the device, in [0, 255] (as
        ``roi_crops`` gives it) or already ImageNet-normalised."""
        if len(crops) == 0:
            return np.empty((0, self.feature_dim), dtype=np.float32)
        if not normalized:
            crops = (crops / 255.0 - self.mean) / self.std
        with torch.autocast("cuda", dtype=torch.float16, enabled=self.amp):
            feats = [self.model(crops[i:i + self.batch_size]).float() for i in range(0, len(crops), self.batch_size)]
        return torch.cat(feats).cpu().numpy().astype(np.float32)


def roi_windows(boxes_tlwh, img_hw: Tuple[int, int], offsets=(0.0, 0.0, 0.0, 0.0),
                min_w: float = 0.0, min_h: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """Crop windows ``(N, 4)`` x1, y1, x2, y2 of tlwh boxes and the mask of boxes that crop, in float32: a box crops unless w / h <= 0, w < ``min_w``,
    h < ``min_h``, or it is empty after the fractional ``offsets`` (x1, y1, x2, y2) and clipping to the image. Needs
    only the geometry, so the boxes to sample are known before any frame is decoded."""
    b = np.asarray(boxes_tlwh, dtype=np.float32).reshape(-1, 4)
    x1, y1, w, h = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    ox1, oy1, ox2, oy2 = (float(o) for o in offsets)
    invalid = (w <= 0) | (h <= 0) | (w < min_w) | (h < min_h)
    nx1 = x1 + w * np.float32(ox1)
    ny1 = y1 + h * np.float32(oy1)
    nx2 = nx1 + w * np.float32(1.0 + ox2)
    ny2 = ny1 + h * np.float32(1.0 + oy2)
    nx1, ny1 = np.maximum(nx1, np.float32(0)), np.maximum(ny1, np.float32(0))
    nx2, ny2 = np.minimum(nx2, np.float32(img_hw[1])), np.minimum(ny2, np.float32(img_hw[0]))
    valid = ~(invalid | (nx2 <= nx1) | (ny2 <= ny1))
    return np.stack([nx1, ny1, nx2, ny2], axis=1).astype(np.float32), valid


def roi_crops(frame_rgb: np.ndarray, windows_xyxy: np.ndarray, out_hw: Tuple[int, int], device: str) -> torch.Tensor:
    """(N, 3, H, W) float crops in [0, 255] of ``roi_windows`` windows (valid ones only) of an HWC uint8 RGB frame,
    bilinear-sampled by ``roi_align`` (not a PIL crop + resize: values differ slightly)."""
    from torchvision.ops import roi_align
    windows = torch.as_tensor(np.asarray(windows_xyxy, dtype=np.float32).reshape(-1, 4), device=device)
    if len(windows) == 0:
        return torch.empty((0, 3, *out_hw), device=device)
    frame = torch.from_numpy(np.ascontiguousarray(frame_rgb)).to(device).permute(2, 0, 1)[None].float()
    rois = torch.cat([torch.zeros((len(windows), 1), device=device), windows], dim=1)
    return roi_align(frame, rois, output_size=tuple(out_hw), spatial_scale=1.0, sampling_ratio=2, aligned=True)


def to_xyxy(tlwh: np.ndarray) -> np.ndarray:
    tlwh = np.asarray(tlwh, dtype=np.float64).reshape(-1, 4)
    return np.concatenate([tlwh[:, :2], tlwh[:, :2] + tlwh[:, 2:]], axis=1)
