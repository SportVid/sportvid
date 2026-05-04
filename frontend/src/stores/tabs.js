import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";

export const useTabStore = defineStore(
  "tabs",
  () => {
    const { t } = useI18n();

    const visualizationTabId = ref("timeline");
    const visualizationTabs = computed(() => [
      // { id: "timeline", name: t("analysis_view.visualization_tabs.timeline") },
      // { id: "events", name: t("analysis_view.visualization_tabs.events") },
      { id: "heatmap", name: t("analysis_view.visualization_tabs.heatmap") },
      { id: "kpi", name: t("analysis_view.visualization_tabs.kpi") },
    ]);

    const kpiViewMode = ref("table");

    return {
      visualizationTabId,
      visualizationTabs,
      kpiViewMode,
    };
  },
  {
    persist: {
      pick: ["visualizationTabId", "kpiViewMode"],
      storage: sessionStorage,
    },
  }
);
