import json
import logging
import time
from collections import defaultdict
from typing import Callable, Dict

from data import Data, DataManager, VideoData, BboxesData, TeamsData
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder
from .tracker.tracklets import TeamId, frame_time_ms, video_meta


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

requires = {
    "video": VideoData,
    "tracklets": BboxesData,
}

provides = {
    "teams": TeamsData,
}

# the ReID model of the embeddings when a request names none (the serializer always sets it)
DEFAULT_REID_MODEL = {"model_name": "osnet_ain_x1_0", "model_path": "/models/reid/osnet_ain_ms_d_c.pth.tar"}


def _frame_ids(keys, fps: float) -> Dict[str, int]:
    """ ``bboxes`` key (frame time in ms) -> index of the decoded frame (object_tracker decodes at ``fps``). """
    ids = {}
    for key in keys:
        frame_id = round(int(key) * fps / 1000.0)
        if frame_time_ms(frame_id, fps) != int(key):
            raise ValueError(f"team_clustering: tracklet key {key} ms is no frame at {fps:g} fps.")
        ids[key] = frame_id
    return ids


@AnalyserPluginManager.export("team_clustering")
class TeamClustering(
    AnalyserPlugin,
    config=default_config,
    parameters={},
    version="0.3",
    requires=requires,
    provides=provides,
):
    """ Team per player track (``plugins/team/clustering.py``, tracker/README.md):

    1. the player tracks from the tracklets: entity id 0 (ball, untracked detections) and the ball rows are left
       out, and the referee tracks too with ``keep_referees`` (they keep object_tracker's class-based team);
    2. up to ``max_samples_per_track`` boxes per track, evenly spaced over the track, chosen from the geometry alone
       (boxes below ``min_box_w`` x ``min_box_h`` px or outside the frame do not crop);
    3. one decoding pass up to the last sampled frame: the sampled boxes are cropped (``roi_align``, as in
       ``osnet_reid``), and get their colour feature and / or OSNet-AIN embedding (``hsv_only`` / ``embedding_only``);
    4. median per track, KMeans (or HDBSCAN) into ``K`` clusters, the ``num_teams`` largest are the teams.

    Output ``teams_data``: ``{frame_time_ms: {track_id: label}}`` for every frame of a clustered track, with label
    0..num_teams-1 for a team (largest first) and -1 for no team (another cluster, or too few crops). The frontend
    merge writes ``label + 3`` (``TeamId.TEAM_LEFT`` + label) and ``TeamId.BYSTANDER`` for -1 into the tracklets.
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ):
        import numpy as np
        import torch
        from .team import TeamClusterer
        from .tracker.appearance import ReIDEncoder, reid_input_size, roi_crops, roi_windows

        cfg = dict(parameters or {})
        if "tracklets" not in inputs:
            raise ValueError("team_clustering requires 'tracklets' input.")
        if "video" not in inputs:
            raise ValueError("team_clustering requires 'video' input.")

        # the serializer's key is clustering_algo (it used to be read as clustering_method, so HDBSCAN never ran)
        cfg["clustering_method"] = cfg.get("clustering_algo", cfg.get("clustering_method", "KMEANS"))
        clusterer = TeamClusterer(cfg)
        crop_hw = (int(cfg.get("crop_size_y", 256)), int(cfg.get("crop_size_x", 128)))
        offsets = tuple(float(cfg.get(k, 0.0)) for k in
                        ("crop_x1_offset", "crop_y1_offset", "crop_x2_offset", "crop_y2_offset"))
        # the ReID crop gate on the raw box; min_crop_w / _h gate the resized crop
        min_box_w, min_box_h = float(cfg.get("min_box_w", 16)), float(cfg.get("min_box_h", 32))
        skip_teams = {int(TeamId.BALL)} | ({int(TeamId.REFEREE)} if cfg.get("keep_referees", True) else set())
        device = "cuda" if torch.cuda.is_available() else "cpu"

        encoder = None
        if clusterer.uses_embeddings:
            reid = cfg.get("reid_model") or DEFAULT_REID_MODEL
            size = reid_input_size(reid["model_name"])
            if size and tuple(size) != crop_hw:
                raise ValueError(f"team_clustering: {reid['model_name']} takes {size[1]}x{size[0]} crops "
                                 f"(crop_size_x / _y are {crop_hw[1]}x{crop_hw[0]}).")
            encoder = ReIDEncoder(reid["model_path"], device, model_name=reid["model_name"],
                                  amp=bool(cfg.get("reid_amp", False)))

        with inputs["tracklets"] as tracklets_data:
            # frame size the tracklet boxes are normalised by (object_tracker writes video.h / video.w)
            fps, frame_h, frame_w = video_meta(json.loads(tracklets_data.meta_data or "{}"))
            tracklets_by_time = json.loads(tracklets_data.bboxes)

        # -------> 1) player tracks per decoded frame: [(track_id, tlwh px)]
        frame_ids = _frame_ids(tracklets_by_time.keys(), fps)
        frames = {}
        scale = np.array([frame_w, frame_h, frame_w, frame_h], dtype=np.float64)
        for key, rows in tracklets_by_time.items():
            players = [(int(r[0]), np.asarray(r[5:9], dtype=np.float64) * scale)
                       for r in rows if int(r[0]) != 0 and int(r[1]) not in skip_teams]
            if players:
                frames[frame_ids[key]] = (key, players)

        # -------> 2) sample from the geometry
        track_occ = defaultdict(list)    # tid -> [(frame_id, row in frames[frame_id])]
        for frame_id in sorted(frames):
            players = frames[frame_id][1]
            _, valid = roi_windows([b for _, b in players], (frame_h, frame_w), offsets, min_box_w, min_box_h)
            for k, ((tid, _), ok) in enumerate(zip(players, valid)):
                if ok:
                    track_occ[tid].append((frame_id, k))
        tasks = clusterer.sample(track_occ)
        by_frame = defaultdict(list)     # frame_id -> positions in tasks
        for i, (_, (frame_id, _)) in enumerate(tasks):
            by_frame[frame_id].append(i)
        n_tracks = len({tid for _, players in frames.values() for tid, _ in players})
        logging.info(f"team_clustering: {n_tracks} player tracks in {len(frames)} frames, {len(track_occ)} with "
                     f"crops; {len(tasks)} sampled crops in {len(by_frame)} frames.")

        # -------> 3) crop the samples while decoding; embeddings in batches
        colors = [None] * len(tasks)
        embeddings = [None] * len(tasks)
        pending_idx, pending_crops = [], []

        def flush():
            if pending_crops:
                feats = encoder.embed_crops(torch.cat(pending_crops))
                for i, feat in zip(pending_idx, feats):
                    embeddings[i] = feat
                pending_idx.clear()
                pending_crops.clear()

        last_frame = max(by_frame) if by_frame else -1
        if last_frame >= 0:
            with inputs["video"] as video_input_data:
                with video_input_data.open_video() as f_video:
                    video_decoder = VideoDecoder(
                        f_video,
                        fps=fps,
                        extension=f".{video_input_data.ext}",
                        ref_id=video_input_data.id,
                    )
                    last_reported = 0.0
                    reached = -1
                    for frame_id, frame_obj in enumerate(video_decoder):
                        if frame_id > last_frame:
                            break
                        reached = frame_id
                        ks = by_frame.get(frame_id)
                        if not ks:
                            continue
                        img = frame_obj["frame"]  # HWC uint8 RGB
                        if img.shape[:2] != (frame_h, frame_w):
                            raise ValueError(f"team_clustering: decoded frame {img.shape[:2]} != the tracklets' "
                                             f"frame {(frame_h, frame_w)}.")
                        players = frames[frame_id][1]
                        windows, _ = roi_windows([players[tasks[i][1][1]][1] for i in ks], (frame_h, frame_w), offsets)
                        crops = roi_crops(img, windows, crop_hw, device)
                        if clusterer.uses_color:
                            crops_u8 = crops.round().clamp_(0, 255).to(torch.uint8).permute(0, 2, 3, 1).cpu().numpy()
                            for i, crop in zip(ks, crops_u8):
                                colors[i] = clusterer.color_feature(crop)
                        if encoder is not None:
                            pending_idx.extend(ks)
                            pending_crops.append(crops)
                            if len(pending_idx) >= encoder.batch_size:
                                flush()
                        now = time.time()
                        if now - last_reported >= 1.0:
                            last_reported = now
                            self.update_callbacks(callbacks, progress=0.9 * (frame_id + 1) / (last_frame + 1))
            if encoder is not None:
                flush()
            if reached < last_frame:
                logging.warning(f"team_clustering: the video ended at frame {reached}, before the last sampled frame "
                                f"{last_frame}; {sum(len(by_frame[f]) for f in by_frame if f > reached)} samples lost.")
        self.update_callbacks(callbacks, progress=0.9)

        # -------> 4) per-track features, clustering
        results = [(tid, clusterer.crop_feature(colors[i], embeddings[i])) for i, (tid, _) in enumerate(tasks)]
        track_features = clusterer.track_features(results)
        track_teams = clusterer.track_teams(track_features)
        if not track_features:
            logging.warning("team_clustering: no track has enough usable crops; every track gets -1.")
        labels = [v for v in track_teams.values() if v >= 0]
        logging.info(f"team_clustering: {len(track_teams)} of {n_tracks} tracks clustered, team sizes "
                     f"{np.bincount(np.array(labels, dtype=np.int32)).tolist() if labels else []}; "
                     f"{sum(1 for f in results if f[1] is None)} of {len(results)} sampled crops abstained.")

        teams_mapping = {
            key: {tid: int(track_teams.get(tid, -1)) for tid, _ in players}
            for key, players in (frames[f] for f in sorted(frames))
        }

        with data_manager.create_data("TeamsData") as teams:
            teams.teams_data = json.dumps(teams_mapping)
            self.update_callbacks(callbacks, progress=1.0)
            return {"teams": teams}
