import logging
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping
from rest_framework import serializers
from backend.plugin_manager import PluginManager


DETECTOR_CHOICES = ["yolox", "yolo10", "yolo11", "yolo12", "yolo26", "rfdetr", "rtdetr"]
TRACKER_CHOICES = ["bytetrack"]
BALL_TRACKER_CHOICES = ["kalman"]


# TODO: dynamic checkpoint loading based on context / sports type.
default_yolox_params = {
    "batch_size": 1,
    "conf_thresh": 0.2,
    "nms_thresh": 0.4,
    "classes": [0],
    "fp16": False,
    "num_classes": 1, 
    "decode": True,
    "model_path": "yolox-x",
    "checkpoint": "/models/yolox/bytetrack_x_mot17.pth.tar",
    "output_class_mapping": {
        -1: {
            "entity_type": "unknown",
            "default_team": -1
        },
        0: {
            "entity_type": "athlete",
            "default_team": 3
        }
    }
}

default_yolo10_params = {
    "batch_size": 1,
    "conf": 0.15,               # min confidence threshold [0.15 - 0.6]
    "iou": 0.4,                 # threshold for NMS; lower values -> less detections [0.3 - 0.6]
    "agnostic_nms": False,      # class-agnostic NMS; merge overlapping boxes of different classes
    "classes": [0, 32],         # filters predictions to specified class set: 'person','sports_ball' for COCO dataset
    "half": False,
    "imgsz": None,              # e.g. [640, 1280] or null to use img dims
    "max_det": 100,             # max amount of detections per frame
    "embed": None,              # specify layers from which to extract feature vectors or embeddings
    "verbose": False,
    "model_path": "yolov10",
    "checkpoint": "/models/yolo_ultra/yolov10x.pt",
    "output_class_mapping": {
        -1: {
            "entity_type": "unknown",
            "default_team": -1
        },
        0: {
            "entity_type": "athlete",
            "default_team": 3
        },
        32: {
            "entity_type": "ball",
            "default_team": 0
        }
    }
}

default_yolo11_params = {
    **default_yolo10_params,
    "model_path": "yolo11",
    "checkpoint": "/models/yolo_ultra/yolo11x.pt",
}

default_yolo12_params = {
    **default_yolo10_params,
    "model_path": "yolo12",
    "checkpoint": "/models/yolo_ultra/yolo12x.pt",
}

default_yolo26_params = {
    **default_yolo10_params,
    "model_path": "yolo26",
    "checkpoint": "/models/yolo_ultra/yolo26x.pt",
}

default_rfdetr_params = {
    "batch_size": 1,
    "conf": 0.6,               
    # "classes": [0, 32],  # default COCO: 0 - person, 32 - ball
    "classes": ['ball', 'player', 'referee', 'goalkeeper'], # SoccerNet checkpoint
    "resolution": 1288,  # divisible by 56 -> [672,728,784,896,1008,1064,1120]
    "verbose": False,
    "fp16": False,
    "model_path": "RFDETRLarge",
    "checkpoint": "/models/detr/rfdetr-large-sn.pth",
    "output_class_mapping": {
        -1: {
            "entity_type": "unknown",
            "default_team": -1
        },
        0: {
            "entity_type": "ball",
            "default_team": 0
        },
        1: {
            "entity_type": "player",
            "default_team": 3
        },
        2: {
            "entity_type": "referee",
            "default_team": 2
        },
        3: {
            "entity_type": "goalkeeper",
            "default_team": 3
        }
    }
}

default_rtdetr_params = {
    "batch_size": 1,
    "conf": 0.25,
    "classes": [0, 32],  # default COCO: 0 - person, 32 - ball
    "verbose": False, 
    "model_path": "RTDETR",
    "checkpoint": "/models/detr/rtdetr-x.pt",
    "output_class_mapping": {
        -1: {
            "entity_type": "unknown",
            "default_team": -1
        },
        0: {
            "entity_type": "person",
            "default_team": 3
        },
        32: {
            "entity_type": "ball",
            "default_team": 0
        }
    }
}

