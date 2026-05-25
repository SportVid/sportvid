import logging
import torch
import torch.nn.functional as F

from typing import Any
from omegaconf import OmegaConf, DictConfig
from ultralytics import YOLO
from .detector import Detector


class YoloUltralytics(Detector):
    def __init__(
        self, 
        model_path: str,
        mode: str,
        batch_size: int,
        image_size: tuple[int, int],
        inference_params: DictConfig,
        finetune_params: DictConfig,
        device: str = "cuda",
        **kwargs
    ):
        super().__init__(
            model_path, mode, batch_size, image_size, inference_params, finetune_params, device)

        self.model = YOLO(model_path)
        self.model.to(device)

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs):
        input = inputs['frame']
        input = input.to(self.device).float()
        input_shape = input.shape
        # logging.debug(f"orig shape: {input_shape}")
        
        # add batch_size dim
        # img = img.unsqueeze(0) 
        
        # calculate stride-safe shape
        h, w = input_shape[2], input_shape[3]
        pad_h = (32 - h % 32) % 32 
        pad_w = (32 - w % 32) % 32
        
        input_padded = F.pad(input, (0, pad_w, 0, pad_h), mode='constant', value=114) # fills with constant gray     
        
        self.h = h + pad_h
        self.w = w + pad_w
        self.det_shape = (self.h, self.w)
        
        # width (or fraction) of video resolution
        if not self.cfg['imgsz']: self.cfg['imgsz'] = [self.h, self.w]
        
        return {
            'inputs': input_padded.float() / 255.0, # normalize inputs
            'shape': (self.h, self.w)
        }

    def process(self, inputs: Any, **kwargs):
        return super().process(inputs)

    @torch.no_grad()
    def run_inference(self, inputs):
        # NOTE: via TorchIterator
        images = inputs['inputs']
        shapes = inputs['shape']
        
        # TODO: resize original input?
        # https://docs.ultralytics.com/modes/predict/#inference-arguments
        raw_outputs = self.model.predict( # NOTE: model() returns a Tensor, model.predict() returns another format
            images,
            batch=self.batch_size,
            # imgsz=shapes, 
            **self.cfg
        )
        # logging.debug(results)
        # logging.debug(len(results))
        # boxes = results[1]["boxes"]
        
        # NOTE: not sure if we should return "raw_outputs"?
        for result_per_img in raw_outputs:
            bbox_list = list()
            for bbox in result_per_img.boxes:
                b = bbox.cpu().numpy()
                bbox_dict = dict(
                    xyxy=b.xyxy[0],
                    xywh=b.xywh[0],
                    cls_id=int(b.cls[0]),
                    conf=float(b.conf[0])
                )
                logging.debug(bbox_dict)
                bbox_list.append(bbox_dict)
            self.state.append(bbox_list)
            self.img_id += 1
        
        return raw_outputs
