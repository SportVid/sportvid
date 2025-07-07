import { defineStore } from "pinia";
import { nextTick, ref } from "vue";
import { useI18n } from "vue-i18n";

export const useVisualizationStore = defineStore("visualization", () => {
  const showAggregatedFull = ref(false);
  const viewAggregatedFull = () => {
    showAggregatedFull.value = !showAggregatedFull.value;
    showAggregatedFirst.value = false;
    showAggregatedSecond.value = false;
    showProgress.value = false;
  };

  const showAggregatedFirst = ref(false);
  const viewAggregatedFirst = () => {
    showAggregatedFirst.value = !showAggregatedFirst.value;
    showAggregatedFull.value = false;
    showAggregatedSecond.value = false;
    showProgress.value = false;
  };

  const showAggregatedSecond = ref(false);
  const viewAggregatedSecond = () => {
    showAggregatedSecond.value = !showAggregatedSecond.value;
    showAggregatedFull.value = false;
    showAggregatedFirst.value = false;
    showProgress.value = false;
  };

  const showProgress = ref(false);
  const viewProgress = () => {
    showProgress.value = !showProgress.value;
    showAggregatedFull.value = false;
    showAggregatedFirst.value = false;
    showAggregatedSecond.value = false;
  };

  return {
    showAggregatedFull,
    viewAggregatedFull,
    showAggregatedFirst,
    viewAggregatedFirst,
    showAggregatedSecond,
    viewAggregatedSecond,
    showProgress,
    viewProgress,
  };
});
