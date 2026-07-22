import logging
import numpy as np
import torch
from typing import Any, Dict


class RTDetr:
    def __init__(
        self,
        model_path: str,
        image_size: tuple[int, int],
        detector_params: Dict[Any, Any],
        **kwargs,
    ):
        from ultralytics import RTDETR
        from ultralytics.data.augment import LetterBox

        self.device = detector_params.get(
            "device",
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"

        self.state = []
        self.img_id = 0
        self.detector_params = detector_params

        self.checkpoint = detector_params.get("checkpoint", model_path)
        self.model = RTDETR(self.checkpoint)
        self.model.to(self.device)

        self.conf = detector_params.get("conf", 0.25)
        self.max_det = detector_params.get("max_det", 300)
        self.verbose = detector_params.get("verbose", False)

        imgsz = detector_params.get("imgsz", image_size)
        if isinstance(imgsz, int):
            self.imgsz = (imgsz, imgsz)
        else:
            self.imgsz = tuple(imgsz)

        self.use_fp16 = bool(
            detector_params.get("fp16", False) and str(self.device).startswith("cuda")
        )
        if self.use_fp16:
            try:
                self.model.model.half()
            except Exception:
                logging.warning("Could not cast RT-DETR backend model to FP16.")

        self.letterbox = LetterBox(
            new_shape=self.imgsz,
            auto=False,
            scale_fill=True,
            scaleup=True,
            center=True,
            stride=32,
        )

        logging.info("RT-DETR loaded from %s on %s", self.checkpoint, self.device)

    def _ensure_batched_hwc(self, frames):
        if isinstance(frames, torch.Tensor):
            frames = frames.detach().cpu().numpy()

        if not isinstance(frames, np.ndarray):
            raise TypeError(f"Unsupported input type: {type(frames)}")

        if frames.ndim == 3:
            frames = frames[None, ...]
        if frames.ndim != 4:
            raise RuntimeError(f"Expected (H,W,C) or (N,H,W,C), got {frames.shape}")
        if frames.shape[-1] != 3:
            raise RuntimeError(f"Expected 3-channel input, got {frames.shape}")

        return np.ascontiguousarray(frames)

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        frames = self._ensure_batched_hwc(inputs["frame"])
        n, h, w, _ = frames.shape

        self.h, self.w = h, w
        self.orig_shape = (h, w)

        processed = []
        for frame in frames:
            if frame.dtype != np.uint8:
                if frame.max() <= 1.0:
                    frame = (frame * 255.0).clip(0, 255).astype(np.uint8)
                else:
                    frame = frame.clip(0, 255).astype(np.uint8)

            if self.detector_params.get("bgr_input", False):
                frame = frame[..., ::-1]

            frame_lb = self.letterbox(image=frame)
            processed.append(frame_lb)

        batch = np.stack(processed, axis=0)  # NHWC
        self.det_shape = batch.shape[1:3]

        batch = np.ascontiguousarray(batch.transpose(0, 3, 1, 2))  # NCHW
        images = torch.from_numpy(batch)

        images = images.to(torch.float16 if self.use_fp16 else torch.float32).div_(255.0)

        if str(self.device).startswith("cuda"):
            images = images.pin_memory().to(self.device, non_blocking=True)
        else:
            images = images.to(self.device)

        return {
            "inputs": images,
            "orig_shape": self.orig_shape,
            "infer_shape": self.det_shape,
        }

    @torch.no_grad()
    def run_inference(self, inputs):
        images = inputs["inputs"]

        results = self.model(
            images,
            conf=self.conf,
            max_det=self.max_det,
            verbose=self.verbose,
        )

        for result_per_img in results:
            bbox_list = []

            if result_per_img.boxes is not None and len(result_per_img.boxes) > 0:
                boxes = result_per_img.boxes
                xyxy = boxes.xyxy.detach().cpu().numpy()
                xywh = boxes.xywh.detach().cpu().numpy()
                cls = boxes.cls.detach().cpu().numpy().astype(np.int32)
                conf = boxes.conf.detach().cpu().numpy()

                bbox_list = [
                    {
                        "xyxy": xyxy[i],
                        "xywh": xywh[i],
                        "cls_id": int(cls[i]),
                        "conf": float(conf[i]),
                    }
                    for i in range(len(xyxy))
                ]

            self.state.append(bbox_list)
            self.img_id += 1

        return results