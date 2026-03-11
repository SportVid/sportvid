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

      <v-card-text class="mt-2">
        <v-row>
          <v-col
            cols="12"
            sm="6"
            v-for="tutorial in tutorialStore.availableTutorials"
            :key="tutorial.id"
          >
            <v-card
              :class="[
                'd-flex flex-row align-center px-4 py-3',
                tutorial.disabled
                  ? 'opacity-30 pointer-events-none'
                  : !tutorial.isAvailable
                  ? 'opacity-60'
                  : 'hover:bg-gray-100',
                tutorialStore.currentTutorialId === tutorial.id ? 'tutorial-active' : '',
              ]"
              :ripple="!tutorial.disabled && !tutorial.isAvailable"
              @click="handleTutorialClick(tutorial)"
            >
              <div class="d-flex align-center justify-center" style="min-width: 40px">
                <v-icon size="32" class="text-primary">
                  {{ tutorial.icon }}
                </v-icon>
              </div>

              <div class="d-flex flex-column justify-center ml-4">
                <span class="text-subtitle-1 font-weight-medium">
                  {{ tutorial.name }}

                  <v-icon
                    size="20"
                    class="mt-n1 steps-overview-icon"
                    @click.stop="showStepsOverview(tutorial.id)"
                    :title="$t('modal.tutorial.show_steps')"
                  >
                    mdi-information-outline
                  </v-icon>

                  <v-icon
                    v-if="!tutorial.isAvailable"
                    size="20"
                    color="error"
                    class="mt-n1 steps-overview-icon"
                    @click.stop="showMissingRequirements(tutorial.id)"
                    :title="$t('modal.tutorial.show_missing_requirements')"
                  >
                    mdi-alert-circle-outline
                  </v-icon>
                </span>
                <span class="text-body-2 text-grey-darken-1">{{ tutorial.description }}</span>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-dialog v-model="overviewDialog" max-width="700px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ overviewTitle }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="overviewDialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 450px; overflow-y: auto">
        <v-list dense>
          <v-list-item v-for="(step, index) in overviewSteps" :key="index">
            <v-list-item-content>
              <v-list-item-title>
                {{ $t("modal.tutorial.step") }} {{ index + 1 }}:
              </v-list-item-title>
              <v-list-item-subtitle class="subtitle-wrap">{{ step.text }}</v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-dialog v-model="missingDialog" max-width="700px">
    <v-card>
      <v-toolbar color="error">
        <v-toolbar-title class="text-h6">
          {{ missingTitle }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="missingDialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 450px; overflow-y: auto">
        <v-card-title>{{ $t("modal.tutorial.missing_requirements.title") }}</v-card-title>
        <ul>
          <li v-for="(req, index) in missingRequirementsList" :key="index" class="ml-12">
            {{ req.text }}
          </li>
        </ul>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import Shepherd from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";

import { useTutorialStore } from "@/stores/tutorial";

const tutorialStore = useTutorialStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);

const toggleTutorial = async (id) => {
  if (tutorialStore.tour) {
    tutorialStore.stopTutorial();
    return;
  }

  const config = tutorialStore.tutorialSteps[id];
  if (!config) return;

  tutorialStore.tour = new Shepherd.Tour({
    defaultStepOptions: {
      cancelIcon: { enabled: true },
      scrollTo: { behavior: "smooth", block: "center" },
    },
    useModalOverlay: true,
    keyboardNavigation: false,
  });

  const totalSteps = config.steps.length;

  config.steps.forEach((step, index) => {
    const stepNum = index + 1;
    const titleWithCount = `${stepNum}/${totalSteps}`;

    tutorialStore.tour.addStep({
      ...step,
      title: titleWithCount,
    });
  });

  tutorialStore.startTutorial(id);

  dialog.value = false;
};
const handleTutorialClick = (tutorial) => {
  if (tutorial.disabled) return;

  if (!tutorial.isAvailable) return;

  toggleTutorial(tutorial.id);
};

const overviewDialog = ref(false);
const overviewSteps = ref([]);
const overviewTitle = ref("");
const showStepsOverview = (tutorialId) => {
  const tutorial = tutorialStore.availableTutorials.find((t) => t.id === tutorialId);
  if (!tutorial) return;

  const steps = tutorialStore.tutorialSteps[tutorialId]?.steps || [];

  overviewSteps.value = steps;
  overviewTitle.value = tutorial.name;
  overviewDialog.value = true;
};

const missingDialog = ref(false);
const missingRequirementsList = ref([]);
const missingTitle = ref("");
const showMissingRequirements = (tutorialId) => {
  const tutorial = tutorialStore.availableTutorials.find((t) => t.id === tutorialId);

  if (!tutorial || tutorial.isAvailable) return;

  missingRequirementsList.value = tutorial.missingRequirements;
  missingTitle.value = tutorial.name;
  missingDialog.value = true;
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

<style scoped>
.tutorial-active {
  background-color: rgba(var(--v-theme-success), 0.3);
  border: 2px solid rgb(var(--v-theme-success));
}

.tutorial-active:hover {
  background-color: rgba(var(--v-theme-error), 0.3);
  border-color: rgb(var(--v-theme-error));
}

.steps-overview-icon {
  cursor: pointer;
  opacity: 0.6;
}

.steps-overview-icon:hover {
  opacity: 1;
}

.subtitle-wrap {
  -webkit-line-clamp: unset !important;
}
</style>
