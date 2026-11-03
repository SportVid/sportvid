import logging
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping
from rest_framework import serializers
from backend.plugin_manager import PluginManager


DETECTOR_CHOICES = ["yolox", "yolox_sn_player", "yolox_sn_ball", "yolo10", "yolo11", "yolo12", "yolo26", "rfdetr", "rtdetr"]
TRACKER_CHOICES = ["bytetrack", "deep_eiou"]
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
    "model_path": "yolox-x",      # the model family; depth, width and the number of classes come from the checkpoint
    "checkpoint": "/models/yolox/bytetrack_x_mot17.pth.tar",
    "input_format": "auto",       # auto: read from the checkpoint (legacy RGB / ImageNet, or BGR 0-255); or force one
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

# YOLOX-L fine-tuned on SoccerNet-GSR (broadcast football) for one person class, COCO initialisation, multi-scale
# training 0.8-1.6 at 736x1280 (BGR 0-255 input, tagged in the checkpoint). On the DSHS recordings (tracker/README.md)
# it beats the RF-DETR SN default: recall 0.91 / precision 0.82 vs. 0.86 / 0.81, and with Deep-EIoU -> GTA-Link it
# gives the identity numbers of default_deep_eiou_params. API-only (the frontend does not offer it).
default_yolox_sn_player_params = {
    "batch_size": 1,
    "conf_thresh": 0.35,          # the threshold it was evaluated with
    "nms_thresh": 0.45,
    "classes": [0],
    "fp16": False,
    "num_classes": 1,
    "decode": True,
    "model_path": "yolox-l",
    "checkpoint": "/models/yolox/yolox_l_sn_player.pth",
    "input_format": "auto",
    "test_size": [736, 1280],     # the training size
    "output_class_mapping": {
        -1: {
            "entity_type": "unknown",
            "default_team": -1
        },
        0: {
            "entity_type": "player",
            "default_team": 3
        }
    }
}

