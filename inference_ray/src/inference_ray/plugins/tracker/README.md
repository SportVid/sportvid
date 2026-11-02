# Tracking in `inference_ray`: design

`object_tracker` (detection, player and ball tracking, tracklet output), `osnet_reid` and `team_clustering` form
the tracking chain. The backend runs them as separate plugin runs, chained by `object_tracker_id`. This package
holds the trackers and the tracklet format they share.

The methods and their defaults were developed and evaluated on the **DSHS recordings**: amateur football on a
small and a large pitch, filmed by static GoPro HERO11 cameras (4 per match, 3 matches per pitch, 1920×1080),
with Kinexon positional ground truth for the players and the ball. Parameters were tuned on one match of the small pitch
and confirmed on its two held-out ones. Identity is judged by IDF1 and the number of predicted IDs (10 real players
per match). That research code is called the *reference implementation* below; the ports were checked against it
(Verification).

| File | Contents |
|---|---|
| `tracker.py` | `Tracker` interface, `track_frame` state schema, `detections_xyxy_conf` |
| `bytetrack.py` | ByteTrack (`third_party/ByteTrack`) behind the interface |
| `deep_eiou.py` | Deep-EIoU, re-implemented (association + wrapper) |
| `refine.py` | offline refinements in `finalize`: GTA-Link (`third_party/gta_link`), interpolation (re-implemented) |
| `appearance.py` | `ReIDEncoder`: torchreid embeddings of boxes (OSNet-AIN by default), strict weight loading; `roi_windows` / `roi_crops`: the ReID / team crops |
| `ball_tracker.py` | Kalman ball tracker |
| `track_class_mapper.py` | per-track class votes (detector class → default team) |
| `tracklets.py` | the `BboxesData` row format, `TeamId`, metadata reading, class routing |
| `../team/clustering.py` | `TeamClusterer`: team features and clustering, used by `team_clustering.py` |
| `../detector/yolox.py`, `yolox_input.py` | YOLOX for any checkpoint (input convention, architecture, classes from the checkpoint) |
| `../detector/slicing.py` | SAHI-style sliced inference around any detector (`SlicedDetector`) |

## Steps

| Step | Content | Status |
|---|---|---|
| 0 | Bug fixes in the existing chain (below) | done |
| 1 | `object_tracker` as staged pipeline, tracker interface, ball split | done |
| 1b | ByteTrack `track_buffer` as a duration (fps scaling), default re-tuned | done |
| 2 | Kalman ball tracker; optional separate ball-detector instance | done |
| 3 | Deep-EIoU (re-implemented), GTA-Link (vendored), interpolation (re-implemented); OSNet-AIN embeddings | done |
| 4 | `team_clustering` on colour and / or ReID embeddings (`embedding_only` / `reid_weight`) | done |
| 5 | `osnet_reid`: `roi_align` crops, strict weights, vectorised gallery scores, lifecycle parameters, `keep_tracker_binding` | done |
| 6 | YOLOX: any checkpoint; SAHI tiling for every detector; presets for the SoccerNet YOLOX player and ball models | done |

Decisions (2026-11-02):

- **Deep-EIoU is re-implemented**, not vendored: its upstream repository has no license, and SportVid is GPL-3.0.
  It is BoT-SORT's association without camera motion compensation, plus the expanded IoU.
- **New trackers, stages and presets are API-only for now.** The frontend is not changed. New options are
  serializer fields and presets in `backend/serializers/object_tracker.py` that the frontend does not send. A
  ByteTrack run is never silently mapped to another tracker.
- **Third-party code lives under `inference_ray/third_party/`**, with no dependency on GitHub repositories
  (as ByteTrack and sportsreid already are). That covers GTA-Link (MIT) as well.
- **YOLOX checkpoints describe themselves.** The input convention, depth, width and number of classes are read
  from the checkpoint, so legacy (ByteTrack, MixSort, YOLOX 0.0.1) and BGR 0–255 checkpoints (YOLOX ≥ 0.1.1rc0,
  the SoccerNet fine-tunes) load the same way. The files are still the presets' (allowlist): a new checkpoint is
  a server-side preset, not a request parameter.
- **The ball detector is another instance of a detector wrapper**, with its own parameters. It is not a special
  ball model type.

## Pipeline (`object_tracker.call`)

1. **Detection** over the decoded video: the (player) detector, plus the ball detector if `ball_detector` is
   set. Both see every decoded frame, either directly or sliced (`sahi`). Detector dicts are
   `{xyxy, xywh, cls_id, conf}` in frame pixels, where `xywh` is *centre* x, y plus width, height.
2. **Routing** by `output_class_mapping`. The classes with `entity_type: ball` never reach the player tracker.
   The ball candidates come from the ball detector's ball classes when it runs, and the player detector's ball
   class is then dropped. Otherwise they are the player detector's ball class.
3. **Player tracking** (`tracker`: `bytetrack` | `deep_eiou`), frame by frame inside the detection loop, with
   the frame's pixels: Deep-EIoU embeds the detections and GTA-Link the output boxes while the frame is in
   memory, and no frame is kept after its iteration. Then `Tracker.finalize` runs once over the whole clip
   (GTA-Link, interpolation). So GTA-Link must live inside `object_tracker`, not in a separate plugin. It
   renumbers the track IDs.
