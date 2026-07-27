from pathlib import Path
from rest_framework import serializers
from backend.plugin_manager import PluginManager


MODEL_CHOICES = [
    "osnet_x1_0", 
    "osnet_ibn_x1_0", 
    "osnet_ain_x1_0"
]


MODEL_CHECKPOINTS = [
    # Trained on multiple sources for domain generalization:
    "/models/reid/osnet_x1_0_ms_d_c.pth",
    "/models/reid/osnet_ain_ms_d_c.pth",
    "/models/reid/osnet_ibn_ms_d_c.pth",
    # TODO: test sportsreid package:
    # "/models/reid/model.osnet.pth.tar-10",
    # "/models/reid/model.deit_s.pth.tar-16",
    # "/models/reid/model_soup.deit_l.pth",
]


@PluginManager.export_serializer("osnet_reid")
class OSNetReIdentificationSerializer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(required=True)
    
    model_name = serializers.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        default="osnet_x1_0",
    )
    checkpoint = serializers.CharField(
        required=False, 
        allow_blank=False,
        default="/models/reid/osnet_x1_0_ms_d_c.pth")
    
    # TODO: integrate for sportsreid checkpoints
    # def validate(self, attrs):
    #     model_name = attrs["model_name"]
    #     checkpoint = attrs["checkpoint"]

    #     filename = Path(checkpoint).name
    #     if not filename.startswith(f"{model_name}_"):
    #         raise serializers.ValidationError(
    #             {
    #                 "checkpoint_path": (
    #                     f"Checkpoint '{checkpoint}' does not belong to model '{model_name}'."
    #                 )
    #             }
    #         )

    #     return attrs
    
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
        default=0.72,
        min_value=0.6,
        max_value=0.9,
    )
    # when to update proto 
    update_threshold = serializers.FloatField( # [0.85-0.9]
        required=False,
        default=0.85,
        min_value=0.85,
        max_value=0.95,
    )
    # EMA prototype drift 
    ema_alpha = serializers.FloatField( # [0.98-0.99]
        required=False,
        default=0.98,
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
        default=120,
        min_value=90,
        max_value=300
    )
    
    # NOTE: crop_size_x & crop_size_y need to be set according to the crop size used by the embedding model!
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