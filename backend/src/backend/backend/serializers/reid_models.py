"""Appearance (ReID) embedding presets, shared by object_tracker (Deep-EIoU, GTA-Link), team_clustering and
osnet_reid. A request names a preset (``reid_preset``); the model file is fixed per preset: weights are unpickled
when loaded, so a client never chooses one. The files are loaded strictly, so each fits its ``model_name``."""

REID_PRESETS = {
    # torchreid OSNets trained on MSMT17 + DukeMTMC + CUHK03 (MS+D+C, pedestrians)
    "osnet_ain": {"model_name": "osnet_ain_x1_0", "model_path": "/models/reid/osnet_ain_ms_d_c.pth.tar"},
    "osnet_x1_0": {"model_name": "osnet_x1_0", "model_path": "/models/reid/osnet_x1_0_ms_d_c.pth.tar"},
    "osnet_ibn": {"model_name": "osnet_ibn_x1_0", "model_path": "/models/reid/osnet_ibn_ms_d_c.pth.tar"},
    # OSNet x1.0 trained on SportsMOT (basketball, volleyball, football players): Deep-EIoU's own embedding
    "osnet_sportsmot": {"model_name": "osnet_x1_0", "model_path": "/models/reid/sports_model.pth.tar-60"},
    # sportsreid DeiT-L model soup (SoccerNet ReID): 224x224 input, fp16 autocast on CUDA, much slower than an OSNet
    "deit_l_sportsreid": {"model_name": "deit_l_16_ls", "model_path": "/models/reid/model_soup.deit_l.pth",
                          "amp": True},
}
DEFAULT_REID_PRESET = "osnet_ain"
REID_PRESET_CHOICES = list(REID_PRESETS)

# Deep-EIoU / GTA-Link settings that go with an embedding, whose cosine distances are on its own scale. Applied to
# the tracker preset before the request's own values, so a request can still set each of them.
REID_TRACKER_DEFAULTS = {
    "deit_l_sportsreid": {"appearance_thresh": 0.35, "gta_link": {"merge_dist_thres": 0.5, "eps": 0.7}},
}


def reid_model(preset: str) -> dict:
    """``{model_name, model_path}`` of a preset."""
    p = REID_PRESETS[preset]
    return {"model_name": p["model_name"], "model_path": p["model_path"]}


def reid_amp(preset: str) -> bool:
    return bool(REID_PRESETS[preset].get("amp", False))


def reid_input_size(model_name: str):
    """The (h, w) input an architecture requires, or None for any size (OSNet). Mirrors
    inference_ray's ``tracker.appearance.reid_input_size``: the sportsreid DeiTs / ViTs take 224x224."""
    return (224, 224) if model_name.startswith(("deit", "vit")) else None


def fit_crop_size(attrs: dict, model_name: str) -> None:
    """Set ``crop_size_x`` / ``crop_size_y`` to the model's fixed input, if it has one (the plugins refuse other
    crop sizes for it)."""
    size = reid_input_size(model_name)
    if size is not None:
        attrs["crop_size_y"], attrs["crop_size_x"] = size
