from rest_framework import serializers
from backend.plugin_manager import PluginManager


CLUSTERING_ALGORITHM_CHOICE = ["KMEANS", "HDBSCAN"]
HDBSCAN_METRIC_CHOICE = ["euclidean", "cosine"]


@PluginManager.export_serializer("team_clustering")
class TeamClusteringSeriaizer(serializers.Serializer):
    object_tracker_id = serializers.UUIDField(
        required=False,
        default=None
    )
    osnet_reid_id = serializers.UUIDField(
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
        default=2,
        min_value=2,
        max_value=16
    )
    
    use_pca = serializers.BooleanField(
        required=False,
        default=True
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
    hsv_only = serializers.BooleanField(
        required=False,
        default=True
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
        default=False
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
    min_crop_w = serializers.IntegerField(
        required=False,
        default=12,
        min_value=6
    )
    min_crop_h = serializers.IntegerField(
        required=False,
        default=24,
        min_value=12
    )
    min_samples_per_track = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1
    )
    max_samples_per_track = serializers.IntegerField(
        required=False,
        default=15,
        min_value=5
    )

    n_init = serializers.IntegerField(
        required=False,
        default=20,
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