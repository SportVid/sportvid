<template>
  <v-dialog v-model="dialog" width="400px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.position_data.select.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-select
          v-model="selectedCalibrationAsset"
          :items="Object.values(calibrationAssetStore.calibrationAssetsList)"
          item-title="name"
          item-value="id"
          label="Select Calibration Asset"
          variant="underlined"
          class="mt-0"
        />

        <v-select
          v-model="selectedBytetrack"
          :items="bytetrackRuns"
          item-title="date"
          item-value="id"
          label="Select Bytetrack Plugin"
          variant="underlined"
          class="mt-2"
        />

        <v-btn
          class="mt-2"
          @click="confirmSelection(selectedCalibrationAsset, selectedBytetrack)"
          :disabled="!selectedCalibrationAsset || selectedBytetrack === null"
        >
          {{ $t("modal.position_data.select.select") }}
        </v-btn>

        <!-- <v-list density="compact" style="height: 210px; overflow-y: auto">
          <v-list-item
            v-for="plugin in bytetrackRuns"
            :key="plugin.type"
            class="mr-4"
            @click="loadBytetrackData(plugin.id)"
          >
            {{ plugin.type }} ({{ plugin.date }})
          </v-list-item>
        </v-list> -->
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useBboxesStore } from "@/stores/bboxes";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

const playerStore = usePlayerStore();
const bboxesStore = useBboxesStore();
const pluginRunStore = usePluginRunStore();
const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const selectedBytetrack = ref(null);
const bytetrackRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "bytetrack" && e.status === "DONE")
    .map((pluginRun, index) => ({
      id: index,
      type: "Bytetrack",
      date: pluginRun.date
        .replace("T", " ")
        .replace("Z", "")
        .substring(0, pluginRun.date.length - 8),
    }));
});

const selectedCalibrationAsset = ref(null);
onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
});

const confirmSelection = (calibrationAssetId, bytetrackPluginIndex) => {
  calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);
  bboxesStore.bboxPluginRun = bytetrackPluginIndex;
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