# Example parameter settings:
#   1) balanced: [0.5 60 0.7]
#   2) conservative: [0.5 60 0.75]
#   3) occlusion-heavy: [0.45 90 0.7]
# track_buffer counts frames at 30 fps (ByteTrack's convention): the plugin scales it to the decoding rate, so it
# is a duration (150 = 5 s at any fps). 150 is trak's ByteTrack re-tune on the DSHS recordings (buffer 150 of
# 30 / 60 / 150; inference_ray plugins/tracker/README.md).
default_bytetrack_params = {
    "track_thresh": 0.45,       # tracking confidence threshold (0.6 = default)
    "track_buffer": 150,        # keep lost tracks this many frames at 30 fps (150 = 5 s)
    "match_thresh": 0.7,        # [0.8, 0.6, 0.4]; high = fewer ID switches, low -> More MOTA; IoU matching threshold for associating detections to existing tracks
    "mot20": False,             # 'True' skips fusing scores?
    "aspect_ratio_thresh": 5.0, # reject tracking artifacts / FPs of unrealistic shape
    "min_box_area": 0,          # min box area thresholds (px^2)
}

DETECTOR_DEFAULTS = {
    "yolox": default_yolox_params,
    "yolo10": default_yolo10_params,
    "yolo11": default_yolo11_params,
    "yolo12": default_yolo12_params,
    "yolo26": default_yolo26_params,
    "rfdetr": default_rfdetr_params,
    "rtdetr": default_rtdetr_params, 
}

TRACKER_DEFAULTS = {
    "bytetrack": default_bytetrack_params
}

# Ball detector: another instance of a detector preset (same model files), with its own parameters. Only the
# detectors whose preset model has a ball class; the low confidence floor is trak's (0.10): the ball tracker gates
# weak candidates itself (min_conf / init_conf below).
BALL_DETECTOR_OVERRIDES = {
    "yolo10": {"classes": [32], "conf": 0.1},
    "yolo11": {"classes": [32], "conf": 0.1},
    "yolo12": {"classes": [32], "conf": 0.1},
    "yolo26": {"classes": [32], "conf": 0.1},
    "rtdetr": {"classes": [32], "conf": 0.1},
    "rfdetr": {"classes": ["ball"], "conf": 0.1},
}
BALL_DETECTOR_CHOICES = list(BALL_DETECTOR_OVERRIDES)

# Kalman ball tracker (inference_ray plugins/tracker/ball_tracker.py; trak's configs/ball_tracker/kalman.yaml).
# Frame-based values are given at 30 fps and scaled to the decoding rate by the plugin. Below min_fps the ball
# candidates are written untracked.
default_kalman_ball_params = {
    "min_conf": 0.10,             # candidates below are ignored
    "init_conf": 0.40,            # confidence needed to (re)acquire the ball
    "gate_px": 60.0,              # association radius around the predicted position (px / frame)
    "gate_growth_px": 20.0,       # + per frame without a match, scaled by the candidate's confidence
    "max_missed": 15,             # frames without a match before the track is dropped
    "switch_frames": 3,           # re-acquire elsewhere after this many frames with a confident candidate outside the gate
    "max_gap": 10,                # fill gaps up to this many frames within a track segment
    "outlier_px": 25.0,           # a weak detection this far off the smoothed path is dropped, unless supported
    "corner_dv_px": 5.0,          # kick corner: velocity change (px / frame) where the path may change direction
    "kick_vel_px": 30.0,          # expected kick speed (px / frame): widens the gate after a touch
    "player_hint": True,          # ball at a player's foot -> a kick may happen there (needs a player tracker)
    "foot_reach": 1.5,            # "at a player's foot": within this many player box widths of the foot point
    "confirm_frames": 4,          # weak detections needed to confirm a provisional track
    "tentative_gate_px": 30.0,    # association radius of a provisional track (px / frame)
    "tentative_max_missed": 2,    # frames a provisional track may go unseen
    "reacquire_px": 60.0,         # starting this close to the last known ball position: accepted
    "reacquire_growth_px": 15.0,  # further away: must move, and start within a radius growing by this per frame
    "reacquire_max_px": 400.0,    # ... up to this
    "min_move_px": 20.0,          # "moving": distance covered along the longest recent smooth run
    "tentative_resid_px": 6.0,    # ... which must fit a constant-velocity line within this RMS (px)
    "tentative_skip_body": 0.75,  # provisional tracks ignore weak candidates on the upper part of a player box
    "accel_px": 4.0,              # Kalman process noise: ball acceleration std (px / frame^2)
    "meas_px": 2.0,               # Kalman measurement noise of a conf=1 detection (px), scales with 1 / conf
    "static_filter": True,        # drop ball candidates that never move (cones, spare balls, markings)
    "static_radius_px": 12.0,     # "same spot": within this radius
    "static_min_hits": 60,        # ... for at least this many frames
    "static_min_span": 150,       # ... spanning more than this many frames
    "min_fps": 10.0,              # below this decoding rate the ball is not tracked
}

