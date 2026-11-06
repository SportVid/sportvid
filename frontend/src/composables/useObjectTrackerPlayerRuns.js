import { computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

// Finished object_tracker (or legacy bytetrack) runs for the current video, restricted to
// player-tracking runs -- i.e. excluding ball-only runs (result name "bboxes_ball", see
// backend tasks/object_tracker.py). Shared by Parameters.vue's "select_object_tracker_run"
// field (team_clustering/osnet_reid/kpi_computation's object_tracker_id pickers) and
// ModalPositionDataCreate.vue's "reuse an existing player-tracking run" picker -- same check
// as usePositionDataStatus.js's isBallTrackerRun, kept in sync manually since that composable
// derives aggregate status rather than a concrete list of runs.
const formatLocalDate = (dateString) => {
  if (!dateString) return "";
  let isoString = dateString.replace(" ", "T");
  if (!isoString.endsWith("Z")) {
    isoString += "Z";
  }
  const date = new Date(isoString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${isoDate} ${localTime}`;
};

export function useObjectTrackerPlayerRuns() {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();

  const isBallTrackerRun = (pluginRunId) =>
    pluginRunResultStore.forPluginRun(pluginRunId).some((r) => r.name === "bboxes_ball");

  const objectTrackerPlayerRuns = computed(() => {
    return pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => ["bytetrack", "object_tracker"].includes(e.type) && e.status === "DONE")
      .map((e) => ({ id: e.id, name: formatLocalDate(e.date) }))
      .filter((e) => !isBallTrackerRun(e.id));
  });

  return { objectTrackerPlayerRuns, formatLocalDate };
}
