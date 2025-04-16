import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";

export const usePluginRunResultStore = defineStore("pluginRunResult", () => {
  const pluginRunResults = ref({});
  const pluginRunResultList = ref([]);
  const isLoading = ref(false);

  const get = (id) => pluginRunResults[id];

  const all = computed(() => pluginRunResultList.value);

  const forPlugin = (id) => pluginRunResults[id];

  const forPluginRun = (pluginRunId) =>
    pluginRunResultList.value
      .map((id) => pluginRunResults[id])
      .filter((e) => e.plugin_run_id === pluginRunId);

  const fetchForVideo = async ({ addResults = false, videoId = null, pluginRunId = null }) => {
    if (isLoading.value) return;

    isLoading.value = true;

    const params = { add_results: addResults };

    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const currentVideoId = playerStore.videoId;
      if (currentVideoId) {
        params.video_id = currentVideoId;
      }
    }

    if (pluginRunId) {
      params.plugin_run_id = pluginRunId;
    }
    try {
      const res = await axios.get(`${config.API_LOCATION}/plugin/run/result/list`, { params });
      if (res.data.status === "ok") {
        updateAll(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    Object.keys(pluginRunResults).forEach((key) => delete pluginRunResults[key]);
    pluginRunResultList.value = [];
  };

  const deleteForPluginRuns = (idList) => {
    idList.forEach((id) => {
      const results = forPluginRun(id);
      results.forEach((resultId) => {
        const index = pluginRunResultList.value.findIndex((item) => item === resultId);
        if (index !== -1) {
          pluginRunResultList.value.splice(index, 1);
          delete pluginRunResults[resultId];
        }
      });
    });
  };

  const updateAll = (newPluginRunResults) => {
    newPluginRunResults.forEach((e) => {
      if (!(e.id in pluginRunResults)) {
        pluginRunResults[e.id] = e;
        pluginRunResultList.value.push(e.id);
      }
    });
  };

  return {
    pluginRunResults,
    pluginRunResultList,
    isLoading,
    get,
    all,
    forPlugin,
    forPluginRun,
    fetchForVideo,
    clearStore,
    deleteForPluginRuns,
    updateAll,
  };
});
