import logging
import torch
import torch.nn.functional as F
import numpy as np
from typing import Any, Dict, List


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

class YoloX():
    """
    YOLOX detector wrapper for inference.
    Source: https://github.com/Megvii-BaseDetection/YOLOX
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
        self.w, self.h = image_size

        self._init_inference(detector_params)
        
        # ImageNet norm constants for preprocessing
        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

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
        new_h = max(1, int(round(h * ratio)))
        new_w = max(1, int(round(w * ratio)))

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
            pimg = pimg / 255.0
            pimg = (pimg - mean) / std
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

            bbox_list = [
                {
                    "xyxy": xyxy_cpu[i],
                    "xywh": xywh_cpu[i],
                    "cls_id": int(pred_cpu[i, -1].item()),
                    "conf": float(pred_cpu[i, -2].item()),
                }
                for i in range(pred_cpu.shape[0])
                if torch.isfinite(pred_cpu[i, :4]).all()
            ]

            self.state.append(bbox_list)
            self.img_id += 1

        return raw_outputs

    def _init_inference(self, cfg: Dict[Any, Any]):
        """
        Build and prepare the model for inference:
          - loads architecture from exp
          - restores weights from checkpoint (strict)
          - sets eval mode and disables internal decoding
        """
        import torch
        
        self.cfg = cfg
        self.exp.num_classes = self.num_classes = cfg["num_classes"]
        self.conf_thresh = cfg["conf_thresh"]
        self.nms_thresh = cfg["nms_thresh"]

        # test_size must match the training input_size exactly
        self.test_size = self.exp.test_size # default is determined by exp
        if "test_size" in cfg:
            if cfg["test_size"]:
                self.test_size = tuple(cfg["test_size"])
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

        # build model
        self.model = self.exp.get_model().to(self.device)

        # load checkpoint
        if self.checkpoint:
            logging.info(f"[inference] Loading checkpoint: {self.checkpoint}")
            chkpt = torch.load(self.checkpoint, map_location=self.device)
            self.model.load_state_dict(chkpt["model"], strict=True) # strict=True to check for architecture mismatches
            logging.info("[inference] Checkpoint loaded successfully.")
        else:
            logging.warning(
                "[inference] No checkpoint provided -> running with random weights. "
                "Set model_chkpt in your config."
            )

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

    # NOTE: old numpy/torch mixed code...
    # @torch.no_grad()
    # def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
    #     """
    #     Letterbox-resize each frame to test_size and normalise with ImageNet stats.
    #     Args:
    #         inputs: dict with 'frame' tensor (N, H, W, C)
    #     Returns:
    #         dict with 'inputs' (model-ready tensor), 'shape', 'ratio' (list[float])
    #     """
    #     from yolox.data.data_augment import preproc

    #     # NOTE: VideoBatcher returns (N,H,W,C); VideoDecoder returns (H,W,C)
    #     inputs = inputs["frame"]
    #     fp16 = self.cfg.get("fp16", False)

    #     if len(inputs.shape) == 3:
    #         if isinstance(inputs, np.ndarray):
    #             inputs = np.expand_dims(inputs, axis=0)
    #         else:
    #             inputs = inputs.unsqueeze(0)
    #     input_shape = inputs.shape
        
    #     if input_shape[3] != 3:
    #         raise RuntimeError("Expected 3-channel RGB input.")

    #     processed = np.zeros( # (N, C, H, W)
    #         (input_shape[0], input_shape[3], self.test_size[0], self.test_size[1]),
    #         dtype=np.float16 if fp16 else np.float32,
    #     )
    
    #     ratios = []
    #     last_hwc_shape = None
    #     for i, frame in enumerate(inputs):
    #         img_hwc = frame
    #         # img_hwc = frame.permute(1, 2, 0).numpy() # torch
    #         # img_hwc = np.permute_dims(frame, (1, 2, 0)) # (H, W, C) # numpy
    #         logging.error("img_hwc type=%s shape=%s dtype=%s", type(img_hwc), getattr(img_hwc, "shape", None), getattr(img_hwc, "dtype", None))
    #         pimg, ratio = preproc(img_hwc, self.test_size, self.rgb_means, self.std)
    #         processed[i] = pimg
    #         ratio_scalar = (
    #             ratio[0] if isinstance(ratio, (list, tuple, np.ndarray)) else float(ratio)
    #         )
    #         ratios.append(ratio_scalar)
    #         last_hwc_shape = img_hwc.shape

    #     self.h, self.w = input_shape[1], input_shape[2]
    #     self.det_shape = (self.h, self.w)

    #     images = torch.from_numpy(processed).to(self.device)
    #     if fp16: images = images.half()
            
    #     return {
    #         "inputs": images,
    #         "shape": last_hwc_shape,
    #         "ratio": ratios,
    #     }

    # @torch.no_grad()
    # def run_inference(self, inputs):
    #     from yolox.utils import postprocess
        
    #     images = inputs["inputs"]
    #     logging.error("Running inference...")
    #     raw = self.model(images) # forward pass: raw grid-relative outputs (decode_in_inference=False)
    #     logging.error("Decoding outputs...")
    #     decoded = self.model.head.decode_outputs(raw, dtype=raw.type()) # manual decode into absolute pixel coordinates

    #     logging.error(
    #         f"decoded range: x={decoded[0,:,0].min():.1f}~{decoded[0,:,0].max():.1f}, "
    #         f"y={decoded[0,:,1].min():.1f}~{decoded[0,:,1].max():.1f}, "
    #         f"max_conf={torch.sigmoid(decoded[0,:,4]).max():.4f}"
    #     )
    #     logging.error("Postprocessing...")
    #     raw_outputs = postprocess(
    #         decoded, self.num_classes, self.conf_thresh, self.nms_thresh,
    #     )

    #     for pred, ratio in zip(raw_outputs, inputs["ratio"]):
    #         if pred is None:
    #             self.state.append([])
    #             self.img_id += 1
    #             continue

    #         if not np.isfinite(ratio) or ratio < 1e-6:
    #             logging.warning(f"Invalid ratio={ratio}, skipping frame {self.img_id}")
    #             self.state.append([])
    #             self.img_id += 1
    #             continue

    #         # scale boxes from letterboxed space back to original resolution
    #         scaling_factor = 1.0 / ratio
    #         pred[:, [0, 2]] *= scaling_factor  # x1, x2
    #         pred[:, [1, 3]] *= scaling_factor  # y1, y2

    #         # clamp to image bounds
    #         pred[:, 0].clamp_(0, self.w)
    #         pred[:, 1].clamp_(0, self.h)
    #         pred[:, 2].clamp_(0, self.w)
    #         pred[:, 3].clamp_(0, self.h)

    #         bbox_list = []
    #         for box in pred:
    #             b = box.cpu().numpy()
    #             if not np.all(np.isfinite(b[:4])):
    #                 continue
    #             box_coords = np.array((b[0], b[1], b[2], b[3]))
    #             bbox_list.append({
    #                 "xyxy": box_coords,
    #                 "xywh": xyxy_to_xywh(box_coords),
    #                 "cls_id": int(b[-1]),
    #                 "conf": float(b[-2]),
    #             })

    #         self.state.append(bbox_list)
    #         self.img_id += 1

    #     return raw_outputs