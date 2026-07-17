import logging
import torch
import torch.nn.functional as F
from typing import Any, Dict


# TODO: Refactor -> merge this class with 'yolo_ultra' since they use the same API.
# Should run under the detector "ultralytics" and instantiate different classes via `model_path`.
class RTDetr():
    def __init__(
        self,
        model_path: str,
        image_size: tuple[int, int],
        detector_params: Dict [Any, Any],
        **kwargs
    ):
        from ultralytics import RTDETR
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.state = list()
        self.img_id = 0
        
        self.detector_params = detector_params
        
        self.checkpoint = detector_params.get("checkpoint", None)
        self.model = RTDETR(self.checkpoint)
        self.model.to(self.device)
        
        logging.info(f"RT-DETR loaded from {self.checkpoint}")

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        input = torch.from_numpy(inputs['frame']).float().to(self.device)
        input_shape = inputs["frame"].shape  # NOTE: VideoDecoder returns (N,H,W,C)
        input = input.permute(0, 3, 1, 2)
        self.h, self.w = input_shape[1], input_shape[2]
        
        # pad to stride-safe shape (32x stride is optional for transformers, but helps with efficiency)
        pad_h = (32 - self.h % 32) % 32
        pad_w = (32 - self.w % 32) % 32
        input_padded = F.pad(input, (0, pad_w, 0, pad_h), mode='constant', value=0)
        
        self.h = self.h + pad_h
        self.w = self.w + pad_w
        self.det_shape = (self.h, self.w)
        
        return {
            'inputs': input_padded.float() / 255.0,  # normalize inputs
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
            batch=self.detector_params.get('batch_size', 1),
            imgsz=shapes,
            conf=self.detector_params.get('conf', 0.25),
            verbose=self.detector_params.get('verbose', False)
        )
        
        for result_per_img in raw_outputs:
            bbox_list = []
            if result_per_img.boxes is not None:
                for bbox in result_per_img.boxes:
                    b = bbox.cpu().numpy()
                    cls_id = int(b.cls[0])
                    conf = float(b.conf[0])
                    
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