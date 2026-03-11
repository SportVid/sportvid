import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";

export const useTabStore = defineStore(
  "tabs",
  () => {
    const { t } = useI18n();

    const analysisTabId = ref("position_data");
    const analysisTabs = computed(() => [
      { id: "position_data", name: t("analysis_view.analysis_tabs.position_data") },
    ]);

    const visualizationTabId = ref("timeline");
    const visualizationTabs = computed(() => [
      { id: "timeline", name: t("analysis_view.visualization_tabs.timeline") },
      { id: "events", name: t("analysis_view.visualization_tabs.events") },
      { id: "heatmap", name: t("analysis_view.visualization_tabs.heatmap") },
      { id: "running_distance", name: t("analysis_view.visualization_tabs.running_distance") },
    ]);

    return {
      analysisTabId,
      analysisTabs,
      visualizationTabId,
      visualizationTabs,
    };
  },
  {
    persist: {
      pick: ["analysisTabId", "visualizationTabId"],
      storage: sessionStorage,
    },
  }
);
