import logging
import torch
import numpy as np
from PIL import Image
from typing import Any, Dict


def xyxy_to_xywh(xyxy):
    """
    Transforms [x1,y1,x2,y2] -> [center of x,c enter of y, width, height]
    Shape stays the same [N,4]
    """
    if len(xyxy.shape) == 1: # handle mini-batch
        xyxy = xyxy.reshape(1, -1)
    
    x1, y1, x2, y2 = xyxy[:, 0], xyxy[:, 1], xyxy[:, 2], xyxy[:, 3]
    cx = (x1 + x2) * 0.5
    cy = (y1 + y2) * 0.5
    w = x2 - x1
    h = y2 - y1
    
    return np.array((cx,cy,w,h))


class RFDetr():

    def __init__(
        self, 
        model_path: str,
        image_size: tuple[int, int],
        detector_params: Dict [Any, Any],
        **kwargs
    ):
        from rfdetr import RFDETRLarge
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.state = list()
        self.img_id = 0
        
        self.detector_params = detector_params
    
        self.det_shape = image_size
        self.classes_to_detect = detector_params.get('classes', [])
        if len(self.classes_to_detect) == 0:
            raise RuntimeError("Expected at least 1 class to detect, please check the 'classes' args.")
        self.num_classes = len(self.classes_to_detect)
        
        self.min_confidence = detector_params.get('conf', 0.25)
        self.resolution = detector_params.get('resolution', 672)
        self.max_det = detector_params.get('max_det', 100)
        
        pretrain_weights = None
        self.checkpoint = detector_params.get("checkpoint", None)
        if self.checkpoint is not None and (
            str(self.checkpoint).strip().lower() not in {"", "none", "null"}):
                pretrain_weights = str(self.checkpoint)
        # TODO: instantiate from model_path string representation.
        self.model = RFDETRLarge(
            device=self.device,
            pretrain_weights=pretrain_weights
        )
        self.model.model.model.to(self.device)
        self.model.model.model.eval()
        
        logging.info(f"Model loaded successfully from checkpoint '{self.checkpoint}'...")
        try:
            self.model.optimize_for_inference(
                compile=False,
                batch_size=detector_params.get("batch_size", 1),
                dtype="float16" if (self.device.startswith("cuda") and detector_params.get("fp16", False)) else "float32",
            )
        except Exception:
            logging.warning("RF-DETR optimize_for_inference failed; continuing without optimized model.", exc_info=True)

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

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        frames = self._ensure_batched_hwc(inputs["frame"])
        n, h, w, _ = frames.shape
        self.h, self.w = h, w

        pil_images = []
        for frame in frames:
            if frame.dtype != np.uint8:
                if frame.max() <= 1.0:
                    frame = (frame * 255.0).clip(0, 255).astype(np.uint8)
                else:
                    frame = frame.clip(0, 255).astype(np.uint8)
            pil_images.append(Image.fromarray(frame))

        return {
            "inputs": pil_images,
            "shape": (self.h, self.w),
        }

    def process(self, inputs: Any, **kwargs):
        return super().process(inputs, **kwargs)

    @torch.no_grad()
    def run_inference(self, inputs):
        pil_images = inputs["inputs"]

        try:
            results = self.model.predict(
                pil_images,
                threshold=self.min_confidence,
            )
            batched = True
        except Exception:
            results = [self.model.predict(img, threshold=self.min_confidence) for img in pil_images]
            batched = False

        batch_results = []

        iterable = results if batched else results
        for det in iterable:
            xyxy = np.asarray(det.xyxy)
            conf = np.asarray(det.confidence)
            cls = np.asarray(det.class_id)

            if len(xyxy) > self.max_det:
                order = np.argsort(-conf)[: self.max_det]
                xyxy = xyxy[order]
                conf = conf[order]
                cls = cls[order]

            xywh = self.xyxy_to_xywh(xyxy)

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
            batch_results.append(bbox_list)
            self.img_id += 1

        return batch_results