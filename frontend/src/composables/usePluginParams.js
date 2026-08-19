import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useUserStore } from "@/stores/user";

// Hides the given (always-required-until-now) parameter names from the UI in "simple"
// experience mode, showing them all again in "complex" mode -- their current values (the
// existing defaults) are left untouched either way. Uses a dedicated `simpleHidden` flag
// rather than the existing `hidden` -- `hidden` also drops a parameter from submission
// entirely (see submitPlugin below), which is only safe for genuinely inapplicable fields
// (e.g. a detector-specific param for a different detector). These fields are still
// required by the backend, just defaulted instead of user-editable, so they must keep being
// submitted with whatever value they currently hold. Shared by objectTrackerParams/
// teamClusteringParams/osnetReidParams below; kpi_computation and calibration_static_dlt are
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
// tracker/tracker_params entirely since there's nothing to track between
// frames for a single ball detection. Ported from the retired ModalPlugin.vue.
const ALL_OBJECT_TRACKER_DETECTOR_ITEMS = [
  { title: "YOLOX", value: "yolox" },
  { title: "YOLOv10 (Ultralytics)", value: "yolo10" },
  { title: "YOLOv11 (Ultralytics)", value: "yolo11" },
  { title: "YOLOv12 (Ultralytics)", value: "yolo12" },
  { title: "YOLOv26 (Ultralytics)", value: "yolo26" },
  { title: "RF-DETR", value: "rfdetr" },
  { title: "RT-DETR", value: "rtdetr" },
];
const BALL_OBJECT_TRACKER_DETECTOR_ITEMS = ALL_OBJECT_TRACKER_DETECTOR_ITEMS.filter((d) =>
  ["yolo11", "yolo12", "rfdetr"].includes(d.value)
);

const DETECTOR_PARAM_VISIBILITY = {
  yolox: ["confidence_threshold", "batch_size", "nms_thresh", "fp16", "decode", "num_classes"],
  yolo10: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo11: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo12: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo26: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  rfdetr: ["confidence_threshold", "batch_size", "max_det", "resolution", "verbose"],
  rtdetr: ["confidence_threshold", "batch_size", "verbose"],
};

const DETECTOR_CONFIDENCE_DEFAULT = {
  yolox: 0.2,
  yolo10: 0.2,
  yolo11: 0.2,
  yolo12: 0.2,
  yolo26: 0.2,
  rfdetr: 0.5,
  rtdetr: 0.25,
};

const BALL_TARGET_DETECTORS = ["yolo11", "yolo12", "rfdetr"];
const BALL_RFDETR_CONFIDENCE_DEFAULT = 0.2;
const BALL_YOLO_IOU_DEFAULT = 0.5;
const PLAYER_IOU_DEFAULT = 0.3;

// Ball vs. player class filters per detector, keyed by tracking_target. There's no UI
// control for `classes` -- it's derived from the (UI-only) tracking_target parameter in
// submitPlugin() below, which then strips tracking_target from the payload since the
// backend doesn't know that field.
const OBJECT_TRACKER_CLASSES_BY_TARGET = {
  ball: {
    yolo11: [32],
    yolo12: [32],
    rfdetr: ["ball"],
  },
  player: {
    yolox: [0],
    yolo10: [0],
    yolo11: [0],
    yolo12: [0],
    yolo26: [0],
    rtdetr: [0],
    rfdetr: ["player", "referee", "goalkeeper"],
  },
};

