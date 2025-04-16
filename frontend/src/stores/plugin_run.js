import { reactive, computed } from "vue";
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

  const forVideo = (videoId) => {
    return state.pluginRunList
      .map((id) => state.pluginRuns[id])
      .filter((e) => e.video_id === videoId);
  };

  const submit = async ({ plugin, parameters = [], videoId = null }) => {
    const formData = new FormData();
    formData.append("plugin", plugin);

    const jsonParameters = [];
    parameters.forEach((p) => {
      if ("file" in p) {
        formData.append(`file_${p.name}`, p.file);
      } else {
        jsonParameters.push(p);
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
                !currentPluginRunStatus.find((t) => t.id === e.id)?.status === "DONE"
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
            console.log("plugin_run: plugin run result fetch done!");
            timelineStore.fetchForVideo({ videoId: video_id });
            console.log("plugin_run: timeline fetch done!");
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

  return {
    state,
    all,
    forVideo,
    submit,
    fetchAll,
    fetchForVideo,
    clearStore,
    deleteItems,
    updateAll,
  };
});
