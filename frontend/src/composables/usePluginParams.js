import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePositionDataStore } from "@/stores/position_data";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useUserStore } from "@/stores/user";
import { usePlayerStore } from "@/stores/player";
import { useLensProfileStore } from "@/stores/lens_profile";
import { useVideoStore } from "@/stores/video";

// Hides the given (always-required-until-now) parameter names from the UI in "simple"
// experience mode, showing them all again in "complex" mode -- their current values (the
// existing defaults) are left untouched either way. Uses a dedicated `simpleHidden` flag
// rather than the existing `hidden` -- `hidden` also drops a parameter from submission
// entirely (see submitPlugin below), which is only safe for genuinely inapplicable fields
// (e.g. a detector-specific param for a different detector). These fields are still
// required by the backend, just defaulted instead of user-editable, so they must keep being
// submitted with whatever value they currently hold. Shared by objectTrackerParams/
// teamClusteringParams/osnetReidParams below; kpi_computation and calibrationParams are
// already minimal enough not to need this.
function hideInSimpleMode(parameters, names) {
  const userStore = useUserStore();
  watch(
    () => userStore.experienceMode,
    (mode) => {
      const hide = mode === "simple";
      for (const p of parameters.value) {
        if (names.includes(p.name)) p.simpleHidden = hide;
      }
    },
    { immediate: true }
  );
}

// object_tracker replaces bytetrack as the generic detector+tracker plugin —
// it additionally lets the user pick a tracking_target (player vs. ball),
// which restricts the available detectors and (for ball runs) drops the
// tracker/tracker_params entirely, so player and ball always run as two separate
// object_tracker runs (backend: "bboxes" vs. "bboxes_ball" results). Shared with the
// batch ModalPlugin.vue via watchObjectTrackerSelection/objectTrackerClasses below.
//
// The presets (backend serializers/object_tracker.py): the YOLOX person detectors and the
// COCO models are generic; the *_sn_* models are SoccerNet (football) fine-tunes with one
// class each -- player or ball, the ball ones partly tiled (SAHI) -- hence each is offered
// only for its own tracking_target.
const OBJECT_TRACKER_DETECTOR_ITEMS = {
  yolox: { title: "YOLOX-X MOT17 (people)", value: "yolox" },
  yolox_l: { title: "YOLOX-L MOT17 (people, lighter)", value: "yolox_l" },
  yolox_dancetrack: { title: "YOLOX-X DanceTrack (dance)", value: "yolox_dancetrack" },
  yolox_sportsmot: { title: "YOLOX-X SportsMOT (team sports)", value: "yolox_sportsmot" },
  yolox_sn_player: { title: "YOLOX-L SoccerNet (Player)", value: "yolox_sn_player" },
  yolox_sn_ball: { title: "YOLOX-L SoccerNet (Ball)", value: "yolox_sn_ball" },
  yolox_sn_ball_zoom2: { title: "YOLOX-L SoccerNet x2 (Ball, slow)", value: "yolox_sn_ball_zoom2" },
  yolo11: { title: "YOLO11-X COCO (Ultralytics)", value: "yolo11" },
  yolo11_l: { title: "YOLO11-L COCO (Ultralytics, lighter)", value: "yolo11_l" },
  yolo11_sn_player: { title: "YOLO11-X SoccerNet (Player)", value: "yolo11_sn_player" },
  rfdetr: { title: "RF-DETR-L COCO", value: "rfdetr" },
  rfdetr_sn_player: { title: "RF-DETR-L SoccerNet (Player)", value: "rfdetr_sn_player" },
  rfdetr_sn_ball: { title: "RF-DETR-L SoccerNet (Ball)", value: "rfdetr_sn_ball" },
};
const PLAYER_TARGET_DETECTORS = [
  "yolox",
  "yolox_l",
  "yolox_dancetrack",
  "yolox_sportsmot",
  "yolox_sn_player",
  "yolo11",
  "yolo11_l",
  "yolo11_sn_player",
  "rfdetr",
  "rfdetr_sn_player",
];
// the detectors whose model has a ball class (backend BALL_DETECTOR_OVERRIDES)
const BALL_TARGET_DETECTORS = [
  "yolox_sn_ball",
  "yolox_sn_ball_zoom2",
  "rfdetr_sn_ball",
  "yolo11",
  "yolo11_l",
  "rfdetr",
];
// detector a ball run falls back to when the selected one has no ball class
const BALL_TARGET_FALLBACK_DETECTOR = "yolo11";
// backend DEFAULT_DETECTOR
export const DEFAULT_PLAYER_DETECTOR = "yolox_sportsmot";
const PLAYER_TARGET_FALLBACK_DETECTOR = DEFAULT_PLAYER_DETECTOR;
export const PLAYER_OBJECT_TRACKER_DETECTOR_ITEMS = PLAYER_TARGET_DETECTORS.map(
  (d) => OBJECT_TRACKER_DETECTOR_ITEMS[d]
);
const BALL_OBJECT_TRACKER_DETECTOR_ITEMS = BALL_TARGET_DETECTORS.map(
  (d) => OBJECT_TRACKER_DETECTOR_ITEMS[d]
);

const YOLOX_PARAMS = ["confidence_threshold", "batch_size", "nms_thresh", "fp16", "decode"];
const YOLO_ULTRALYTICS_PARAMS = [
  "confidence_threshold",
  "batch_size",
  "iou",
  "agnostic_nms",
  "half",
  "max_det",
  "verbose",
];
const RFDETR_PARAMS = ["confidence_threshold", "batch_size", "max_det", "resolution", "verbose"];
const DETECTOR_PARAM_VISIBILITY = {
  // num_classes only for the generic YOLOX: the other checkpoints have one class each
  // (the backend reads it from the checkpoint anyway)
  yolox: [...YOLOX_PARAMS, "num_classes"],
  yolox_l: YOLOX_PARAMS,
  yolox_dancetrack: YOLOX_PARAMS,
  yolox_sportsmot: YOLOX_PARAMS,
  yolox_sn_player: YOLOX_PARAMS,
  yolox_sn_ball: YOLOX_PARAMS,
  yolox_sn_ball_zoom2: YOLOX_PARAMS,
  yolo11: YOLO_ULTRALYTICS_PARAMS,
  yolo11_l: YOLO_ULTRALYTICS_PARAMS,
  yolo11_sn_player: YOLO_ULTRALYTICS_PARAMS,
  rfdetr: RFDETR_PARAMS,
  rfdetr_sn_player: RFDETR_PARAMS,
  rfdetr_sn_ball: RFDETR_PARAMS,
};

