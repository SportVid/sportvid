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
        default=3,
        min_value=2,
        max_value=100
    )
    
    use_pca = serializers.BooleanField(
        required=False,
        default=True
    )
    pca_components = serializers.IntegerField(
        required=False,
        default=50,
        min_value=2,
        max_value=1000
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
    
    min_cluster_size = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=100
    )
    cluster_selection_epsilon = serializers.FloatField(
        required=False,
        default=0.6,
        min_value=0.01,
        max_value=0.99
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