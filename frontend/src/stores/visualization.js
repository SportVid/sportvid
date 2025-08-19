import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useBboxesStore } from "@/stores/bboxes";

export const useVisualizationStore = defineStore("visualization", () => {
  const bboxesStore = useBboxesStore();

  const showAggregatedFull = ref(true);
  const showAggregatedFirst = ref(false);
  const showAggregatedSecond = ref(false);
  const showProgress = ref(false);

  const halftimesExist = computed(() => {
    const allBboxes = Object.values(topViewStore.positionDataTopView).flat();
    const gameSections = new Set(allBboxes.map((bbox) => bbox.game_section));
    return gameSections.has("firstHalf") && gameSections.has("secondHalf");
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