// Values set whenever the detector changes. The YOLOX-family presets differ in nms and
// batch size (yolox_sn_ball: batch_size = tiles per forward pass); everything the frontend
// sends overrides the backend preset, so these mirror the backend presets.
const DETECTOR_PARAM_DEFAULTS = {
  yolox: { confidence_threshold: 0.2, nms_thresh: 0.65, batch_size: 1 },
  yolox_l: { confidence_threshold: 0.2, nms_thresh: 0.65, batch_size: 1 },
  yolox_dancetrack: { confidence_threshold: 0.2, nms_thresh: 0.65, batch_size: 1 },
  yolox_sportsmot: { confidence_threshold: 0.2, nms_thresh: 0.65, batch_size: 1 },
  yolox_sn_player: { confidence_threshold: 0.35, nms_thresh: 0.45, batch_size: 1 },
  // low floor on purpose: the backend's ball tracker gates weak candidates itself
  yolox_sn_ball: { confidence_threshold: 0.1, nms_thresh: 0.45, batch_size: 4 },
  yolox_sn_ball_zoom2: { confidence_threshold: 0.1, nms_thresh: 0.45, batch_size: 4 },
  yolo11: { confidence_threshold: 0.2, batch_size: 1 },
  yolo11_l: { confidence_threshold: 0.2, batch_size: 1 },
  yolo11_sn_player: { confidence_threshold: 0.35, batch_size: 1 },
  rfdetr: { confidence_threshold: 0.5, batch_size: 1, resolution: 1280 },
  rfdetr_sn_player: { confidence_threshold: 0.35, batch_size: 1, resolution: 1280 },
  rfdetr_sn_ball: { confidence_threshold: 0.1, batch_size: 1, resolution: 1920 },
};
// on top of DETECTOR_PARAM_DEFAULTS, per tracking_target
const PLAYER_IOU_DEFAULT = 0.3;
const BALL_YOLO_IOU_DEFAULT = 0.5;
const TARGET_PARAM_DEFAULTS = {
  ball: {
    rfdetr: { confidence_threshold: 0.2 },
    yolo11: { iou: BALL_YOLO_IOU_DEFAULT },
    yolo11_l: { iou: BALL_YOLO_IOU_DEFAULT },
  },
  player: Object.fromEntries(PLAYER_TARGET_DETECTORS.map((d) => [d, { iou: PLAYER_IOU_DEFAULT }])),
};

// Ball vs. player class filters per detector, keyed by tracking_target. There's no UI
// control for `classes` -- it's derived from the (UI-only) tracking_target parameter in
// submitPlugin() below, which then strips tracking_target from the payload since the
// backend doesn't know that field.
const OBJECT_TRACKER_CLASSES_BY_TARGET = {
  // raw class ids: COCO for yolo11 (0 person, 32 sports ball) and rfdetr (COCO category ids:
  // 1 person, 37 sports ball); the single-class checkpoints use 0
  ball: {
    yolox_sn_ball: [0],
    yolox_sn_ball_zoom2: [0],
    rfdetr_sn_ball: [0],
    yolo11: [32],
    yolo11_l: [32],
    rfdetr: [37],
  },
  player: {
    yolox: [0],
    yolox_l: [0],
    yolox_dancetrack: [0],
    yolox_sportsmot: [0],
    yolox_sn_player: [0],
    yolo11: [0],
    yolo11_l: [0],
    yolo11_sn_player: [0],
    rfdetr: [1],
    rfdetr_sn_player: [0],
  },
};

// Keep in sync with default_kalman_ball_params["min_fps"] (backend serializers/object_tracker.py).
const BALL_TRACKER_MIN_FPS = 10;

export function objectTrackerClasses(target, detector) {
  return OBJECT_TRACKER_CLASSES_BY_TARGET[target]?.[detector];
}

// Default fps of an object_tracker run: the video's own frame rate, rounded and clamped to
// the backend's 1-30 range.
export function defaultObjectTrackerFps(videoFps) {
  const fps = Math.round(Number(videoFps));
  return Number.isFinite(fps) ? Math.min(30, Math.max(1, fps)) : 30;
}

// Appearance (ReID) embeddings (backend serializers/reid_models.py REID_PRESETS), shared by
// object_tracker's Deep-EIoU / GTA-Link, team_clustering and osnet_reid. The backend fixes
// each preset's model file (and its crop size and fp16 setting where the model needs them).
export const REID_PRESET_ITEMS = [
  { title: "OSNet-AIN (people, MS+D+C)", value: "osnet_ain" },
  { title: "OSNet x1.0 (people, MS+D+C)", value: "osnet_x1_0" },
  { title: "OSNet-IBN (people, MS+D+C)", value: "osnet_ibn" },
  { title: "OSNet x1.0 SportsMOT (team sports)", value: "osnet_sportsmot" },
  { title: "DeiT-L sportsreid (football, slow)", value: "deit_l_sportsreid" },
];
export const DEFAULT_REID_PRESET = "osnet_ain";

export function reidPresetField(t, textKey, extra = {}) {
  return {
    field: "select_options",
    name: "reid_preset",
    value: DEFAULT_REID_PRESET,
    items: REID_PRESET_ITEMS,
    text: t(textKey),
    ...extra,
  };
}

