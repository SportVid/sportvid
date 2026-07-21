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
        if not isinstance(frames, np.ndarray):
            raise TypeError(f"Unsupported frame type: {type(frames)}")
        if frames.ndim == 3:  # HWC
            frames = np.expand_dims(frames, axis=0)
        if frames.ndim != 4:
            raise RuntimeError(f"Expected (H,W,C) or (N,H,W,C), got {tuple(frames.shape)}")
        if frames.shape[-1] != 3:
            raise RuntimeError(f"Expected RGB NHWC input with 3 channels, got {tuple(frames.shape)}")
        return np.ascontiguousarray(frames)

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        frames = inputs['frame'] # expected shape (N, C, H, W)
        n, self.h, self.w, _ = frames.shape

        pil_images = []
        for frame in frames:
            # NOTE: RF-DETR expects PIL image format (H,W,C)
            img_np = frame.permute(1, 2, 0).astype(np.uint8)
            pil_images.append(Image.fromarray(img_np))

        return {
            "inputs": pil_images,
            "shape": (self.h, self.w),
        }

    @torch.no_grad()
    def run_inference(self, inputs):
        pil_images = inputs["inputs"]

        try:
            results = self.model.predict(
                pil_images,
                threshold=self.min_confidence,
            )
        except Exception:
            raise ValueError("Something went wrong...")

        batch_results = []
        bbox_list = []
        
        for box, score, class_id in zip(results.xyxy, results.confidence, results.class_id):  
            bbox_dict = dict(
                xyxy=box,
                xywh=xyxy_to_xywh(box),
                cls_id=int(class_id),
                conf=float(score)
            )
            bbox_list.append(bbox_dict)
        
        self.state.append(bbox_list)
        batch_results.append(bbox_list)
        self.img_id += 1
        
        logging.error(batch_results)            
        return batch_results