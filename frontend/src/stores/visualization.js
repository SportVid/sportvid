import { defineStore } from "pinia";
import { ref, shallowRef, computed } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";
import axios from "../plugins/axios";
import config from "../../app.config";

export const useVisualizationStore = defineStore(
  "visualization",
  () => {
    const topViewStore = useTopViewStore();
    const playerStore = usePlayerStore();

    const halftimesExist = computed(() => {
      const s = topViewStore.precomputedGameSections;
      return s.has(1) && s.has(2);
    });

    const teamColorMapping = ref({
      0: "#808080", // grey
      1: "#000000", // black
      2: "#FF0000", // red
      3: "#0000FF", // blue
      4: "#008000", // green
      5: "#FFFF00", // yellow
      6: "#800080", // purple
      7: "#FFA500", // orange
      8: "#FFC0CB", // pink
      9: "#A52A2A", // brown
      10: "#FFFFFF", // white
    });
    function getTeamColor(teamId) {
      return teamColorMapping.value[teamId] || "#808080";
    }
    function setTeamColor(teamId, newColor) {
      teamColorMapping.value = { ...teamColorMapping.value, [teamId]: newColor };
    }

    function getNextTeamId() {
      const usedIds = Object.keys(teamColorMapping.value)
        .map(Number)
        .filter((id) => id >= 2);
      let id = 2;
      while (usedIds.includes(id)) {
        id++;
      }
      return id;
    }

    function addTeamColor(newColor) {
      const usedIds = Object.keys(this.teamColorMapping)
        .map(Number)
        .filter((id) => id >= 2);
      let id = 2;
      while (usedIds.includes(id)) id++;
      this.teamColorMapping[id] = newColor;
      return id;
    }

    const kpiData = shallowRef({});
    const kpiNames = ref([]);
    const kpiFramerate = ref(null);
    const kpiDataLoaded = ref(false);
    const isLoadingKpi = ref(false);

    const loadKpiData = async (trackingDataId) => {
      kpiDataLoaded.value = false;
      isLoadingKpi.value = true;
      kpiData.value = {};

      try {
        let offset = 0;
        const limit = 5000;
        let total = null;
        let metaData = null;
        const allFrames = {};

        while (total === null || offset < total) {
          const res = await axios.get(`${config.API_LOCATION}/plugin/run/result/kpi/chunk`, {
            params: {
              tracking_data_id: trackingDataId,
              video_id: playerStore.videoId,
              offset,
              limit,
            },
          });

          if (res.data.status === "error" && res.data.type === "not_found") {
            // No KPI data for this tracking_data_id
            return;
          }

          if (res.data.status !== "ok") throw new Error("KPI chunk load failed");

          Object.assign(allFrames, res.data.frames);
          total = res.data.total;
          if (res.data.meta_data) metaData = res.data.meta_data;

          offset += limit;
        }

        if (total === 0) return;

        kpiData.value = allFrames;
        kpiNames.value = metaData?.kpi_names ?? [];
        kpiFramerate.value = metaData?.framerate ?? null;
        kpiDataLoaded.value = true;
      } catch (err) {
        console.error("loadKpiData failed:", err);
      } finally {
        isLoadingKpi.value = false;
      }
    };

    return {
      halftimesExist,
      teamColorMapping,
      getTeamColor,
      setTeamColor,
      getNextTeamId,
      addTeamColor,
      kpiData,
      kpiNames,
      kpiFramerate,
      kpiDataLoaded,
      isLoadingKpi,
      loadKpiData,
    };
  },
  {
    persist: {
      pick: ["teamColorMapping"],
      storage: sessionStorage,
    },
  }
);
