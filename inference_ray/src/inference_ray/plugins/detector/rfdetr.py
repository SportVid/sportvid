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
        self.classes_to_detect = detector_params .get('classes_to_detect')
        self.num_classes = len(self.classes_to_detect)
        
        self.min_confidence = detector_params.get('conf', 0.25)
        self.resolution = detector_params.get('resolution', 672)
        self.max_det = detector_params.get('max_det', 100)
        
        pretrain_weights = None
        self.checkpoint = detector_params.get("checkpoint", None)
        if self.checkpoint :
            if str(self.checkpoint ) != "" or str(self.checkpoint ) != "None":
                pretrain_weights = str(self.checkpoint)
        # TODO: instantiate from model_path string representation.
        self.model = RFDETRLarge(
            device=self.device,
            pretrain_weights=pretrain_weights
        )
        self.model.model.model.to(self.device)
        self.model.model.model.eval()
        
        logging.info(f"Model loaded successfully from checkpoint '{self.checkpoint}'...")
        self.model.optimize_for_inference(compile=False)

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        input_shape = inputs["frame"].shape  # NOTE: VideoDecoder returns (N,H,W,C)
        
        assert input_shape[3] == 3, "Expected 3-channel RGB input"
        
        pil_images = []
        for i, frame in enumerate(inputs['frame']):
            # NOTE: RF-DETR expects PIL image format (H,W,C)
            # img_np = input[i].permute(1, 2, 0).cpu().numpy().astype(np.uint8)
            img_hwc = frame
            pil_images.append(Image.fromarray(img_hwc))
        
        self.h, self.w = input.shape[2], input.shape[3]
        
        return {
            'inputs': pil_images,
            'shape': (self.h, self.w)
        }

    def process(self, inputs: Any, **kwargs):
        return super().process(inputs, **kwargs)

    @torch.no_grad()
    def run_inference(self, inputs):
        pil_images = inputs['inputs']
        batch_results = []
        
        for image in pil_images:
            results = self.model.predict(image, threshold=self.min_confidence)
            
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
            
        return batch_results