4. **Default team per track** from `TrackClassMapper`'s cumulative class votes and `output_class_mapping`.
   Without a tracker (a detection-only run), the non-ball detections are written untracked (entity ID 0).
5. **Ball**: `ball_tracker: kalman` runs over the whole clip, with the player tracks as kick hints (no hints
   in a run without a player tracker). With `ball_tracker: null`, or below its `min_fps`, the candidates are
   written untracked. The ball is entity ID 0, team `BALL`.

The configuration evaluated best on the DSHS recordings, as a request:

```json
{"detector": "yolox_sn_player", "tracker": "deep_eiou", "ball_detector": "yolox_sn_ball", "ball_tracker": "kalman"}
```

### Detector contract

Every wrapper in `../detector/` sets `frame_shape` (H, W of the decoded frame) and reports boxes in frame
pixels. `object_tracker` normalises by `frame_shape` and gives the trackers frame-pixel boxes
(`image_shape == det_shape`, so BYTETracker does not rescale). The player and ball detectors share these
coordinates: the ball tracker uses the player tracks' foot points. Before this contract:

- **Ultralytics** (`yolo10/11/12/26`): `rect` pads the frame to a multiple of 32 and reported the padded size as
  the frame size, so the normalised output was off by up to 0.7 % (1080 → 1088). Without `rect`, boxes were in
  `imgsz` coordinates; they are now scaled back. A second, shadowed `preprocess` was removed.
- **RT-DETR**: the same padding issue, plus `det_shape` padded twice, which made BYTETracker shrink every box
  slightly.
- **YOLOX, RF-DETR**: already in frame pixels; unchanged.

`SlicedDetector` (SAHI) keeps the contract: its `frame_shape` is the frame's, and the tile boxes are shifted into
frame pixels.

### YOLOX checkpoints (`../detector/yolox.py`, `yolox_input.py`)

- **Input convention**: there are two.
  - *legacy*: RGB, /255, ImageNet mean / std. YOLOX 0.0.1, ByteTrack, MixSort and SportsMOT weights, e.g.
    `bytetrack_x_mot17` (the `yolox` preset).
  - *bgr255*: BGR 0–255. YOLOX 0.1.1rc0 and later, and the SoccerNet fine-tunes (`yolox_sn_*` presets).

  A checkpoint fed the other one does not fail: the SoccerNet player model gives 0 boxes per frame at
  conf ≥ 0.1 instead of 12. The old wrapper always used legacy. `input_format: auto` (default) reads the
  checkpoint's `input_format` tag, else its stem BatchNorm statistics (the conv output variance is ~3400× larger
  for 0–255 input; margin 2.7–3.4 orders of magnitude on 15 tested checkpoints). `legacy` / `bgr255` force one,
  and an error is raised if the checkpoint disagrees.
- **Architecture**: depth (CSP blocks in `dark2`), width (stem channels / 64) and `num_classes` (classifier
  outputs) come from the state dict. `model_path` (the exp name) only picks the family, so a YOLOX-L checkpoint
  loads under an exp named `yolox-x`. The load is still strict. `classes` must exist in the checkpoint;
  `num_classes` is ignored, with a warning if it disagrees.
- **Loading**: `torch.load(weights_only=True)`, with only numpy scalars / dtypes allowed besides tensors (YOLOX's
  trainer stores `best_ap` as a numpy scalar, which a plain weights-only load rejects). `module.` prefixes (DDP)
  are stripped. A missing checkpoint is an error; before, it ran with random weights.
- **Score**: `conf` is `obj × cls`, the score YOLOX's postprocess thresholds on. The old wrapper reported `cls`
  alone, so YOLOX scores, and with them ByteTrack's high / low split, change.
- **Letterbox**: the size is truncated (`int`) as in YOLOX's `preproc`, not rounded.

### YOLOX presets

| Preset | Model | Input | Evaluated on the DSHS recordings |
|---|---|---|---|
| `yolox` | ByteTrack YOLOX-X MOT17 (`bytetrack_x_mot17.pth.tar`) | legacy, exp default size | (the previous default) |
| `yolox_sn_player` | YOLOX-L fine-tuned on SoccerNet-GSR, one person class, COCO init, multi-scale 0.8–1.6 (`/models/yolox/yolox_l_sn_player.pth`) | BGR, 736×1280, conf 0.35 | recall 0.91 / precision 0.82 on the held-out matches (RF-DETR SN default: 0.86 / 0.81); with Deep-EIoU → GTA-Link the IDF1 of the Deep-EIoU section |
| `yolox_sn_ball` | YOLOX-L ball model trained on 560 px SoccerNet-GSR tiles at native scale (`/models/yolox/yolox_l_sn_ball_tiles.pth`) | BGR, 576×576 per tile, SAHI 560 px tiles, no full frame, conf 0.1, fp16 on CUDA | ball recall with the Kalman tracker 0.62 / 0.53 (tuning / held-out matches) vs. 0.28 / 0.23 for the RF-DETR SN default |

