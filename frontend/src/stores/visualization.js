import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useTopViewStore } from "@/stores/top_view";

export const useVisualizationStore = defineStore(
  "visualization",
  () => {
    const topViewStore = useTopViewStore();

    const showAggregatedFull = ref(true);
    const showAggregatedFirst = ref(false);
    const showAggregatedSecond = ref(false);
    const showProgress = ref(false);

    const halftimesExist = computed(() => {
      const allPositions = Object.values(topViewStore.positionDataTopView).flat();
      const gameSections = new Set(allPositions.map((p) => p[2]));
      return gameSections.has(1) && gameSections.has(2);
    });

    function resetAndActivate(targetRef) {
      if (targetRef.value) {
        viewAggregatedFull();
      } else {
        showAggregatedFull.value = false;
        showAggregatedFirst.value = false;
        showAggregatedSecond.value = false;
        showProgress.value = false;
        targetRef.value = true;
      }
    }

    function viewAggregatedFull() {
      resetAndActivate(showAggregatedFull);
    }

    function viewAggregatedFirst() {
      resetAndActivate(showAggregatedFirst);
    }

    function viewAggregatedSecond() {
      resetAndActivate(showAggregatedSecond);
    }

    function viewProgress() {
      resetAndActivate(showProgress);
    }

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
      teamColorMapping.value[teamId] = newColor;
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

    return {
      showAggregatedFull,
      showAggregatedFirst,
      showAggregatedSecond,
      showProgress,
      viewAggregatedFull,
      viewAggregatedFirst,
      viewAggregatedSecond,
      viewProgress,
      halftimesExist,
      teamColorMapping,
      getTeamColor,
      setTeamColor,
      getNextTeamId,
      addTeamColor,
    };
  },
  {
    persist: {
      pick: ["teamColorMapping"],
      storage: sessionStorage,
    },
  }
);
