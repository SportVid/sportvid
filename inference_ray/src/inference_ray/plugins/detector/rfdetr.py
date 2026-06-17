import logging
import torch
import numpy as np

from PIL import Image
from typing import Any, Dict
from omegaconf import DictConfig, OmegaConf
from rfdetr import RFDETRBase, RFDETRNano, RFDETRSmall, RFDETRMedium, RFDETRLarge
from .detector import Detector
from trak.utils.coords import xyxy_to_xywh


class RFDetr(Detector):

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
            model_path, mode, batch_size, image_size, inference_params, finetune_params, device
        )
        self.det_shape = image_size
        self.model_variant = kwargs.get('model_variant', 'medium')
        self.classes_to_detect = kwargs.get('classes_to_detect', ['ball', 'player', 'referee', 'goalkeeper']) # TODO: fix...
        self.num_classes = len(self.classes_to_detect)
        self.min_confidence = self.cfg.get('conf_thresh', 0.25)
        self.resolution = self.cfg.get('resolution', 672)
        
        print(self.num_classes)
        
        # variants = {
        #     "nano": RFDETRNano,
        #     "small": RFDETRSmall,
        #     "medium": RFDETRMedium,
        #     "base": RFDETRBase,
        #     "large": RFDETRLarge
        # }
        # logging.info(f"Initializing RF-DETR {self.model_variant} on {self.device}")
        # model_class = variants.get(self.model_variant.lower(), RFDETRBase)
        # self.model = model_class(
        #     pretrain_weights=model_path, # NOTE: uncommenting, auto-downloads checkpoint
        #     resolution=self.resolution,
        #     device=self.device
        # ) # type: ignore
        
        self.model = RFDETRLarge()
        logging.info(f"Reinit detection head for {self.num_classes} classes...")
        self.model.model.model.reinitialize_detection_head(self.num_classes)
        # https://huggingface.co/julianzu9612/RFDETR-Soccernet
        # ---> load checkpoint
        checkpoint = torch.load(str(model_path), map_location=self.device, weights_only=False)
        
        # ---> extract model state
        if 'model' in checkpoint:
            model_state = checkpoint['model']
        elif 'model_state_dict' in checkpoint:
            model_state = checkpoint['model_state_dict']
        else:
            model_state = checkpoint
        
        # ---> load state dict
        self.model.model.model.load_state_dict(model_state)
        
        # ---> show checkpoint info
        if 'best_mAP' in checkpoint:
            logging.info(f"📊 Model mAP: {checkpoint['best_mAP']:.3f}")
        if 'epoch' in checkpoint:
            logging.info(f"🔄 Trained epochs: {checkpoint['epoch']}")

        # Move to device and set eval mode
        self.model.model.model.to(self.device)
        self.model.model.model.eval()
        
        logging.info(f"Model loaded successfully...")
        
        if hasattr(self.model, 'optimize_for_inference'):
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