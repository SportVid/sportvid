<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.calibration_asset.create.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center" data-tour="modal-calibration-asset-create">
        <v-select
          v-model="objectType"
          :items="objectTypes"
          item-title="title"
          item-value="value"
          :label="$t('modal.calibration_asset.create.object_type')"
          variant="underlined"
          class="mr-6"
        />

        <v-btn
          @click="createCalibrationAsset(topViewStore.currentSport.title, objectType)"
          :disabled="!objectType"
          size="small"
        >
          {{ $t("button.create") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import { useI18n } from "vue-i18n";

const calibrationAssetStore = useCalibrationAssetStore();
const topViewStore = useTopViewStore();

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const objectType = ref(null);
const objectTypes = [
  { value: "marker", title: t("calibration_asset.object_types.marker") },
  { value: "segment", title: t("calibration_asset.object_types.segment") },
];

const createCalibrationAsset = (sport, objectType) => {
  calibrationAssetStore.createCalibrationAsset({
    sport: sport,
    objectType: objectType,
  });
  dialog.value = false;
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
