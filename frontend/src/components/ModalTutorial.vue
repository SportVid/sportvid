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
          <v-col cols="12" sm="6" v-for="tutorial in tutorialStore.tutorials" :key="tutorial.id">
            <v-card
              :class="[
                'd-flex flex-row align-center px-4 py-3',
                tutorial.disabled ? 'opacity-30 pointer-events-none' : 'hover:bg-gray-100',
              ]"
              :ripple="!tutorial.disabled"
              @click="!tutorial.disabled && runTutorial(tutorial.id)"
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
import { useI18n } from "vue-i18n";
import Shepherd from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";

import { useTutorialStore } from "@/stores/tutorial";

const { t } = useI18n();

const tutorialStore = useTutorialStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);

const runTutorial = async (id) => {
  const config = tutorialStore.tutorialSteps[id];
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
