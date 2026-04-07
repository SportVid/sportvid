import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";

export const useTabStore = defineStore(
  "tabs",
  () => {
    const { t } = useI18n();

    const visualizationTabId = ref("timeline");
    const visualizationTabs = computed(() => [
      { id: "timeline", name: t("analysis_view.visualization_tabs.timeline") },
      { id: "events", name: t("analysis_view.visualization_tabs.events") },
      { id: "heatmap", name: t("analysis_view.visualization_tabs.heatmap") },
      { id: "kpi", name: t("analysis_view.visualization_tabs.kpi") },
    ]);

    const tutorialTabId = ref("single");
    const tutorialTabs = computed(() => [
      { id: "single", name: t("modal.tutorial.tabs.singles") },
      { id: "pipeline", name: t("modal.tutorial.tabs.pipelines") },
    ]);

    return {
      visualizationTabId,
      visualizationTabs,
      tutorialTabId,
      tutorialTabs,
    };
  },
  {
    persist: {
      pick: ["visualizationTabId", "tutorialTabId"],
      storage: sessionStorage,
    },
  }
);
