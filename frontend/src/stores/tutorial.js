import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useVideoStore } from "@/stores/video";
import { useTopViewStore } from "@/stores/top_view";
import { useTabStore } from "@/stores/tabs";

export const useTutorialStore = defineStore("tutorial", () => {
  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const calibrationAssetStore = useCalibrationAssetStore();
  const videoStore = useVideoStore();
  const topViewStore = useTopViewStore();
  const tabStore = useTabStore();

  const currentTutorialId = ref(null);
  const currentStepId = ref(null);
  const currentStepIdx = ref(null);
  const currentStepText = ref("");
  const nextStepText = ref("");
  const totalSteps = ref(0);

  const isTutorialRunning = ref(false);
  const uploadFormReady = ref(false);

  const modalPluginVisible = ref(false);
  const tutorialActivePluginId = ref(null);
  const tutorialPluginGroupOpen = ref(null);

  function evaluateRequirements(tutorial) {
    const missing = [];

    if (tutorial.requirements?.length) {
      tutorial.requirements.forEach((req) => {
        switch (req) {
          case "video-uploaded":
            if (videoStore.all.length === 0) missing.push(tutorialRequirements[req]);
            break;
          case "analysis-view-opened":
            if (route.name !== "AnalysisView") missing.push(tutorialRequirements[req]);
            break;
          case "position-data-selected":
            if (topViewStore.sortedFrameKeys.length === 0) missing.push(tutorialRequirements[req]);
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
      id: "upload-video",
      group: "basics",
      name: t("modal.tutorial.upload_video.name"),
      description: t("modal.tutorial.upload_video.description"),
      icon: "mdi-upload-outline",
      disabled: false,
      requirements: [],
    },
    {
      id: "analyse-video",
      group: "basics",
      name: t("modal.tutorial.analyse_video.name"),
      description: t("modal.tutorial.analyse_video.description"),
      icon: "mdi-google-analytics",
      disabled: false,
      requirements: ["video-uploaded"],
    },
    {
      id: "run-plugin",
      group: "basics",
      name: t("modal.tutorial.run_plugin.name"),
      description: t("modal.tutorial.run_plugin.description"),
      icon: "mdi-puzzle-outline",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "check-status",
      group: "basics",
      name: t("modal.tutorial.check_status.name"),
      description: t("modal.tutorial.check_status.description"),
      icon: "mdi-status",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "export",
      group: "basics",
      name: t("modal.tutorial.export.name"),
      description: t("modal.tutorial.export.description"),
      icon: "mdi-swap-vertical-bold",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "dlt-ransac",
      group: "position_data",
      name: t("modal.tutorial.dlt_ransac.name"),
      description: t("modal.tutorial.dlt_ransac.description"),
      icon: "mdi-link",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "posdata-bytetrack",
      group: "position_data",
      name: t("modal.tutorial.posdata_bytetrack.name"),
      description: t("modal.tutorial.posdata_bytetrack.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "posdata-manual",
      group: "position_data",
      name: t("modal.tutorial.posdata_manual.name"),
      description: t("modal.tutorial.posdata_manual.description"),
      icon: "mdi-crosshairs-gps",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "kpi-computation",
      group: "analysis",
      name: t("modal.tutorial.kpi_computation.name"),
      description: t("modal.tutorial.kpi_computation.description"),
      icon: "mdi-chart-box-plus-outline",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened"],
    },
    {
      id: "top-view",
      group: "analysis",
      name: t("modal.tutorial.top_view.name"),
      description: t("modal.tutorial.top_view.description"),
      icon: "mdi-soccer-field",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened", "position-data-selected"],
    },
    {
      id: "heatmap",
      group: "analysis",
      name: t("modal.tutorial.heatmap.name"),
      description: t("modal.tutorial.heatmap.description"),
      icon: "mdi-blur",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened", "position-data-selected"],
    },
    {
      id: "kpi-visualization",
      group: "analysis",
      name: t("modal.tutorial.kpi_visualization.name"),
      description: t("modal.tutorial.kpi_visualization.description"),
      icon: "mdi-chart-areaspline",
      disabled: false,
      requirements: ["video-uploaded", "analysis-view-opened", "position-data-selected"],
    },
    {
      id: "position-data-generation",
      group: "pipelines",
      name: t("modal.tutorial.position_data_generation.name"),
      description: t("modal.tutorial.position_data_generation.description"),
      icon: "mdi-map-marker-path",
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
          text: t("tutorials.run_plugin.open_modal"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "run-plugin-panel",
          text: t("tutorials.run_plugin.plugin_panel"),
          attachTo: {
            element: '[data-tour="plugin-panel"]',
            on: "right",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tutorialPluginGroupOpen.value = 7;
                tour.value.next();
              },
            },
          ],
        },
        {
          id: "run-plugin-select",
          text: t("tutorials.run_plugin.plugin_select"),
          attachTo: {
            element: '[data-tour="plugin-kpi-computation"]',
            on: "right",
          },
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-kpi-computation"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(2, []),
        },
        {
          id: "run-plugin-details",
          text: t("tutorials.run_plugin.plugin_details"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
            on: "left",
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-details"] .v-card-title');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
    "check-status": {
      steps: [
        {
          id: "check-status-open",
          text: t("tutorials.check_status.open_modal"),
          attachTo: {
            element: '[data-tour="modal-status-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "check-status-table",
          text: t("tutorials.check_status.status_table"),
          attachTo: {
            element: '[data-tour="status-table"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="status-table"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "check-status-delete",
          text: t("tutorials.check_status.delete_panel"),
          attachTo: {
            element: '[data-tour="status-delete-panel"]',
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
    export: {
      steps: [
        {
          id: "export-open",
          text: t("tutorials.export.open_modal"),
          attachTo: {
            element: '[data-tour="modal-export-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "export-tab-panel",
          text: t("tutorials.export.export_panel"),
          attachTo: {
            element: '[data-tour="export-tab-panel"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="export-tab-panel"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "export-select",
          text: t("tutorials.export.export_select"),
          attachTo: {
            element: '[data-tour="export_select"]',
            on: "right",
          },
          buttons: [],
          when: createClickToNextStepHandler(2, []),
        },
        {
          id: "export-details",
          text: t("tutorials.export.export_details"),
          attachTo: {
            element: '[data-tour="export-details"]',
            on: "left",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="export-details"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
    "dlt-ransac": {
      steps: [
        {
          id: "calibration-open-modal",
          text: t("tutorials.dlt_ransac.open_modal"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "calibration-select-plugin",
          text: t("tutorials.dlt_ransac.select_plugin"),
          attachTo: {
            element: '[data-tour="plugin-calibration-dlt"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              tutorialPluginGroupOpen.value = 7;
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-calibration-dlt"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(1, []),
        },
        {
          id: "calibration-plugin-overview",
          text: t("tutorials.dlt_ransac.plugin_overview"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-details"] .v-card-title');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "calibration-create-select",
          text: t("tutorials.dlt_ransac.create_select"),
          attachTo: {
            element: '[data-tour="dlt-calibration-create-select"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(3, []),
        },
        {
          id: "calibration-create-modal",
          text: t("tutorials.dlt_ransac.create_modal"),
          attachTo: {
            element: '[data-tour="modal-calibration-asset-create"]',
            on: "bottom",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="modal-calibration-asset-create"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(4, []),
        },
        {
          id: "calibration-asset-btn",
          text: t("tutorials.dlt_ransac.calibration_asset_btn"),
          attachTo: {
            element: '[data-tour="calibration-asset-btn"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="calibration-asset-btn"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "calibration-object-btn",
          text: t("tutorials.dlt_ransac.object_btn"),
          attachTo: {
            element: '[data-tour="calibration-object-btn"]',
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
          id: "calibration-object-info",
          text: t("tutorials.dlt_ransac.object_info"),
          attachTo: {
            element: '[data-tour="object-info"]',
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
          classes: "tutorial-final-step",
        },
      ],
    },
    "posdata-bytetrack": {
      steps: [
        {
          id: "bytetrack-open-modal",
          text: t("tutorials.posdata_bytetrack.open_modal"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "bytetrack-select-plugin",
          text: t("tutorials.posdata_bytetrack.select_plugin"),
          attachTo: {
            element: '[data-tour="plugin-bytetrack"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              tutorialPluginGroupOpen.value = 7;
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-bytetrack"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(1, []),
        },
        {
          id: "bytetrack-overview",
          text: t("tutorials.posdata_bytetrack.plugin_overview"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-details"] .v-card-title');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "bytetrack-fps",
          text: t("tutorials.posdata_bytetrack.fps"),
          attachTo: {
            element: '[data-tour="bytetrack-fps"]',
            on: "left",
          },
          when: createNoOverlayHandler(),
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
          id: "bytetrack-run",
          text: t("tutorials.posdata_bytetrack.run_plugin"),
          attachTo: {
            element: '[data-tour="kpi-run-plugin"]',
            on: "top",
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
    "posdata-manual": {
      steps: [
        {
          id: "posdata-manual-upload-open",
          text: t("tutorials.posdata_manual.upload_open"),
          attachTo: {
            element: '[data-tour="posdata-manual-upload-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "posdata-manual-upload-modal",
          text: t("tutorials.posdata_manual.upload_modal"),
          attachTo: {
            element: '[data-tour="posdata-manual-upload-modal"]',
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="posdata-manual-upload-modal"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "posdata-manual-format",
          text: t("tutorials.posdata_manual.format_select"),
          attachTo: {
            element: '[data-tour="posdata-manual-format"]',
            on: "right",
          },
          when: createNoOverlayHandler(),
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
          id: "posdata-manual-upload",
          text: t("tutorials.posdata_manual.upload"),
          attachTo: {
            element: '[data-tour="posdata-manual-upload"]',
            on: "top",
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
    "kpi-computation": {
      steps: [
        {
          id: "kpi-open-modal",
          text: t("tutorials.kpi_computation.open_modal"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(0, []),
        },
        {
          id: "kpi-select-plugin",
          text: t("tutorials.kpi_computation.select_plugin"),
          attachTo: {
            element: '[data-tour="plugin-kpi-computation"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              tutorialPluginGroupOpen.value = 7;
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-kpi-computation"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(1, []),
        },
        {
          id: "kpi-overview",
          text: t("tutorials.kpi_computation.plugin_overview"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
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
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-details"] .v-card-title');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "kpi-format",
          text: t("tutorials.kpi_computation.format_select"),
          attachTo: {
            element: '[data-tour="kpi-format"]',
            on: "left",
          },
          when: createNoOverlayHandler(),
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
          id: "kpi-tracking-data",
          text: t("tutorials.kpi_computation.tracking_data"),
          attachTo: {
            element: '[data-tour="kpi-tracking-data"]',
            on: "left",
          },
          when: createNoOverlayHandler(),
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
          id: "kpi-advanced-options",
          text: t("tutorials.kpi_computation.advanced_options"),
          attachTo: {
            element: '[data-tour="kpi-advanced-options"]',
            on: "left",
          },
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const panelTitle = document.querySelector(
                '[data-tour="kpi-advanced-options"] .v-expansion-panel-title'
              );
              if (panelTitle && panelTitle.getAttribute("aria-expanded") !== "true") {
                panelTitle.click();
              }
              setTimeout(resolve, 350);
            });
          },
          when: createNoOverlayHandler(),
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
          id: "kpi-run",
          text: t("tutorials.kpi_computation.run_plugin"),
          attachTo: {
            element: '[data-tour="kpi-run-plugin"]',
            on: "top",
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
    "top-view": {
      steps: [
        {
          id: "top-view-pitch",
          text: t("tutorials.top_view.pitch_overview"),
          attachTo: {
            element: '[data-tour="top-view-pitch"]',
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
          id: "top-view-controls",
          text: t("tutorials.top_view.controls"),
          attachTo: {
            element: '[data-tour="top-view-controls-area"]',
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
          id: "top-view-display-settings-open",
          text: t("tutorials.top_view.display_settings_open"),
          attachTo: {
            element: '[data-tour="top-view-display-settings-btn"]',
            on: "top",
          },
          buttons: [],
          when: createClickToNextStepHandler(2, ["top-view-download"]),
        },
        {
          id: "top-view-display-settings",
          text: t("tutorials.top_view.display_settings"),
          attachTo: {
            element: '[data-tour="top-view-display-settings-list"]',
            on: "left",
          },
          when: createNoOverlayHandler(),
          buttons: [
            {
              text: "Next",
              action: () => {
                const btn = document.querySelector('[data-tour="top-view-display-settings-btn"]');
                if (btn) btn.click();
                tour.value.next();
              },
            },
          ],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="top-view-display-settings-list"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "top-view-download",
          text: t("tutorials.top_view.download"),
          attachTo: {
            element: '[data-tour="top-view-download"]',
            on: "top",
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
    heatmap: {
      steps: [
        {
          id: "heatmap-tab-switch",
          text: t("tutorials.heatmap.tab_switch"),
          attachTo: {
            element: '[data-tour="analysis-visualization-tabs"]',
            on: "top",
          },
          scrollTo: false,
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
              if (tabStore.visualizationTabId !== "heatmap") {
                tabStore.visualizationTabId = "heatmap";
              }
              const el = document.querySelector('[data-tour="analysis-visualization-tabs"]');
              if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "start" });
              }
              setTimeout(resolve, 150);
            });
          },
        },
        {
          id: "heatmap-pitch",
          text: t("tutorials.heatmap.pitch_overview"),
          attachTo: {
            element: '[data-tour="heatmap-pitch"]',
            on: "top",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="heatmap-pitch"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "heatmap-player-legend",
          text: t("tutorials.heatmap.player_legend"),
          attachTo: {
            element: '[data-tour="heatmap-player-legend"]',
            on: "top",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="heatmap-player-legend"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "heatmap-settings",
          text: t("tutorials.heatmap.settings"),
          attachTo: {
            element: '[data-tour="heatmap-settings"]',
            on: "bottom",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="heatmap-settings"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "heatmap-controls-row",
          text: t("tutorials.heatmap.time_selector"),
          attachTo: {
            element: '[data-tour="heatmap-controls-row"]',
            on: "top",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="heatmap-controls-row"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
    "kpi-visualization": {
      steps: [
        {
          id: "kpi-tab-switch",
          text: t("tutorials.kpi_visualization.tab_switch"),
          attachTo: {
            element: '[data-tour="analysis-visualization-tabs"]',
            on: "top",
          },
          scrollTo: false,
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
              if (tabStore.visualizationTabId !== "kpi") {
                tabStore.visualizationTabId = "kpi";
              }
              tabStore.kpiViewMode = "table";
              const el = document.querySelector('[data-tour="analysis-visualization-tabs"]');
              if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "start" });
              }
              setTimeout(resolve, 150);
            });
          },
        },
        {
          id: "kpi-table-view",
          text: t("tutorials.kpi_visualization.table_view"),
          attachTo: {
            element: '[data-tour="kpi-table-view"]',
            on: "top",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="kpi-table-view"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "kpi-chart-view",
          text: t("tutorials.kpi_visualization.chart_view"),
          attachTo: {
            element: '[data-tour="kpi-chart-view"]',
            on: "top",
          },
          scrollTo: false,
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
              tabStore.kpiViewMode = "chart";
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="kpi-chart-view"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "kpi-settings",
          text: t("tutorials.kpi_visualization.settings"),
          attachTo: {
            element: '[data-tour="kpi-settings"]',
            on: "bottom",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="kpi-settings"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        {
          id: "kpi-controls-row",
          text: t("tutorials.kpi_visualization.time_selector"),
          attachTo: {
            element: '[data-tour="kpi-controls-row"]',
            on: "top",
          },
          scrollTo: false,
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="kpi-controls-row"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          classes: "tutorial-final-step",
        },
      ],
    },
    "position-data-generation": {
      steps: [
        // index 0
        {
          id: "pipeline-video-select",
          text: t("tutorials.position_data_generation.video_select"),
          attachTo: {
            element: '[data-tour="video-select"]',
            on: "bottom",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              if (router.currentRoute.value.path.startsWith("/video-analysis")) {
                tour.value.show("pipeline-choose-path");
              } else if (router.currentRoute.value.path !== "/") {
                router.push({ name: "VideoView" }).then(() => {
                  resolve();
                });
              } else {
                resolve();
              }
            });
          },
          when: {
            show() {
              const targetEl = document.querySelector('[data-tour="video-select"]');
              if (!targetEl) return;
              const onClick = () => {
                if (!isTutorialRunning.value) return;
                targetEl.removeEventListener("click", onClick);
                const waitForAnalysis = () => {
                  if (!isTutorialRunning.value) return;
                  if (router.currentRoute.value.path.startsWith("/video-analysis")) {
                    tour.value.show("pipeline-choose-path");
                  } else {
                    requestAnimationFrame(waitForAnalysis);
                  }
                };
                waitForAnalysis();
              };
              targetEl.addEventListener("click", onClick);
            },
            hide() {},
          },
        },
        // index 1
        {
          id: "pipeline-choose-path",
          text: t("tutorials.position_data_generation.choose_path"),
          classes: "pipeline-choose-step",
          buttons: [
            {
              text: t("tutorials.position_data_generation.choose_manual"),
              action: () => {
                tour.value.show("pipeline-manual-upload");
              },
            },
            {
              text: t("tutorials.position_data_generation.choose_bytetrack"),
              action: () => {
                tour.value.show("pipeline-open-plugin-dlt");
              },
            },
          ],
        },
        // index 2
        {
          id: "pipeline-manual-upload",
          text: t("tutorials.position_data_generation.manual_upload"),
          attachTo: {
            element: '[data-tour="posdata-manual-upload-open"]',
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
        // index 3
        {
          id: "pipeline-open-plugin-dlt",
          text: t("tutorials.position_data_generation.open_plugin_panel"),
          attachTo: {
            element: '[data-tour="modal-plugin-open"]',
            on: "bottom",
          },
          buttons: [],
          when: createClickToNextStepHandler(3, []),
        },
        // index 4
        {
          id: "pipeline-select-dlt",
          text: t("tutorials.position_data_generation.select_dlt"),
          attachTo: {
            element: '[data-tour="plugin-calibration-dlt"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              tutorialPluginGroupOpen.value = 7;
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-calibration-dlt"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(4, []),
        },
        // index 5
        {
          id: "pipeline-dlt-details",
          text: t("tutorials.position_data_generation.dlt_details"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
            on: "left",
          },
          buttons: [
            {
              text: "Next",
              action: () => {
                tour.value.show("pipeline-select-bytetrack");
              },
            },
          ],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-details"] .v-card-title');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
        },
        // index 6
        {
          id: "pipeline-select-bytetrack",
          text: t("tutorials.position_data_generation.select_bytetrack"),
          attachTo: {
            element: '[data-tour="plugin-bytetrack"]',
            on: "right",
          },
          buttons: [],
          beforeShowPromise: () => {
            return new Promise((resolve) => {
              tutorialPluginGroupOpen.value = 7;
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="plugin-bytetrack"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
            });
          },
          when: createClickToNextStepHandler(6, []),
        },
        // index 7
        {
          id: "pipeline-run-bytetrack",
          text: t("tutorials.position_data_generation.run_bytetrack"),
          attachTo: {
            element: '[data-tour="plugin-details"]',
            on: "left",
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
              const check = () => {
                if (!isTutorialRunning.value) return;
                const el = document.querySelector('[data-tour="bytetrack-fps"]');
                if (el) {
                  resolve();
                } else {
                  requestAnimationFrame(check);
                }
              };
              check();
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
    "analysis-view-opened": {
      id: "analysis-view-opened",
      text: t("modal.tutorial.missing_requirements.analysis_view_opened"),
    },
    "position-data-selected": {
      id: "position-data-selected",
      text: t("modal.tutorial.missing_requirements.position_data_selected"),
    },
  };

  function createNoOverlayHandler() {
    return {
      show() {
        const overlay = document.querySelector(".shepherd-modal-overlay-container");
        if (overlay) overlay.style.display = "none";
      },
      hide() {
        const overlay = document.querySelector(".shepherd-modal-overlay-container");
        if (overlay) overlay.style.display = "";
      },
    };
  }

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
    tutorialActivePluginId.value = null;
    tutorialPluginGroupOpen.value = null;

    if (tour.value) {
      tour.value.complete();
      tour.value = null;
    }
  }

  const tour = ref(null);

  const openTutorialModal = ref(false);

  return {
    tutorials,
    availableTutorials,
    tutorialSteps,
    modalPluginVisible,
    tutorialActivePluginId,
    tutorialPluginGroupOpen,
    isTutorialRunning,
    currentTutorialId,
    currentStepId,
    currentStepIdx,
    currentStepText,
    nextStepText,
    totalSteps,
    uploadFormReady,
    openTutorialModal,
    startTutorial,
    stopTutorial,
    tour,
  };
});
