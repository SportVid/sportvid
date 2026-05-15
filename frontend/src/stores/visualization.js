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

    // team_id semantics (matches posdata_convert): 0=inactive, 1=ball, 2=refs, ≥3=active teams.
    const teamColorMapping = ref({
      0: "#9E9E9E", // grey — inactive / spectator
      1: "#000000", // black — ball (rendered as SVG icon; color used only for matchup labels)
      2: "#FFD600", // yellow — referees
      3: "#FF0000", // red — team A
      4: "#0000FF", // blue — team B
      5: "#004f00", // green
      6: "#800080", // purple
      7: "#FFA500", // orange
      8: "#FFC0CB", // pink
      9: "#A52A2A", // brown
      10: "#FFFFFF", // white
      11: "#00FFFF", // cyan
      12: "#808000", // olive
    });
    function getTeamColor(teamId) {
      return teamColorMapping.value[teamId] || "#808080";
    }
    function setTeamColor(teamId, newColor) {
      teamColorMapping.value = { ...teamColorMapping.value, [teamId]: newColor };
    }

    function getNextTeamId() {
      // Active player teams start at id=3 (slots 0/1/2 reserved for inactive/ball/refs).
      const usedIds = Object.keys(teamColorMapping.value)
        .map(Number)
        .filter((id) => id >= 3);
      let id = 3;
      while (usedIds.includes(id)) {
        id++;
      }
      return id;
    }

    function addTeamColor(newColor) {
      const usedIds = Object.keys(this.teamColorMapping)
        .map(Number)
        .filter((id) => id >= 3);
      let id = 3;
      while (usedIds.includes(id)) id++;
      this.teamColorMapping[id] = newColor;
      return id;
    }

    const kpiData = shallowRef({});
    const kpiNames = ref([]);
    const kpiFramerate = ref(null);
    const kpiMetaTeamIds = ref({});
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
        kpiMetaTeamIds.value = metaData?.team_ids ?? {};
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
      kpiMetaTeamIds,
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
