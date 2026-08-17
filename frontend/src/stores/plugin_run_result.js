import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";

export const usePluginRunResultStore = defineStore("pluginRunResult", () => {
  const pluginRunResults = ref({});
  const pluginRunResultList = ref([]);
  // True while at least one fetchForVideo request is in flight (see pendingFetches).
  const isLoading = ref(false);
  // Coalesces identical concurrent fetchForVideo calls (same params) onto one request/promise,
  // instead of a single global "isLoading" flag that silently dropped any call arriving while
  // another (possibly unrelated) fetch was in flight -- e.g. ModalPositionDataSelect's onMounted
  // fetch losing the race against video.js's own fetchForVideo on video load, leaving its
  // object-/ball-tracker classification stuck on stale/incomplete results.
  const pendingFetches = new Map();

  const get = (id) => pluginRunResults[id];

  const all = computed(() => pluginRunResultList.value);

  const forPlugin = (id) => pluginRunResults[id];

  const forPluginRun = (pluginRunId) =>
    pluginRunResultList.value
      .map((id) => pluginRunResults[id])
      .filter((e) => e.plugin_run_id === pluginRunId);

  const forPluginRunWithData = async (pluginRunId, videoId = null) => {
    const existing = forPluginRun(pluginRunId);
    if (existing.length === 0 || existing.some((r) => r.data === undefined)) {
      await fetchForVideo({ videoId, pluginRunId, addResults: true });
    }
    return forPluginRun(pluginRunId);
  };

  const fetchForVideo = ({ addResults = false, videoId = null, pluginRunId = null, excludeTypes = [] } = {}) => {
    let resolvedVideoId = videoId;
    if (!resolvedVideoId) {
      const playerStore = usePlayerStore();
      resolvedVideoId = playerStore.videoId || null;
    }

    // Dedup key: identical concurrent calls share one in-flight request/promise. Calls with
    // different params (e.g. a different pluginRunId or excludeTypes) are NOT blocked by each
    // other -- they run concurrently, so no caller's data silently goes missing.
    const key = JSON.stringify({
      addResults,
      videoId: resolvedVideoId,
      pluginRunId,
      excludeTypes: [...excludeTypes].sort(),
    });

    const pending = pendingFetches.get(key);
    if (pending) return pending;

    const params = { add_results: addResults };
    if (resolvedVideoId) {
      params.video_id = resolvedVideoId;
    }
    if (pluginRunId) {
      params.plugin_run_id = pluginRunId;
    }
    if (excludeTypes.length > 0) {
      params.exclude_types = excludeTypes;
    }

    isLoading.value = true;
    const promise = (async () => {
      try {
        const res = await axios.get(`${config.API_LOCATION}/plugin/run/result/list`, { params });
        if (res.data.status === "ok") {
          updateAll(res.data.entries);
        }
      } finally {
        pendingFetches.delete(key);
        if (pendingFetches.size === 0) {
          isLoading.value = false;
        }
      }
    })();

    pendingFetches.set(key, promise);
    return promise;
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
      } else if (e.data !== undefined && pluginRunResults[e.id].data === undefined) {
        // Update when data is now available but wasn't before (lazy load)
        pluginRunResults[e.id] = e;
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
    forPluginRunWithData,
    fetchForVideo,
    clearStore,
    deleteForPluginRuns,
    updateAll,
  };
});
