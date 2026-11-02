# Tracking in `inference_ray`: design and the port from trak

`object_tracker` (detection, player tracking, tracklet output), `osnet_reid` and `team_clustering` form
the tracking chain. The backend runs them as separate plugin runs, chained by `object_tracker_id`. This package
holds the trackers and the tracklet format they share. The tracking methods are being ported from trak
(`Alexk1704/trak`, `trak/tracker/`, `trak/reid/`, `trak/team/`), where they were evaluated on the DSHS
recordings with Kinexon ground truth.

| File | Contents |
|---|---|
| `tracker.py` | `Tracker` interface, `track_frame` state schema, `detections_xyxy_conf` |
| `bytetrack.py` | ByteTrack (`third_party/ByteTrack`) behind the interface |
| `track_class_mapper.py` | per-track class votes (detector class → default team) |
| `tracklets.py` | the `BboxesData` row format, `TeamId`, metadata reading, class routing |

## Port plan

| Step | Content | Status |
|---|---|---|
| 0 | Bug fixes in the existing chain (below) | done |
| 1 | `object_tracker` as staged pipeline, trak's tracker interface, ball split | done |
| 1b | ByteTrack `track_buffer` as a duration (fps scaling), default re-tuned | done |
| 2 | Kalman ball tracker; optional separate ball-detector instance | open |
| 3 | Deep-EIoU (re-implemented), GTA-Link, interpolation; OSNet-AIN embeddings | open |
| 4 | `team_clustering` on ReID embeddings (trak `Clustering`, `embedding_only` / `reid_weight`) | open |
| 5 | `osnet_reid` in line with trak (vectorised gallery scores, `keep_tracker_binding`) | open |
| later | YOLOX input convention (BGR 0–255 checkpoints) and SAHI tiling | open |

Decisions (2026-11-02):

- **Deep-EIoU is re-implemented**, not vendored: its upstream repository has no license, and SportVid is GPL-3.0.
  It is BoT-SORT's association without camera motion compensation, plus the expanded IoU.
- **New trackers and stages are API-only for now.** The frontend is not changed. New options are serializer
  fields in `backend/serializers/object_tracker.py` that the frontend does not send. A ByteTrack run is never
  silently mapped to another tracker.
- **Third-party code lives under `inference_ray/third_party/`**, with no dependency on GitHub repositories
  (as ByteTrack and sportsreid already are). That covers GTA-Link (MIT) as well.
- **YOLOX convention and SAHI are ported later.** trak's identity numbers (Deep-EIoU → GTA-Link, IDF1 0.59 /
  0.46) were measured on YOLOX-L SN detections, not on the RF-DETR SN default here.
- **The ball detector is another instance of a detector wrapper**, with its own parameters (as trak's
  `player_detector` / `ball_detector` stages share the detector configs). It is not a special ball model type.

## Pipeline (`object_tracker.call`)

1. **Detection** over the decoded video (unchanged). Detector dicts are `{xyxy, xywh, cls_id, conf}` in frame
   pixels, where `xywh` is *centre* x, y plus width, height (all four detector wrappers).
2. **Routing.** With a tracker, the classes whose `output_class_mapping` entry is `entity_type: ball` are
   split off and never reach the player tracker. That is trak's rule (`ball_cls_id`): a ball box would
   otherwise start or steal player tracks.
3. **Player tracking**: `Tracker.process` over all frames, then `Tracker.finalize` once over the whole clip.
   The offline refinements of step 3 (GTA-Link, interpolation) go into `finalize`. GTA-Link needs the frames
   while tracking, so it must live inside `object_tracker`, not in a separate plugin.
4. **Default team per track** from `TrackClassMapper`'s cumulative class votes and `output_class_mapping`.
5. **Output.** Player tracks, plus the untracked detections with entity ID 0. Those are the split-off ball
   candidates, or every detection when no tracker is set (ball runs from the UI). Step 2 replaces the ball part
   with the Kalman ball tracker.

### Detector contract

Every wrapper in `../detector/` sets `frame_shape` (H, W of the decoded frame) and reports boxes in frame
pixels. `object_tracker` normalises by `frame_shape` and gives the trackers frame-pixel boxes
(`image_shape == det_shape`, so BYTETracker does not rescale). A ball detector (step 2) will share these
coordinates with the player detector: the ball tracker uses the player tracks' foot points. Before this contract:

- **Ultralytics** (`yolo10/11/12/26`): `rect` pads the frame to a multiple of 32 and reported the padded size as
  the frame size, so the normalised output was off by up to 0.7 % (1080 → 1088). Without `rect`, boxes were in
  `imgsz` coordinates; they are now scaled back. A second, shadowed `preprocess` was removed.
- **RT-DETR**: the same padding issue, plus `det_shape` padded twice, which made BYTETracker shrink every box
  slightly.
- **YOLOX, RF-DETR**: already in frame pixels; unchanged.

