import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useTopViewStore } from "@/stores/top_view";

export const useVisualizationStore = defineStore("visualization", () => {
  const topViewStore = useTopViewStore();

  const showAggregatedFull = ref(true);
  const showAggregatedFirst = ref(false);
  const showAggregatedSecond = ref(false);
  const showProgress = ref(false);

  const halftimesExist = computed(() => {
    const allPositions = Object.values(topViewStore.positionDataTopView).flat();
    const gameSections = new Set(allPositions.map((p) => p[4]));
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
  };
});
