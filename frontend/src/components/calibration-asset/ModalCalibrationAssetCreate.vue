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

      <v-card-text class="d-flex align-center">
        <v-select
          v-model="sport"
          :items="topViewStore.sports.map((sport) => sport.title)"
          :label="$t('modal.calibration_asset.create.sport')"
          variant="underlined"
          class="mr-6"
        />

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
          @click="createCalibrationAsset(sport, objectType)"
          :disabled="!sport || !objectType"
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

const calibrationAssetStore = useCalibrationAssetStore();
const topViewStore = useTopViewStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const sport = ref(null);
const objectType = ref(null);
const objectTypes = [
  { value: "marker", title: "Marker" },
  { value: "segment", title: "Segment" },
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