### Tracker interface

Same as trak's `trak.tracker.tracker.Tracker`, so the trak wrappers port with little change:
`preprocess(inputs)`, `process(inputs)` appends one `track_frame` per input frame to `self.state`,
`finalize()`, and `reset_state()`. `track_frame` is `{frame_id, track_ids, track_scores, track_boxes}`, with
boxes as tlwh in frame pixels. trak's `team_ids` field is left out: here the team comes from the class
mapping, and trak's 0 would read as `TeamId.BALL`.

### ByteTrack: `track_buffer` is a duration

`track_buffer` counts frames *at 30 fps* (upstream's convention). The wrapper passes the decoding rate to
`BYTETracker`, which keeps a lost track for `fps / 30 * track_buffer` decoded frames, at least 1. Before, the
rate never reached it, so `track_buffer` counted decoded frames: the UI's 300 kept a lost track for 5 minutes
at its default 1 fps.

- Backend default: 90 → **150** (5 s at any rate). That is trak's ByteTrack re-tune on the DSHS recordings
  (`reports/README.md` §18: `track_buffer` 150 together with `track_thresh` 0.6 / `match_thresh` 0.8 for the
  YOLOX-L COCO-init detections). Only the buffer is taken over: the thresholds depend on the detector's score
  distribution (YOLOX scores are compressed high), so they stay as they are for the RF-DETR default.
- The UI's slider default (300) now means 10 s at any rate. It is a frontend value and not changed here.
- At 30 fps nothing changes.

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
| 5 | A frame without any detection crashed every tracked run (1-D `np.array([])` in `hstack`). | `detections_xyxy_conf` builds `(0, 5)`. `update` still runs, so lost tracks age (as in trak). | runs with empty frames complete |
| 6 | ByteTrack's ID counter is class-level, so a second run in the same Ray replica continued the first run's numbering. | reset `BaseTrack._count` per tracker | the same input gives the same IDs |
| 7 | Player boxes were truncated with `int()` before normalisation (up to 1 px per coordinate, ~3 % of a far player's height). | removed | boxes up to 1 px different |
| 8 | Ball-class detections went into the player tracker. | routing (stage 2) | API runs whose classes include the ball: the ball is ID 0 instead of ByteTrack IDs. UI player runs are not affected (no ball class requested). |
| 9 | The decoding rate never reached ByteTrack: `track_buffer` counted decoded frames. | `frame_rate` passed, buffer ≥ 1 frame, default 150 | lost tracks kept for the same time at any fps; unchanged at 30 fps |
| 10 | The Ultralytics wrapper appended one state entry *per detection*, and none for a frame whose detections were all filtered out. Every YOLO10/11/12/26 run (including the UI's default ball detector, yolo11) misaligned frames and times. | one entry per frame | Ultralytics boxes at the right time |
| 11 | Ultralytics (`rect`) and RT-DETR normalised by the padded frame size; RT-DETR's `det_shape` was padded twice. Ultralytics without `rect` reported `imgsz` coordinates. | detector contract (`frame_shape`, frame-pixel boxes) | ≤ 0.7 % box offsets fixed; RT-DETR tracks slightly different |

**Plugin versions** are part of the analyser's cache key. Every plugin whose output changes must bump its
`version`: `object_tracker` 0.1 → 0.2 (steps 0–1b), `osnet_reid` 0.2 → 0.3, `team_clustering` 0.1 → 0.2.

### Verification

- Backend tests: 464 passed, including `tests/plugins/test_object_tracker_params.py` (buffer default, UI payload).
- The old (`git HEAD`) and new `object_tracker.call()` end to end on scripted detections (14 walking players with
  missed detections, a ball, 300 frames), with a fake detector and decoder and the vendored ByteTrack:
  - player-only detections: the same frames, track IDs, teams and scores; boxes within the < 1 px truncation (7);
  - with ball detections: the ball split leaves the player tracks as in a run without ball detections;
  - empty frames: the old code crashes, the new one completes; two runs in one process give the same IDs;
  - detection-only runs: the old code wrote the centre as top-left, the new one writes `xyxy[:2]`;
  - ByteTrack keeps lost tracks for 150 / 50 / 5 frames at 30 / 10 / 1 fps for `track_buffer` 150, and 1 frame
    for 20 at 1 fps;
  - the Ultralytics wrapper writes one state entry per frame, and resized boxes come back in frame pixels.

None of this has been run on a real video with real detectors yet; that needs the GPU deployment.

## Known, not changed

- The YOLOX wrapper always uses the legacy input (RGB, /255, ImageNet mean / std). BGR 0–255 checkpoints
  (trak's fine-tunes) would give garbage boxes. Ported later (above).
- The standalone `bytetrack` plugin (`plugins/bytetrack.py`) has the same ID counter issue (6). It is left as is.
- `TrackClassMapper` and `osnet_reid` log at `error` level for every frame.
