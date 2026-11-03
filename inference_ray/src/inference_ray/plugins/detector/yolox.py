import logging
from utils.model_paths import checked_model_path
import torch
import torch.nn.functional as F
import numpy as np
from typing import Any, Dict, List


def model_path_name(exp) -> str:
    return getattr(exp, "exp_name", type(exp).__name__)


@staticmethod
def xyxy_to_xywh(xyxy):
    xyxy = np.asarray(xyxy)
    if xyxy.ndim == 1:
        x1, y1, x2, y2 = xyxy
        return np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5, x2 - x1, y2 - y1], dtype=xyxy.dtype)
    x1, y1, x2, y2 = xyxy[:, 0], xyxy[:, 1], xyxy[:, 2], xyxy[:, 3]
    return np.stack(((x1 + x2) * 0.5, (y1 + y2) * 0.5, x2 - x1, y2 - y1), axis=-1)


@staticmethod
def xyxy_to_xywh_tensor(xyxy: torch.Tensor) -> torch.Tensor:
    if xyxy.ndim == 1:
        xyxy = xyxy.unsqueeze(0)
    x1, y1, x2, y2 = xyxy[:, 0], xyxy[:, 1], xyxy[:, 2], xyxy[:, 3]
    cx = (x1 + x2) * 0.5
    cy = (y1 + y2) * 0.5
    w = x2 - x1
    h = y2 - y1
    return torch.stack((cx, cy, w, h), dim=-1)


def load_checkpoint(path: str, device: str) -> Dict[str, Any]:
    """ ``torch.load`` without arbitrary unpickling: weights only, plus the numpy scalars YOLOX's trainer stores
    (``best_ap``, ``curr_ap``; pickled as ``numpy.core.multiarray.scalar`` by numpy 1). """
    allowed = [np.dtype, *[getattr(np.dtypes, n) for n in dir(np.dtypes) if n.endswith("DType")]]
    if int(np.__version__.split(".")[0]) >= 2:
        from numpy._core.multiarray import scalar
    else:
        from numpy.core.multiarray import scalar
    allowed += [scalar, (scalar, "numpy.core.multiarray.scalar")]
    with torch.serialization.safe_globals(allowed):
        return torch.load(path, map_location=device, weights_only=True)


