from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping
from rest_framework import serializers
from backend.plugin_manager import PluginManager

DETECTOR_CHOICES = ["yolox", "yoloultra", "rfdetr", "rtdetr"]
TRACKER_CHOICES = ["bytetrack"]

YOLOULTRA_CHOICES = ["yolo10", "yolo11", "yolo12", "yolo26"]

default_yolox_params = {
    "batch_size": 1,
    "conf_thresh": 0.2,
    "nms_thresh": 0.65,
    "fp16": True,
    "num_classes": 1, 
    "decode": True,
    "model_path": "yolox-x",
    "checkpoint": "/models/yolox/bytetrack_x_mot17.pth.tar"
}

default_yoloultra_params = {
    "batch_size": 1,
    "conf": 0.2,                # min confidence threshold [0.1 - 0.6]
    "iou": 0.3,                 # threshold for NMS; lower values -> less detections [0.3 - 0.6]
    "agnostic_nms": False,      # class-agnostic NMS; merge overlapping boxes of different classes
    "classes": [0, 32],         # filters predictions to specified class set: 'person','sports_ball' for COCO dataset
    "half": False,
    "imgsz": None,              # e.g. [640, 1280] or null to use img dims
    "max_det": 100,             # max amount of detections per frame
    "embed": None,              # specify layers from which to extract feature vectors or embeddings
    "verbose": False,
    "model_path": "/models/yolo_ultra/yolo12x.pt",
    "checkpoint": "/models/yolo_ultra/yolo12x.pt"
}

default_rfdetr_params = {
    "batch_size": 1,
    "conf": 0.5,               
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    # "classes": ['ball', 'player', 'referee', 'goalkeeper'], # soccernet checkpoint
    "max_det": 100,
    "resolution": 1288,         # has to be divisible by 56: [672,728,784,896,1008,1064,1120]
    "verbose": False,
    "checkpoint": "/models/detr/rf-detr-large.pth"
}

default_rtdetr_params = {
    "batch_size": 1,
    "conf": 0.25,
    "classes": [0, 32],         # default COCO: 0 - person, 32 - ball
    "verbose": False, 
    "checkpoint": "/models/detr/rtdetr-x.pt"
}

default_bytetrack_params = {
    "track_thresh": 0.4,        # tracking confidence threshold (0.6 = default)
    "track_buffer": 300,        # num of frames to keep lost tracks
    "match_thresh": 0.8,        # [0.8, 0.6, 0.4]; high = fewer ID switches, low -> More MOTA; IoU matching threshold for associating detections to existing tracks
    "mot20": False,             # 'True' skips fusing scores?
    "aspect_ratio_thresh": 5.0, # reject tracking artifacts / FPs of unrealistic shape
    "min_box_area": 0,          # min box area thresholds (px^2)
}

DETECTOR_DEFAULTS = {
    "yolox": default_yolox_params,
    "yolov10": default_yoloultra_params,
    "yolov11": default_yoloultra_params,
    "yolov26": default_yoloultra_params,
    "rfdetr": default_rfdetr_params,
    "rtdetr": default_rtdetr_params, 
}

TRACKER_DEFAULTS = {
    "bytetrack": default_bytetrack_params
}


class DetectorParamsSerializer(serializers.Serializer):
    batch_size = serializers.IntegerField(required=False, min_value=1)
    checkpoint = serializers.CharField(required=False, allow_blank=False)

    confidence_threshold = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Optional model-agnostic confidence threshold alias.",
    )
    conf = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    conf_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    
    iou = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    nms_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)

    agnostic_nms = serializers.BooleanField(required=False)
    half = serializers.BooleanField(required=False)
    fp16 = serializers.BooleanField(required=False)
    decode = serializers.BooleanField(required=False)
    verbose = serializers.BooleanField(required=False)

    max_det = serializers.IntegerField(required=False, min_value=1)
    num_classes = serializers.IntegerField(required=False, min_value=1)

    classes = serializers.ListField(
        required=False,
        child=serializers.JSONField(),
        allow_empty=False,
    )

    embed = serializers.ListField(
        required=False,
        child=serializers.IntegerField(min_value=0),
        allow_empty=True,
    )

    imgsz = serializers.ListField(
        required=False,
        child=serializers.IntegerField(min_value=32),
        min_length=2,
        max_length=2,
        allow_empty=False,
    )

    test_size = serializers.ListField(
        required=False,
        child=serializers.IntegerField(min_value=32),
        min_length=2,
        max_length=2,
        allow_empty=False,
    )

    resolution = serializers.IntegerField(required=False, min_value=56)
    model_path = serializers.CharField(required=False, allow_blank=False)
    model_checkpoint = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if "confidence_threshold" in attrs:
            if "conf" in attrs or "conf_thresh" in attrs:
                raise serializers.ValidationError({
                    "confidence_threshold": [
                        "Use either confidence_threshold or a backend-specific confidence field, not both."
                    ]
                })
        return attrs

