import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";

export const useClusterTimelineItemStore = defineStore("clusterTimelineItem", () => {
  const clusterTimelineItems = ref({});
  const isLoading = ref(false);
  const selectedPlaceClustering = ref(null);
  const selectedFaceClustering = ref(null);

  const pluginRunStore = usePluginRunStore();
  const playerStore = usePlayerStore();

  const faceClusteringList = computed(() => {
    return pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type === "face_clustering" && e.status === "DONE")
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .map((e) => ({
        index: e.id,
        name: new Date(e.date),
      }));
  });

  const placeClusteringList = computed(() => {
    return pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type === "place_clustering" && e.status === "DONE")
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .map((e) => ({
        index: e.id,
        name: new Date(e.date),
      }));
  });

  const latestPlaceClustering = computed(() => {
    const placeClustering = pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type === "place_clustering" && e.status === "DONE")
      .sort((a, b) => new Date(b.date) - new Date(a.date));

    if (!placeClustering.length) {
      return [];
    }
    return Object.values(clusterTimelineItems)
      .filter((cti) => cti.plugin_run === selectedPlaceClustering.value)
      .sort((a, b) => b.items.length - a.items.length);
  });

  const latestFaceClustering = computed(() => {
    const faceClustering = pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type === "face_clustering" && e.status === "DONE")
      .sort((a, b) => new Date(b.date) - new Date(a.date));

    if (!faceClustering.length) {
      return [];
    }
    return Object.values(clusterTimelineItems)
      .filter((cti) => cti.plugin_run === selectedFaceClustering.value)
      .sort((a, b) => b.items.length - a.items.length);
  });

  const setSelectedPlaceClustering = async ({ videoId = null, pluginRunId = null }) => {
    selectedPlaceClustering.value = pluginRunId;

    if (isLoading.value) return;
    isLoading.value = true;

    const params = { plugin_run_id: pluginRunId, video_id: videoId || playerStore.videoId };

    try {
      await axios.post(`${config.API_LOCATION}/video/analysis/setselectedplaceclustering`, params);
    } finally {
      isLoading.value = false;
    }
  };

  const setSelectedFaceClustering = async ({ videoId = null, pluginRunId = null }) => {
    selectedFaceClustering.value = pluginRunId;

    if (isLoading.value) return;
    isLoading.value = true;

    const params = { plugin_run_id: pluginRunId, video_id: videoId || playerStore.videoId };

    try {
      await axios.post(`${config.API_LOCATION}/video/analysis/setselectedfaceclustering`, params);
    } finally {
      isLoading.value = false;
    }
  };

  const fetchAll = async (videoId = null) => {
    videoId = videoId || playerStore.videoId;

    if (!videoId || isLoading.value) return;
    isLoading.value = true;

    try {
      const [itemsRes, selectedRes] = await Promise.all([
        axios.get(`${config.API_LOCATION}/cluster/timeline/item/fetch`, {
          params: { video_id: videoId },
        }),
        axios.get(`${config.API_LOCATION}/video/analysis/get`, {
          params: { video_id: videoId },
        }),
      ]);

      if (itemsRes.data.status === "ok") {
        replaceStore(itemsRes.data.entries);
      }
      if (selectedRes.data.status === "ok") {
        selectedPlaceClustering.value = selectedRes.data.entry.selected_place_clustering;
        selectedFaceClustering.value = selectedRes.data.entry.selected_face_clustering;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const merge = async ({ cluster_from_id, cluster_to_id }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const cluster_from = clusterTimelineItems[cluster_from_id];
    const cluster_to = clusterTimelineItems[cluster_to_id];

    try {
      const res = await axios.post(`${config.API_LOCATION}/cluster/timeline/item/merge`, {
        from_id: cluster_from.id,
        to_id: cluster_to.id,
      });

      if (res.data.status === "ok") {
        cluster_to.items = [...cluster_to.items, ...cluster_from.items];
        deleteFromStore(cluster_from_id);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const deleteFromStore = (cluster_id) => {
    delete clusterTimelineItems[cluster_id];
  };

  const replaceStore = (items) => {
    clearStore();
    items.forEach((e) => {
      clusterTimelineItems[e.cluster_id] = e;
    });
  };

  const clearStore = () => {
    Object.keys(clusterTimelineItems).forEach((key) => {
      delete clusterTimelineItems[key];
    });
  };

  return {
    clusterTimelineItems,
    isLoading,
    selectedPlaceClustering,
    selectedFaceClustering,
    faceClusteringList,
    placeClusteringList,
    latestPlaceClustering,
    latestFaceClustering,
    setSelectedPlaceClustering,
    setSelectedFaceClustering,
    fetchAll,
    merge,
    deleteFromStore,
    replaceStore,
    clearStore,
  };
});
