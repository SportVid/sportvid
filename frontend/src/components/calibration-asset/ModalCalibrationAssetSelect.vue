<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.calibration_asset.select.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text>
        <!-- One row per asset, its name alone; what distinguishes its calibrations is only
             interesting once that asset is the one in question, so it lives behind the fold.
             Picking one of them selects the asset and that calibration in a single click. -->
        <v-expansion-panels variant="accordion" style="max-height: 400px; overflow-y: auto">
          <v-expansion-panel v-for="asset in calibrationAssetStore.calibrationAssetsList" :key="asset.id">
            <v-expansion-panel-title>
              <div class="d-flex align-center w-100">
                <span>{{ asset.name }}</span>
                <v-spacer />
                <v-btn
                  size="x-small"
                  color="red"
                  variant="plain"
                  class="mr-2"
                  @click.stop="calibrationAssetStore.deleteCalibrationAsset(asset.id)"
                >
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <CalibrationList :asset="asset" @select="select(asset, $event)" />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import CalibrationList from "@/components/calibration-asset/CalibrationList.vue";

const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue", "selected"]);

const dialog = ref(props.modelValue);

// One click does both: make the picked calibration the asset's active one (what the overlay,
// the metrics and the position data use) and load the asset itself into the editor.
const select = async (asset, calibration) => {
  if (calibration && asset.active_calibration_id !== calibration.id) {
    await calibrationAssetStore.activateCalibration(calibration.id);
  }
  calibrationAssetStore.loadCalibrationAsset(asset.id);
  dialog.value = false;
  emit("selected", asset.id);
};

onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
});

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