class TrackerParamsSerializer(serializers.Serializer):
    track_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    track_buffer = serializers.IntegerField(required=False, min_value=1)
    match_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    mot20 = serializers.BooleanField(required=False)
    aspect_ratio_thresh = serializers.FloatField(required=False, min_value=0.0)
    min_box_area = serializers.FloatField(required=False, min_value=0.0)


@PluginManager.export_serializer("object_tracker")
class ObjectTrackerSerializer(serializers.Serializer):
    fps = serializers.IntegerField(
        required=False, 
        min_value=1, 
        max_value=30,
        default=10
    )
    detector = serializers.ChoiceField(
        choices=DETECTOR_CHOICES,
        required=False,
        default="yolox",
    )
    tracker = serializers.ChoiceField(
        choices=TRACKER_CHOICES,
        required=False,
        default="bytetrack",
    )
    detector_params = DetectorParamsSerializer(required=False, default=dict)
    tracker_params = TrackerParamsSerializer(required=False, default=dict)

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        detector = data.get("detector", "yolox")
        tracker = data.get("tracker", "bytetrack")
        detector_params = data.get("detector_params", {})
        tracker_params = data.get("tracker_params", {})

        detector_validator = self._get_detector_validator(detector)
        detector_validator(detector_params)

        tracker_validator = self._get_tracker_validator(tracker)
        tracker_validator(tracker_params)

        data["detector_params"] = self.build_detector_runtime_params(
            detector=detector,
            user_params=detector_params,
        )
        data["tracker_params"] = self.build_tracker_runtime_params(
            tracker=tracker,
            user_params=tracker_params,
        )
        return data

    @classmethod
    def build_detector_runtime_params(
        cls,
        detector: str,
        user_params: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        params = cls._merge_with_presets(DETECTOR_DEFAULTS, detector, user_params)
        return cls._normalize_detector_params(detector, params)

    @classmethod
    def build_tracker_runtime_params(
        cls,
        tracker: str,
        user_params: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return cls._merge_with_presets(TRACKER_DEFAULTS, tracker, user_params)

    @staticmethod
    def _merge_with_presets(
        presets: Mapping[str, Mapping[str, Any]],
        key: str,
        user_params: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        merged = deepcopy(dict(presets[key]))
        if user_params:
            merged.update(dict(user_params))
        return merged

    @classmethod
    def _normalize_detector_params(cls, detector: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = deepcopy(params)

        confidence_threshold = params.pop("confidence_threshold", None)
        if confidence_threshold is not None:
            if detector == "yolox":
                params["conf_thresh"] = confidence_threshold
            else:
                params["conf"] = confidence_threshold

        if detector in YOLOULTRA_CHOICES:
            if "checkpoint" not in params:
                params["checkpoint"] = default_yoloultra_params["checkpoint"]

        return params

    def _get_detector_validator(self, detector: str):
        mapping = {
            "yolox": self._validate_yolox_params,
            "yolo10": self._validate_yoloultra_params,
            "yolo11": self._validate_yoloultra_params,
            "yolo26": self._validate_yoloultra_params,
            "rfdetr": self._validate_rfdetr_params,
            "rtdetr": self._validate_rtdetr_params,
        }
        return mapping[detector]

    def _get_tracker_validator(self, tracker: str):
        mapping = {
            "bytetrack": self._validate_bytetrack_params,
        }
        return mapping[tracker]

    def _validate_yolox_params(self, params: Mapping[str, Any]) -> None:
        allowed = {
            "batch_size",
            "conf_thresh",
            "nms_thresh",
            "fp16",
            "num_classes",
            "decode",
            "test_size",
            "model_path",
            "model_checkpoint",
            "confidence_threshold",
        }
        self._reject_unknown_keys("detector_params", params, allowed)

        if "classes" in params:
            self._raise_field_error(
                "detector_params",
                "classes",
                "YOLOX configuration does not support a 'classes' filter in this schema."
            )

        test_size = params.get("test_size")
        if test_size is not None:
            h, w = test_size
            if h % 32 != 0 or w % 32 != 0:
                self._raise_field_error(
                    "detector_params",
                    "test_size",
                    "YOLOX test_size should typically be divisible by 32."
                )

    def _validate_yoloultra_params(self, params: Mapping[str, Any]) -> None:
        allowed = {
            "batch_size",
            "conf",
            "iou",
            "agnostic_nms",
            "classes",
            "half",
            "imgsz",
            "max_det",
            "embed",
            "verbose",
            "checkpoint",
            "confidence_threshold",
        }
        self._reject_unknown_keys("detector_params", params, allowed)

        classes = params.get("classes")
        if classes is not None and not all(isinstance(x, int) for x in classes):
            self._raise_field_error(
                "detector_params",
                "classes",
                "Ultralytics detectors expect integer class IDs."
            )

        imgsz = params.get("imgsz")
        if imgsz is not None:
            h, w = imgsz
            if h % 32 != 0 or w % 32 != 0:
                self._raise_field_error(
                    "detector_params",
                    "imgsz",
                    "imgsz should typically use stride-compatible values, usually divisible by 32."
                )

    def _validate_rfdetr_params(self, params: Mapping[str, Any]) -> None:
        allowed = {
            "batch_size",
            "conf",
            "classes",
            "max_det",
            "resolution",
            "verbose",
            "checkpoint",
            "confidence_threshold",
        }
        self._reject_unknown_keys("detector_params", params, allowed)

        # TODO: validation of classes should be flexible enough to handle both cases, i.e. integers & class names should be accetable.
        # classes = params.get("classes")
        # if classes is not None:
        #     invalid = [x for x in classes if x not in RFDETR_CLASS_CHOICES]
        #     if invalid:
        #         self._raise_field_error(
        #             "detector_params",
        #             "classes",
        #             f"Invalid RFDETR class names: {invalid}. Allowed values: {list(RFDETR_CLASS_CHOICES)}"
        #         )

        resolution = params.get("resolution")
        if resolution is not None and resolution % 56 != 0:
            self._raise_field_error(
                "detector_params",
                "resolution",
                "RFDETR resolution must be divisible by 56."
            )

    def _validate_rtdetr_params(self, params: Mapping[str, Any]) -> None:
        allowed = {
            "batch_size",
            "conf",
            "classes",
            "verbose",
            "checkpoint",
            "confidence_threshold",
        }
        self._reject_unknown_keys("detector_params", params, allowed)

        classes = params.get("classes")
        if classes is not None and not all(isinstance(x, int) for x in classes):
            self._raise_field_error(
                "detector_params",
                "classes",
                "RTDETR expects integer class IDs."
            )

    def _validate_bytetrack_params(self, params: Mapping[str, Any]) -> None:
        allowed = {
            "track_thresh",
            "track_buffer",
            "match_thresh",
            "mot20",
            "aspect_ratio_thresh",
            "min_box_area",
        }
        self._reject_unknown_keys("tracker_params", params, allowed)

        track_thresh = params.get("track_thresh")
        match_thresh = params.get("match_thresh")
        if track_thresh is not None and match_thresh is not None and match_thresh < track_thresh:
            self._raise_field_error(
                "tracker_params",
                "match_thresh",
                "match_thresh should usually be greater than or equal to track_thresh."
            )

    @staticmethod
    def _reject_unknown_keys(
        group_name: str,
        payload: Mapping[str, Any],
        allowed: Iterable[str],
    ) -> None:
        unknown = sorted(set(payload.keys()) - set(allowed))
        if unknown:
            raise serializers.ValidationError({
                group_name: {
                    "non_field_errors": [
                        f"Unknown parameters: {unknown}. Allowed keys: {sorted(set(allowed))}"
                    ]
                }
            })

    @staticmethod
    def _raise_field_error(group_name: str, field_name: str, message: str) -> None:
        raise serializers.ValidationError({
            group_name: {
                field_name: [message]
            }
        })