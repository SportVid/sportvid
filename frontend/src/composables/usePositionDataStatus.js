import { computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { usePositionDataStore } from "@/stores/position_data";

// Shared "how far along is position data / KPI generation" derivation, extracted out of
// ModalStatus.vue (the app-bar status overview) so other places -- e.g. PositionDataMenu's
// disabled-Select tooltip -- can explain to the user exactly what's still missing instead of
// just showing a bare disabled button.
const TRACKER_TYPES = ["bytetrack", "object_tracker"];
const DLT_TYPES = ["calibration_static_dlt"];
const UPLOAD_TYPES = ["posdata_convert"];
const KPI_TYPES = ["kpi_computation"];
const TRANSCRIPT_TYPES = ["whisper"];

export function usePositionDataStatus() {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();
  const positionDataStore = usePositionDataStore();

  const rawPluginRuns = computed(() => pluginRunStore.forVideo(playerStore.videoId));

  // Once a plugin has succeeded, callers should keep showing the most advanced state reached
  // so far (done) rather than flipping back to "running" just because a new run of the same
  // type was started afterwards -- hence "done" is checked before "running" here.
  const deriveState = (types) => {
    const runs = rawPluginRuns.value.filter((run) => types.includes(run.type));
    if (runs.length === 0) return "none";
    if (runs.some((run) => run.status === "DONE")) return "done";
    if (runs.some((run) => run.status === "RUNNING" || run.status === "QUEUED")) return "running";
    if (runs.some((run) => run.status === "ERROR")) return "error";
    return "none";
  };

  // AND: all given states must be "done" (e.g. player tracking + DLT belong together as one variant).
  const combineAll = (states) => {
    if (states.every((s) => s === "done")) return "done";
    if (states.some((s) => s === "running")) return "running";
    if (states.some((s) => s === "error")) return "error";
    return "none";
  };

  // OR: any one of the given states being "done" is enough (alternative variants).
  const combineAny = (states) => {
    if (states.some((s) => s === "done")) return "done";
    if (states.some((s) => s === "running")) return "running";
    if (states.some((s) => s === "error")) return "error";
    return "none";
  };

  // An object_tracker run without a tracker attached only detects the ball (result name
  // "bboxes_ball", see backend tasks/object_tracker.py); legacy bytetrack runs and
  // object_tracker runs with a tracker attached (result name "bboxes") track players. Same
  // check as Parameters.vue / ModalPositionDataSelect.vue's isBallTrackerRun.
  const isBallTrackerRun = (pluginRunId) =>
    pluginRunResultStore.forPluginRun(pluginRunId).some((r) => r.name === "bboxes_ball");

  const deriveTrackerState = (wantBall) => {
    const runs = rawPluginRuns.value.filter((run) => TRACKER_TYPES.includes(run.type));
    if (runs.length === 0) return "none";
    // Player vs. ball can only be told apart once a run is DONE (via its result name) - the
    // parameters that decide this aren't available on non-finished runs. So a still-running or
    // failed run of ambiguous kind is surfaced on both variants until it resolves to one of them.
    if (runs.some((run) => run.status === "DONE" && isBallTrackerRun(run.id) === wantBall)) {
      return "done";
    }
    if (runs.some((run) => run.status === "RUNNING" || run.status === "QUEUED")) return "running";
    if (runs.some((run) => run.status === "ERROR")) return "error";
    return "none";
  };

  const playerTrackingState = computed(() => deriveTrackerState(false));
  const objectTrackingState = computed(() => deriveTrackerState(true));
  const dltState = computed(() => deriveState(DLT_TYPES));
  const uploadState = computed(() => deriveState(UPLOAD_TYPES));
  const kpiState = computed(() => deriveState(KPI_TYPES));
  const transcriptState = computed(() => deriveState(TRANSCRIPT_TYPES));

  // Ball tracking (object tracking) is optional: position data only requires player
  // tracking + DLT calibration to count as available.
  const variantAutoState = computed(() => combineAll([playerTrackingState.value, dltState.value]));

  const posdataOverallState = computed(() => {
    if (positionDataStore.positionDataList.length > 0) return "done";
    return combineAny([variantAutoState.value, uploadState.value]);
  });

  const posdataAvailable = computed(() => posdataOverallState.value === "done");

  const maxProgress = (types) => {
    const runningRuns = rawPluginRuns.value.filter(
      (run) => types.includes(run.type) && (run.status === "RUNNING" || run.status === "QUEUED")
    );
    if (!runningRuns.length) return null;
    return Math.round(Math.max(...runningRuns.map((run) => parseFloat(run.progress) * 100)));
  };

  return {
    playerTrackingState,
    objectTrackingState,
    dltState,
    uploadState,
    kpiState,
    transcriptState,
    posdataOverallState,
    posdataAvailable,
    maxProgress,
  };
}
