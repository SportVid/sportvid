from rest_framework import serializers
from backend.plugin_manager import PluginManager
from .reid_models import REID_PRESET_CHOICES, REID_PRESETS, fit_crop_size, reid_amp


# The embedding is a preset (reid_models.py, ``reid_preset``). Older clients name an architecture instead
# (``model_name``, the MS+D+C OSNets) and may send a checkpoint: both stay accepted, and validate() replaces the
# checkpoint with the preset's file (the weights are loaded strictly, so the file follows the model).
MODEL_PRESET = {"osnet_x1_0": "osnet_x1_0", "osnet_ibn_x1_0": "osnet_ibn", "osnet_ain_x1_0": "osnet_ain"}
MODEL_CHOICES = list(MODEL_PRESET)
MODEL_CHECKPOINT = {name: REID_PRESETS[preset]["model_path"] for name, preset in MODEL_PRESET.items()}
# only the preset files are accepted
MODEL_CHECKPOINTS = sorted({p["model_path"] for p in REID_PRESETS.values()})


# Defaults: OSNet-AIN MS+D+C (the embedding the trackers and team_clustering use) and keep_tracker_binding. The frontend sends its own values for most fields (usePluginParams.js).
@PluginManager.export_serializer("osnet_reid")
class OSNetReIdentificationSerializer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(required=True)

    # the embedding; when omitted, the preset of model_name
    reid_preset = serializers.ChoiceField(
        choices=REID_PRESET_CHOICES,
        required=False,
        default=None,
        allow_null=True,
    )
    model_name = serializers.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        default="osnet_ain_x1_0",
    )
    # accepted for older clients; validate() replaces it with the preset's file
    checkpoint = serializers.ChoiceField(
        choices=MODEL_CHECKPOINTS,
        required=False,
        default=MODEL_CHECKPOINT["osnet_ain_x1_0"])
    # fp16 autocast of the embeddings (CUDA only); null: the preset's setting
    reid_amp = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None,
    )
    
    gallery_mode = serializers.ChoiceField(
        choices=['tracks', 'protos'],
        required=False,
        default="protos",
    )
    
    # rejects low-score matches
    # --> too high: many re-entries get assigned "new" IDs
    # --> too low: might merge different players
    match_thresh = serializers.FloatField( # [0.6-0.75]
        required=False,
        default=0.6,
        min_value=0.6,
        max_value=0.9,
    )
    # when to update proto 
    update_threshold = serializers.FloatField( # [0.85-0.9]
        required=False,
        default=0.88,
        min_value=0.85,
        max_value=0.95,
    )
    # EMA prototype drift 
    ema_alpha = serializers.FloatField( # [0.98-0.99]
        required=False,
        default=0.99,
        min_value=0.98,
        max_value=0.99,
    )
    
    # rejects ambiguous matches when best and second-best are too close
    margin = serializers.FloatField( # [0.05-0.08]
        required=False,
        default=0.06,
        min_value=0.05,
        max_value=0.08,
    )
    prototype_weight = serializers.FloatField( # [0.65-0.85]
        required=False,
        default=0.70,
        min_value=0.65,
        max_value=0.8,
    )
    cache_weight = serializers.FloatField( # [0.2-0.35]
        required=False,
        default=0.3,
        min_value=0.2,
        max_value=0.35,
    )
    # cached feature representations  
    cache_size = serializers.IntegerField( # [8-12]
        required=False,
        default=10,
        min_value=8,
        max_value=12,
    )
    # prunes stale tracks after N frames
    max_missed = serializers.IntegerField( # [120-200]
        required=False,
        default=150,
        min_value=90,
        max_value=300
    )

    # global-id lifecycle (protos mode): active -> lost after active_ttl unseen frames -> retired after lost_ttl
    active_ttl = serializers.IntegerField(
        required=False,
        default=30,
        min_value=1,
    )
    lost_ttl = serializers.IntegerField(
        required=False,
        default=300,
        min_value=1,
    )
    # similarity to re-bind a lost id (below match_thresh)
    reentry_threshold = serializers.FloatField(
        required=False,
        default=0.55,
        min_value=0.0,
        max_value=1.0,
    )
    # an active id only matches within this many px of its last box
    spatial_gate_px = serializers.FloatField(
        required=False,
        default=150.0,
        min_value=1.0,
    )
    use_spatial_gate = serializers.BooleanField(
        required=False,
        default=True,
    )
    # a lost id stays bound to its tracker id, so ReID only merges tracks and never splits one
    keep_tracker_binding = serializers.BooleanField(
        required=False,
        default=True,
    )
    # boxes smaller than this (px) get no embedding and never match: too few pixels for the models
    min_box_w = serializers.IntegerField(
        required=False,
        default=16,
        min_value=1,
    )
    min_box_h = serializers.IntegerField(
        required=False,
        default=32,
        min_value=1,
    )
    
    # the embedding's crop size; replaced by the model's fixed input for the DeiT / ViT presets
    crop_size_x = serializers.IntegerField(
        required=False,
        default=128,
        min_value=5
    )
    crop_size_y = serializers.IntegerField(
        required=False,
        default=256,
        min_value=5
    )
    
    # NOTE: in case we want to crop bounding boxes, e.g. upper third or half
    crop_x1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=0.8
    )
    crop_y1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=0.8
    )
    crop_x2_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=0.8
    )
    crop_y2_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=0.8
    )

    def validate(self, attrs):
        preset = attrs.get("reid_preset") or MODEL_PRESET[attrs.get("model_name", "osnet_ain_x1_0")]
        attrs["reid_preset"] = preset
        attrs["model_name"] = REID_PRESETS[preset]["model_name"]
        attrs["checkpoint"] = REID_PRESETS[preset]["model_path"]
        if attrs.get("reid_amp") is None:
            attrs["reid_amp"] = reid_amp(preset)
        fit_crop_size(attrs, attrs["model_name"])
        return attrs
