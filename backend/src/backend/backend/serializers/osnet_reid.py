from pathlib import Path
from rest_framework import serializers
from backend.plugin_manager import PluginManager


MODEL_CHOICES = [
    "osnet_x1_0", 
    "osnet_ibn_x1_0", 
    "osnet_ain_x1_0"
]
MODEL_CHECKPOINTS = [
    # ImageNet pretrained
    "/models/reid/osnet_x1_0_imagenet.pth",
    "/models/reid/osnet_ibn_x1_0_imagenet.pth",
    "/models/reid/osnet_ain_x1_0_imagenet.pth",
    # MSMT17 benchmark
    "/models/reid/osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
    "/models/reid/osnet_x1_0_msmt17_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip",
    "/models/reid/osnet_ibn_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
    "/models/reid/osnet_ain_x1_0_msmt17_256x128_amsgrad_ep50_lr0.0015_coslr_b64_fb10_softmax_labsmth_flip_jitter.pth",  
    # Multi-source domain generalization
    "/models/reid/osnet_x1_0_ms_d_c.pth",
    "/models/reid/osnet_ain_ms_d_c.pth",
    "/models/reid/osnet_ibn_ms_d_c.pth",
]


@PluginManager.export_serializer("osnet_reid")
class OSNetReIdentificationSerializer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(required=True)
    
    model_name = serializers.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        default="osnet_ain_x1_0",
    )
    checkpoint = serializers.CharField(
        required=False, 
        allow_blank=False,
        default="/models/reid/osnet_ain_x1_0_msmt17_256x128_amsgrad_ep50_lr0.0015_coslr_b64_fb10_softmax_labsmth_flip_jitter.pth")
    
    def validate(self, attrs):
        model_name = attrs["model_name"]
        checkpoint = attrs["checkpoint"]

        filename = Path(checkpoint).name
        if not filename.startswith(f"{model_name}_"):
            raise serializers.ValidationError(
                {
                    "checkpoint_path": (
                        f"Checkpoint '{checkpoint}' does not belong to model '{model_name}'."
                    )
                }
            )

        return attrs
    
    reid_threshold = serializers.FloatField(
        required=False,
        default=0.6,
        min_value=0.01,
        max_value=1.0,
    )
    max_missed = serializers.IntegerField(
        required=False,
        default=300,
        min_value=1
    )
    
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

    crop_x1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_y1_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_x2_offset = serializers.FloatField(
        required=False,
        default=0.,
        min_value=0.,
        max_value=1.0
    )
    crop_y2_offset = serializers.FloatField(
        required=False,
        default=0.6,
        min_value=0.,
        max_value=1.0
    )