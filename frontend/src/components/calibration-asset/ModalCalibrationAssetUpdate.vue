<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.calibration_asset.update.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex flex-column">
        <div class="d-flex align-center">
          <v-text-field
            v-model="name"
            :label="$t('modal.calibration_asset.save.name')"
            prepend-icon="mdi-pencil"
            variant="underlined"
            class="mr-6"
            style="width: 260px"
          />

          <v-btn
            @click="updateCalibrationAsset(name, topViewStore.currentSport.title, objectType)"
            :disabled="!name || !calibrationAssetStore.allAssetObjectsValid"
            size="small"
          >
            {{ $t("button.update") }}
          </v-btn>
        </div>

        <div
          v-if="!calibrationAssetStore.allAssetObjectsValid"
          class="text-caption text-error text-center"
        >
          {{
            $t("modal.calibration_asset.required", {
              current: calibrationAssetStore.filteredReferenceObjects.length,
              required: 4,
              type: $t(
                `modal.calibration_asset.object_types.${calibrationAssetStore.calibrationAssetType}`
              ),
            })
          }}
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
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

const nameProxy = ref(null);
const name = computed({
  get() {
    const name = calibrationAssetStore.calibrationAssetsList.find(
      (asset) => asset.id === calibrationAssetStore.calibrationAssetId
    )?.name;
    return nameProxy.value === null ? name : nameProxy.value;
  },
  set(val) {
    nameProxy.value = val;
  },
});
const objectType = ref(calibrationAssetStore.calibrationAssetType);

const updateCalibrationAsset = (name, template, objectType) => {
  calibrationAssetStore.updateCalibrationAsset(name, template, objectType);
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