BALL_TRACKER_DEFAULTS = {
    "kalman": default_kalman_ball_params
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


class KalmanBallTrackerParamsSerializer(serializers.Serializer):
    min_conf = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    init_conf = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    gate_px = serializers.FloatField(required=False, min_value=0.0)
    gate_growth_px = serializers.FloatField(required=False, min_value=0.0)
    max_missed = serializers.IntegerField(required=False, min_value=1)
    switch_frames = serializers.IntegerField(required=False, min_value=1)
    max_gap = serializers.IntegerField(required=False, min_value=0)
    outlier_px = serializers.FloatField(required=False, min_value=0.0)
    corner_dv_px = serializers.FloatField(required=False, min_value=0.0)
    kick_vel_px = serializers.FloatField(required=False, min_value=0.0)
    player_hint = serializers.BooleanField(required=False)
    foot_reach = serializers.FloatField(required=False, min_value=0.0)
    confirm_frames = serializers.IntegerField(required=False, min_value=2)
    tentative_gate_px = serializers.FloatField(required=False, min_value=0.0)
    tentative_max_missed = serializers.IntegerField(required=False, min_value=0)
    reacquire_px = serializers.FloatField(required=False, min_value=0.0)
    reacquire_growth_px = serializers.FloatField(required=False, min_value=0.0)
    reacquire_max_px = serializers.FloatField(required=False, min_value=0.0)
    min_move_px = serializers.FloatField(required=False, min_value=0.0)
    tentative_resid_px = serializers.FloatField(required=False, min_value=0.0)
    tentative_skip_body = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    accel_px = serializers.FloatField(required=False, min_value=0.0)
    meas_px = serializers.FloatField(required=False, min_value=1e-6)
    static_filter = serializers.BooleanField(required=False)
    static_radius_px = serializers.FloatField(required=False, min_value=0.0)
    static_min_hits = serializers.IntegerField(required=False, min_value=1)
    static_min_span = serializers.IntegerField(required=False, min_value=1)
    min_fps = serializers.FloatField(required=False, min_value=1.0)

    def to_internal_value(self, data):
        # a misspelt key would otherwise be dropped silently and its default used
        unknown = sorted(set(data or {}) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({"non_field_errors": [f"Unknown parameters: {unknown}."]})
        return super().to_internal_value(data)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        min_conf = attrs.get("min_conf", default_kalman_ball_params["min_conf"])
        init_conf = attrs.get("init_conf", default_kalman_ball_params["init_conf"])
        if init_conf <= min_conf:
            raise serializers.ValidationError({"init_conf": ["init_conf must be greater than min_conf."]})
        return attrs


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
        default=None,
        allow_blank=True
    )
    detector_params = DetectorParamsSerializer(required=False, default=dict)
    tracker_params = TrackerParamsSerializer(required=False, default=dict)
    # API-only for now (the frontend does not send these): a second detector instance for the ball, and the
    # ball tracker. Without ball_detector the ball candidates are the detector's ball class.
    ball_detector = serializers.ChoiceField(
        choices=BALL_DETECTOR_CHOICES,
        required=False,
        default=None,
        allow_blank=True,
        allow_null=True,
    )
    ball_detector_params = DetectorParamsSerializer(required=False, default=dict)
    ball_tracker = serializers.ChoiceField(
        choices=BALL_TRACKER_CHOICES,
        required=False,
        default="kalman",
        allow_blank=True,
        allow_null=True,
    )
    ball_tracker_params = KalmanBallTrackerParamsSerializer(required=False, default=dict)

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        detector = data.get("detector", "yolox")
        tracker = data.get("tracker", "bytetrack")
        
        detector_params = data.get("detector_params", {})
        tracker_params = data.get("tracker_params", {})

        detector_validator = self._get_detector_validator(detector)
        detector_validator(detector_params)
        self._validate_model_files(detector, detector_params)

        data["detector_params"] = self.build_detector_runtime_params(
            detector=detector,
            user_params=detector_params,
        )
        if tracker not in (None, ""):
            tracker_validator = self._get_tracker_validator(tracker)
            tracker_validator(tracker_params)
            data["tracker_params"] = self.build_tracker_runtime_params(
                tracker=tracker,
                user_params=tracker_params,
            )
        else:
            if tracker_params:
                raise serializers.ValidationError({
                    "tracker_params": ["tracker_params cannot be provided when tracker is null or omitted."]
                })
            data["tracker_params"] = {}

        ball_detector = data.get("ball_detector")
        ball_detector_params = data.get("ball_detector_params", {})
        if ball_detector not in (None, ""):
            self._validate_as_group("ball_detector_params", self._get_detector_validator(ball_detector),
                                    ball_detector_params)
            self._validate_as_group("ball_detector_params", lambda p: self._validate_model_files(ball_detector, p),
                                    ball_detector_params)
            data["ball_detector_params"] = self.build_ball_detector_runtime_params(
                detector=ball_detector,
                user_params=ball_detector_params,
            )
        else:
            if ball_detector_params:
                raise serializers.ValidationError({
                    "ball_detector_params": ["ball_detector_params cannot be provided when ball_detector is null or omitted."]
                })
            data["ball_detector"] = None
            data["ball_detector_params"] = {}

        ball_tracker = data.get("ball_tracker")
        ball_tracker_params = data.get("ball_tracker_params", {})
        if ball_tracker not in (None, ""):
            data["ball_tracker_params"] = self._merge_with_presets(BALL_TRACKER_DEFAULTS, ball_tracker, ball_tracker_params)
        else:
            if ball_tracker_params:
                raise serializers.ValidationError({
                    "ball_tracker_params": ["ball_tracker_params cannot be provided when ball_tracker is null."]
                })
            data["ball_tracker"] = None
            data["ball_tracker_params"] = {}

        return data

    @classmethod
    def build_ball_detector_runtime_params(
        cls,
        detector: str,
        user_params: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """ The detector preset with the ball overrides (classes, confidence floor), then the user's values. """
        params = deepcopy(dict(DETECTOR_DEFAULTS[detector]))
        params.update(deepcopy(BALL_DETECTOR_OVERRIDES[detector]))
        if user_params:
            params.update(dict(user_params))
        return cls._normalize_detector_params(detector, params)

    @staticmethod
    def _validate_as_group(group_name: str, validator, params: Mapping[str, Any]) -> None:
        """ Run a detector_params validator on another parameter group, reporting errors under that group. """
        try:
            validator(params)
        except serializers.ValidationError as ex:
            detail = ex.detail.get("detector_params", ex.detail) if isinstance(ex.detail, dict) else ex.detail
            raise serializers.ValidationError({group_name: detail})

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
        return params

    # Model files are fixed per detector preset: weights are unpickled when loaded, so a
    # client must never choose the file.
    MODEL_FILE_KEYS = ("checkpoint", "model_path", "model_checkpoint")

    def _validate_model_files(self, detector: str, params: Mapping[str, Any]) -> None:
        preset = DETECTOR_DEFAULTS[detector]
        for key in self.MODEL_FILE_KEYS:
            if key in params and params[key] != preset.get(key):
                self._raise_field_error(
                    "detector_params",
                    key,
                    f"Only the preset {key} of detector '{detector}' is allowed.",
                )

    def _get_detector_validator(self, detector: str):
        mapping = {
            "yolox": self._validate_yolox_params,
            "yolo10": self._validate_yoloultra_params,
            "yolo11": self._validate_yoloultra_params,
            "yolo12": self._validate_yoloultra_params,
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
            "classes",
            "num_classes",
            "decode",
            "test_size",
            "model_path",
            "model_checkpoint",
            "confidence_threshold",
            "output_class_mapping"
        }
        self._reject_unknown_keys("detector_params", params, allowed)

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
            "output_class_mapping"
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
            "output_class_mapping"
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
            "output_class_mapping"
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