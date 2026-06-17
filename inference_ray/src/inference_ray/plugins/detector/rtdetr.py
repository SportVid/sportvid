import logging
import torch
import torch.nn.functional as F
from typing import Any
from omegaconf import DictConfig
from .detector import Detector

logger = logging.getLogger(__name__)


class RTDetr(Detector):

    def __init__(
        self,
        model_path: str,
        mode: str,
        batch_size: int,
        image_size: tuple,
        inference_params: DictConfig,
        finetune_params: DictConfig,
        device: str = "cuda",
        **kwargs
    ):
        super().__init__(
            model_path, mode, batch_size, image_size,
            inference_params, finetune_params, device
        )
        
        # Load model 
        from ultralytics import RTDETR
        self.model = RTDETR(model_path)
        self.model.to(device)
        
        logger.info(f"RT-DETR loaded from {model_path}")

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        """Preprocess - identical to YOLO."""
        input_frame = inputs['frame']
        input_frame = input_frame.to(self.device).float()
        input_shape = input_frame.shape
        
        h, w = input_shape[2], input_shape[3]
        
        # Pad to 32x stride (optional for transformers, but helps efficiency)
        pad_h = (32 - h % 32) % 32
        pad_w = (32 - w % 32) % 32
        input_padded = F.pad(input_frame, (0, pad_w, 0, pad_h), mode='constant', value=0)
        
        self.h = h + pad_h
        self.w = w + pad_w
        self.det_shape = (self.h, self.w)  # For tracker
        
        return {
            'inputs': input_padded.float() / 255.0,
            'shape': (self.h, self.w)
        }

    def process(self, inputs: Any, **kwargs):
        return super().process(inputs)

    @torch.no_grad()
    def run_inference(self, inputs):
        images = inputs['inputs']
        shapes = inputs['shape']
        
        raw_outputs = self.model.predict(
            images,
            batch=self.batch_size,
            imgsz=shapes,
            conf=self.cfg.get('conf', 0.25),
            verbose=self.cfg.get('verbose', False)
        )
        
        for result_per_img in raw_outputs:
            bbox_list = []
            if result_per_img.boxes is not None:
                for bbox in result_per_img.boxes:
                    b = bbox.cpu().numpy()
                    cls_id = int(b.cls[0])
                    conf = float(b.conf[0])
                    
                    # Filter by class if needed
                    if self.cfg.get('classes') and cls_id not in self.cfg['classes']:
                        continue
                    
                    bbox_dict = dict(
                        xyxy=b.xyxy[0],
                        xywh=b.xywh[0],
                        cls_id=cls_id,
                        conf=conf
                    )
                    bbox_list.append(bbox_dict)
            
            self.state.append(bbox_list)
            self.img_id += 1
        
        return raw_outputs