"""team_clustering parameters: the API defaults, the UI's parameter set, the fixed ReID model."""
from backend.serializers.object_tracker import REID_MODEL
from backend.serializers.team_clustering import TeamClusteringSeriaizer

# the shape the frontend sends (usePluginParams.js, its default values)
UI_PARAMS = {
    "clustering_algo": "KMEANS", "K": 2, "min_samples_per_track": 2, "max_samples_per_track": 20,
    "min_cluster_size": 3, "min_pixels": 12, "use_illumination_norm": False, "use_central_band": False,
    "use_torso_crop": False, "use_green_mask": False, "use_gray_mask": False, "two_channel": True,
    "use_pca": True, "pca_components": 16, "metric": "euclidean", "cluster_selection_epsilon": 0.5,
    "n_init": 20, "random_state": 42, "hist_h_bins": 16, "hist_s_bins": 4, "hist_v_bins": 4,
    "min_crop_w": 12, "min_crop_h": 24, "crop_size_x": 128, "crop_size_y": 256,
    "crop_x1_offset": 0, "crop_y1_offset": 0, "crop_x2_offset": 0, "crop_y2_offset": 0,
}


def validate(params):
    s = TeamClusteringSeriaizer(data=params)
    assert s.is_valid(), s.errors
    return s.validated_data


def errors(params):
    s = TeamClusteringSeriaizer(data=params)
    assert not s.is_valid()
    return s.errors


def test_api_defaults():
    data = validate({})
    # K=3 on the OSNet-AIN embeddings alone, the two largest clusters are the teams
    assert data["clustering_algo"] == "KMEANS" and data["K"] == 3 and data["num_teams"] == 2
    assert data["embedding_only"] and not data["use_pca"]
    assert data["use_green_mask"] and data["use_gray_mask"] and data["use_illumination_norm"]
    assert (data["min_box_w"], data["min_box_h"]) == (16, 32)
    assert (data["min_crop_w"], data["min_crop_h"]) == (8, 16)
    assert data["min_samples_per_track"] == 2 and data["max_samples_per_track"] == 15 and data["n_init"] == 10
    assert data["keep_referees"] and data["skip_bystanders"]


def test_ui_parameters_are_kept():
    data = validate(UI_PARAMS)
    for key, value in UI_PARAMS.items():
        assert data[key] == value, key
    # keys the UI does not send come from the defaults
    assert data["num_teams"] == 2 and (data["min_box_w"], data["min_box_h"]) == (16, 32)
    assert data["embedding_only"]


def test_reid_model_is_the_fixed_preset():
    data = validate({"embedding_only": True, "reid_model": {"model_name": "x", "model_path": "/etc/passwd"}})
    assert data["reid_model"] == REID_MODEL


def test_more_teams_than_clusters_rejected():
    assert "num_teams" in errors({"K": 2, "num_teams": 3})
    # HDBSCAN has no K
    validate({"clustering_algo": "HDBSCAN", "K": 2, "num_teams": 3})


def test_defaults_match_the_inference_plugin():
    # TeamClusteringSeriaizer and team.DEFAULTS must stay equal (loaded by path: the plugin
    # package imports Ray)
    import importlib.util
    from pathlib import Path

    path = Path(__file__).parents[2] / "inference_ray/src/inference_ray/plugins/team/clustering.py"
    spec = importlib.util.spec_from_file_location("team_clustering_defaults", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = validate({})
    data["clustering_method"] = data.pop("clustering_algo")
    for key, value in module.DEFAULTS.items():
        assert data[key] == value, key
