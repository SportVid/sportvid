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
        <v-list density="compact" style="height: 210px; overflow-y: auto">
          <v-list-item
            v-for="asset in calibrationAssetStore.calibrationAssetsList"
            :key="asset.id"
            @click="loadCalibrationAsset(asset.id)"
            class="mr-4"
          >
            <template #prepend>
              <v-btn
                size="x-small"
                color="red"
                variant="plain"
                class="mr-2"
                @click.stop="calibrationAssetStore.deleteCalibrationAsset(asset.id)"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            {{ asset.name }}
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const loadCalibrationAsset = (id) => {
  calibrationAssetStore.loadCalibrationAsset(id);
  dialog.value = false;
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