`yolox_sn_ball` is a ball detector (`ball_detector: yolox_sn_ball`) and can also be the detector of a ball-only
run. It must not see whole frames: there the ball is 2–3× smaller than in training. It costs 15 tile passes per
1920×1080 frame (5 × 3), about 4 min per minute of 30 fps video on a laptop GPU (RTX 2000 Ada, fp16).

The two checkpoint files hold the weights only, tagged `input_format: bgr255`. They are not in the repository:
every deployment needs them under `/models/yolox/` (`DATA_PATH/models/yolox/` locally).

### SAHI (`../detector/slicing.py`)

SAHI-style sliced inference (Akyon et al., 2022): tile grid, NMM / NMS merge by IoS / IoU, as the wrapper
`SlicedDetector` around any detector instance (YOLOX, Ultralytics, RF-DETR, RT-DETR), player or ball detector.
`detector_params.sahi` / `ball_detector_params.sahi`, validated by `SahiParamsSerializer` (strict). A request
overrides single keys of a preset's `sahi`; the keys neither sets come from `SAHI_DEFAULTS`:

| Field | Default | Meaning |
|---|---|---|
| `enabled` | false | |
| `slice_size` | [560, 560] | [h, w] tile in frame px; each tile is resized to the model input |
| `overlap` | [0.2, 0.2] | minimum overlap of neighbouring tiles; tiles are spread evenly (1920×1080 at 560: 5×3) |
| `full_frame` | true | also detect on the whole frame (large, near objects); false for models trained on tiles only |
| `tile_batch_size` | null | tiles per forward pass (null: `batch_size`) |
| `tile_classes` | null | keep only these raw class IDs from the tiles |
| `merge` / `match_metric` / `match_threshold` | nmm / ios / 0.5 | union of boxes cut by a tile border |
| `class_agnostic` | false | match boxes across classes |

A frame costs about (tiles + 1) plain passes, or tiles passes without `full_frame`.

### Tracker interface

`preprocess(inputs)`, `process(inputs)` appends one `track_frame` per input frame to `self.state`,
`finalize()`, and `reset_state()`. `track_frame` is `{frame_id, track_ids, track_scores, track_boxes}`, with
boxes as tlwh in frame pixels. There is no `team_ids` field: here the team comes from the class mapping.

### Deep-EIoU (`deep_eiou.py`)

A re-implementation: the upstream repository (hsiangwei0903/Deep-EIoU) has no license, so none of its code is
used. It reproduces the behaviour of upstream's SportsMOT setting (`tools/sport_track.py`), the version the DSHS
evaluation used; the module docstring lists the details. Its main properties:

- Association uses the *last detection box* of a track, enlarged by the expansion scale (Expansion IoU: 0.7, then
  0.8 for the high-score detections, 0.5 for the low-score ones), not a motion prediction. The appearance cost
  (cosine / 2) is fused by `min` where the EIoU cost is at most `proximity_thresh` and the appearance cost at most
  `appearance_thresh`.
- The Kalman filter only matters for dropping duplicate tracked / lost pairs (it is never predicted, and corrected
  only on re-finding a lost track). Output boxes are the last detection boxes.
- Quirks kept on purpose, so the evaluated results carry over: floored box expansion and inclusive-pixel IoU; a
  score exactly at `track_high_thresh` takes part in neither round; a track removed in a frame stays in the lost
  pool (and can be re-found) for one more frame; frames without detections skip the association (tracks do not
  age there).
- `track_buffer` counts frames at 30 fps and is scaled to the decoding rate, at least one frame (as ByteTrack).
- Embeddings: `appearance.ReIDEncoder` (the SportsMOT preprocessing: PIL crop of the RGB frame, resize to
  256x128, ImageNet normalisation), OSNet-AIN MS+D+C (`/models/reid/osnet_ain_ms_d_c.pth.tar`) by default, the
  best embedding in both Deep-EIoU and GTA-Link on the DSHS recordings. The weights load strictly (every layer but
  the classifier, or an error). The model is built without the ImageNet download, which the ReID weights replace.

Defaults (`default_deep_eiou_params`): upstream's thresholds (high 0.6, low 0.1, new 0.7, match 0.8, buffer 60,
proximity 0.5, appearance 0.25), ReID on, GTA-Link on with its README's general parameters, interpolation off. On
the DSHS small pitch with `yolox_sn_player` detections: IDF1 0.59 / 16 IDs on the tuning match and 0.46 / 18 on
the held-out ones. The SportsMOT OSNet instead of OSNet-AIN gave 0.50 / 24 and 0.39 / 28, and ByteTrack at
its default settings 0.24 / 109 on the tuning match.
With the RF-DETR SN default these numbers are not measured; the thresholds depend on the detector's score
distribution.

### GTA-Link and interpolation (`refine.py`)

