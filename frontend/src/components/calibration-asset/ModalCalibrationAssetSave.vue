<template>
  <v-dialog v-model="dialog" width="800px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.calibration_asset.save.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center">
        <v-text-field
          v-model="name"
          :label="$t('modal.calibration_asset.save.name')"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
          style="width: 260px"
        />

        <v-btn
          @click="saveCalibrationAsset(name, topViewStore.currentSport.title, objectType)"
          :disabled="
            !name || !calibrationAssetStore.allAssetObjectsValid
          "
          size="small"
        >
          {{ $t("button.save") }}
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

const name = ref(null);
const objectType = ref(calibrationAssetStore.calibrationAssetType);

const saveCalibrationAsset = (name, template, objectType) => {
  calibrationAssetStore.saveCalibrationAsset(name, template, objectType);
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
