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

        <v-expansion-panels
          v-if="
            optionalParameters &&
            optionalParameters.length > 0 &&
            userStore.experienceMode !== 'simple'
          "
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
          <v-btn :data-tour="runButtonDataTour" @click="run">
            {{ $t("button.run_plugin") }}
          </v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>

  <ModalCalibrationAssetCreate v-if="showCalibrationCreate" v-model="showCalibrationCreate" />
</template>

<script setup>
import { ref, watch } from "vue";
import { useUserStore } from "@/stores/user";
import { submitPlugin } from "@/composables/usePluginParams";
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

const { parameters, optionalParameters } = props.paramsFactory();

const { showCalibrationCreate, onCreateCalibration, onSelectCalibration } =
  useCalibrationCreateFlow(dialog);

const run = () => {
  const allParams = [...parameters.value, ...optionalParameters.value];
  submitPlugin(props.plugin, allParams, props.videoId).then(() => {
    dialog.value = false;
  });
};
</script>
