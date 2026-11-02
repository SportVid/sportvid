"""Appearance embeddings for the trackers (Deep-EIoU, GTA-Link), ported from trak's ``trak/tracker/appearance.py``."""

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
        # fp16 autocast: ~3x faster for the transformers, cosine to fp32 >= 0.99999 (trak, GT crops)
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
        with torch.autocast("cuda", dtype=torch.float16, enabled=self.amp):
            feats = [self.model(crops[i:i + self.batch_size]).float() for i in range(0, len(crops), self.batch_size)]
        return torch.cat(feats).cpu().numpy().astype(np.float32)


def to_xyxy(tlwh: np.ndarray) -> np.ndarray:
    tlwh = np.asarray(tlwh, dtype=np.float64).reshape(-1, 4)
    return np.concatenate([tlwh[:, :2], tlwh[:, :2] + tlwh[:, 2:]], axis=1)
