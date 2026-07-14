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
        mode: str,
        batch_size: int,
        image_size: tuple[int, int],
        inference_params: Dict [Any, Any],
        finetune_params: Dict [Any, Any],
        device: str = "cuda",
        **kwargs
    ):
        from rfdetr import RFDETRBase, RFDETRNano, RFDETRSmall, RFDETRMedium, RFDETRLarge
        
        super().__init__(
            model_path, mode, batch_size, image_size, inference_params, finetune_params, device
        )
        self.det_shape = image_size
        self.model_variant = kwargs.get('model_variant', 'medium')
        self.classes_to_detect = kwargs.get('classes_to_detect', ['ball', 'player', 'referee', 'goalkeeper']) # TODO: fix...
        self.num_classes = len(self.classes_to_detect)
        self.min_confidence = self.cfg.get('conf_thresh', 0.25)
        self.resolution = self.cfg.get('resolution', 672)
        
        pretrain_weights = None
        if model_path:
            if str(model_path) != "" or str(model_path) != "None":
                pretrain_weights = str(model_path)
        self.model = RFDETRLarge(
            device=device,
            pretrain_weights=pretrain_weights
        )
        
        # move to device and set eval mode
        self.model.model.model.to(self.device)
        self.model.model.model.eval()
        
        logging.info(f"Model loaded successfully...")
        
        if self.mode == 'inference' and hasattr(self.model, 'optimize_for_inference'):
            self.model.optimize_for_inference(compile=False)

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        input = inputs['frame'] # expected shape (N, C, H, W)
        input = input.to(self.device).float()
        self.h, self.w = input.shape[2], input.shape[3]
        
        pil_images = []
        for i in range(input.shape[0]):
            # NOTE: RF-DETR expects PIL image format (H,W,C)
            img_np = input[i].permute(1, 2, 0).cpu().numpy().astype(np.uint8)
            pil_images.append(Image.fromarray(img_np))
            
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
                # if int(class_id) in self.classes_to_detect: # TODO!
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

    def run_finetune(self, inputs):
        return {}

    def reset_state(self):
        super().reset_state()

    def save_state(self, state_path):
        super().save_state(state_path)
    
    def load_state(self, state_path):
        return super().load_state(state_path)
