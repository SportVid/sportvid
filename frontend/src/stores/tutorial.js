import { defineStore } from "pinia";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTabStore } from "./tabs";
import { useBboxesStore } from "@/stores/bboxes";

export const useTutorialStore = defineStore("tutorial", () => {
  const router = useRouter();
  const { t } = useI18n();

  const calibrationAssetStore = useCalibrationAssetStore();
  const tabStore = useTabStore();
  const bboxesStore = useBboxesStore();

  const currentTutorialId = ref(null);
  const currentStepId = ref(null);
  const currentStepIdx = ref(null);
  const currentStepText = ref("");
  const nextStepText = ref("");
  const totalSteps = ref(0);

  const isTutorialRunning = ref(false);

  const modalPluginVisible = ref(false);

  const tutorials = [
    {
      id: "position-data-generation",
      name: t("modal.tutorial.position_data_generation.name"),
      description: t("modal.tutorial.position_data_generation.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
    },
    {
      id: "timeline-plugin",
      name: t("modal.tutorial.timeline_plugin.name"),
      description: t("modal.tutorial.timeline_plugin.description"),
      icon: "mdi-timeline-text",
      disabled: true,
    },
    {
      id: "run-aggregation",
      name: t("modal.tutorial.run_aggregation.name"),
      description: t("modal.tutorial.run_aggregation.description"),
      icon: "mdi-run-fast",
      disabled: true,
    },
    {
      id: "kpi-visualization",
      name: t("modal.tutorial.kpi_visualization.name"),
      description: t("modal.tutorial.kpi_visualization.description"),
      icon: "mdi-chart-line",
      disabled: true,
    },
    {
      id: "data-export",
      name: t("modal.tutorial.data_export.name"),
      description: t("modal.tutorial.data_export.description"),
      icon: "mdi-file-export",
      disabled: true,
    },
  ];

  const tutorialSteps = {
    "position-data-generation": {
      steps: [
        {
          id: "video-select",
          text: t("tutorials.position_data_generation.video_select"),
          attachTo: {
            element: '[data-tour="video-select"]',
            on: "top",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (router.currentRoute.value.path.startsWith("/video-analysis")) {
                tour.value.next();
              } else if (router.currentRoute.value.path !== "/") {
                router.push({ name: "VideoView" }).then(() => {
                  tour.value.show(0);
                });
              } else {
                resolve();
              }
            });
          },
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "calibration-asset-select",
          text: t("tutorials.position_data_generation.calibration_asset_select"),
          attachTo: {
            element: '[data-tour="calibration-asset-menu"]',
            on: "left",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (tabStore.analysisTabId !== "calibration") {
                tabStore.analysisTabId = "calibration";
              }
              const showMenu = calibrationAssetStore.marker.length === 0;
              if (!showMenu) {
                tour.value.next();
              } else {
                resolve();
              }
            });
          },
          when: createClickToNextStepHandler(1, ["modal-plugin-open"]),
        },
        {
          id: "calibration-asset-edit",
          text: t("tutorials.position_data_generation.calibration_asset_edit"),
          attachTo: {
            element: '[data-tour="calibration-asset-edit-row"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.next();
              },
            },
          ],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (tabStore.analysisTabId !== "calibration") {
                tabStore.analysisTabId = "calibration";
              }
              resolve();
            });
          },
          when: createClickToNextStepHandler(2, ["modal-plugin-open"]),
        },
        {
          id: "modal-plugin-open",
          text: t("tutorials.position_data_generation.modal_plugin_open"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(3, []),
        },
        {
          id: "modal-plugin-select",
          text: t("tutorials.position_data_generation.modal_plugin_select"),
          attachTo: {
            element: '[data-tour="plugin-object-tracking-overview"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (
                document.querySelector('[data-tour="plugin-object-tracking-overview"]') &&
                modalPluginVisible.value === true
              ) {
                resolve();
              }
            });
          },
          when: createClickToNextStepHandler(4, []),
        },
        {
          id: "position-data-select",
          text: t("tutorials.position_data_generation.position_data_select"),
          attachTo: {
            element: '[data-tour="position-data-menu"]',
            on: "left",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (
                tabStore.analysisTabId === "position_data" &&
                modalPluginVisible.value === false
              ) {
                const showMenu = Object.keys(topViewStore.positionDataTopView).length === 0;
                if (!showMenu) {
                  tour.value.next();
                } else {
                  resolve();
                }
              }
            });
          },
          when: createClickToNextStepHandler(5, []),
        },
        {
          id: "position-data-analyse",
          text: t("tutorials.position_data_generation.position_data_analyse"),
          attachTo: {
            element: '[data-tour="position-data-edit-row"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Analyse",
              action: () => {
                stopTutorial();
              },
            },
          ],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (
                tabStore.analysisTabId === "position_data" &&
                modalPluginVisible.value === false
              ) {
                resolve();
              }
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
  };

  function createClickToNextStepHandler(currentStepIndex, forbiddenStepIds = []) {
    let targetEl = null;
    let onClick;

    return {
      show() {
        if (!tour.value || !isTutorialRunning.value) return;

        const steps = tour.value.steps || [];
        if (!steps.length) return;
        totalSteps.value = steps.length;

        const currentStepSelector = steps[currentStepIndex]?.options?.attachTo?.element;

        currentStepId.value = steps[currentStepIndex]?.options?.id;
        currentStepIdx.value = currentStepIndex + 1;
        currentStepText.value = steps[currentStepIndex]?.options?.text;
        nextStepText.value = steps[currentStepIndex + 1]?.options?.text;

        if (!currentStepSelector) return;

        targetEl = document.querySelector(currentStepSelector);
        if (!targetEl) return;

        onClick = () => {
          if (!isTutorialRunning.value) return;

          tour.value.hide();

          targetEl.removeEventListener("click", onClick);
          document.removeEventListener("click", onClick, true);

          const waitForNextStep = () => {
            if (!isTutorialRunning.value) return;

            const nextStepsToCheck = [currentStepIndex + 1, currentStepIndex + 2];
            for (const stepIdx of nextStepsToCheck) {
              if (stepIdx >= steps.length) continue;

              const stepId = steps[stepIdx]?.id;
              if (!stepId) continue;

              if (forbiddenStepIds.includes(stepId)) {
                continue;
              } else {
                const selector = steps[stepIdx].options?.attachTo?.element;
                if (!selector) continue;

                const el = document.querySelector(selector);

                if (el) {
                  tour.value.show(stepIdx);
                  return;
                }
              }
            }
            requestAnimationFrame(waitForNextStep);
          };

          waitForNextStep();
        };

        targetEl.addEventListener("click", onClick);
        document.addEventListener("click", onClick, true);
      },

      hide() {
        if (targetEl && onClick) {
          targetEl.removeEventListener("click", onClick);
          document.removeEventListener("click", onClick);
        }
      },
    };
  }

  function startTutorial(id) {
    isTutorialRunning.value = true;
    currentTutorialId.value = id;
    tour.value.start();
  }

  function stopTutorial() {
    isTutorialRunning.value = false;
    currentTutorialId.value = null;
    currentStepId.value = null;

    if (tour.value) {
      tour.value.complete();
      tour.value = null;
    }
  }

  const tour = ref(null);

  return {
    tutorials,
    tutorialSteps,
    modalPluginVisible,
    isTutorialRunning,
    currentTutorialId,
    currentStepId,
    currentStepIdx,
    currentStepText,
    nextStepText,
    totalSteps,
    startTutorial,
    stopTutorial,
    tour,
  };
});
