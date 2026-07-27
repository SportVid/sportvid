import logging
import torch
import torch.nn.functional as F
import numpy as np
from typing import Any, Dict


class YoloUltralytics():
    def __init__(
        self, 
        model_path: str,
        image_size: tuple[int, int],
        detector_params: Dict [Any, Any],
        device: str = "cuda",
        **kwargs
    ):
        from ultralytics import YOLO
        
        self.device = device if (device != "cuda" or torch.cuda.is_available()) else "cpu"
        
        self.state = []
        self.img_id = 0

        self.detector_params = detector_params

        self.classes = self.detector_params.get('classes', [])
        self.num_classes = len(self.classes)
        if self.num_classes == 0:
            raise RuntimeError("Expected at least 1 class to detect, please check the 'classes' args.")

        self.checkpoint = detector_params.get("checkpoint", None)
        self.model = YOLO(self.checkpoint)
        self.model.to(self.device)
        
        self.batch_size = detector_params.get('batch_size', 1)
        self.use_fp16 = bool(detector_params.get("fp16", False) and self.device.startswith("cuda"))
        self.conf = detector_params.get("conf", 0.25)
        self.iou = detector_params.get("iou", 0.7)
        self.max_det = detector_params.get("max_det", 300)
        self.rect = detector_params.get("rect", True)
        self.verbose = detector_params.get("verbose", False)
        
        if self.use_fp16:
            try:
                self.model.model.half()
            except Exception:
                logging.warning("FP16 cast not applied to underlying Ultralytics model.")

    def _ensure_batched_hwc(self, frames):
        if isinstance(frames, np.ndarray):
            frames = torch.from_numpy(frames)
        elif not isinstance(frames, torch.Tensor):
            raise TypeError(f"Unsupported frame type: {type(frames)}")

        if frames.ndim == 3:  # HWC
            frames = frames.unsqueeze(0)
        if frames.ndim != 4:
            raise RuntimeError(f"Expected (H,W,C) or (N,H,W,C), got {tuple(frames.shape)}")
        if frames.shape[-1] != 3:
            raise RuntimeError(f"Expected RGB NHWC input with 3 channels, got {tuple(frames.shape)}")

        return frames.contiguous()

    def _move_to_device(self, x: torch.Tensor) -> torch.Tensor:
        if x.device.type == "cpu" and self.device.startswith("cuda"):
            x = x.pin_memory().to(self.device, non_blocking=True)
        else:
            x = x.to(self.device)
        return x

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        input = torch.from_numpy(inputs['frame']).float().to(self.device)
        input_shape = inputs["frame"].shape  # NOTE: VideoDecoder returns (N,H,W,C)
        input = input.permute(0, 3, 1, 2)
        self.h, self.w = input_shape[1], input_shape[2]
        
        # NOTE: adds a batch_size dim, if needed.
        # img = img.unsqueeze(0) 
        
        # pad to stride-safe shape (32x stride is optional for transformers, but helps with efficiency)
        pad_h = (32 - self.h % 32) % 32
        pad_w = (32 - self.w % 32) % 32
        
        input_padded = F.pad(input, (0, pad_w, 0, pad_h), mode='constant', value=114) # fills with constant gray     
        
        self.h = self.h + pad_h
        self.w = self.w + pad_w
        self.det_shape = (self.h, self.w)
        
        # width (or fraction) of video resolution
        if not self.detector_params['imgsz']: self.detector_params['imgsz'] = [self.h, self.w]
        
        return {
            'inputs': input_padded.float() / 255.0,  # normalize inputs
            'shape': (self.h, self.w)
        }

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        frames = self._ensure_batched_hwc(inputs["frame"])   # NHWC
        n, h, w, c = frames.shape
        self.orig_h, self.orig_w = int(h), int(w)

        x = frames.permute(0, 3, 1, 2).contiguous()     # NCHW

        if x.dtype == torch.uint8:
            x = x.float().div_(255.0)
        else:
            x = x.float()
            if x.max() > 1.0:
                x = x.div_(255.0)

        x = self._move_to_device(x)

        if self.use_fp16:
            x = x.half()

        imgsz = self.detector_params.get("imgsz", None)
        if imgsz is None:
            target_h, target_w = self.orig_h, self.orig_w
        elif isinstance(imgsz, int):
            target_h, target_w = imgsz, imgsz
        else:
            target_h, target_w = int(imgsz[0]), int(imgsz[1])

        if self.rect:
            pad_h = (32 - self.orig_h % 32) % 32
            pad_w = (32 - self.orig_w % 32) % 32
            if pad_h or pad_w:
                x = F.pad(x, (0, pad_w, 0, pad_h), mode="constant", value=114.0 / 255.0)
            self.h = self.orig_h + pad_h
            self.w = self.orig_w + pad_w
            infer_shape = (self.orig_h + pad_h, self.orig_w + pad_w)
        else:
            if (x.shape[-2], x.shape[-1]) != (target_h, target_w):
                x = F.interpolate(x, size=(target_h, target_w), mode="bilinear", align_corners=False)
            self.h = target_h
            self.w = target_w
            infer_shape = (target_h, target_w)
        self.det_shape = infer_shape
        
        return {
            "inputs": x,
            "orig_shape": (self.orig_h, self.orig_w),
            "infer_shape": infer_shape,
        }

    @torch.no_grad()
    def run_inference(self, inputs):
        images = inputs["inputs"]

        results = self.model(
            images,
            batch=self.batch_size,
            conf=self.conf,
            iou=self.iou,
            max_det=self.max_det,
            verbose=self.verbose,
        )

        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                self.state.append([])
                self.img_id += 1
                continue

            boxes = r.boxes
            xyxy = boxes.xyxy.detach().cpu().numpy()
            xywh = boxes.xywh.detach().cpu().numpy()
            conf = boxes.conf.detach().cpu().numpy()
            cls = boxes.cls.detach().cpu().numpy().astype(np.int32)

            for i in range(len(xyxy)):
                if int(cls[i]) not in self.classes:
                    continue
                bbox_list = [
                    {
                        "xyxy": xyxy[i],
                        "xywh": xywh[i],
                        "cls_id": int(cls[i]),
                        "conf": float(conf[i]),
                    }
                ]

                self.state.append(bbox_list)
                self.img_id += 1

        return results