// Player trackers (backend TRACKER_CHOICES). Their tracker_params differ, so each field is
// shown only for the tracker(s) listed in TRACKER_PARAM_VISIBILITY, and switching the tracker
// resets the fields to that tracker's defaults (TRACKER_PARAM_DEFAULTS) -- several names
// (track_buffer, match_thresh, min_box_area) are shared but have different defaults.
export const OBJECT_TRACKER_TRACKER_ITEMS = [
  { title: "ByteTrack", value: "bytetrack" },
  { title: "Deep-EIoU", value: "deep_eiou" },
];
const TRACKER_PARAM_VISIBILITY = {
  bytetrack: [
    "track_thresh",
    "track_buffer",
    "match_thresh",
    "mot20",
    "aspect_ratio_thresh",
    "min_box_area",
  ],
  deep_eiou: [
    "track_high_thresh",
    "track_low_thresh",
    "new_track_thresh",
    "track_buffer",
    "match_thresh",
    "min_box_area",
    "remove_edge_dets",
    "with_reid",
    "reid_preset",
    "proximity_thresh",
    "appearance_thresh",
    "gta_link_enabled",
    "interpolation_enabled",
  ],
};
const TRACKER_PARAM_DEFAULTS = {
  bytetrack: {
    track_thresh: 0.4,
    track_buffer: 300,
    match_thresh: 0.8,
    mot20: false,
    aspect_ratio_thresh: 5.0,
    min_box_area: 0,
  },
  // backend default_deep_eiou_params (upstream's SportsMOT setting)
  deep_eiou: {
    track_high_thresh: 0.6,
    track_low_thresh: 0.1,
    new_track_thresh: 0.7,
    track_buffer: 60,
    match_thresh: 0.8,
    min_box_area: 10,
    remove_edge_dets: false,
    with_reid: true,
    reid_preset: DEFAULT_REID_PRESET,
    proximity_thresh: 0.5,
    appearance_thresh: 0.25,
    gta_link_enabled: true,
    interpolation_enabled: false,
  },
};

// The Deep-EIoU-only tracker_params fields, appended to the object_tracker optional
// parameters of both objectTrackerParams() and the batch ModalPlugin.vue. gta_link /
// interpolation are nested groups in the backend (tracker_params.gta_link.enabled), hence
// `subgroup` + `subname` (see setGroupedValue).
export function deepEiouTrackerFields(t) {
  const slider = (name, step = 0.05) => ({
    field: "slider",
    min: 0,
    max: 1,
    value: TRACKER_PARAM_DEFAULTS.deep_eiou[name],
    step,
    name,
    text: t(`modal.plugin.object_tracker.${name}`),
    group: "tracker_params",
    hidden: true,
  });
  const checkbox = (name, extra = {}) => ({
    field: "checkbox",
    value: TRACKER_PARAM_DEFAULTS.deep_eiou[name],
    name,
    text: t(`modal.plugin.object_tracker.${name}`),
    group: "tracker_params",
    hidden: true,
    ...extra,
  });
  return [
    slider("track_high_thresh"),
    slider("track_low_thresh"),
    slider("new_track_thresh"),
    checkbox("remove_edge_dets"),
    checkbox("with_reid"),
    // the embedding of Deep-EIoU and GTA-Link; the backend adds the tracker settings that go with it
    reidPresetField(t, "modal.plugin.object_tracker.reid_preset", { group: "tracker_params", hidden: true }),
    slider("proximity_thresh"),
    slider("appearance_thresh"),
    checkbox("gta_link_enabled", { subgroup: "gta_link", subname: "enabled" }),
    checkbox("interpolation_enabled", { subgroup: "interpolation", subname: "enabled" }),
  ];
}

// Puts a `group`-tagged parameter into the grouped payload: grouped[group][name], or
// grouped[group][subgroup][subname] for nested backend groups.
export function setGroupedValue(grouped, p) {
  const group = (grouped[p.group] = grouped[p.group] || {});
  if (p.subgroup) {
    group[p.subgroup] = group[p.subgroup] || {};
    group[p.subgroup][p.subname ?? p.name] = p.value;
  } else {
    group[p.name] = p.value;
  }
}

// Keeps the object_tracker fields consistent with tracking_target + detector:
//  - restricts the detector choices to the target's (falling back to a valid one),
//  - shows only the selected detector's detector_params, with its defaults,
//  - hides the tracker and all tracker_params fields for ball runs. `hidden` (unlike
//    simpleHidden) also drops the field from submission -- for "tracker" that's the actual
//    signal the backend uses to tell ball- from player-tracking runs apart
//    (tasks/object_tracker.py: `"bboxes" if parameters.get("tracker") else "bboxes_ball"`),
//    so this must stay driven by tracking_target alone and never by experience mode.
// `parameters`/`optionalParameters` are refs (or computeds) of parameter arrays.
export function watchObjectTrackerSelection(parameters, optionalParameters) {
  const { t } = useI18n();
  const find = (list, name) => list.value.find((p) => p.name === name);
  // Below the Kalman ball tracker's min_fps the backend silently skips ball tracking and
  // writes the raw ball candidates instead -- warn right under the fps slider. Only for
  // ball runs: player runs detect no ball class, so the ball tracker has nothing to do.
  watch(
    () => [find(parameters, "tracking_target")?.value, find(parameters, "fps")?.value],
    ([target, fps]) => {
      const param = find(parameters, "fps");
      if (!param) return;
      // the parameter lists can arrive after setup (ModalPlugin's computed), so the slider's
      // own hint is remembered on the parameter itself the first time it is seen
      if (!("defaultHint" in param)) param.defaultHint = param.hint;
      const lowFps = target === "ball" && Number(fps) < BALL_TRACKER_MIN_FPS;
      param.hint = lowFps
        ? t("modal.plugin.object_tracker.ball_tracker_low_fps_hint", { min: BALL_TRACKER_MIN_FPS })
        : param.defaultHint;
      param.hintWarning = lowFps;
    },
    { immediate: true }
  );
  watch(
    () => [
      find(parameters, "tracking_target")?.value,
      find(parameters, "detector")?.value,
      find(parameters, "tracker")?.value,
    ],
    ([target, detector, tracker]) => {
      const detectorParam = find(parameters, "detector");
      if (!detectorParam) return;
      const isBall = target === "ball";
      detectorParam.items = isBall
        ? BALL_OBJECT_TRACKER_DETECTOR_ITEMS
        : PLAYER_OBJECT_TRACKER_DETECTOR_ITEMS;
      const allowed = isBall ? BALL_TARGET_DETECTORS : PLAYER_TARGET_DETECTORS;
      if (!allowed.includes(detector)) {
        // re-runs this watcher with the new detector
        detectorParam.value = isBall
          ? BALL_TARGET_FALLBACK_DETECTOR
          : PLAYER_TARGET_FALLBACK_DETECTOR;
        return;
      }

      const visible = DETECTOR_PARAM_VISIBILITY[detector] || [];
      const defaults = {
        ...DETECTOR_PARAM_DEFAULTS[detector],
        ...TARGET_PARAM_DEFAULTS[isBall ? "ball" : "player"][detector],
      };
      for (const p of optionalParameters.value) {
        if (p.group === "detector_params") {
          p.hidden = !visible.includes(p.name);
          if (p.name in defaults) p.value = defaults[p.name];
        } else if (p.group === "tracker_params") {
          p.hidden = isBall || !(TRACKER_PARAM_VISIBILITY[tracker] || []).includes(p.name);
        }
      }
      const trackerParam = find(parameters, "tracker");
      if (trackerParam) trackerParam.hidden = isBall;
    },
    { immediate: true }
  );
  // separate from the above so that changing the detector / target keeps the tracker values
  watch(
    () => find(parameters, "tracker")?.value,
    (tracker) => {
      const defaults = TRACKER_PARAM_DEFAULTS[tracker] || {};
      for (const p of optionalParameters.value) {
        if (p.group === "tracker_params" && p.name in defaults) p.value = defaults[p.name];
      }
    },
    { immediate: true }
  );
}