class YoloX():
    """
    YOLOX detector wrapper for inference.
    Source: https://github.com/Megvii-BaseDetection/YOLOX

    Any YOLOX checkpoint loads: the architecture (depth, width, number of classes) and the input convention
    (``input_format``: legacy RGB / 255 / ImageNet mean-std, or BGR 0-255, ``yolox_input.py``) are read from it.
    ``model_path`` (an exp name, e.g. ``yolox-x``) picks the model family.
    """
    def __init__(
        self,
        model_path: str,
        image_size: tuple[int, int],
        detector_params: Dict [Any, Any],
        **kwargs,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.state = list()
        self.img_id = 0
        
        self.detector_params = detector_params
        
        from yolox.exp import get_exp
        self.exp = get_exp(None, model_path)
        
        self.checkpoint = detector_params.get("checkpoint", None)
        if self.checkpoint:
            self.checkpoint = checked_model_path(self.checkpoint)
        self.w, self.h = image_size

        # ImageNet norm constants of the legacy input
        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

        self._init_inference(detector_params)

    def _init_inference(self, cfg: Dict[Any, Any]):
        """
        Build and prepare the model for inference:
          - loads architecture from exp
          - restores weights from checkpoint (strict)
          - sets eval mode and disables internal decoding
        """
        from .yolox_input import FORMATS, architecture, state_input_format

        self.cfg = cfg
        self.conf_thresh = self.cfg["conf_thresh"]
        self.nms_thresh = self.cfg["nms_thresh"]

        self.classes = [int(c) for c in self.cfg.get('classes', [])]
        if not self.classes:
            raise RuntimeError("Expected at least 1 class to detect, please check the 'classes' args.")
        if not self.checkpoint:
            raise ValueError("YOLOX needs a checkpoint (detector_params.checkpoint); random weights detect nothing.")

        logging.info(f"[inference] Loading checkpoint: {self.checkpoint}")
        chkpt = load_checkpoint(self.checkpoint, self.device)
        state_dict = chkpt.get("model", chkpt) if isinstance(chkpt, dict) else chkpt
        if all(k.startswith("module.") for k in state_dict):  # saved from DistributedDataParallel
            state_dict = {k[len("module."):]: v for k, v in state_dict.items()}

        # architecture from the weights, so a checkpoint of another size than the exp's default loads too
        arch = architecture(state_dict)
        if (self.exp.depth, self.exp.width) != (arch["depth"], arch["width"]):
            logging.info(f"[inference] {self.checkpoint}: depth {arch['depth']}, width {arch['width']} "
                         f"(exp '{model_path_name(self.exp)}' defaults to {self.exp.depth}, {self.exp.width}).")
        self.exp.depth, self.exp.width = arch["depth"], arch["width"]
        self.exp.num_classes = self.num_classes = arch["num_classes"]
        if self.cfg.get("num_classes") not in (None, self.num_classes):
            logging.warning(f"[inference] num_classes {self.cfg['num_classes']} ignored: the checkpoint has "
                            f"{self.num_classes} classes.")
        unknown = [c for c in self.classes if not 0 <= c < self.num_classes]
        if unknown:
            raise ValueError(f"classes {unknown} do not exist in {self.checkpoint} ({self.num_classes} classes).")

        # input convention: the checkpoint's input_format tag (a converted checkpoint), else its stem statistics; an
        # explicit setting must agree (the wrong one gives hundreds of low-score boxes per frame instead of an error)
        tag = chkpt.get("input_format") if isinstance(chkpt, dict) else None
        if tag is not None and tag not in FORMATS:
            raise ValueError(f"{self.checkpoint}: unknown input_format tag {tag!r}.")
        detected, source = (tag, "its input_format tag") if tag else (state_input_format(state_dict)[0],
                                                                       "its stem statistics")
        wanted = self.cfg.get("input_format") or "auto"
        if wanted not in ("auto", *FORMATS):
            raise ValueError(f"input_format must be auto, legacy or bgr255, got {wanted!r}.")
        if wanted != "auto" and wanted != detected:
            raise ValueError(f"{self.checkpoint} expects {detected} input ({source}), but input_format is {wanted}.")
        self.input_format = detected
        logging.info(f"[inference] YOLOX checkpoint input: {detected} ({source}).")

        # test_size must match the training input_size exactly
        self.test_size = self.exp.test_size # default is determined by exp
        if "test_size" in self.cfg:
            if self.cfg["test_size"]:
                self.test_size = tuple(self.cfg["test_size"])
                self.exp.test_size = self.test_size
        else:
            logging.warning(
                "No test_size in inference_params -> using exp default "
                f"{self.test_size}. Make sure this matches your training input_size."
            )
        logging.info(
            f"[inference] " 
            f"test_size={self.test_size}, "
            f"num_classes={self.num_classes}, "
            f"conf={self.conf_thresh}, nms={self.nms_thresh}"
        )

        # build model; strict=True still catches another family (tiny / nano: depthwise convs)
        self.model = self.exp.get_model().to(self.device)
        self.model.load_state_dict(state_dict, strict=True)
        logging.info("[inference] Checkpoint loaded successfully.")

        # fp16 after checkpoint load so the cast doesn't affect weight loading
        self.fp16 = bool(cfg.get("fp16", False) and self.device.startswith("cuda"))
        if self.fp16:
            self.model = self.model.half()
            logging.info("[inference] Model cast to fp16.")

        # eval mode + disable internal decoding (we call decode_outputs manually)
        self.model.eval()
        if hasattr(self.model, "head"):
            self.model.head.training = False
            self.model.head.decode_in_inference = False

    def _prepare_frames_tensor(self, frames):
        if isinstance(frames, np.ndarray):
            frames = torch.from_numpy(frames)
        elif not isinstance(frames, torch.Tensor):
            raise TypeError(f"Unsupported frame type: {type(frames)}")
        if frames.ndim == 3:
            frames = frames.unsqueeze(0)
        if frames.ndim != 4:
            raise RuntimeError(f"Expected input shape (N,H,W,C) or (H,W,C), got {tuple(frames.shape)}")
        if frames.shape[-1] != 3:
            raise RuntimeError(f"Expected 3-channel RGB input, got shape {tuple(frames.shape)}")
        return frames

    def _letterbox_torch(self, img_chw: torch.Tensor, out_h: int, out_w: int, pad_value: float = 114.0):
        c, h, w = img_chw.shape
        ratio = min(out_h / h, out_w / w)
        # truncated, as yolox.data.data_augment.preproc
        new_h = max(1, int(h * ratio))
        new_w = max(1, int(w * ratio))

        resized = F.interpolate(
            img_chw.unsqueeze(0),
            size=(new_h, new_w),
            mode="bilinear",
            align_corners=False,
        ).squeeze(0)

        padded = torch.full(
            (c, out_h, out_w),
            pad_value,
            dtype=resized.dtype,
            device=resized.device,
        )
        padded[:, :new_h, :new_w] = resized
        return padded, float(ratio)

    def _preprocess_torch(self, frames: torch.Tensor, target_device: torch.device):
        frames = frames.contiguous()
        input_shape = frames.shape
        self.h, self.w = int(input_shape[1]), int(input_shape[2])
        self.det_shape = (self.h, self.w)
        self.frame_shape = (self.h, self.w)  # boxes are scaled back to frame pixels in run_inference

        if frames.dtype != torch.float32 and frames.dtype != torch.float16:
            frames = frames.float()
        else:
            frames = frames.to(dtype=torch.float32)

        if frames.device != target_device:
            if target_device.type == "cuda" and frames.device.type == "cpu":
                frames = frames.pin_memory().to(target_device, non_blocking=True)
            else:
                frames = frames.to(target_device)

        frames = frames.permute(0, 3, 1, 2).contiguous()

        out_h, out_w = self.test_size
        processed_list: List[torch.Tensor] = []
        ratios: List[float] = []

        mean = torch.tensor(self.rgb_means, device=target_device, dtype=torch.float32).view(3, 1, 1)
        std = torch.tensor(self.std, device=target_device, dtype=torch.float32).view(3, 1, 1)

        for img_chw in frames:
            pimg, ratio = self._letterbox_torch(img_chw, out_h, out_w, pad_value=114.0)
            if self.input_format == "legacy":
                # ValTransform(legacy=True): RGB, /255, ImageNet mean / std (YOLOX <= 0.1.0, ByteTrack, MixSort)
                pimg = (pimg / 255.0 - mean) / std
            else:
                # ValTransform(legacy=False): BGR 0-255, cv2.imread's channel order (YOLOX 0.1.1rc0, the SoccerNet fine-tunes)
                pimg = pimg.flip(0)
            processed_list.append(pimg)
            ratios.append(ratio)

        images = torch.stack(processed_list, dim=0).contiguous()
        if self.fp16:
            images = images.to(dtype=torch.float16)

        return {
            "inputs": images,
            "shape": (self.h, self.w, 3),
            "ratio": ratios,
            "orig_hw": (self.h, self.w),
        }

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        frames = self._prepare_frames_tensor(inputs["frame"])
        target_device = torch.device(self.device)
        return self._preprocess_torch(frames, target_device)

    @torch.no_grad()
    def run_inference(self, inputs):
        from yolox.utils import postprocess

        images = inputs["inputs"]

        # if images.device.type == "cuda": torch.cuda.synchronize()
        raw = self.model(images)

        def _decode_outputs(raw):
            """ Custom CUDA-compatible implementation of YOLOX model head decode_outputs(). """
            grids = []
            strides = []
            
            device = raw.device
            dtype = raw.dtype
            
            for (hsize, wsize), stride in zip(self.model.head.hw, self.model.head.strides):
                yv, xv = torch.meshgrid(
                    torch.arange(hsize, device=device),
                    torch.arange(wsize, device=device),
                    indexing="ij",
                )
                grid = torch.stack((xv, yv), dim=2).view(1, -1, 2)
                grids.append(grid)
                
                shape = grid.shape[:2]
                stride_tensor = torch.full((*shape, 1), stride, device=device, dtype=dtype)
                strides.append(stride_tensor)

            grids = torch.cat(grids, dim=1).to(device=device, dtype=dtype)
            strides = torch.cat(strides, dim=1).to(device=device, dtype=dtype)

            raw = raw.clone()
            raw[..., :2] = (raw[..., :2] + grids) * strides
            raw[..., 2:4] = torch.exp(raw[..., 2:4]) * strides
            return raw

        # NOTE: Might also move back raw computations to cpu, since YOLOX does not support "on-CUDA" decode_outputs().
        # if raw.device.type == "cuda":
        #    raw = raw.detach().cpu()
        # if images.device.type == "cuda": torch.cuda.synchronize()
        # decoded = self.model.head.decode_outputs(raw, dtype=raw.dtype)
        self.hw = [
            (images.shape[2] // stride, images.shape[3] // stride)
            for stride in self.model.head.strides
        ]
        decoded = _decode_outputs(raw)

        # if images.device.type == "cuda": torch.cuda.synchronize()
        raw_outputs = postprocess(
            decoded, self.num_classes, self.conf_thresh, self.nms_thresh
        )
        # if images.device.type == "cuda": torch.cuda.synchronize()

        img_h, img_w = inputs["orig_hw"]

        for pred, ratio in zip(raw_outputs, inputs["ratio"]):
            if pred is None or pred.numel() == 0:
                self.state.append([])
                self.img_id += 1
                continue

            if not np.isfinite(ratio) or ratio < 1e-6:
                logging.warning("Invalid ratio=%s, skipping frame %s", ratio, self.img_id)
                self.state.append([])
                self.img_id += 1
                continue

            pred = pred.clone()

            scaling_factor = 1.0 / ratio
            pred[:, [0, 2]] *= scaling_factor
            pred[:, [1, 3]] *= scaling_factor

            pred[:, 0].clamp_(0, img_w)
            pred[:, 1].clamp_(0, img_h)
            pred[:, 2].clamp_(0, img_w)
            pred[:, 3].clamp_(0, img_h)

            xyxy = pred[:, :4]
            xywh = xyxy_to_xywh_tensor(xyxy)

            pred_cpu = pred.detach().cpu()
            xyxy_cpu = xyxy.detach().cpu().numpy()
            xywh_cpu = xywh.detach().cpu().numpy()

            # rows are x1, y1, x2, y2, obj_conf, cls_conf, cls; the score postprocess thresholds
            # is obj * cls, not cls_conf alone
            bbox_list = [
                {
                    "xyxy": xyxy_cpu[i],
                    "xywh": xywh_cpu[i],
                    "cls_id": int(pred_cpu[i, -1].item()),
                    "conf": float(pred_cpu[i, 4].item() * pred_cpu[i, 5].item()),
                }
                for i in range(pred_cpu.shape[0])
                if torch.isfinite(pred_cpu[i, :4]).all()
                and int(pred_cpu[i, -1].item()) in self.classes
            ]

            self.state.append(bbox_list)
            self.img_id += 1

        return raw_outputs