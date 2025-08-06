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

  const currentStepId = ref(null);
  const stepModalPluginButton = ref(null);

  const modalPluginVisible = ref(false);

  const tutorials = [
    {
      id: "calibration-tracking",
      name: t("modal.tutorial.calibration_tracking.name"),
      description: t("modal.tutorial.calibration_tracking.description"),
      icon: "mdi-camera-control",
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
    "calibration-tracking": {
      steps: [
        {
          id: "check-view",
          text: "Bitte wähle ein Video aus, um mit der Kalibrierung zu beginnen.",
          attachTo: {
            element: '[data-tour="select-video"]',
            on: "top",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (router.currentRoute.value.path.startsWith("/video-analysis")) {
                window.currentTutorial?.next();
              } else if (router.currentRoute.value.path !== "/") {
                router.push({ name: "VideoView" }).then(() => {
                  window.currentTutorial?.show(0);
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
          text: "Please create a new calibration asset or choose an existing one.",
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
                window.currentTutorial?.next();
              } else {
                resolve();
              }
            });
          },
          when: createClickToNextStepHandler(1, ["modal-plugin-button"]),
        },
        {
          id: "calibration-asset-edit",
          text: "Edit the calibration asset by adding or deleting marker and save it for plugin usage.",
          attachTo: {
            element: '[data-tour="calibration-asset-edit-row"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                stepModalPluginButton.value = true;
                window.currentTutorial?.next();
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
          when: createClickToNextStepHandler(2, []),
        },
        {
          id: "modal-plugin-button",
          text: "Open the plugin overview.",
          attachTo: {
            element: '[data-tour="modal-plugin-button"]',
            on: "bottom",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (stepModalPluginButton.value === true) {
                resolve();
              } else if (stepModalPluginButton.value === false) {
                window.currentTutorial?.next();
              }
            });
          },
          when: createClickToNextStepHandler(3, []),
        },
        {
          id: "modal-plugin-overview",
          text: "Run those 2 plugins to get the tracking data.",
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
          text: "Please select calibration asset and position data.",
          attachTo: {
            element: '[data-tour="position-data-menu"]',
            on: "left",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (tabStore.analysisTabId === "pos_data" && modalPluginVisible.value === false) {
                const showMenu = Object.keys(bboxesStore.bboxDataTopView).length === 0;
                if (!showMenu) {
                  window.currentTutorial?.next();
                } else {
                  resolve();
                }
              }
            });
          },
          when: createClickToNextStepHandler(5, []),
        },
        {
          id: "position-data-analysis",
          text: "Now you finished the tutorial and can analyse your data with your individual settings",
          attachTo: {
            element: '[data-tour="position-data-edit-row"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Analyse",
              action: () => {
                window.currentTutorial?.complete();
              },
            },
          ],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (tabStore.analysisTabId === "pos_data" && modalPluginVisible.value === false) {
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
        const steps = window.currentTutorial?.steps || [];
        if (!steps.length) return;

        const currentStepSelector = steps[currentStepIndex]?.options?.attachTo?.element;
        currentStepId.value = steps[currentStepIndex]?.options?.id;
        if (!currentStepSelector) return;

        targetEl = document.querySelector(currentStepSelector);
        if (!targetEl) return;

        onClick = (event) => {
          if (event.target.closest('[data-tour="calibration-asset-edit-row"]')) {
            stepModalPluginButton.value = false;
          }

          window.currentTutorial.hide();

          targetEl.removeEventListener("click", onClick);
          // document.removeEventListener("click", onClick);

          const waitForNextStep = () => {
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
                  window.currentTutorial.show(stepIdx);
                  return;
                }
              }
            }
            requestAnimationFrame(waitForNextStep);
          };

          waitForNextStep();
        };

        targetEl.addEventListener("click", onClick);
        // document.addEventListener("click", onClick, true);
      },

      hide() {
        if (targetEl && onClick) {
          targetEl.removeEventListener("click", onClick);
          // document.removeEventListener("click", onClick);
        }
      },
    };
  }

  return { tutorials, tutorialSteps, currentStepId, modalPluginVisible };
});
