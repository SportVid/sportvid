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
import Shepherd from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue", "start-tutorial"]);

const dialog = ref(props.modelValue);

const tutorials = [
  {
    id: "video-upload",
    name: "Video Upload",
    description: "Upload video, fill out questionnaire",
    icon: "mdi-video-plus",
  },
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

const runTutorial = (id) => {
  const config = tutorialSteps[id];
  if (!config) return;

  const tour = new Shepherd.Tour({
    defaultStepOptions: {
      cancelIcon: { enabled: true },
      classes: "bg-primary",
      scrollTo: { behavior: "smooth", block: "center" },
    },
    useModalOverlay: true,
  });

  config.steps.forEach((step, index) => {
    const isLast = index === config.steps.length - 1;

    tour.addStep({
      ...step,
      buttons: [
        ...(index > 0
          ? [
              {
                text: "Back",
                action: tour.back,
              },
            ]
          : []),
        {
          text: isLast ? "Done" : "Next",
          action: isLast ? tour.complete : tour.next,
        },
      ],
    });
  });

  dialog.value = false;
  tour.start();
};

const tutorialSteps = {
  "video-upload": {
    steps: [
      {
        id: "upload-1",
        text: "Click here to upload a video.",
        attachTo: {
          element: '[data-tour="video-upload-button"]',
          on: "bottom",
        },
        buttons: [{ text: "Done", action: () => tour.complete() }],
      },
    ],
  },

  "calibration-tracking-flow": {
    steps: [
      {
        id: "calibration-1",
        text: "Add a new calibration asset.",
        attachTo: {
          element: '[data-tour="calibration-asset-create-button"]',
          on: "bottom",
        },
        buttons: [{ text: "Done", action: () => tour.complete() }],
      },
    ],
  },

  // Weitere Tutorials …
};

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