export function objectTrackerParams() {
  const { t } = useI18n();
  const playerStore = usePlayerStore();

  const parameters = ref([
    {
      field: "select_options",
      name: "tracking_target",
      value: "player",
      items: [
        { title: t("modal.plugin.object_tracker.tracking_target_player"), value: "player" },
        { title: t("modal.plugin.object_tracker.tracking_target_ball"), value: "ball" },
      ],
      text: t("modal.plugin.object_tracker.tracking_target"),
    },
    {
      field: "select_options",
      name: "detector",
      value: DEFAULT_PLAYER_DETECTOR,
      items: PLAYER_OBJECT_TRACKER_DETECTOR_ITEMS,
      text: t("modal.plugin.object_tracker.detector"),
    },
    {
      field: "select_options",
      name: "tracker",
      value: "bytetrack",
      items: OBJECT_TRACKER_TRACKER_ITEMS,
      text: t("modal.plugin.object_tracker.tracker"),
    },
    {
      field: "slider",
      min: 1,
      max: 30,
      value: defaultObjectTrackerFps(playerStore.videoFPS),
      step: 1,
      name: "fps",
      text: t("modal.plugin.fps"),
      dataTour: "bytetrack-fps",
    },
  ]);

  const optionalParameters = ref([
    {
      field: "slider",
      min: 0,
      max: 1,
      value: 0.2,
      step: 0.05,
      name: "confidence_threshold",
      text: t("modal.plugin.object_tracker.confidence_threshold"),
      group: "detector_params",
    },
    {
      field: "slider",
      min: 1,
      max: 16,
      value: 1,
      step: 1,
      name: "batch_size",
      text: t("modal.plugin.object_tracker.batch_size"),
      group: "detector_params",
    },
    {
      field: "slider",
      min: 0,
      max: 1,
      value: 0.65,
      step: 0.05,
      name: "nms_thresh",
      text: t("modal.plugin.object_tracker.nms_thresh"),
      group: "detector_params",
    },
    {
      field: "slider",
      min: 0,
      max: 1,
      value: 0.3,
      step: 0.05,
      name: "iou",
      text: t("modal.plugin.object_tracker.iou"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "checkbox",
      value: false,
      name: "agnostic_nms",
      text: t("modal.plugin.object_tracker.agnostic_nms"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "checkbox",
      value: true,
      name: "fp16",
      text: t("modal.plugin.object_tracker.fp16"),
      group: "detector_params",
    },
    {
      field: "checkbox",
      value: false,
      name: "half",
      text: t("modal.plugin.object_tracker.half"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "checkbox",
      value: true,
      name: "decode",
      text: t("modal.plugin.object_tracker.decode"),
      group: "detector_params",
    },
    {
      field: "slider",
      min: 1,
      max: 10,
      value: 1,
      step: 1,
      name: "num_classes",
      text: t("modal.plugin.object_tracker.num_classes"),
      group: "detector_params",
    },
    {
      field: "slider",
      min: 1,
      max: 300,
      value: 100,
      step: 1,
      name: "max_det",
      text: t("modal.plugin.object_tracker.max_det"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "slider",
      min: 320,
      max: 1920,
      value: 1280,          // set per RF-DETR preset (DETECTOR_PARAM_DEFAULTS)
      step: 32,
      name: "resolution",
      text: t("modal.plugin.object_tracker.resolution"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "checkbox",
      value: false,
      name: "verbose",
      text: t("modal.plugin.object_tracker.verbose"),
      group: "detector_params",
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 1,
      value: 0.4,
      step: 0.05,
      name: "track_thresh",
      text: t("modal.plugin.object_tracker.track_thresh"),
      group: "tracker_params",
    },
    {
      field: "slider",
      min: 1,
      max: 600,
      value: 300,
      step: 10,
      name: "track_buffer",
      text: t("modal.plugin.object_tracker.track_buffer"),
      group: "tracker_params",
    },
    {
      field: "slider",
      min: 0,
      max: 1,
      value: 0.8,
      step: 0.05,
      name: "match_thresh",
      text: t("modal.plugin.object_tracker.match_thresh"),
      group: "tracker_params",
    },
    {
      field: "checkbox",
      value: false,
      name: "mot20",
      text: t("modal.plugin.object_tracker.mot20"),
      group: "tracker_params",
    },
    {
      field: "slider",
      min: 0,
      max: 10,
      value: 5.0,
      step: 0.1,
      name: "aspect_ratio_thresh",
      text: t("modal.plugin.object_tracker.aspect_ratio_thresh"),
      group: "tracker_params",
    },
    {
      field: "slider",
      min: 0,
      max: 500,
      value: 0,
      step: 10,
      name: "min_box_area",
      text: t("modal.plugin.object_tracker.min_box_area"),
      group: "tracker_params",
    },
    ...deepEiouTrackerFields(t),
  ]);

  watchObjectTrackerSelection(parameters, optionalParameters);

  hideInSimpleMode(parameters, ["fps", "detector", "tracker"]);

  return { parameters, optionalParameters };
}

// Only relevant for HDBSCAN: distance metric and cluster-selection epsilon.
const HDBSCAN_ONLY_PARAMS = ["metric", "cluster_selection_epsilon"];
// Only relevant for K-Means: number of initializations and the random seed.
const KMEANS_ONLY_PARAMS = ["n_init", "random_state"];

export function teamClusteringParams() {
  const { t } = useI18n();

  const parameters = ref([
    {
      field: "select_object_tracker_run",
      name: "object_tracker_id",
      value: "",
      text: t("modal.plugin.team_clustering.object_tracker_id"),
      hint: t("modal.plugin.team_clustering.object_tracker_id_hint"),
      no_data_text: "modal.plugin.team_clustering.object_tracker_run_none",
    },
    {
      field: "select_options",
      name: "clustering_algo",
      value: "KMEANS",
      items: [
        { title: "K-Means", value: "KMEANS" },
        { title: "HDBSCAN", value: "HDBSCAN" },
      ],
      text: t("modal.plugin.team_clustering.clustering_algo"),
    },
    {
      field: "slider",
      min: 2,
      max: 16,
      value: 2,
      step: 1,
      name: "K",
      text: t("modal.plugin.team_clustering.K"),
    },
  ]);

  const optionalParameters = ref([
    reidPresetField(t, "modal.plugin.team_clustering.reid_preset"),
    {
      field: "slider",
      min: 1,
      max: 50,
      value: 2,
      step: 1,
      name: "min_samples_per_track",
      text: t("modal.plugin.team_clustering.min_samples_per_track"),
    },
    {
      field: "slider",
      min: 5,
      max: 100,
      value: 20,
      step: 1,
      name: "max_samples_per_track",
      text: t("modal.plugin.team_clustering.max_samples_per_track"),
    },
    {
      field: "slider",
      min: 1,
      max: 100,
      value: 3,
      step: 1,
      name: "min_cluster_size",
      text: t("modal.plugin.team_clustering.min_cluster_size"),
    },
    {
      field: "slider",
      min: 12,
      max: 500,
      value: 12,
      step: 4,
      name: "min_pixels",
      text: t("modal.plugin.team_clustering.min_pixels"),
    },
    {
      field: "checkbox",
      value: false,
      name: "use_illumination_norm",
      text: t("modal.plugin.team_clustering.use_illumination_norm"),
    },
    {
      field: "checkbox",
      value: false,
      name: "use_central_band",
      text: t("modal.plugin.team_clustering.use_central_band"),
    },
    {
      field: "checkbox",
      value: false,
      name: "use_torso_crop",
      text: t("modal.plugin.team_clustering.use_torso_crop"),
    },
    {
      field: "checkbox",
      value: false,
      name: "use_green_mask",
      text: t("modal.plugin.team_clustering.use_green_mask"),
    },
    {
      field: "checkbox",
      value: false,
      name: "use_gray_mask",
      text: t("modal.plugin.team_clustering.use_gray_mask"),
    },
    {
      field: "checkbox",
      value: true,
      name: "two_channel",
      text: t("modal.plugin.team_clustering.two_channel"),
    },
    {
      field: "checkbox",
      value: true,
      name: "use_pca",
      text: t("modal.plugin.team_clustering.use_pca"),
    },
    {
      field: "slider",
      min: 2,
      max: 128,
      value: 16,
      step: 1,
      name: "pca_components",
      text: t("modal.plugin.team_clustering.pca_components"),
      hidden: true,
    },
    {
      field: "select_options",
      name: "metric",
      value: "euclidean",
      items: [
        { title: "Euclidean", value: "euclidean" },
        { title: "Cosine", value: "cosine" },
      ],
      text: t("modal.plugin.team_clustering.metric"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0.01,
      max: 0.99,
      value: 0.5,
      step: 0.01,
      name: "cluster_selection_epsilon",
      text: t("modal.plugin.team_clustering.cluster_selection_epsilon"),
      hidden: true,
    },
    {
      field: "slider",
      min: 1,
      max: 100,
      value: 20,
      step: 1,
      name: "n_init",
      text: t("modal.plugin.team_clustering.n_init"),
      hidden: false,
    },
    {
      field: "slider",
      min: 0,
      max: 9999,
      value: 42,
      step: 1,
      name: "random_state",
      text: t("modal.plugin.team_clustering.random_state"),
      hidden: false,
    },
    {
      field: "slider",
      min: 4,
      max: 64,
      value: 16,
      step: 1,
      name: "hist_h_bins",
      text: t("modal.plugin.team_clustering.hist_h_bins"),
      hidden: true,
    },
    {
      field: "slider",
      min: 1,
      max: 32,
      value: 4,
      step: 1,
      name: "hist_s_bins",
      text: t("modal.plugin.team_clustering.hist_s_bins"),
      hidden: true,
    },
    {
      field: "slider",
      min: 1,
      max: 32,
      value: 4,
      step: 1,
      name: "hist_v_bins",
      text: t("modal.plugin.team_clustering.hist_v_bins"),
      hidden: true,
    },
    {
      field: "slider",
      min: 6,
      max: 200,
      value: 12,
      step: 1,
      name: "min_crop_w",
      text: t("modal.plugin.team_clustering.min_crop_w"),
      hidden: true,
    },
    {
      field: "slider",
      min: 12,
      max: 400,
      value: 24,
      step: 1,
      name: "min_crop_h",
      text: t("modal.plugin.team_clustering.min_crop_h"),
      hidden: true,
    },
    {
      field: "slider",
      min: 5,
      max: 512,
      value: 128,
      step: 1,
      name: "crop_size_x",
      text: t("modal.plugin.team_clustering.crop_size_x"),
      hidden: true,
    },
    {
      field: "slider",
      min: 5,
      max: 512,
      value: 256,
      step: 1,
      name: "crop_size_y",
      text: t("modal.plugin.team_clustering.crop_size_y"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_x1_offset",
      text: t("modal.plugin.team_clustering.crop_x1_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_y1_offset",
      text: t("modal.plugin.team_clustering.crop_y1_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_x2_offset",
      text: t("modal.plugin.team_clustering.crop_x2_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_y2_offset",
      text: t("modal.plugin.team_clustering.crop_y2_offset"),
      hidden: true,
    },
  ]);

  watch(
    () => parameters.value.find((p) => p.name === "clustering_algo")?.value,
    (algo) => {
      for (const p of optionalParameters.value) {
        if (HDBSCAN_ONLY_PARAMS.includes(p.name)) p.hidden = algo !== "HDBSCAN";
        if (KMEANS_ONLY_PARAMS.includes(p.name)) p.hidden = algo !== "KMEANS";
      }
    },
    { immediate: true }
  );

  watch(
    () => optionalParameters.value.find((p) => p.name === "use_pca")?.value,
    (usePca) => {
      const pcaComponentsParam = optionalParameters.value.find((p) => p.name === "pca_components");
      if (pcaComponentsParam) pcaComponentsParam.hidden = !usePca;
    },
    { immediate: true }
  );

  hideInSimpleMode(parameters, ["clustering_algo", "K"]);

  return { parameters, optionalParameters };
}

// Only relevant for gallery_mode "protos" (ProtoGallery): prototype/cache-based matching
// hyperparameters. "tracks" mode (Gallery) only uses match_thresh & max_missed.
const OSNET_REID_PROTOS_ONLY_PARAMS = [
  "update_threshold",
  "ema_alpha",
  "cache_size",
  "margin",
  "prototype_weight",
  "cache_weight",
];

export function osnetReidParams() {
  const { t } = useI18n();

  const parameters = ref([
    {
      field: "select_object_tracker_run",
      name: "object_tracker_id",
      value: "",
      text: t("modal.plugin.osnet_reid.object_tracker_id"),
      hint: t("modal.plugin.osnet_reid.object_tracker_id_hint"),
      no_data_text: "modal.plugin.team_clustering.object_tracker_run_none",
    },
    {
      field: "select_options",
      name: "gallery_mode",
      value: "protos",
      items: [
        { title: t("modal.plugin.osnet_reid.gallery_mode_protos"), value: "protos" },
        { title: t("modal.plugin.osnet_reid.gallery_mode_tracks"), value: "tracks" },
      ],
      text: t("modal.plugin.osnet_reid.gallery_mode"),
    },
    reidPresetField(t, "modal.plugin.osnet_reid.reid_preset"),
  ]);

  const optionalParameters = ref([
    {
      field: "slider",
      min: 0.6,
      max: 0.9,
      value: 0.72,
      step: 0.01,
      name: "match_thresh",
      text: t("modal.plugin.osnet_reid.match_thresh"),
    },
    {
      field: "slider",
      min: 0.85,
      max: 0.95,
      value: 0.85,
      step: 0.01,
      name: "update_threshold",
      text: t("modal.plugin.osnet_reid.update_threshold"),
    },
    {
      field: "slider",
      min: 0.98,
      max: 0.99,
      value: 0.98,
      step: 0.001,
      name: "ema_alpha",
      text: t("modal.plugin.osnet_reid.ema_alpha"),
    },
    {
      field: "slider",
      min: 0.05,
      max: 0.08,
      value: 0.06,
      step: 0.005,
      name: "margin",
      text: t("modal.plugin.osnet_reid.margin"),
    },
    {
      field: "slider",
      min: 0.65,
      max: 0.8,
      value: 0.7,
      step: 0.01,
      name: "prototype_weight",
      text: t("modal.plugin.osnet_reid.prototype_weight"),
    },
    {
      field: "slider",
      min: 0.2,
      max: 0.35,
      value: 0.3,
      step: 0.01,
      name: "cache_weight",
      text: t("modal.plugin.osnet_reid.cache_weight"),
    },
    {
      field: "slider",
      min: 8,
      max: 12,
      value: 10,
      step: 1,
      name: "cache_size",
      text: t("modal.plugin.osnet_reid.cache_size"),
    },
    {
      field: "slider",
      min: 90,
      max: 300,
      value: 120,
      step: 10,
      name: "max_missed",
      text: t("modal.plugin.osnet_reid.max_missed"),
    },
    {
      field: "slider",
      min: 5,
      max: 512,
      value: 128,
      step: 1,
      name: "crop_size_x",
      text: t("modal.plugin.osnet_reid.crop_size_x"),
      hidden: true,
    },
    {
      field: "slider",
      min: 5,
      max: 512,
      value: 256,
      step: 1,
      name: "crop_size_y",
      text: t("modal.plugin.osnet_reid.crop_size_y"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_x1_offset",
      text: t("modal.plugin.osnet_reid.crop_x1_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_y1_offset",
      text: t("modal.plugin.osnet_reid.crop_y1_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_x2_offset",
      text: t("modal.plugin.osnet_reid.crop_x2_offset"),
      hidden: true,
    },
    {
      field: "slider",
      min: 0,
      max: 0.8,
      value: 0,
      step: 0.05,
      name: "crop_y2_offset",
      text: t("modal.plugin.osnet_reid.crop_y2_offset"),
      hidden: true,
    },
  ]);

  watch(
    () => parameters.value.find((p) => p.name === "gallery_mode")?.value,
    (galleryMode) => {
      for (const p of optionalParameters.value) {
        if (OSNET_REID_PROTOS_ONLY_PARAMS.includes(p.name)) p.hidden = galleryMode !== "protos";
      }
    },
    { immediate: true }
  );

  hideInSimpleMode(parameters, ["gallery_mode", "reid_preset"]);

  return { parameters, optionalParameters };
}

// The two calibration plugins, in the order the rule below prefers them. There is no method
// picker: which one runs follows from whether a lens profile is picked for the video. Without one
// the lens solver runs, and the backend task decides whether it can (static camera, enough
// landmarks, ...) and falls back to the plain DLT on the raw landmarks when it cannot solve a lens,
// flagging the calibration with a lens_notice (see tasks/calibration_lens_solve.py's
// lens_intrinsics), so there is nothing left to choose.
export const CALIBRATION_METHODS = ["calibration_static_dlt", "calibration_lens_solve"];

// Writes the lens profile a calibrationParams set has picked onto the video. The hosts call this
// right before they submit the run: the backend task reads the profile off the video, so it has
// to land first. Returns false when it couldn't be saved, which aborts the run rather than
// quietly calibrating with the old profile.
export async function applyLensProfileSelection(parameters, videoId) {
  const field = parameters.find((p) => p.field === "select_lens_profile");
  const picked = field?.value ?? null;
  // No picker in this parameter set, or one that never got as far as reporting a selection (the
  // video isn't converted yet, so no profile can be assigned): the video keeps what it carries.
  if (!picked || !videoId) return true;

  // Written out unconditionally, without comparing against a video entry held in some store
  // first: that comparison is what used to skip the save whenever the local copy had drifted
  // (an entry replaced over the live event stream, a profile assigned in the other dialog), and
  // the run then went out with the previously stored profile. One extra request per run.
  const res = await useLensProfileStore().setForVideo({
    videoId,
    lensProfileId: picked.lensProfileId ?? null,
    lensCrop: picked.lensCrop ?? 1.0,
  });
  if (res.status !== "ok") {
    console.error("Could not save the video's lens profile, not starting the calibration:", res);
    return false;
  }
  // Two stores hold a video: the player's single open one and the gallery's map (which the video
  // overview and its own camera/lens dialog read). The response is the updated entry, so both
  // are brought up to date -- otherwise the change only shows up in the dialog it was made in.
  const playerStore = usePlayerStore();
  useVideoStore().upsert(res.entry);
  if (playerStore.video?.id === res.entry.id) {
    await playerStore.fetchVideo({ videoId });
  }
  return true;
}

// Camera calibration is offered as one entry instead of one button per plugin. Which of the two
// plugins actually runs is derived state, returned as `plugin` for the hosts to submit with --
// not a parameter that something writes into: deriving it is what keeps it from going stale
// against the picked lens profile.
export function calibrationParams() {
  const { t } = useI18n();
  const pluginRunStore = usePluginRunStore();
  const playerStore = usePlayerStore();

  // Plugins the backend can run right now (deployed Ray plugins); null until the answer is in,
  // which means "assume everything is there" as everywhere else.
  const available = ref(null);
  pluginRunStore.fetchAvailable().then((plugins) => {
    available.value = plugins;
  });
  const canRun = (plugin) => available.value === null || available.value.includes(plugin);

  // The { lensProfileId, lensCrop } the picker has reported, null until it has mounted.
  const lensProfileSelection = ref(null);

  // Which profile the run will use: what the picker reported, or -- in the moment before it has
  // -- what the video already carries.
  const lensProfileId = computed(() =>
    lensProfileSelection.value
      ? (lensProfileSelection.value.lensProfileId ?? null)
      : (playerStore.video?.lens_profile_id ?? null)
  );

  // The rule: with a lens profile the clicked points are undistorted with it, without one the
  // lens is solved from the video. Everything the solver needs (a static camera, enough landmarks,
  // a pitch model for the sport) is the backend's business -- it falls back to the plain DLT fit
  // without lens correction on its own and tells the user so on the calibration, so the choice here
  // is not second-guessed.
  const plugin = computed(() =>
    !lensProfileId.value && canRun("calibration_lens_solve")
      ? "calibration_lens_solve"
      : "calibration_static_dlt"
  );

  const parameters = ref([
    {
      // The video's lens profile: a property of the video, not a plugin parameter (hence
      // `uiOnly`), and only written to the video when the run is started
      // (applyLensProfileSelection above). Backed by the ref so everything derived from it has
      // one explicit source.
      field: "select_lens_profile",
      name: "lens_profile",
      uiOnly: true,
      get value() {
        return lensProfileSelection.value;
      },
      set value(selection) {
        lensProfileSelection.value = selection;
      },
    },
    {
      field: "select_calibration",
      name: "calibration_id",
      value: "",
      // Which asset is calibrated is the one thing the run cannot be started without (see
      // ModalPluginRun's hasMissingRequired); the lens profile and the solver's parameters below
      // are all optional.
      required: true,
      text: t("modal.plugin.calibration_static_dlt.calibration_id"),
      // Reads which plugin the run would use, so it changes with the picked profile.
      get hint() {
        return plugin.value === "calibration_lens_solve"
          ? t("modal.plugin.calibration_lens_solve.calibration_id_hint")
          : t("modal.plugin.calibration_static_dlt.calibration_id_hint");
      },
    },
  ]);

  // The lens solver's own parameters (see the calibration_lens_solve serializer); defaults match
  // the analyser plugin's own, so leaving them untouched changes nothing. They stay offered
  // whichever plugin the rule picks -- calibration_static_dlt's serializer ignores parameters it
  // doesn't declare, and a run that falls back to it was meant to try the solver first.
  const optionalParameters = ref([
    {
      field: "slider",
      min: 2,
      max: 20,
      value: 8,
      step: 1,
      name: "num_frames",
      text: t("modal.plugin.calibration_lens_solve.num_frames"),
      hint: t("modal.plugin.calibration_lens_solve.num_frames_hint"),
    },
    {
      field: "slider",
      min: 1,
      max: 10,
      value: 5,
      step: 1,
      name: "rounds",
      text: t("modal.plugin.calibration_lens_solve.rounds"),
      hint: t("modal.plugin.calibration_lens_solve.rounds_hint"),
    },
    {
      field: "slider",
      min: 3,
      max: 8,
      value: 6,
      step: 1,
      name: "poly_degree",
      text: t("modal.plugin.calibration_lens_solve.poly_degree"),
      hint: t("modal.plugin.calibration_lens_solve.poly_degree_hint"),
    },
  ]);

  return { parameters, optionalParameters, plugin };
}

export function kpiComputationParams() {
  const { t } = useI18n();
  const positionDataStore = usePositionDataStore();

  const parameters = ref([
    {
      field: "select_options",
      name: "format",
      value: "kinexon",
      items: [
        ...positionDataStore.provider.map((p) => ({ title: p.name, value: p.id })),
        { title: "SportVid", value: "sportvid" },
      ],
      text: t("modal.plugin.kpi_computation.format"),
      dataTour: "kpi-format",
    },
    {
      field: "select_tracking_data",
      name: "tracking_data_id",
      value: "",
      text: t("modal.plugin.kpi_computation.tracking_data_id"),
      hint: t("modal.plugin.kpi_computation.tracking_data_id_hint"),
      format_filter: "kinexon",
      dataTour: "kpi-tracking-data",
    },
    {
      field: "select_object_tracker_run",
      name: "object_tracker_run_id",
      value: "",
      text: t("modal.plugin.kpi_computation.object_tracker_run_id"),
      hint: t("modal.plugin.kpi_computation.object_tracker_run_id_hint"),
      hidden: true,
      dataTour: "kpi-bytetrack-run",
    },
    {
      field: "select_calibration",
      name: "calibration_id",
      value: "",
      text: t("modal.plugin.kpi_computation.calibration_id"),
      hint: t("modal.plugin.kpi_computation.calibration_id_hint"),
      hidden: true,
      dlt: true,
      dataTour: "kpi-calibration",
    },
  ]);

  const optionalParameters = ref([
    {
      field: "select_options",
      name: "filter_type",
      value: "",
      items: [
        { title: t("modal.plugin.kpi_computation.filter_none"), value: "" },
        {
          title: t("modal.plugin.kpi_computation.filter_butterworth"),
          value: "butterworth_lowpass",
        },
        { title: t("modal.plugin.kpi_computation.filter_savgol"), value: "savgol_lowpass" },
      ],
      text: t("modal.plugin.kpi_computation.filter_type"),
      dataTour: "kpi-filter-type",
    },
    {
      field: "slider",
      name: "order",
      value: 3,
      min: 1,
      max: 10,
      step: 1,
      text: t("modal.plugin.kpi_computation.order"),
      hidden: true,
    },
    {
      field: "slider",
      name: "Wn",
      value: 1.0,
      min: 0.01,
      max: 10.0,
      step: 0.01,
      text: t("modal.plugin.kpi_computation.Wn"),
      hidden: true,
    },
    {
      field: "slider",
      name: "window_length",
      value: 5,
      min: 3,
      max: 51,
      step: 2,
      text: t("modal.plugin.kpi_computation.window_length"),
      hidden: true,
    },
    {
      field: "slider",
      name: "poly_order",
      value: 3,
      min: 1,
      max: 10,
      step: 1,
      text: t("modal.plugin.kpi_computation.poly_order"),
      hidden: true,
    },
  ]);

  // Toggle visibility of filter hyperparameters based on selected filter_type
  watch(
    () => optionalParameters.value.find((p) => p.name === "filter_type")?.value,
    (filterType) => {
      for (const p of optionalParameters.value) {
        if (p.name === "order" || p.name === "Wn") {
          p.hidden = filterType !== "butterworth_lowpass";
        } else if (p.name === "window_length" || p.name === "poly_order") {
          p.hidden = filterType !== "savgol_lowpass";
        }
      }
    },
    { immediate: true }
  );

  // Toggle tracking_data_id / object_tracker_run_id / calibration_id visibility based on format
  watch(
    () => parameters.value.find((p) => p.name === "format")?.value,
    (fmt) => {
      const trackingParam = parameters.value.find((p) => p.name === "tracking_data_id");
      const bytetrackParam = parameters.value.find((p) => p.name === "object_tracker_run_id");
      const calibrationParam = parameters.value.find((p) => p.name === "calibration_id");
      if (trackingParam) {
        trackingParam.hidden = fmt === "sportvid";
        trackingParam.format_filter = fmt !== "sportvid" ? fmt : null;
        trackingParam.value = "";
      }
      if (bytetrackParam) bytetrackParam.hidden = fmt !== "sportvid";
      if (calibrationParam) calibrationParam.hidden = fmt !== "sportvid";
    },
    { immediate: true }
  );

  return { parameters, optionalParameters };
}

export function submitPlugin(plugin, parameters, videoId) {
  const pluginRunStore = usePluginRunStore();
  // `uiOnly` fields drive the dialog rather than the plugin and never go into the payload (the
  // lens profile block, explanatory notes) -- they carry no parameter at all.
  parameters = parameters.filter((p) => !p.uiOnly);

  if (plugin === "object_tracker") {
    const targetIndex = parameters.findIndex((p) => p.name === "tracking_target");
    if (targetIndex >= 0) {
      const target = parameters[targetIndex].value;
      const detector = parameters.find((p) => p.name === "detector")?.value;
      parameters.splice(targetIndex, 1);

      const classes = objectTrackerClasses(target, detector);
      if (classes) {
        parameters.push({ name: "classes", value: classes, group: "detector_params" });
      }
    }
  }

  // `hidden` always means "not applicable to the current selection" (e.g. object_tracker's
  // detector-dependent params) -- such entries are dropped entirely rather than submitted
  // with a stale/empty value, so the backend falls back to its own defaults/conditional
  // logic. Parameters additionally tagged with `group` (e.g. object_tracker's
  // detector_params/tracker_params) are bundled into a single nested object under that
  // group name instead of being submitted individually.
  const grouped = {};
  const ungrouped = [];
  for (const p of parameters) {
    if (p.hidden) continue;
    if (p.group) {
      setGroupedValue(grouped, p);
    } else {
      ungrouped.push(p);
    }
  }

  const mappedParameters = ungrouped.map((p) =>
    "file" in p ? { name: p.name, file: p.file } : { name: p.name, value: p.value }
  );
  for (const [name, value] of Object.entries(grouped)) {
    mappedParameters.push({ name, value });
  }

  return pluginRunStore.submit({ plugin, parameters: mappedParameters, videoId });
}