# YOLOX-L ball model trained on 560 px tiles of SoccerNet-GSR at native scale: it runs sliced (SAHI) and never on the
# whole frame, which would show it the ball 2-3x too small. On the DSHS recordings, with the Kalman ball tracker:
# ball recall 0.62 / 0.53 (tuning / held-out matches) vs. 0.28 / 0.23 for the RF-DETR SN default. 1920x1080 is
# 5 x 3 tiles per frame. A ball detector (ball_detector: yolox_sn_ball), or the detector of a ball-only run.
default_yolox_sn_ball_params = {
    "batch_size": 4,              # tiles per forward pass
    "conf_thresh": 0.1,           # the low confidence floor: the ball tracker gates weak candidates
    "nms_thresh": 0.45,
    "classes": [0],
    "fp16": True,                 # on CUDA only; matched fp32 on this model family
    "num_classes": 1,
    "decode": True,
    "model_path": "yolox-l",
    "checkpoint": "/models/yolox/yolox_l_sn_ball_tiles.pth",
    "input_format": "auto",
    "test_size": [576, 576],      # each 560 px tile at native scale, as trained
    "sahi": {
        "enabled": True,
        "slice_size": [560, 560],
        "full_frame": False,
    },
    "output_class_mapping": {
        0: {
            "entity_type": "ball",
            "default_team": 0
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
# is a duration (150 = 5 s at any fps). 150 was the best of 30 / 60 / 150 in a ByteTrack re-tune on amateur football
# recordings (inference_ray plugins/tracker/README.md).
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
    "yolox_sn_player": default_yolox_sn_player_params,
    "yolox_sn_ball": default_yolox_sn_ball_params,
    "yolo10": default_yolo10_params,
    "yolo11": default_yolo11_params,
    "yolo12": default_yolo12_params,
    "yolo26": default_yolo26_params,
    "rfdetr": default_rfdetr_params,
    "rtdetr": default_rtdetr_params, 
}

# Offline refinements (inference_ray plugins/tracker/refine.py), available to every tracker. The ReID model files
# are fixed presets (weights are unpickled when loaded, so a client must never choose the file).
REID_MODEL = {
    "model_name": "osnet_ain_x1_0",
    "model_path": "/models/reid/osnet_ain_ms_d_c.pth.tar",
}
# GTA-Link (third_party/gta_link): the general parameters of its README
default_gta_link_params = {
    "enabled": False,
    **REID_MODEL,
    "amp": False,                 # fp16 autocast for the embeddings
    "use_split": True,
    "min_len": 100,               # tracklets shorter than this are not split
    "eps": 0.6,                   # DBSCAN neighbourhood (cosine) when looking for identity switches
    "min_samples": 10,
    "max_k": 3,                   # at most this many sub-tracklets per tracklet
    "use_connect": True,          # upstream always runs the connect step
    "spatial_factor": 1.0,        # scales the max exit / entry distance between merged tracklets
    "merge_dist_thres": 0.4,      # merge tracklets whose mean cosine distance is below this
}
# linear interpolation of short gaps (Deep-EIoU's SportsMOT post-processing, re-implemented)
default_interpolation_params = {
    "enabled": False,
    "n_min": 5,                   # only tracks with more boxes than this
    "n_dti": 20,                  # fill gaps shorter than this many frames
    "distance_thres": 200,        # ... unless the box centre moves more than this (px) across the gap
}

# Deep-EIoU (re-implemented, inference_ray plugins/tracker/deep_eiou.py) -> GTA-Link: the best tracker on the DSHS
# recordings (deep_eiou_gta with OSNet-AIN MS+D+C in both; IDF1 0.59 / 16 IDs small M1, 0.46 / 18 Matches 2-3, on
# YOLOX-L SN detections). Tracker thresholds are upstream's SportsMOT setting; track_buffer counts frames at 30 fps.
default_deep_eiou_params = {
    "track_high_thresh": 0.6,     # first association: detections above this
    "track_low_thresh": 0.1,      # detections at or below are dropped; between low and high: second association
    "new_track_thresh": 0.7,      # an unmatched detection starts a track from this score on
    "track_buffer": 60,           # keep lost tracks this many frames at 30 fps (60 = 2 s)
    "match_thresh": 0.8,          # max fused cost of a first-round match
    "min_box_area": 10,           # output filter (px^2)
    "remove_edge_dets": False,    # drop detections touching the top / left image edge
    "with_reid": True,            # fuse appearance embeddings into the first-round cost
    "reid_model_name": REID_MODEL["model_name"],
    "reid_model_path": REID_MODEL["model_path"],
    "reid_amp": False,
    "proximity_thresh": 0.5,      # appearance only counts where the EIoU cost is at most this
    "appearance_thresh": 0.25,    # ... and the halved cosine distance at most this
    "gta_link": {**default_gta_link_params, "enabled": True},
    "interpolation": dict(default_interpolation_params),
}

TRACKER_DEFAULTS = {
    "bytetrack": {
        **default_bytetrack_params,
        "gta_link": dict(default_gta_link_params),
        "interpolation": dict(default_interpolation_params),
    },
    "deep_eiou": default_deep_eiou_params,
}

# Ball detector: another instance of a detector preset (same model files), with its own parameters. Only the
# detectors whose preset model has a ball class; the low confidence floor (0.10) is deliberate: the ball tracker gates
# weak candidates itself (min_conf / init_conf below).
BALL_DETECTOR_OVERRIDES = {
    "yolo10": {"classes": [32], "conf": 0.1},
    "yolo11": {"classes": [32], "conf": 0.1},
    "yolo12": {"classes": [32], "conf": 0.1},
    "yolo26": {"classes": [32], "conf": 0.1},
    "rtdetr": {"classes": [32], "conf": 0.1},
    "rfdetr": {"classes": ["ball"], "conf": 0.1},
    "yolox_sn_ball": {},          # a ball model already
}
BALL_DETECTOR_CHOICES = list(BALL_DETECTOR_OVERRIDES)

# Kalman ball tracker (inference_ray plugins/tracker/ball_tracker.py; the defaults it was tuned with).
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


class StrictSerializer(serializers.Serializer):
    """ Rejects keys it does not declare (DRF drops them silently, and their default would be used). """

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Expected an object."]})
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({"non_field_errors": [f"Unknown parameters: {unknown}."]})
        return super().to_internal_value(data)


# SAHI-style sliced inference (inference_ray plugins/detector/slicing.py), for any detector. The defaults are
# slicing.SliceConfig's. Costs ~(tiles + 1) plain passes per frame.
class SahiParamsSerializer(StrictSerializer):
    enabled = serializers.BooleanField(required=False)
    slice_size = serializers.ListField(      # [h, w] tile size in frame px; each tile is resized to the model input
        required=False, child=serializers.IntegerField(min_value=32), min_length=2, max_length=2)
    overlap = serializers.ListField(         # [h, w] min. overlap ratio of neighbouring tiles
        required=False, child=serializers.FloatField(min_value=0.0, max_value=0.95), min_length=2, max_length=2)
    full_frame = serializers.BooleanField(required=False)   # also detect on the whole frame
    tile_batch_size = serializers.IntegerField(required=False, allow_null=True, min_value=1)  # null: batch_size
    tile_classes = serializers.ListField(    # keep only these raw class ids from the tiles; null -> all
        required=False, allow_null=True, child=serializers.IntegerField(min_value=0))
    merge = serializers.ChoiceField(choices=["nmm", "nms"], required=False)
    match_metric = serializers.ChoiceField(choices=["ios", "iou"], required=False)
    match_threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    class_agnostic = serializers.BooleanField(required=False)


# the values a run gets for every sahi key that neither the preset nor the request sets
SAHI_DEFAULTS = {
    "enabled": False,
    "slice_size": [560, 560],
    "overlap": [0.2, 0.2],
    "full_frame": True,
    "tile_batch_size": None,
    "tile_classes": None,
    "merge": "nmm",                 # nmm: union of the matched boxes (SAHI default) | nms: keep the best box
    "match_metric": "ios",          # ios: intersection over the smaller box, matches boxes cut by a tile border | iou
    "match_threshold": 0.5,
    "class_agnostic": False,
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
    input_format = serializers.ChoiceField(choices=["auto", "legacy", "bgr255"], required=False)
    sahi = SahiParamsSerializer(required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if "confidence_threshold" in attrs:
            if "conf" in attrs or "conf_thresh" in attrs:
                raise serializers.ValidationError({
                    "confidence_threshold": [
                        "Use either confidence_threshold or a backend-specific confidence field, not both."
                    ]
                })
        return attrs

class GTALinkParamsSerializer(StrictSerializer):
    enabled = serializers.BooleanField(required=False)
    amp = serializers.BooleanField(required=False)
    use_split = serializers.BooleanField(required=False)
    min_len = serializers.IntegerField(required=False, min_value=1)
    eps = serializers.FloatField(required=False, min_value=0.0, max_value=2.0)
    min_samples = serializers.IntegerField(required=False, min_value=1)
    max_k = serializers.IntegerField(required=False, min_value=1)
    use_connect = serializers.BooleanField(required=False)
    spatial_factor = serializers.FloatField(required=False, min_value=0.0)
    merge_dist_thres = serializers.FloatField(required=False, min_value=0.0, max_value=2.0)


class InterpolationParamsSerializer(StrictSerializer):
    enabled = serializers.BooleanField(required=False)
    n_min = serializers.IntegerField(required=False, min_value=0)
    n_dti = serializers.IntegerField(required=False, min_value=2)
    distance_thres = serializers.FloatField(required=False, min_value=0.0)


class TrackerParamsSerializer(StrictSerializer):
    """ ByteTrack. """
    track_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    track_buffer = serializers.IntegerField(required=False, min_value=1)
    match_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    mot20 = serializers.BooleanField(required=False)
    aspect_ratio_thresh = serializers.FloatField(required=False, min_value=0.0)
    min_box_area = serializers.FloatField(required=False, min_value=0.0)
    gta_link = GTALinkParamsSerializer(required=False)
    interpolation = InterpolationParamsSerializer(required=False)


class DeepEIoUParamsSerializer(StrictSerializer):
    track_high_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    track_low_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    new_track_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    track_buffer = serializers.IntegerField(required=False, min_value=1)
    match_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    min_box_area = serializers.FloatField(required=False, min_value=0.0)
    remove_edge_dets = serializers.BooleanField(required=False)
    with_reid = serializers.BooleanField(required=False)
    reid_amp = serializers.BooleanField(required=False)
    proximity_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    appearance_thresh = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    gta_link = GTALinkParamsSerializer(required=False)
    interpolation = InterpolationParamsSerializer(required=False)

    def validate(self, attrs):
        low = attrs.get("track_low_thresh", default_deep_eiou_params["track_low_thresh"])
        high = attrs.get("track_high_thresh", default_deep_eiou_params["track_high_thresh"])
        if low >= high:
            raise serializers.ValidationError({"track_low_thresh": ["track_low_thresh must be below track_high_thresh."]})
        return attrs


def json_safe(value):
    """ Validated data (OrderedDicts, nested) as plain dicts / lists. """
    if isinstance(value, Mapping):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


TRACKER_PARAM_SERIALIZERS = {
    "bytetrack": TrackerParamsSerializer,
    "deep_eiou": DeepEIoUParamsSerializer,
}


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
    # validated per tracker in validate() (TRACKER_PARAM_SERIALIZERS); deep_eiou is API-only for now
    tracker_params = serializers.DictField(required=False, default=dict)
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
            tracker_params = self._validated_group("tracker_params", TRACKER_PARAM_SERIALIZERS[tracker], tracker_params)
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
        presets = {detector: {**deepcopy(dict(DETECTOR_DEFAULTS[detector])), **deepcopy(BALL_DETECTOR_OVERRIDES[detector])}}
        return cls._normalize_detector_params(detector, cls._merge_with_presets(presets, detector, user_params))

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
    def _validated_group(group_name: str, serializer_cls, params: Mapping[str, Any]) -> Dict[str, Any]:
        s = serializer_cls(data=params)
        if not s.is_valid():
            raise serializers.ValidationError({group_name: s.errors})
        return json_safe(s.validated_data)

    @staticmethod
    def _merge_with_presets(
        presets: Mapping[str, Mapping[str, Any]],
        key: str,
        user_params: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        merged = deepcopy(dict(presets[key]))
        for k, v in dict(user_params or {}).items():
            # nested groups (gta_link, interpolation) are merged key by key, so the preset's model files stay
            if isinstance(v, Mapping) and isinstance(merged.get(k), Mapping):
                merged[k] = {**merged[k], **dict(v)}
            else:
                merged[k] = v
        return merged

    @classmethod
    def _normalize_detector_params(cls, detector: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = deepcopy(params)
        if "sahi" in params:
            params["sahi"] = {**SAHI_DEFAULTS, **json_safe(params["sahi"])}

        confidence_threshold = params.pop("confidence_threshold", None)
        if confidence_threshold is not None:
            if detector.startswith("yolox"):
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
            "yolox_sn_player": self._validate_yolox_params,
            "yolox_sn_ball": self._validate_yolox_params,
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
            "deep_eiou": lambda params: None,   # DeepEIoUParamsSerializer.validate
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
            "output_class_mapping",
            "input_format",
            "sahi",
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
            "output_class_mapping",
            "sahi",
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
            "output_class_mapping",
            "sahi",
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
            "output_class_mapping",
            "sahi",
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
            "gta_link",
            "interpolation",
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