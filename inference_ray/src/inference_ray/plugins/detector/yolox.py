import logging
import torch
import numpy as np
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


def _is_torch(x):
    return isinstance(x, torch.Tensor)


def _to_numpy(x):
    if isinstance(x, np.ndarray):
        return x
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    raise TypeError(f"Unsupported input type: {type(x)}")


class YoloX():
    """
    YOLOX detector wrapper for inference.
    Source: https://github.com/Megvii-BaseDetection/YOLOX
    """
    def __init__(
        self,
        model_path: str,
        batch_size: int,
        image_size: tuple[int, int],
        detector_params: Dict [Any, Any],
        **kwargs,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.state = list()
        self.img_id = 0
        
        self.detector_params = detector_params
        
        from yolox.exp import get_exp
        self.exp = get_exp(None, model_path)
        
        self.batch_size = batch_size
        self.checkpoint = detector_params.get("checkpoint", None)
        self.w, self.h = image_size

        self._init_inference(detector_params)
        
        # ImageNet norm constants (used in preprocess)
        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

    def _init_inference(self, cfg: Dict[Any, Any]):
        """
        Build and prepare the model for inference:
          - loads architecture from exp
          - restores weights from checkpoint (strict)
          - sets eval mode and disables internal decoding
        """
        import torch
        
        self.cfg = cfg
        self.exp.num_classes = self.num_classes = cfg["num_classes"]
        self.conf_thresh = cfg["conf_thresh"]
        self.nms_thresh = cfg["nms_thresh"]

        # test_size must match the training input_size exactly
        self.test_size = self.exp.test_size # default is determined by exp
        if "test_size" in cfg:
            if cfg["test_size"]:
                self.test_size = tuple(cfg["test_size"])
                self.exp.test_size = self.test_size
        else:
            logging.warning(
                "No test_size in inference_params -> using exp default "
                f"{self.test_size}. Make sure this matches your training input_size."
            )
        logging.info(
            f"[inference] " 
            f"test_size={self.test_size}, "
            f"num_classes={self.num_classes}, "
            f"conf={self.conf_thresh}, nms={self.nms_thresh}"
        )

        # build model
        self.model = self.exp.get_model().to(self.device)

        # load checkpoint
        if self.checkpoint:
            logging.info(f"[inference] Loading checkpoint: {self.checkpoint}")
            chkpt = torch.load(self.checkpoint, map_location=self.device)
            self.model.load_state_dict(chkpt["model"], strict=True) # strict=True to check for architecture mismatches
            logging.info("[inference] Checkpoint loaded successfully.")
        else:
            logging.warning(
                "[inference] No checkpoint provided -> running with random weights. "
                "Set model_chkpt in your config."
            )

        # fp16 after checkpoint load so the cast doesn't affect weight loading
        if cfg.get("fp16", False):
            self.model = self.model.half()
            logging.info("[inference] Model cast to fp16.")

        # eval mode + disable internal decoding (we call decode_outputs manually)
        self.model.eval()
        if hasattr(self.model, "head"):
            self.model.head.training = False
            self.model.head.decode_in_inference = False

    @torch.no_grad()
    def preprocess(self, inputs, **kwargs) -> Dict[Any, Any]:
        """
        Letterbox-resize each frame to test_size and normalise with ImageNet stats.
        Args:
            inputs: dict with 'frame' tensor (N, H, W, C)
        Returns:
            dict with 'inputs' (model-ready tensor), 'shape', 'ratio' (list[float])
        """
        from yolox.data.data_augment import preproc

        input_shape = inputs["frame"].shape  # NOTE: VideoDecoder returns (N,H,W,C)
        fp16 = self.cfg.get("fp16", False)

        assert input_shape[3] == 3, "Expected 3-channel RGB input"

        processed = np.zeros( # (N, C, H, W)
            (input_shape[0], input_shape[3], self.test_size[0], self.test_size[1]),
            dtype=np.float16 if fp16 else np.float32,
        )
    
        ratios = []
        last_hwc_shape = None
        for i, frame in enumerate(inputs["frame"]):
            img_hwc = frame
            # img_hwc = frame.permute(1, 2, 0).numpy() # torch
            # img_hwc = np.permute_dims(frame, (1, 2, 0)) # (H, W, C) # numpy
            logging.debug("img_hwc type=%s shape=%s dtype=%s", type(img_hwc), getattr(img_hwc, "shape", None), getattr(img_hwc, "dtype", None))
            pimg, ratio = preproc(img_hwc, self.test_size, self.rgb_means, self.std)
            processed[i] = pimg
            ratio_scalar = (
                ratio[0] if isinstance(ratio, (list, tuple, np.ndarray)) else float(ratio)
            )
            ratios.append(ratio_scalar)
            last_hwc_shape = img_hwc.shape

        self.h, self.w = input_shape[1], input_shape[2]
        self.det_shape = (self.h, self.w)

        images = torch.from_numpy(processed).to(self.device)
        if fp16: images = images.half()
            
        return {
            "inputs": images,
            "shape": last_hwc_shape,
            "ratio": ratios,
        }

    @torch.no_grad()
    def run_inference(self, inputs):
        from yolox.utils import postprocess
        
        images = inputs["inputs"]

        raw = self.model(images) # forward pass: raw grid-relative outputs (decode_in_inference=False)
        decoded = self.model.head.decode_outputs(raw, dtype=raw.type()) # manual decode into absolute pixel coordinates

        logging.debug(
            f"decoded range: x={decoded[0,:,0].min():.1f}~{decoded[0,:,0].max():.1f}, "
            f"y={decoded[0,:,1].min():.1f}~{decoded[0,:,1].max():.1f}, "
            f"max_conf={torch.sigmoid(decoded[0,:,4]).max():.4f}"
        )

        raw_outputs = postprocess(
            decoded, self.num_classes, self.conf_thresh, self.nms_thresh,
        )

        for pred, ratio in zip(raw_outputs, inputs["ratio"]):
            if pred is None:
                self.state.append([])
                self.img_id += 1
                continue

            if not np.isfinite(ratio) or ratio < 1e-6:
                logging.warning(f"Invalid ratio={ratio}, skipping frame {self.img_id}")
                self.state.append([])
                self.img_id += 1
                continue

            # scale boxes from letterboxed space back to original resolution
            scaling_factor = 1.0 / ratio
            pred[:, [0, 2]] *= scaling_factor  # x1, x2
            pred[:, [1, 3]] *= scaling_factor  # y1, y2

            # clamp to image bounds
            pred[:, 0].clamp_(0, self.w)
            pred[:, 1].clamp_(0, self.h)
            pred[:, 2].clamp_(0, self.w)
            pred[:, 3].clamp_(0, self.h)

            bbox_list = []
            for box in pred:
                b = box.cpu().numpy()
                if not np.all(np.isfinite(b[:4])):
                    continue
                box_coords = np.array((b[0], b[1], b[2], b[3]))
                bbox_list.append({
                    "xyxy": box_coords,
                    "xywh": xyxy_to_xywh(box_coords),
                    "cls_id": int(b[-1]),
                    "conf": float(b[-2]),
                })

            self.state.append(bbox_list)
            self.img_id += 1

        return raw_outputs