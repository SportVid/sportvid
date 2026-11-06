from rest_framework import serializers
from backend.plugin_manager import PluginManager
from .reid_models import DEFAULT_REID_PRESET, REID_PRESET_CHOICES, fit_crop_size, reid_amp, reid_model


CLUSTERING_ALGORITHM_CHOICE = ["KMEANS", "HDBSCAN"]
HDBSCAN_METRIC_CHOICE = ["euclidean", "cosine"]


# Defaults: KMeans into K=3 clusters of the OSNet-AIN embeddings alone; the two largest are the teams and the
# tracks of the third get no team.
# The frontend sends its own values for most of these (usePluginParams.js), but not hsv_only / embedding_only.
@PluginManager.export_serializer("team_clustering")
class TeamClusteringSeriaizer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(
        required=False,
        default=None
    )

    clustering_algo = serializers.ChoiceField(
        choices=CLUSTERING_ALGORITHM_CHOICE,
        required=False,
        default="KMEANS",
    )

    K = serializers.IntegerField(
        required=False,
        default=3,
        min_value=2,
        max_value=16
    )
    # the num_teams most populous clusters are the teams (largest first), the others get no team (-1)
    num_teams = serializers.IntegerField(
        required=False,
        default=2,
        min_value=1,
        max_value=16
    )

    use_pca = serializers.BooleanField(
        required=False,
        default=False
    )
    pca_components = serializers.IntegerField(
        required=False,
        default=16,
        min_value=2,
        max_value=128
    )

    metric = serializers.ChoiceField(
        choices=HDBSCAN_METRIC_CHOICE,
        required=False,
        default="euclidean",
    )
    two_channel = serializers.BooleanField(
        required=False,
        default=True
    )
    # features per crop: colour only (hsv_only), colour + ReID embedding weighted by color_weight / reid_weight
    # (hsv_only: false), or the embedding alone (embedding_only, overrides hsv_only)
    hsv_only = serializers.BooleanField(
        required=False,
        default=True
    )
    embedding_only = serializers.BooleanField(
        required=False,
        default=True
    )
    # the embedding (reid_models.py); its model file is fixed per preset
    reid_preset = serializers.ChoiceField(
        choices=REID_PRESET_CHOICES,
        required=False,
        default=DEFAULT_REID_PRESET
    )
    # fp16 autocast of the embeddings (CUDA only); null: the preset's setting
    reid_amp = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None
    )
    # number depends on number of detections in the video
    min_cluster_size = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=100
    )
    # merges smaller clusters
    cluster_selection_epsilon = serializers.FloatField(
        required=False,
        default=0.5,
        min_value=0.01,
        max_value=0.99
    )

    # HSV bins
    hist_h_bins = serializers.IntegerField(
        required=False,
        default=16,
        min_value=4
    )
    hist_s_bins = serializers.IntegerField(
        required=False,
        default=4,
        min_value=1
    )
    hist_v_bins = serializers.IntegerField(
        required=False,
        default=4,
        min_value=1
    )

    use_illumination_norm = serializers.BooleanField(
        required=False,
        default=True
    )
    use_green_mask = serializers.BooleanField(
        required=False,
        default=True
    )
    use_gray_mask = serializers.BooleanField(
        required=False,
        default=True
    )
    use_torso_crop = serializers.BooleanField(
        required=False,
        default=True
    )
    use_central_band = serializers.BooleanField(
        required=False,
        default=True
    )

    min_pixels = serializers.IntegerField(
        required=False,
        default=40,
        min_value=12
    )
    # boxes smaller than this (px, before the crop offsets) are not sampled (the ReID crop gate)
    min_box_w = serializers.IntegerField(
        required=False,
        default=16,
        min_value=1
    )
    min_box_h = serializers.IntegerField(
        required=False,
        default=32,
        min_value=1
    )
    # minimum size of the resized crop and of its torso region
    min_crop_w = serializers.IntegerField(
        required=False,
        default=8,
        min_value=6
    )
    min_crop_h = serializers.IntegerField(
        required=False,
        default=16,
        min_value=12
    )
    min_samples_per_track = serializers.IntegerField(
        required=False,
        default=2,
        min_value=1
    )
    max_samples_per_track = serializers.IntegerField(
        required=False,
        default=15,
        min_value=5
    )

    n_init = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1
    )
    random_state = serializers.IntegerField(
        required=False,
        default=42
    )

    # NOTE. weighting coefficients
    color_weight = serializers.FloatField(
        required=False,
        default=1.0,
        min_value=0.1,
        max_value=1.0
    )
    reid_weight = serializers.FloatField(
        required=False,
        default=0.1,
        min_value=0.1,
        max_value=1.0
    )

    # referee tracks (object_tracker's class-based team) are neither clustered nor written to the mapping, so the
    # merge keeps them as referees
    keep_referees = serializers.BooleanField(
        required=False,
        default=True
    )
    # bystander tracks (pitch_filter marks the tracks off the pitch so) are neither clustered nor written to the
    # mapping either, so they stay bystanders. Note: a tracker run a team result was merged into carries bystanders
    # from that result too (its tracks without a team).
    skip_bystanders = serializers.BooleanField(
        required=False,
        default=True
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
    # careful: team_clustering does that inside its own logic, if use_torso_crop: true
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
        if attrs.get("clustering_algo", "KMEANS") == "KMEANS" and attrs.get("num_teams", 2) > attrs.get("K", 3):
            raise serializers.ValidationError({"num_teams": "num_teams must not exceed K."})
        # the embedding model is a fixed preset: a client never chooses a model file
        preset = attrs.get("reid_preset", DEFAULT_REID_PRESET)
        attrs["reid_model"] = reid_model(preset)
        if attrs.get("reid_amp") is None:
            attrs["reid_amp"] = reid_amp(preset)
        fit_crop_size(attrs, attrs["reid_model"]["model_name"])
        return attrs
