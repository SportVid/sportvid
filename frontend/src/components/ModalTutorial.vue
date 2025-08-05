<template>
  <v-dialog v-model="dialog" max-width="1000px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.tutorial.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="mt-2 scrollable-content">
        <v-row>
          <v-col cols="12" sm="6" v-for="tutorial in tutorials" :key="tutorial.id">
            <v-card
              @click="runTutorial(tutorial.id)"
              class="d-flex flex-row align-center hover:bg-gray-100 px-4 py-3"
            >
              <div class="d-flex align-center justify-center" style="min-width: 40px">
                <v-icon size="32" class="text-primary">
                  {{ tutorial.icon }}
                </v-icon>
              </div>

              <div class="d-flex flex-column justify-center ml-4">
                <span class="text-subtitle-1 font-weight-medium">{{ tutorial.name }}</span>
                <span class="text-body-2 text-grey-darken-1">{{ tutorial.description }}</span>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import Shepherd from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

const router = useRouter();
const { t } = useI18n();

const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);

const tutorials = [
  {
    id: "calibration-tracking-flow",
    name: "Calibration & Tracking",
    description: "Calibrate camera, run homography, track players",
    icon: "mdi-camera-control",
  },
  {
    id: "timeline-plugin",
    name: "Event Timeline",
    description: "View events per player",
    icon: "mdi-timeline-text",
  },
  {
    id: "run-aggregation",
    name: "Running Data",
    description: "Aggregate distance & speed by interval",
    icon: "mdi-run-fast",
  },
  {
    id: "kpi-visualization",
    name: "KPI Visualization",
    description: "Space control, EPS, player zones",
    icon: "mdi-chart-line",
  },
  {
    id: "data-export",
    name: "Export",
    description: "Export positions, stats, images, video",
    icon: "mdi-file-export",
  },
];

const runTutorial = async (id) => {
  const config = tutorialSteps[id];
  if (!config) return;

  const tour = new Shepherd.Tour({
    defaultStepOptions: {
      cancelIcon: { enabled: true },
      scrollTo: { behavior: "smooth", block: "center" },
    },
    useModalOverlay: true,
    keyboardNavigation: false,
  });
  window.currentTutorial = tour;

  const totalSteps = config.steps.length;

  config.steps.forEach((step, index) => {
    const stepNum = index + 1;
    const titleWithCount = `${stepNum}/${totalSteps}`;

    tour.addStep({
      ...step,
      title: titleWithCount,
    });
  });

  dialog.value = false;
  tour.start();
};

const tutorialSteps = {
  "calibration-tracking-flow": {
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
        when: createClickToNextStepHandler(4, []),
      },
    ],
  },
};

const stepModalPluginButton = ref(null);

function createClickToNextStepHandler(currentStepIndex, forbiddenStepIds = []) {
  let targetEl = null;
  let onClick;

  return {
    show() {
      const steps = window.currentTutorial?.steps || [];
      if (!steps.length) return;

      const currentStepSelector = steps[currentStepIndex]?.options?.attachTo?.element;
      if (!currentStepSelector) return;

      targetEl = document.querySelector(currentStepSelector);
      if (!targetEl) return;

      onClick = (event) => {
        if (event.target.closest('[data-tour="calibration-asset-edit-row"]')) {
          stepModalPluginButton.value = false;
        }

        window.currentTutorial.hide();

        targetEl.removeEventListener("click", onClick);
        document.removeEventListener("click", onClick);

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

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);
</script>
