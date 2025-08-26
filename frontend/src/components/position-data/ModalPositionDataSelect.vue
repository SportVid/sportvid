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
            <v-tab v-for="mode in PositionDataModes" :key="mode.id" :value="mode.id">
              {{ mode.name }}
            </v-tab>
          </v-tabs>
        </v-row>

        <v-row>
          <v-col>
            <v-tabs-window v-model="selectedMode">
              <v-tabs-window-item v-for="mode in PositionDataModes" :key="mode.id" :value="mode.id">
                <template v-if="mode.id === 'bytetrack'">
                  <v-select
                    v-model="selectedCalibrationAsset"
                    :items="Object.values(calibrationAssetStore.calibrationAssetsList)"
                    item-title="name"
                    item-value="id"
                    :label="$t('modal.position_data.select.asset')"
                    variant="underlined"
                    class="mt-0"
                  />

                  <v-select
                    v-model="selectedBytetrack"
                    :items="bytetrackRuns"
                    item-title="date"
                    item-value="id"
                    :label="$t('modal.position_data.select.bytetrack')"
                    variant="underlined"
                    class="mt-2"
                  />
                </template>

                <template v-else-if="mode.id === 'manual'">
                  <v-list density="compact" style="height: 210px; overflow-y: auto">
                    <v-list-item
                      v-for="data in positionDataStore.positionDataList"
                      :key="data.id"
                      class="mr-4"
                      :active="selectedPositionData && selectedPositionData.id === data.id"
                      @click="selectedPositionData = data.id"
                    >
                      <template #append>
                        <v-btn
                          size="x-small"
                          color="primary"
                          variant="plain"
                          class="mr-1"
                          @click.stop="showModalPositionDataRename = true"
                        >
                          <v-icon>mdi-pencil</v-icon>
                        </v-btn>

                        <v-btn
                          size="x-small"
                          color="red"
                          variant="plain"
                          class="mr-2"
                          @click.stop="positionDataStore.deletePositionData(data.id)"
                        >
                          <v-icon>mdi-delete</v-icon>
                        </v-btn>
                      </template>
                      {{ data.name }}

                      <ModalPositionDataRename
                        v-if="showModalPositionDataRename"
                        v-model="showModalPositionDataRename"
                        :positionDataId="data.id"
                      />
                    </v-list-item>
                  </v-list>
                </template>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>

        <v-btn
          class="mt-2"
          @click="
            confirmSelection(selectedCalibrationAsset, selectedBytetrack, selectedPositionData)
          "
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
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useBboxesStore } from "@/stores/bboxes";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePositionDataStore } from "@/stores/position_data";
import ModalPositionDataRename from "./ModalPositionDataRename.vue";

const { t } = useI18n();

const playerStore = usePlayerStore();
const bboxesStore = useBboxesStore();
const pluginRunStore = usePluginRunStore();
const calibrationAssetStore = useCalibrationAssetStore();
const positionDataStore = usePositionDataStore();

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

const selectedMode = ref("bytetrack");
const PositionDataModes = ref([
  { id: "bytetrack", name: t("modal.position_data.select.modes.bytetrack") },
  { id: "manual", name: t("modal.position_data.select.modes.manual") },
]);

const selectedCalibrationAsset = ref(null);
onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
});

const selectedPositionData = ref(null);
onMounted(() => {
  positionDataStore.loadPositionDataList();
});

const selectedBytetrack = ref(null);
const formatLocalDate = (dateString) => {
  if (!dateString) return "";

  let isoString = dateString.replace(" ", "T");
  if (!isoString.endsWith("Z")) {
    isoString += "Z";
  }
  const date = new Date(isoString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return `${isoDate} ${localTime}`;
};
const bytetrackRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "bytetrack" && e.status === "DONE")
    .map((pluginRun) => ({
      id: pluginRun.id,
      type: "Bytetrack",
      date: formatLocalDate(pluginRun.date),
    }));
});

const isButtonDisabled = computed(() => {
  if (selectedMode.value === "bytetrack") {
    return selectedCalibrationAsset.value === null || selectedBytetrack.value === null;
  } else if (selectedMode.value === "manual") {
    return !selectedPositionData.value;
  }
  return true;
});

import { useTopViewStore } from "@/stores/top_view";
const topViewStore = useTopViewStore();
const confirmSelection = (calibrationAssetId, bytetrackPluginId, positionDataId) => {
  if (selectedMode.value === "bytetrack") {
    // calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);
    // bboxesStore.loadBboxData(bytetrackPluginId);
    topViewStore.transformBBoxToPositionDataTopView(calibrationAssetId, bytetrackPluginId);
    console.log(
      "selected posdata plugin",
      topViewStore.positionDataTopView,
      bboxesStore.bboxDataActive
    );
  } else if (selectedMode.value === "manual") {
    positionDataStore.loadPositionData(positionDataId);
    // bboxesStore.bboxDataTopView = processCsvPositions(selectedPositionData.value);
    // calibrationAssetStore.marker = [];
    // calibrationAssetStore.calibrationAssetId = null;
    console.log("selected posdata upload", topViewStore.positionDataTopView);
  }
  dialog.value = false;
};

const showModalPositionDataRename = ref(false);

// function processCsvPositions(csvText, fps = 30) {
//   const lines = csvText
//     .split("\n")
//     .map((line) => line.trim())
//     .filter((line) => line !== "");
//   if (lines.length < 2) return [];

//   const headers = lines
//     .shift()
//     .split(";")
//     .map((h) => h.trim());
//   const timeIdx = headers.indexOf("ts in ms");
//   const xIdx = headers.indexOf("x in m");
//   const yIdx = headers.indexOf("y in m");
//   const groupIdx = headers.indexOf("group id");

//   const items = lines.map((line) => {
//     const parts = line.split(";").map((s) => s.trim());
//     return {
//       origTime: parts[timeIdx],
//       x: parseFloat(parts[xIdx]),
//       y: parseFloat(parts[yIdx]),
//       groupId: parseInt(parts[groupIdx]),
//     };
//   });

//   const uniqueTimes = Array.from(new Set(items.map((item) => item.origTime))).sort(
//     (a, b) => parseInt(a) - parseInt(b)
//   );

//   const timeMapping = {};
//   uniqueTimes.forEach((time, index) => {
//     timeMapping[time] = playerStore.roundTimeToFPS(index / fps, fps);
//   });

//   const teamColorMapping = {
//     1: "red",
//     2: "blue",
//     5: "black",
//   };

//   const enrichedItems = items.map((item) => ({
//     ...item,
//     newTime: timeMapping[item.origTime],
//     new_x: (item.x + 99.94 / 2) / 99.94,
//     new_y: (65.88 / 2 - item.y) / 65.88,
//     team_id: teamColorMapping[item.groupId] || null,
//   }));

//   return enrichedItems.reduce((groupedData, item) => {
//     const key = item.newTime;
//     if (!groupedData[key]) {
//       groupedData[key] = [];
//     }
//     groupedData[key].push(item);
//     return groupedData;
//   }, {});
// }
</script>