Both run in `Tracker.finalize` and work on top of any tracker (`tracker_params.gta_link` / `.interpolation`,
each with `enabled`; on for Deep-EIoU's GTA-Link, off otherwise).

- **GTA-Link** (MIT) is vendored in `inference_ray/third_party/gta_link` (`Tracklet.py`, `refine_tracklets.py`,
  matplotlib / seaborn imported lazily; provenance in its README). It is installed through the `tracking` extra
  (`inference_ray/pyproject.toml`, path source). It embeds every output box during tracking (one 512-d float32
  vector per box, kept until `finalize`), then splits tracklets whose embeddings cluster into several identities
  (DBSCAN) and connects tracklets of one identity. Output IDs are renumbered 1..N and every score is 1 (upstream's
  output).
- **Interpolation** re-implements Deep-EIoU's `tools/sport_interpolation.py` (same license problem): gaps shorter
  than `n_dti` frames in tracks with more than `n_min` boxes are filled linearly, unless the box centre moves more
  than `distance_thres` px; a (frame, ID) pair that occurs twice is dropped first. Interpolated boxes get score 1.

### ByteTrack: `track_buffer` is a duration

`track_buffer` counts frames *at 30 fps* (upstream's convention). The wrapper passes the decoding rate to
`BYTETracker`, which keeps a lost track for `fps / 30 * track_buffer` decoded frames, at least 1. Before, the
rate never reached it, so `track_buffer` counted decoded frames: the UI's 300 kept a lost track for 5 minutes
at its default 1 fps.

- Backend default: 90 → **150** (5 s at any rate), the best of 30 / 60 / 150 in a ByteTrack re-tune on the DSHS
  recordings (together with `track_thresh` 0.6 / `match_thresh` 0.8 for YOLOX-L detections). Only the buffer is
  taken over: the thresholds depend on the detector's score distribution (YOLOX scores are compressed high), so
  they stay as they are for the RF-DETR default.
- The UI's slider default (300) now means 10 s at any rate. It is a frontend value and not changed here.
- At 30 fps nothing changes.

### Ball tracker (`ball_tracker.py`)

A single-ball tracker. A constant-velocity Kalman filter predicts where the ball should be, and the candidate
nearest the prediction, weighted by confidence, continues the track inside a confidence-scaled gate. Kicks are
allowed at player feet and at detected corners. A static-object filter, re-acquisition from weak detections and
an RTS smoother with gap filling are built in. The module docstring describes it in full.

- **Frame-based parameters are given at 30 fps** (where they were tuned) and scaled by `scale_to_fps`, with
  k = 30 / fps:
  - durations (`max_missed`, `switch_frames`, `max_gap`, `tentative_max_missed`, `static_min_span`): ÷ k, at
    least 1; `static_min_hits` ÷ k, at least 3;
  - per-frame motion (`gate_px`, `gate_growth_px`, `kick_vel_px`, `corner_dv_px`, `tentative_gate_px`,
    `reacquire_growth_px`, plus the filter's initial-velocity and kick variances): × k;
  - acceleration (`accel_px`): × k².

  Distances that do not depend on the frame step, confidences, measurement noise and `confirm_frames` (a
  number of detections) are not scaled.
- **`min_fps` (10):** below it the ball moves too far between frames to associate (at 1 fps a pass covers
  several hundred px). The candidates are then written untracked, as before, with a warning. UI ball runs
  at the UI's default 1 fps therefore give the same output as before; from 10 fps on they are tracked.
- **The pixel thresholds are not scaled with resolution.** They were tuned at the DSHS recordings' native frame
  size (1920×1080). For much smaller or larger videos, `gate_px` and the other px values may need adjusting.
- Output: at most one ball box per frame. The score is the detection confidence, or 0 for gap-filled boxes.
  Segment and status fields are not written (the row format has no field for them).

### API parameters (`ObjectTrackerSerializer`)

| Field | Default | Meaning |
|---|---|---|
| `detector` | `yolox` | a preset: `yolox`, `yolox_sn_player`, `yolox_sn_ball` (API-only), `yolo10/11/12/26`, `rfdetr`, `rtdetr` |
| `tracker` | none | `bytetrack` (UI) or `deep_eiou` (API-only) |
| `tracker_params` | the tracker's preset | validated per tracker (`TRACKER_PARAM_SERIALIZERS`), unknown keys rejected; nested `gta_link` / `interpolation` are merged key by key into the preset; the ReID model files are fixed presets, not parameters |
| `ball_detector` | none | a second detector instance for the ball: `yolox_sn_ball`, `yolo10/11/12/26`, `rtdetr`, `rfdetr` (presets with a ball class) |
| `ball_detector_params` | the preset + `BALL_DETECTOR_OVERRIDES` | merged key by key into the preset; the same model files as the preset (allowlist), ball classes only, `conf` 0.1 (the tracker gates weak candidates) |
| `ball_tracker` | `kalman` | `null` writes the candidates untracked |
| `ball_tracker_params` | `default_kalman_ball_params` | the tuned defaults, plus `min_fps`; unknown keys are rejected, and `init_conf` must exceed `min_conf` |
| `detector_params.sahi`, `ball_detector_params.sahi` | the preset's, else disabled | sliced inference around either detector (SAHI section) |
| `detector_params.input_format` | `auto` | YOLOX presets only: `auto` (from the checkpoint), `legacy` or `bgr255` (must agree with the checkpoint) |

The ball-tracker defaults exist twice: in the serializer, which validates and fills the run parameters, and in
`ball_tracker.DEFAULTS` for direct calls. They must stay equal. The frontend sends none of these fields, so a UI
run gets `ball_tracker: kalman` with the defaults and no ball detector. UI player runs request no ball class
(`usePluginParams.js`), so they have no ball candidates.

### Team clustering (`team_clustering.py`, `team/clustering.py`)

Team assignment per player track, from crops and embeddings it computes itself (it does not depend on
`osnet_reid`), for the sampled boxes only:

1. **Population**: the player tracks of the tracklets. Entity ID 0 (the ball and untracked detections) and the
   ball rows are left out. Before, the ball was clustered as "track 0" and the merge gave it a team. With
   `keep_referees` (default), tracks whose class-based team is `REFEREE` are left out as well: they are neither
   clustered nor in the mapping, so the merge keeps them as referees.
2. **Sampling** from the geometry alone, before decoding: a box crops unless it is smaller than `min_box_w` ×
   `min_box_h` (16×32, the ReID crop gate) or empty after the offsets and clipping. Up to
   `max_samples_per_track` crops are taken per track, evenly spaced over the track. The old code took the first
   20 boxes, i.e. the first second of a track.
3. **One decoding pass** that stops after the last sampled frame. Each sampled box is cropped with `roi_align`
   (bilinear, 256×128); the old code used a PIL Lanczos resize and swapped R and B of the already-RGB frame. The
   crop then gets its colour feature (HSV histogram and statistics of the masked torso) and / or its OSNet-AIN
   MS+D+C embedding (batches of 64), depending on `hsv_only` / `embedding_only`:
   - colour only (`hsv_only`, default);
   - colour ⊕ embedding, weighted by `color_weight` / `reid_weight` (`hsv_only: false`). A crop whose colour
     feature fails abstains here too (its embedding is not used alone);
   - the embedding alone (`embedding_only`). A crop abstains only below the box gate.
4. **Per track** the median feature, from `min_samples_per_track` usable crops on. Then KMeans (`K`) or
   HDBSCAN. The `num_teams` most populous clusters become teams 0, 1, … (largest first); the other clusters
   (goalkeepers, referees, outliers) and HDBSCAN noise become -1.

Output, unchanged in format: `teams_data = {frame_time_ms: {track_id: label}}`, for every frame of a track in
the population. A track that was not clustered (too few crops) is also -1. The frontend merge
(`top_view.js:mergeTeamAssignment`, not changed) writes `TeamId.TEAM_LEFT + label` for a team and `BYSTANDER`
for -1.

**Defaults** (`TeamClusteringSeriaizer` and `team.DEFAULTS`, which must stay equal) are the settings used on the
DSHS recordings: KMeans K=4 → 2 teams, colour only, green / grey masks, illumination normalisation, torso crop and
central band. With them, 63–89 % of the matched boxes got a team, 80–92 % of those the right one. On ground-truth
labelled crops of the same recordings, the embeddings separate the teams much better: 98–99 % right per crop
(KMeans K=2 on OSNet embeddings) vs. 75 % for colour, which abstains on 56 % of the crops. That has not been
confirmed end to end yet, so `embedding_only` is not the default. The UI sends its own values for most fields
(K=2, no masks, PCA on); the new fields (`num_teams`, `embedding_only`, `min_box_w/_h`, `keep_referees`,
`reid_amp`) come from the defaults. The ReID model is a fixed preset (`REID_MODEL`, the same as the trackers'),
set by the serializer; a client cannot choose it. `min_crop_w/_h` gate the resized crop, which makes them no-ops
at 256×128.

### ReID (`osnet_reid.py`, `reid/`)

Global identities across tracker IDs. `reid/gallery.py` has a vectorised score matrix, equivalent to the
per-pair loop it replaces; `reid/gid_manager.py` has `keep_tracker_binding`; both log at debug level. Per decoded
frame:

1. **Boxes**: the player rows of the tracklets. Entity ID 0 and the ball rows are left out; before, the ball got
   a global ID, which the merge then wrote over its entity ID 0. Referees are kept.
2. **Crops**: `roi_align`, as in team clustering. Before, a PIL Lanczos resize swapped R and B. The weights load
   strictly (`ReIDEncoder`) instead of through torchreid's `FeatureExtractor`, which silently keeps ImageNet
   weights for every layer that does not fit. Boxes below `min_box_w` × `min_box_h` (16×32) get a zero
   embedding and never match a prototype.
3. **Assignment**:
   - `gallery_mode: protos` uses the prototype gallery and `GlobalIDManager`, whose lifecycle parameters are now
     parameters (`active_ttl`, `lost_ttl`, `reentry_threshold`, `spatial_gate_px`, `use_spatial_gate`). Before,
     they were hard-coded, with `reentry_threshold` 0.68 instead of 0.55.
   - `keep_tracker_binding` keeps a lost ID bound to its tracker ID, so ReID only merges tracks. Without it, ReID
     split the long and gappy GTA-Link tracks on the DSHS recordings and lowered IDF1 with every model tried
     (0.50 → 0.41–0.45 on the tuning match).
   - `gallery_mode: tracks` (the plain gallery) never ran: `Gallery.match` returned `None` or the IDs alone, and
     every caller unpacked (IDs, scores). A box without an embedding continues its tracker ID's last global ID;
     its zero embedding would otherwise register a new one in every frame.

**Defaults**: the settings used on the DSHS recordings, with OSNet-AIN MS+D+C (as in the trackers and team
clustering) and `keep_tracker_binding: true`. The gallery values are not tuned yet. The UI sends its own values
for the gallery fields (`match_thresh` 0.72, …) and `model_name: osnet_x1_0`.

The checkpoint follows `model_name` (`MODEL_CHECKPOINT`). The UI always sends `osnet_x1_0`'s checkpoint (a hidden
field), so selecting OSNet-AIN or IBN in the UI used to load OSNet x1.0 weights into that architecture. The
AIN choice in the allowlist was also misspelt (`.pt.tarh`). It is still accepted, and replaced like every value.

Output: `mapping = {frame_time_ms: {track_id: global_id}}`, which the frontend's `mergeReid` reads, as before. The
per-frame arrays are still written but are not read anywhere: `tracks` (the player rows, now normalised as in the
tracklets), `reid_ids` and `features`. `reid_ids` is now int64; it was an object array, so `tobytes()` stored
memory addresses.

### CPU-only deployments

`deploy.yml`, for local development without a GPU, runs the same image (`inference_ray/Dockerfile`, CUDA torch,
which runs on the CPU too) without GPU resources. Every model in the chain falls back to the CPU when CUDA is not
available: the detectors, `ReIDEncoder` (Deep-EIoU, GTA-Link, team clustering, ReID), `roi_align` and GTA-Link's
distance step. AMP and fp16 are only used on CUDA. All checks below were also run with CUDA hidden
(`CUDA_VISIBLE_DEVICES=""`, the reference implementation on the CPU as well), with the same results. CPU runs are
slow: every player box is embedded once in Deep-EIoU, once more in GTA-Link and once in `osnet_reid`, and SAHI
multiplies the detector passes. Results on CPU and GPU can differ in near-ties (see below).

### Tracklet format (`tracklets.py`)

`bboxes` is `{frame_time_ms: [[entity_id, team_id, 0, x_center, y_bottom, x, y, w, h, score], ...]}`.
Coordinates are normalised by the frame size; `x, y` is the top-left corner. `meta_data` holds:

- `team_ids`: all six `TeamId`s, as before, so the editor can assign teams before `team_clustering` has run;
- `player_ids` / `ref_ids` / `ball_ids`: from `data.compute_bboxes_meta`, the same scheme the bbox editor
  writes after an edit. The function used to be private to `backend/views/bounding_boxes.py` and now lives in
  `packages/data`, used by both;
- `video: {fps, h, w}`: the decoding rate and the frame size the boxes are normalised by. Readers use
  `video_meta()`.

## Changes

| # | Problem | Fix | Output change |
|---|---|---|---|
| 1 | `osnet_reid` and `team_clustering` read `video.detector_h/_w`, which `object_tracker` never wrote. Crops were taken at 1920×1080 scale for every video. | Read `video.h/w` via `video_meta()` (the old keys remain a fallback). | ReID / team crops correct for non-1080p videos |
| 2 | Untracked (ball) detections took the centre `xywh` as top-left: boxes shifted by half their size. | `center_to_tlwh` | ball boxes in the right place |
| 3 | `player_ids` metadata gave every player the team of the last box written (all players were team 2 = Referee in the test). Referees and ball tracks were listed as players. | `compute_bboxes_meta` | per-player teams; `ref_ids` / `ball_ids` filled |
| 4 | `osnet_reid` declared `requires={video}`, `provides={tracklets}`, but reads `tracklets` and returns `reids`. The analyser cache looks results up by `provides`, so it could never hit. | `requires={video, tracklets}`, `provides={reids: ReIDData}` | cache can work |
| 5 | A frame without any detection crashed every tracked run (1-D `np.array([])` in `hstack`). | `detections_xyxy_conf` builds `(0, 5)`. `update` still runs, so lost tracks age. | runs with empty frames complete |
| 6 | ByteTrack's ID counter is class-level, so a second run in the same Ray replica continued the first run's numbering. | reset `BaseTrack._count` per tracker | the same input gives the same IDs |
| 7 | Player boxes were truncated with `int()` before normalisation (up to 1 px per coordinate, ~3 % of a far player's height). | removed | boxes up to 1 px different |
| 8 | Ball-class detections went into the player tracker. | routing (stage 2) | API runs whose classes include the ball: the ball is ID 0 instead of ByteTrack IDs. UI player runs are not affected (no ball class requested). |
| 9 | The decoding rate never reached ByteTrack: `track_buffer` counted decoded frames. | `frame_rate` passed, buffer ≥ 1 frame, default 150 | lost tracks kept for the same time at any fps; unchanged at 30 fps |
| 10 | The Ultralytics wrapper appended one state entry *per detection*, and none for a frame whose detections were all filtered out. Every YOLO10/11/12/26 run (including the UI's default ball detector, yolo11) misaligned frames and times. | one entry per frame | Ultralytics boxes at the right time |
| 11 | Ultralytics (`rect`) and RT-DETR normalised by the padded frame size; RT-DETR's `det_shape` was padded twice. Ultralytics without `rect` reported `imgsz` coordinates. | detector contract (`frame_shape`, frame-pixel boxes) | ≤ 0.7 % box offsets fixed; RT-DETR tracks slightly different |
| 12 | Ball runs wrote every ball detection (several per frame, clutter included). | Kalman ball tracker | from 10 fps on: one ball per frame, gaps filled, clutter and static decoys dropped |
| 13 | Player tracking ran after the detection loop, without pixels. | tracking inside the loop, with the frame | none for ByteTrack (same order of updates) |
| 14 | `tracker_params` went through a ByteTrack-only nested serializer, which silently dropped unknown keys. | per-tracker serializers that reject unknown keys | a misspelt key is an error; the UI's keys are all known |
| 15 | `team_clustering` read `clustering_method`, but the serializer and UI send `clustering_algo`: HDBSCAN never ran. `hsv_only` / `color_weight` / `reid_weight` were accepted and ignored. | `clustering_algo` read; the feature modes | the UI's HDBSCAN choice takes effect |
| 16 | The ball and untracked detections (entity 0) were clustered as one track, and the merge overwrote the ball's team. Referee tracks were clustered and lost their referee team. | entity 0 / ball rows left out; `keep_referees` | the ball and referees keep object_tracker's team |
| 17 | Team crops: R and B swapped (`cvtColor(BGR2RGB)` on RGB frames), Lanczos resize, the first 20 boxes of a track. With K > 2, clusters 2… became team IDs 5… in the merge. | `roi_align` crops, even sampling, `num_teams` | different team features; at most `num_teams` teams |
| 18 | `osnet_reid` read `match_threshold`, the serializer and UI send `match_thresh`: the UI's match threshold never applied. The ID lifecycle was hard-coded. | `match_thresh` read; lifecycle parameters | the UI's threshold takes effect |
| 19 | ReID: the checkpoint did not follow `model_name` (the UI selects AIN / IBN with osnet_x1_0's weights), the AIN path was misspelt, and torchreid silently kept ImageNet weights for unloaded layers. R and B swapped, Lanczos crops. | checkpoint from `model_name`, strict loading, `roi_align` | the selected model is the one that runs (or the run fails) |
| 20 | ReID gave the ball (entity 0) a global ID. `gallery_mode: tracks` crashed on the first frame. `reid_ids` were stored as object pointers. Per-frame `error` logging. | entity 0 left out; `Gallery.match` returns (IDs, scores); int64; debug | the ball keeps ID 0; `tracks` mode runs |
| 21 | YOLOX always fed the legacy input: BGR 0–255 checkpoints detected nothing. `conf` was the class score alone. A missing checkpoint ran with random weights; YOLOX trainer checkpoints failed `torch.load` under torch ≥ 2.6 (numpy scalars). | input convention, architecture and classes from the checkpoint; `obj × cls`; weights-only load with numpy scalars | any YOLOX checkpoint loads; YOLOX scores are `obj × cls` |
| 22 | No sliced inference; no preset for the SoccerNet YOLOX models. | `SlicedDetector`, `sahi` for every detector; `yolox_sn_player`, `yolox_sn_ball` | small objects (the ball) at native resolution |

**Plugin versions** are part of the analyser's cache key. Every plugin whose output changes must bump its
`version`: `object_tracker` 0.1 → 0.2 (steps 0–2) → 0.3 (step 3) → 0.4 (step 6), `osnet_reid` 0.2 → 0.3 → 0.4
(step 5), `team_clustering` 0.1 → 0.2 → 0.3 (step 4).

### Verification

- Backend tests: 499 passed, including `tests/plugins/test_object_tracker_params.py` (buffer default, UI
  payloads, ball-detector presets and the model-file allowlist, ball-tracker parameter validation, Deep-EIoU /
  GTA-Link / interpolation presets, nested merges, rejected model paths and unknown keys, SAHI, `input_format`,
  the `yolox_sn_*` presets and partial SAHI overrides), `tests/plugins/test_team_clustering_params.py` (defaults,
  the UI payload, the fixed ReID model, `num_teams` ≤ K) and `tests/plugins/test_osnet_reid_params.py`
  (defaults, the UI payload, the checkpoint following the model). The characterization test
  `test_reid_accepts_frontend_checkpoints` pins the checkpoint replacement: every allowlisted value is accepted,
  and the model's own checkpoint is used.
- Against the reference implementation, each on inputs fed identically to both:
  - **Deep-EIoU's association**, on synthetic clips (18 players, crossings, dropouts, scores across all
    thresholds, identity embeddings with noise): identical tracks (IDs, boxes, scores, every frame) on 3 clips ×
    ReID on / off × 30 / 10 fps.
  - **Deep-EIoU → GTA-Link** on a synthetic video (12 coloured players in two teams, 160 frames) with real
    OSNet-AIN embeddings: identical online tracks (42 IDs), identical embeddings, identical tracks after GTA-Link
    (16 IDs).
  - **Interpolation**: identical IDs and boxes. One score differs: the reference gives a box interpolated at a
    dropped duplicate (frame, ID) the duplicate's score; here it gets 1, like every interpolated box.
  - **Ball tracker** at 30 fps, on a synthetic 600-frame clip (ball with kicks, gaps and weak detections, a static
    decoy, clutter, players): identical state (boxes, scores, segments, status), with and without player hints,
    with default and non-default parameters.
  - **Team clustering** (`team_clustering.call()`), on a synthetic 240-frame clip (two teams with goalkeepers, a
    referee, players below the box gate, track fragments; OSNet-AIN): in 10 variants (default, K=2, mixed,
    embedding-heavy, embedding-only with K 2 / 4, PCA, HDBSCAN, colour HDBSCAN, sample counts) the same tracks are
    clustered in the same order and get identical labels. Colour features bit-identical, embeddings within 6e-6
    on the GPU (batch composition), 5e-8 on the CPU.
  - **ReID** (`osnet_reid.call()`), on a synthetic 300-frame clip (10 players with distinct kits, one below the
    box gate, three leaving for 80–100 frames and returning under new tracker IDs, fragments): the mapping is
    identical in every frame in 5 variants (without and with `keep_tracker_binding`, no spatial gate, other
    thresholds, short TTLs). `tracks` mode, which the reference cannot run, maps every box (26 tracker IDs → 14
    global IDs).
  - **YOLOX and SAHI**, on 6 DSHS frames (1920×1080): two legacy checkpoints (`bytetrack_x_mot17`,
    `yolox_x_sports_mix`), the SoccerNet player model, the SoccerNet ball model sliced (560 px tiles, no full
    frame) and the player model sliced (540×960 + full frame). The same boxes per frame in every configuration;
    on the CPU identical boxes and scores within 3e-8, on the GPU within 0.012 px and 3e-3 (batch composition).
    15 tested checkpoints (legacy and BGR) get the right input convention and load into the `yolox-x` exp; a
    forced wrong `input_format` is an error.
- The old (`git HEAD`) and new `object_tracker.call()` end to end on scripted detections (14 walking players with
  missed detections, a ball, 300 frames), with fake detector instances and decoder and the vendored ByteTrack:
  - player-only detections: the same frames, track IDs, teams and scores; boxes within the < 1 px truncation (7);
  - with ball detections: the ball split leaves the player tracks as in a run without ball detections;
  - empty frames: the old code crashes, the new one completes; two runs in one process give the same IDs;
  - detection-only runs: the old code wrote the centre as top-left, the new one writes `xyxy[:2]`;
  - ByteTrack keeps lost tracks for 150 / 50 / 5 frames at 30 / 10 / 1 fps for `track_buffer` 150, and 1 frame
    for 20 at 1 fps;
  - ball tracker stage: at most one ball box per frame, equal to `BallTracker` run directly on the ball
    candidates with the player tracks as hints; the player tracks are unchanged by it;
  - separate ball detector: the ball rows come from it only, and the player tracks are unchanged;
  - at 1 fps (below `min_fps`) the output equals the untracked one;
  - the Ultralytics wrapper writes one state entry per frame, and resized boxes come back in frame pixels;
  - `tracker: deep_eiou` (without ReID, and with ReID + GTA-Link): the output equals the tracker run directly on
    the player detections and frames; the ball rows are unaffected.
- The whole chain on a real clip (a DSHS camera, 10 s at 30 fps, GPU) with the real `VideoDecoder` and the run
  parameters the serializer makes of `{"detector": "yolox_sn_player", "tracker": "deep_eiou", "ball_detector":
  "yolox_sn_ball"}`, then `osnet_reid` and `team_clustering`: 12 player IDs (10 players on the pitch), ~10 boxes
  per frame, the ball in 92 of 300 frames, 12 global IDs, teams 4 / 4 / 4 (-1) at K=4 and 7 / 5 with embeddings
  at K=2; `object_tracker` took 66 s. On the CPU (2 s at 10 fps) the same chain runs. A smoke test, not an
  evaluation against the ground truth.

The evaluation numbers quoted above come from the DSHS evaluation; inside SportVid only the smoke test ran on real
video.

## Known, not changed

- Detector checkpoints other than the presets' cannot be chosen per request (allowlist). A new model needs a
  server-side preset and its file under `/models`.
- The `yolox_sn_*` checkpoint files are not in the repository; each deployment needs them under `/models/yolox/`.
- The ball tracker's pixel thresholds are not scaled with resolution (see above).
- The standalone `bytetrack` plugin (`plugins/bytetrack.py`) has the same ID counter issue (6). It is left as is.
- `TrackClassMapper` logs at `error` level for every frame.
- `osnet_reid` stores every player box's 512-d embedding as hex in `frames.json`, about 4 KB per box (~5 GB for
  90 min of 22 players at 10 fps). Nothing reads the per-frame arrays yet; dropping `features` would be the fix.
- `team_clustering`: a track with too few usable crops gets -1, and the merge makes it a bystander. The default
  team from the detector class would be no better: every player class maps to Team A.
- **GTA-Link memory**: one 512-d float32 embedding per output box until `finalize`, about 2 KB per box. 90 min of
  22 players at 10 fps is about 1.2 M boxes, i.e. ~2.4 GB (~7 GB at 30 fps). Storing float16, or splitting long
  videos, are the options.
- Embeddings differ slightly between CPU and GPU, and GTA-Link / the appearance gate can then decide a near-tie
  differently: a run is reproducible on the same device type, not across them. `deploy.yml` (CPU only) would also
  embed every detection on the CPU, which is slow; the CUDA deployments give `object_tracker` a GPU share.
- Detections reach Deep-EIoU as float64 (the reference implementation used float32): a score that lies exactly
  on a threshold can fall on the other side. Identical otherwise.
