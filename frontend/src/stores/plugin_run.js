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
    pluginInProgress: false,
  });

  const all = computed(() => {
    return state.pluginRunList.map((id) => state.pluginRuns[id]);
  });

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
      if (res.data.status === "ok") {
        state.pluginInProgress = true;
      }
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
        state.pluginInProgress = all.value.some(
          (e) => e.status === "RUNNING" || e.status === "QUEUED"
        );
      }
    } finally {
      state.isLoading = false;
    }
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

    state.pluginInProgress = currentPluginRunStatus.some(
      (e) => e.status === "RUNNING" || e.status === "QUEUED"
    );

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

        const result = {
          allDone: newPluginRunStatus.every((e) => ["DONE", "ERROR", "UNKNOWN"].includes(e.status)),
          newDone: newPluginRunStatus
            .filter(
              (e) =>
                e.status === "DONE" &&
                currentPluginRunStatus.find((t) => t.id === e.id)?.status !== "DONE"
            )
            .map((e) => e.id),
        };

        state.pluginInProgress = !result.allDone;

        if (fetchResults) {
          const pluginRunResultStore = usePluginRunResultStore();
          const annotationCategoryStore = useAnnotationCategoryStore();
          const annotationStore = useAnnotationStore();
          const timelineStore = useTimelineStore();
          const timelineSegmentStore = useTimelineSegmentStore();
          const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
          const clusterTimelineItemStore = useClusterTimelineItemStore();

          result.newDone.forEach(async (id) => {
            await Promise.all([
              pluginRunResultStore.fetchForVideo({ pluginRunId: id }),
              annotationCategoryStore.clearStore(),
              annotationStore.clearStore(),
              annotationCategoryStore.fetchForVideo({ videoId: video_id }),
              annotationStore.fetchForVideo({ videoId: video_id }),
              timelineSegmentStore.fetchForVideo({ videoId: video_id }),
              timelineSegmentAnnotationStore.fetchForVideo({ videoId: video_id }),
              clusterTimelineItemStore.fetchAll(video_id),
            ]);
            timelineStore.fetchForVideo({ videoId: video_id });
          });
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
  };

  const updateAll = (pluginRuns) => {
    pluginRuns.forEach((e) => {
      if (state.pluginRuns[e.id]) {
        const currPlugin = state.pluginRuns[e.id];
        if (
          e.status !== currPlugin.status ||
          e.progress !== currPlugin.progress ||
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
    openStatusModal,
    forVideo,
    submit,
    fetchAll,
    fetchForVideo,
    clearStore,
    deleteItems,
    updateAll,
    deletePlugins,
    pluginRunDeleteAllSuccess,
    pluginRunDeleteSelectedSuccess,
  };
});
