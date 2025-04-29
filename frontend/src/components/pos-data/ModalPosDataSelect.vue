<template>
  <v-dialog v-model="dialog" width="500">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.select.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text>
        <v-row justify="center" class="mt-0 mb-1">
          <v-tabs v-model="selectedMode" fixed-tabs slider-color="primary">
            <v-tab v-for="mode in PosDataModes" :key="mode.id">
              {{ mode.name }}
            </v-tab>
          </v-tabs>
        </v-row>

        <v-row>
          <v-col>
            <v-tabs-window v-model="selectedMode">
              <v-tabs-window-item v-for="mode in PosDataModes" :key="mode.id">
                <template v-if="mode.name === 'Bytetrack Plugin'">
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
                </template>

                <template v-else-if="mode.name === 'Uploaded Data'">
                  <v-select
                    v-model="selectedUploadedPosData"
                    :items="uploadedPosDataList"
                    item-title="title"
                    item-value="file"
                    label="Select uploaded position data"
                    variant="underlined"
                    class="mt-2"
                  />
                </template>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>

        <v-btn
          class="mt-2"
          @click="confirmSelection(selectedCalibrationAsset, selectedBytetrack)"
          :disabled="isButtonDisabled"
        >
          {{ $t("button.select") }}
        </v-btn>
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
import { group } from "d3";

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

const selectedMode = ref(0);
const PosDataModes = ref([
  { id: 0, name: "Bytetrack Plugin" },
  { id: 1, name: "Uploaded Data" },
]);

const selectedCalibrationAsset = ref(null);
onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
});

const selectedUploadedPosData = ref(null);
const uploadedPosDataList = ref([]);
const loadUploadedPosDataList = () => {
  const list = JSON.parse(localStorage.getItem("uploadedPosDataList") || "[]");
  uploadedPosDataList.value = list;
};
onMounted(() => {
  loadUploadedPosDataList();
});

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

function processCsvPositions(csvText, fps = 30) {
  const lines = csvText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "");
  if (lines.length < 2) return [];

  const headers = lines
    .shift()
    .split(";")
    .map((h) => h.trim());
  const timeIdx = headers.indexOf("ts in ms");
  const xIdx = headers.indexOf("x in m");
  const yIdx = headers.indexOf("y in m");
  const groupIdx = headers.indexOf("group id");

  const items = lines.map((line) => {
    const parts = line.split(";").map((s) => s.trim());
    return {
      origTime: parts[timeIdx],
      x: parseFloat(parts[xIdx]),
      y: parseFloat(parts[yIdx]),
      groupId: parseInt(parts[groupIdx]),
    };
  });

  const uniqueTimes = Array.from(new Set(items.map((item) => item.origTime))).sort(
    (a, b) => parseInt(a) - parseInt(b)
  );

  const timeMapping = {};
  uniqueTimes.forEach((time, index) => {
    timeMapping[time] = playerStore.roundTimeToFPS(index / fps, fps);
  });

  const teamColorMapping = {
    1: "red",
    2: "blue",
    5: "black",
  };

  const enrichedItems = items.map((item) => ({
    ...item,
    newTime: timeMapping[item.origTime],
    new_x: (item.x + 99.94 / 2) / 99.94,
    new_y: (65.88 / 2 - item.y) / 65.88,
    team: teamColorMapping[item.groupId] || null,
  }));

  return enrichedItems.reduce((groupedData, item) => {
    const key = item.newTime;
    if (!groupedData[key]) {
      groupedData[key] = [];
    }
    groupedData[key].push(item);
    return groupedData;
  }, {});
}

const isButtonDisabled = computed(() => {
  if (selectedMode.value === 0) {
    return selectedCalibrationAsset.value === null || selectedBytetrack.value === null;
  } else if (selectedMode.value === 1) {
    return !selectedUploadedPosData.value;
  }
  return true;
});

const confirmSelection = (calibrationAssetId, bytetrackPluginIndex) => {
  if (selectedMode.value === 0) {
    calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);
    bboxesStore.bboxPluginRun = bytetrackPluginIndex;
    console.log("selected posdata plugin", bboxesStore.bboxDataTopView);
  } else if (selectedMode.value === 1) {
    bboxesStore.bboxDataTopView = processCsvPositions(selectedUploadedPosData.value);
    calibrationAssetStore.marker = [];
    calibrationAssetStore.calibrationAssetId = null;
    console.log("selected posdata upload", bboxesStore.bboxDataTopView);
  }
  dialog.value = false;
};
</script>