export function objectTrackerParams() {
  const { t } = useI18n();
  const playerStore = usePlayerStore();

  const parameters = ref([
    {
      field: "slider",
      min: 1,
      max: 30,
      value: Math.round(playerStore.videoFPS),
      step: 1,
      name: "fps",
      text: t("modal.plugin.fps"),
      dataTour: "bytetrack-fps",
    },
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
      value: "yolox",
      items: ALL_OBJECT_TRACKER_DETECTOR_ITEMS,
      text: t("modal.plugin.object_tracker.detector"),
    },
    {
      field: "select_options",
      name: "tracker",
      value: "bytetrack",
      items: [{ title: "ByteTrack", value: "bytetrack" }],
      text: t("modal.plugin.object_tracker.tracker"),
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
      min: 56,
      max: 1400,
      value: 1288,
      step: 56,
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
  ]);

  // Toggle visibility of detector-specific parameters based on the selected detector.
  watch(
    () => parameters.value.find((p) => p.name === "detector")?.value,
    (detector) => {
      const visible = DETECTOR_PARAM_VISIBILITY[detector] || [];
      for (const p of optionalParameters.value) {
        if (p.group !== "detector_params") continue;
        p.hidden = !visible.includes(p.name);
      }
      const confidenceParam = optionalParameters.value.find(
        (p) => p.name === "confidence_threshold"
      );
      if (confidenceParam && detector in DETECTOR_CONFIDENCE_DEFAULT) {
        confidenceParam.value = DETECTOR_CONFIDENCE_DEFAULT[detector];
      }
    },
    { immediate: true }
  );

  // Toggle between "player" and "ball" tracking runs: restricts the detector choices,
  // hides the tracker (ByteTrack) and all tracker_params fields for ball runs (no tracker
  // for ball detections), and adjusts detector confidence/iou defaults accordingly.
  watch(
    () => [
      parameters.value.find((p) => p.name === "tracking_target")?.value,
      parameters.value.find((p) => p.name === "detector")?.value,
    ],
    ([target, detector]) => {
      const detectorParam = parameters.value.find((p) => p.name === "detector");
      const trackerParam = parameters.value.find((p) => p.name === "tracker");
      const trackerParamFields = optionalParameters.value.filter(
        (p) => p.group === "tracker_params"
      );
      const confidenceParam = optionalParameters.value.find(
        (p) => p.name === "confidence_threshold"
      );
      const iouParam = optionalParameters.value.find((p) => p.name === "iou");

      if (target === "ball") {
        detectorParam.items = BALL_OBJECT_TRACKER_DETECTOR_ITEMS;
        if (!BALL_TARGET_DETECTORS.includes(detector)) {
          detectorParam.value = "yolo11";
          return;
        }
        // `hidden` (unlike simpleHidden below) also drops the field from submission
        // (see submitPlugin) -- for "tracker" that's the actual signal the backend uses to
        // tell ball- from player-tracking runs apart (object_tracker.py:
        // `"bboxes" if parameters.get("tracker") else "bboxes_ball"`), so this must stay
        // driven by tracking_target alone and never by experience mode.
        if (trackerParam) trackerParam.hidden = true;
        for (const p of trackerParamFields) p.hidden = true;

        if (detector === "rfdetr" && confidenceParam) {
          confidenceParam.value = BALL_RFDETR_CONFIDENCE_DEFAULT;
        }
        if ((detector === "yolo11" || detector === "yolo12") && iouParam) {
          iouParam.value = BALL_YOLO_IOU_DEFAULT;
        }
      } else {
        detectorParam.items = ALL_OBJECT_TRACKER_DETECTOR_ITEMS;
        if (trackerParam) trackerParam.hidden = false;
        for (const p of trackerParamFields) p.hidden = false;

        if (iouParam) iouParam.value = PLAYER_IOU_DEFAULT;
        if (confidenceParam && detector in DETECTOR_CONFIDENCE_DEFAULT) {
          confidenceParam.value = DETECTOR_CONFIDENCE_DEFAULT[detector];
        }
      }
    },
    { immediate: true }
  );

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

const OSNET_REID_MODEL_CHECKPOINT_MAP = {
  osnet_x1_0: "/models/reid/osnet_x1_0_ms_d_c.pth.tar",
  osnet_ain_x1_0: "/models/reid/osnet_ain_ms_d_c.pt.tarh",
  osnet_ibn_x1_0: "/models/reid/osnet_ibn_ms_d_c.pth.tar",
};

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
    {
      field: "select_options",
      name: "model_name",
      value: "osnet_x1_0",
      items: [
        { title: "OSNet x1.0", value: "osnet_x1_0" },
        { title: "OSNet-IBN x1.0", value: "osnet_ibn_x1_0" },
        { title: "OSNet-AIN x1.0", value: "osnet_ain_x1_0" },
      ],
      text: t("modal.plugin.osnet_reid.model_name"),
    },
  ]);

  const optionalParameters = ref([
    {
      field: "text_field",
      name: "checkpoint",
      value: "/models/reid/osnet_x1_0_ms_d_c.pth.tar",
      hidden: true,
    },
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

  watch(
    () => parameters.value.find((p) => p.name === "model_name")?.value,
    (modelName) => {
      const checkpointParam = optionalParameters.value.find((p) => p.name === "checkpoint");
      if (checkpointParam && modelName in OSNET_REID_MODEL_CHECKPOINT_MAP) {
        checkpointParam.value = OSNET_REID_MODEL_CHECKPOINT_MAP[modelName];
      }
    },
    { immediate: true }
  );

  hideInSimpleMode(parameters, ["gallery_mode", "model_name"]);

  return { parameters, optionalParameters };
}

export function dltParams() {
  const { t } = useI18n();

  const parameters = ref([
    {
      field: "select_calibration",
      name: "calibration_id",
      value: "",
      text: t("modal.plugin.calibration_static_dlt.calibration_id"),
      hint: t("modal.plugin.calibration_static_dlt.calibration_id_hint"),
    },
  ]);

  return { parameters, optionalParameters: ref([]) };
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
  parameters = [...parameters];

  if (plugin === "object_tracker") {
    const targetIndex = parameters.findIndex((p) => p.name === "tracking_target");
    if (targetIndex >= 0) {
      const target = parameters[targetIndex].value;
      const detector = parameters.find((p) => p.name === "detector")?.value;
      parameters.splice(targetIndex, 1);

      const classes = OBJECT_TRACKER_CLASSES_BY_TARGET[target]?.[detector];
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
      grouped[p.group] = grouped[p.group] || {};
      grouped[p.group][p.name] = p.value;
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
