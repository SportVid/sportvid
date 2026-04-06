import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTabStore } from "./tabs";
import { useTopViewStore } from "@/stores/top_view";
import { useVideoStore } from "@/stores/video";

export const useTutorialStore = defineStore("tutorial", () => {
  const router = useRouter();
  const { t } = useI18n();

  const calibrationAssetStore = useCalibrationAssetStore();
  const tabStore = useTabStore();
  const topViewStore = useTopViewStore();
  const videoStore = useVideoStore();

  const currentTutorialId = ref(null);
  const currentStepId = ref(null);
  const currentStepIdx = ref(null);
  const currentStepText = ref("");
  const nextStepText = ref("");
  const totalSteps = ref(0);

  const isTutorialRunning = ref(false);
  const uploadFormReady = ref(false);

  const modalPluginVisible = ref(false);

  function evaluateRequirements(tutorial) {
    const missing = [];

    if (tutorial.requirements?.length) {
      tutorial.requirements.forEach((req) => {
        switch (req) {
          case "video-uploaded":
            if (videoStore.all.length === 0) missing.push(tutorialRequirements[req]);
            break;
        }
      });
    }

    return {
      isAvailable: missing.length === 0,
      missing,
    };
  }

  const tutorials = [
    {
      id: "position-data-generation",
      type: "pipeline",
      group: "pipelines",
      name: t("modal.tutorial.position_data_generation.name"),
      description: t("modal.tutorial.position_data_generation.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
      requirements: ["video-uploaded", "t1", "t2"],
    },
    {
      id: "timeline-plugin",
      type: "pipeline",
      group: "pipelines",
      name: t("modal.tutorial.timeline_plugin.name"),
      description: t("modal.tutorial.timeline_plugin.description"),
      icon: "mdi-timeline-text",
      disabled: true,
      requirements: ["video-uploaded"],
    },
    {
      id: "run-aggregation",
      type: "pipeline",
      group: "pipelines",
      name: t("modal.tutorial.run_aggregation.name"),
      description: t("modal.tutorial.run_aggregation.description"),
      icon: "mdi-run-fast",
      disabled: true,
      requirements: ["video-uploaded"],
    },
    {
      id: "kpi-visualization",
      type: "pipeline",
      group: "pipelines",
      name: t("modal.tutorial.kpi_visualization.name"),
      description: t("modal.tutorial.kpi_visualization.description"),
      icon: "mdi-chart-line",
      disabled: true,
      requirements: ["video-uploaded"],
    },
    {
      id: "data-export",
      type: "pipeline",
      group: "pipelines",
      name: t("modal.tutorial.data_export.name"),
      description: t("modal.tutorial.data_export.description"),
      icon: "mdi-file-export",
      disabled: true,
      requirements: ["video-uploaded"],
    },
    {
      id: "upload-video",
      type: "single",
      group: "video",
      name: t("modal.tutorial.upload_video.name"),
      description: t("modal.tutorial.upload_video.description"),
      icon: "mdi-upload-outline",
      disabled: false,
      requirements: [],
    },
    {
      id: "analyse-video",
      type: "single",
      group: "video",
      name: t("modal.tutorial.analyse_video.name"),
      description: t("modal.tutorial.analyse_video.description"),
      icon: "mdi-google-analytics",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "run-plugin",
      type: "single",
      group: "app_bar",
      name: t("modal.tutorial.run_plugin.name"),
      description: t("modal.tutorial.run_plugin.description"),
      icon: "mdi-puzzle-outline",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "check-history",
      type: "single",
      group: "app_bar",
      name: t("modal.tutorial.check_history.name"),
      description: t("modal.tutorial.check_history.description"),
      icon: "mdi-history",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "export",
      type: "single",
      group: "app_bar",
      name: t("modal.tutorial.export.name"),
      description: t("modal.tutorial.export.description"),
      icon: "mdi-swap-vertical-bolt",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "calibration-asset",
      type: "single",
      group: "plugins",
      name: t("modal.tutorial.calibration_asset.name"),
      description: t("modal.tutorial.calibration_asset.description"),
      icon: "mdi-link",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "posdata-bytetrack",
      type: "single",
      group: "plugins",
      name: t("modal.tutorial.posdata_bytetrack.name"),
      description: t("modal.tutorial.posdata_bytetrack.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "posdata-manual",
      type: "single",
      group: "plugins",
      name: t("modal.tutorial.posdata_manual.name"),
      description: t("modal.tutorial.posdata_manual.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "kpi-computation",
      type: "single",
      group: "plugins",
      name: t("modal.tutorial.kpi_computation.name"),
      description: t("modal.tutorial.kpi_computation.description"),
      icon: "mdi-chart-areaspline",
      disabled: false,
      requirements: ["video-uploaded"],
    },
  ];
  const availableTutorials = computed(() =>
    tutorials.map((t) => {
      const result = evaluateRequirements(t);
      return {
        ...t,
        isAvailable: result.isAvailable,
        missingRequirements: result.missing,
      };
    })
  );

  const tutorialSteps = {
    "upload-video": {
      steps: [
        {
          id: "video-overview",
          text: t("tutorials.upload_video.video_view"),
          attachTo: {
            element: '[data-tour="video-select"]',
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
              if (router.currentRoute.value.path !== "/") {
                router.push({ name: "VideoView" }).then(() => {
                  tour.value.show(0);
                });
              } else {
                resolve();
              }
            });
          },
        },
        {
          id: "open-upload-modal",
          text: t("tutorials.upload_video.open_modal"),
          attachTo: {
            element: '[data-tour="modal-video-upload-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(1, []),
        },
        {
          id: "fill-upload-form",
          text: t("tutorials.upload_video.fill_form"),
          attachTo: {
            element: '[data-tour="modal-video-upload"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(2, []),
        },
        {
          id: "upload-video",
          text: t("tutorials.upload_video.upload_video"),
          attachTo: {
            element: '[data-tour="upload-video"]',
            on: "top",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                if (uploadFormReady.value) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(3, []),
        },
        {
          id: "video-processing",
          text: t("tutorials.upload_video.video_processing"),
          attachTo: {
            element: '[data-tour="video-processing"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Done",
              action: () => {
                stopTutorial();
              },
            },
          ],
          classes: "tutorial-final-step",
        },
      ],
    },
    "analyse-video": {
      steps: [
        {
          id: "video-overview",
          text: t("tutorials.analyse_video.video_view"),
          attachTo: {
            element: '[data-tour="video-select"]',
            on: "bottom",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (router.currentRoute.value.path !== "/") {
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
          id: "analysis-video-player",
          text: t("tutorials.analyse_video.video_player"),
          attachTo: {
            element: '[data-tour="analysis-video-player"]',
            on: "right",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.next();
              },
            },
          ],
        },
        {
          id: "analysis-top-view",
          text: t("tutorials.analyse_video.top_view"),
          attachTo: {
            element: '[data-tour="analysis-top-view"]',
            on: "left",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.next();
              },
            },
          ],
        },
        {
          id: "analysis-visualization-tabs",
          text: t("tutorials.analyse_video.visualization_tabs"),
          attachTo: {
            element: '[data-tour="analysis-visualization-tabs"]',
            on: "top",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.next();
              },
            },
          ],
        },
        {
          id: "analysis-appbar-actions",
          text: t("tutorials.analyse_video.appbar_actions"),
          attachTo: {
            element: '[data-tour="analysis-appbar-actions"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Done",
              action: () => {
                stopTutorial();
              },
            },
          ],
          classes: "tutorial-final-step",
        },
      ],
    },
    "run-plugin": {
      steps: [
        {
          id: "run-plugin-open",
          text: t("tutorials.run_plugin.step1"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
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
        },
        {
          id: "run-plugin-select",
          text: t("tutorials.run_plugin.step2"),
          attachTo: {
            element: '[data-tour="plugin-object-tracking-overview"]',
            on: "right",
          },
          buttons: [
            {
              text: "Done",
              action: () => {
                stopTutorial();
              },
            },
          ],
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
          classes: "tutorial-final-step",
        },
      ],
    },
    "calibration-asset-guide": {
      steps: [
        {
          id: "calibration-menu-guide",
          text: t("tutorials.calibration_asset_guide.step1"),
          attachTo: {
            element: '[data-tour="calibration-asset-menu"]',
            on: "left",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.next();
              },
            },
          ],
        },
        {
          id: "calibration-edit-guide",
          text: t("tutorials.calibration_asset_guide.step2"),
          attachTo: {
            element: '[data-tour="calibration-asset-edit-row"]',
            on: "bottom",
          },
          buttons: [
            {
              text: "Done",
              action: () => {
                stopTutorial();
              },
            },
          ],
          classes: "tutorial-final-step",
        },
      ],
    },
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
              // if (tabStore.analysisTabId !== "calibration") {
              //   tabStore.analysisTabId = "calibration";
              // }
              const showMenu = calibrationAssetStore.calibrationAssetObjects.length === 0;
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
              // if (tabStore.analysisTabId !== "calibration") {
              //   tabStore.analysisTabId = "calibration";
              // }
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
              // if (
              //   tabStore.analysisTabId === "position_data" &&
              //   modalPluginVisible.value === false
              // ) {
              //   const showMenu = Object.keys(topViewStore.positionDataTopView).length === 0;
              //   if (!showMenu) {
              //     tour.value.next();
              //   } else {
              //     resolve();
              //   }
              // }
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
              // if (
              //   tabStore.analysisTabId === "position_data" &&
              //   modalPluginVisible.value === false
              // ) {
              //   resolve();
              // }
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
  };

  const tutorialRequirements = {
    "video-uploaded": {
      id: "video-uploaded",
      text: t("modal.tutorial.missing_requirements.video_uploaded"),
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
    uploadFormReady.value = false;

    if (tour.value) {
      tour.value.complete();
      tour.value = null;
    }
  }

  const tour = ref(null);

  return {
    tutorials,
    availableTutorials,
    tutorialSteps,
    modalPluginVisible,
    isTutorialRunning,
    currentTutorialId,
    currentStepId,
    currentStepIdx,
    currentStepText,
    nextStepText,
    totalSteps,
    uploadFormReady,
    startTutorial,
    stopTutorial,
    tour,
  };
});
