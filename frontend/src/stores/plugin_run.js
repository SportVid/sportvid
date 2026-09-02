import { ref, reactive, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useAnnotationStore } from "@/stores/annotation";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";
import { useTimelineStore } from "@/stores/timeline";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { useClusterTimelineItemStore } from "@/stores/cluster_timeline_item";

export const usePluginRunStore = defineStore("pluginRun", () => {
  const state = reactive({
    pluginRuns: {},
    pluginRunList: [],
    isLoading: false,
  });

  const all = computed(() => {
    return state.pluginRunList.map((id) => state.pluginRuns[id]);
  });

  const ACTIVE_STATUS = ["QUEUED", "RUNNING", "WAITING"];
  const isActive = (run) => ACTIVE_STATUS.includes(run?.status);

  // Derived instead of a hand-maintained flag -- as a plain state field it was never
  // exposed by this store's return value, so every `pluginRunStore.pluginInProgress`
  // watcher outside was silently watching `undefined`.
  const pluginInProgress = computed(() => all.value.some((e) => isActive(e)));

  // The batch of runs currently being worked on, per video. A run joins when it is
  // first seen in flight and stays in the batch once it finishes, so the video card's
  // progress bar runs cleanly through to 100% instead of jumping back whenever one run
  // drops out. Runs from an earlier visit were never observed active, so they are never
  // counted -- yesterday's plugin doesn't dilute what you just started.
  const activeBatches = reactive({});

  const trackBatch = (run) => {
    // Internal asset run behind the gallery cover image, not user-facing work
    // (filtered out of the status list too, see AppBar.vue).
    if (!run || !run.video_id || run.type === "thumbnail") return;

    if (!isActive(run)) return;

    const batch = activeBatches[run.video_id];
    if (!batch) {
      activeBatches[run.video_id] = [run.id];
      return;
    }
    if (batch.includes(run.id)) return;
    // Previous batch fully finished -> this run opens a new one, so the bar restarts
    // from zero rather than continuing a completed set.
    const previousStillRunning = batch.some((id) => isActive(state.pluginRuns[id]));
    activeBatches[run.video_id] = previousStillRunning ? [...batch, run.id] : [run.id];
  };

  // 0..100 for the video gallery's card bar: the mean progress across the current
  // batch, counting finished runs as complete. Three queued plugins with the first at
  // 24% therefore read as 8%, not as "0 of 3 done".
  const batchProgress = (videoId) => {
    const batch = activeBatches[videoId];
    if (!batch || !batch.length) return 0;
    // Runs deleted meanwhile (status panel) drop out of the average entirely instead of
    // counting as unfinished forever.
    const runs = batch.map((id) => state.pluginRuns[id]).filter(Boolean);
    if (!runs.length) return 0;
    const total = runs.reduce((sum, run) => {
      if (run.status === "DONE" || run.status === "ERROR" || run.status === "UNKNOWN") {
        return sum + 1;
      }
      return sum + (parseFloat(run.progress) || 0);
    }, 0);
    return (total / runs.length) * 100;
  };

  // Seconds until the current batch for this video finishes: the largest remaining ETA
  // among its still-active runs (they run in parallel on the io worker, so the batch is
  // done when the slowest one is). null while no run reports an ETA yet -- caller then
  // keeps showing the indeterminate bar.
  const batchEta = (videoId) => {
    const batch = activeBatches[videoId];
    if (!batch || !batch.length) return null;
    const etas = batch
      .map((id) => state.pluginRuns[id])
      .filter((run) => run && isActive(run) && run.eta_seconds != null)
      .map((run) => run.eta_seconds);
    return etas.length ? Math.max(...etas) : null;
  };

  // Lets places outside the app bar (e.g. PositionDataMenu's disabled-Select tooltip) open
  // ModalStatus, which the app bar owns/renders -- same remote-open pattern as
  // tutorialStore.openTutorialModal: set true here, AppBar watches it and flips it back off.
  const openStatusModal = ref(false);

  const forVideo = (videoId) => {
    return state.pluginRunList
      .map((id) => state.pluginRuns[id])
      .filter((e) => e.video_id === videoId);
  };

  const submit = async ({ plugin, parameters = [], videoId = null }) => {
    const formData = new FormData();
    formData.append("plugin", plugin);

    const jsonParameters = {};
    parameters.forEach((p) => {
      if ("file" in p) {
        formData.append(`file_${p.name}`, p.file);
      } else {
        jsonParameters[p.name] = p.value;
      }
    });
    formData.append("parameters", JSON.stringify(jsonParameters));

    const playerStore = usePlayerStore();
    const video_id = videoId || playerStore.videoId;
    if (video_id) {
      formData.append("video_id", video_id);
    }

    try {
      const res = await axios.post(`${config.API_LOCATION}/plugin/run/new`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (res.data.status === "ok" && res.data.entry) {
        // Show the run in the status list/badge right away, without waiting for the
        // live event -- and even if the event stream happens to be down.
        updateAll([res.data.entry]);
      }
      return res.data;
    } finally {
      state.isLoading = false;
    }
  };

  const fetchAll = async ({ addResults = false }) => {
    if (state.isLoading) return;
    state.isLoading = true;

    try {
      const res = await axios.get(`${config.API_LOCATION}/plugin/run/list`, {
        params: { add_results: addResults },
      });
      if (res.data.status === "ok") {
        updateAll(res.data.entries);
      }
    } finally {
      state.isLoading = false;
    }
  };

  // Everything that has to be reloaded once a run reaches DONE. Shared by the fetch
  // path below and by the live event handler, so both stay in step.
  const loadResultsForRun = async ({ pluginRunId, videoId }) => {
    const pluginRunResultStore = usePluginRunResultStore();
    const annotationCategoryStore = useAnnotationCategoryStore();
    const annotationStore = useAnnotationStore();
    const timelineStore = useTimelineStore();
    const timelineSegmentStore = useTimelineSegmentStore();
    const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
    const clusterTimelineItemStore = useClusterTimelineItemStore();

    await Promise.all([
      pluginRunResultStore.fetchForVideo({ pluginRunId }),
      annotationCategoryStore.clearStore(),
      annotationStore.clearStore(),
      annotationCategoryStore.fetchForVideo({ videoId }),
      annotationStore.fetchForVideo({ videoId }),
      timelineSegmentStore.fetchForVideo({ videoId }),
      timelineSegmentAnnotationStore.fetchForVideo({ videoId }),
      clusterTimelineItemStore.fetchAll(videoId),
    ]);
    timelineStore.fetchForVideo({ videoId });
  };

  // Patch a single run in from the live event stream. Replaces the polling loops that
  // used to ask the backend every couple of seconds whether anything had changed.
  const applyRunEvent = (entry) => {
    if (!entry || !entry.id) return;
    const previous = state.pluginRuns[entry.id];
    updateAll([entry]);

    const playerStore = usePlayerStore();
    const justFinished = entry.status === "DONE" && previous?.status !== "DONE";
    if (justFinished && entry.video_id === playerStore.videoId) {
      loadResultsForRun({ pluginRunId: entry.id, videoId: entry.video_id });
    }
  };

  const removeRunEvent = (id) => {
    if (id && state.pluginRuns[id]) deleteItems([id]);
  };

  const fetchForVideo = async ({ videoId = null, fetchResults = false }) => {
    if (state.isLoading) return;
    state.isLoading = true;

    const playerStore = usePlayerStore();
    const video_id = videoId || playerStore.videoId;

    const currentPluginRunStatus = (videoId ? forVideo(videoId) : all.value).map((e) => ({
      id: e.id,
      status: e.status,
    }));

    try {
      const res = await axios.get(`${config.API_LOCATION}/plugin/run/list`, {
        params: { video_id: video_id },
      });
      if (res.data.status === "ok") {
        updateAll(res.data.entries);

        const newPluginRunStatus = (videoId ? forVideo(videoId) : all.value).map((e) => ({
          id: e.id,
          status: e.status,
        }));

        const newDone = newPluginRunStatus
          .filter(
            (e) =>
              e.status === "DONE" &&
              currentPluginRunStatus.find((t) => t.id === e.id)?.status !== "DONE"
          )
          .map((e) => e.id);

        if (fetchResults) {
          newDone.forEach((id) => loadResultsForRun({ pluginRunId: id, videoId: video_id }));
        }
      }
    } finally {
      state.isLoading = false;
    }
  };

  const clearStore = () => {
    state.pluginRuns = {};
    state.pluginRunList = [];
  };

  const deleteItems = (idList) => {
    idList.forEach((id) => {
      const index = state.pluginRunList.indexOf(id);
      if (index > -1) {
        state.pluginRunList.splice(index, 1);
        delete state.pluginRuns[id];
      }
    });
    Object.keys(activeBatches).forEach((videoId) => {
      activeBatches[videoId] = activeBatches[videoId].filter((id) => !idList.includes(id));
    });
  };

  const updateAll = (pluginRuns) => {
    pluginRuns.forEach((e) => {
      trackBatch(e);
      if (state.pluginRuns[e.id]) {
        const currPlugin = state.pluginRuns[e.id];
        if (
          e.status !== currPlugin.status ||
          e.progress !== currPlugin.progress ||
          e.eta_seconds !== currPlugin.eta_seconds ||
          e.update_date !== currPlugin.update_date
        ) {
          state.pluginRuns = { ...state.pluginRuns, [e.id]: e };
        }
      } else {
        state.pluginRuns[e.id] = e;
        state.pluginRunList.push(e.id);
      }
    });
  };

  const pluginRunDeleteAllSuccess = ref(false);
  const pluginRunDeleteSelectedSuccess = ref(false);
  const deletePlugins = async ({
    pluginRuns,
    all = false,
    plugin = null,
    videoId = null,
    ids = [],
  } = {}) => {
    let pluginList = [];

    if (all) {
      pluginList = ["all"];
    } else {
      if (plugin) {
        pluginList.push(...pluginRuns.filter((run) => run.type === plugin).map((run) => run.id));
      }
      if (videoId) {
        pluginList.push(...pluginRuns.map((run) => run.id));
      }
      if (ids.length > 0) {
        pluginList.push(...ids);
      }
      pluginList = [...new Set(pluginList)];
    }

    try {
      const res = await axios.post(`${config.API_LOCATION}/plugin/run/delete`, {
        plugin_list: pluginList,
      });

      if (res.data && res.data.status === "ok") {
        deleteItems(pluginList);
        if (all) {
          pluginRunDeleteAllSuccess.value = true;
        } else {
          pluginRunDeleteSelectedSuccess.value = true;
        }
      }
    } catch (err) {
      console.error("Failed to delete plugin runs:", err);
    }
    return false;
  };

  return {
    state,
    all,
    pluginInProgress,
    batchProgress,
    batchEta,
    openStatusModal,
    forVideo,
    submit,
    fetchAll,
    fetchForVideo,
    loadResultsForRun,
    applyRunEvent,
    removeRunEvent,
    clearStore,
    deleteItems,
    updateAll,
    deletePlugins,
    pluginRunDeleteAllSuccess,
    pluginRunDeleteSelectedSuccess,
  };
});
