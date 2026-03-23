import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { usePlayerStore } from "@/stores/player";

export const useVisualizationStore = defineStore(
  "visualization",
  () => {
    const topViewStore = useTopViewStore();
    const pluginRunStore = usePluginRunStore();
    const pluginRunResultStore = usePluginRunResultStore();
    const playerStore = usePlayerStore();

    const halftimesExist = computed(() => {
      const allPositions = Object.values(topViewStore.positionDataTopView).flat();
      const gameSections = new Set(allPositions.map((p) => p[2]));
      return gameSections.has(1) && gameSections.has(2);
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

    const kpiData = ref({});
    const kpiNames = ref([]);
    const kpiDataLoaded = ref(false);

    const loadKpiData = async (trackingDataId) => {
      let hasValidData = false;

      try {
        const _kpiData = pluginRunStore
          .forVideo(playerStore.videoId)
          .filter((e) => e.type === "kpi_computation" && e.status === "DONE")
          .map((e) => {
            const results = pluginRunResultStore.forPluginRun(e.id);
            return { ...e, results: JSON.parse(JSON.stringify(results)) };
          })
          .filter((e) => e.results?.[0]?.data?.tracking_data_id === trackingDataId);

        if (!_kpiData.length || !_kpiData[0]?.results?.length) {
          return (kpiData.value = {});
        }

        hasValidData = true;

        console.log("Loaded KPI data:", _kpiData[0]);

        kpiData.value = _kpiData[0]?.results[0]?.data?.kpis;
        kpiNames.value = _kpiData[0]?.results[0]?.data?.meta_data?.kpi_names;
      } finally {
        if (hasValidData) {
          kpiDataLoaded.value = true;
        } else {
          kpiDataLoaded.value = false;
        }
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
