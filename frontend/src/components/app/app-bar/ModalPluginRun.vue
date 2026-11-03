<template>
  <v-dialog v-model="dialog" width="60%">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">{{ name }}</v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 70vh; overflow-y: auto">
        <div style="padding-bottom: 2em" v-html="description" />

        <Parameters
          :parameters="parameters"
          :videoIds="[videoId]"
          @create-calibration="onCreateCalibration"
          @select-calibration="onSelectCalibration"
        />

        <!-- Counts only the parameters that would actually render -- a plugin whose optional
             parameters are all inapplicable to the current selection (e.g. the lens solver's
             ones while DLT+RANSAC is the picked calibration method) would otherwise offer an
             empty "Advanced options" panel. -->
        <v-expansion-panels
          v-if="visibleOptionalParameters.length > 0 && userStore.experienceMode !== 'simple'"
          class="mt-4"
          data-tour="kpi-advanced-options"
        >
          <v-expansion-panel>
            <v-expansion-panel-title expand-icon="mdi-menu-down">
              {{ $t("modal.plugin.advanced_options") }}
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <Parameters :parameters="optionalParameters" :videoIds="[videoId]" />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-row class="mt-4">
          <v-spacer />
          <v-btn :data-tour="runButtonDataTour" :disabled="hasMissingRequired" @click="run">
            {{ $t("button.run_plugin") }}
          </v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>

  <ModalCalibrationAssetCreate v-if="showCalibrationCreate" v-model="showCalibrationCreate" />
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useUserStore } from "@/stores/user";
import { applyLensProfileSelection, submitPlugin } from "@/composables/usePluginParams";
import { useCalibrationCreateFlow } from "@/composables/useCalibrationCreateFlow";
import Parameters from "./Parameters.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";

const userStore = useUserStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  plugin: String,
  name: String,
  description: String,
  paramsFactory: Function,
  videoId: [String, Number],
  runButtonDataTour: {
    type: String,
    default: undefined,
  },
});

const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);
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

const { parameters, optionalParameters, plugin: derivedPlugin } = props.paramsFactory();

const { showCalibrationCreate, onCreateCalibration, onSelectCalibration } =
  useCalibrationCreateFlow(dialog);

// A params factory can derive the plugin to run itself (calibrationParams does, from the video's
// lens profile) and hand it back as a computed; for every other factory the `plugin` prop says
// what runs.
const allParams = computed(() => [...parameters.value, ...optionalParameters.value]);
const visibleOptionalParameters = computed(
  () => optionalParameters.value?.filter((p) => !p.hidden && !p.simpleHidden) ?? []
);
const activePlugin = computed(() => derivedPlugin?.value ?? props.plugin);

// A parameter marked `required` has to carry a value before the run can be started: the
// calibration asset is that case -- a calibration run without one fails in the backend, while
// every other field of a parameter set has a usable default. `hidden` parameters are left out of
// the check for the same reason submitPlugin drops them from the payload: they are not
// applicable to the current selection.
const hasMissingRequired = computed(() =>
  allParams.value.some(
    (p) => p.required && !p.hidden && (p.value === null || p.value === undefined || p.value === "")
  )
);

const run = async () => {
  // A lens profile picked in this dialog is a property of the video and has to be saved before
  // the run starts, since the backend task reads it from there (and it decides which calibration
  // plugin runs). If it can't be saved the run is not started.
  if (!(await applyLensProfileSelection(allParams.value, props.videoId))) return;
  await submitPlugin(activePlugin.value, allParams.value, props.videoId);
  dialog.value = false;
};
</script>
