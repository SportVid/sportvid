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

      <v-card-text style="max-height: 490px; overflow-y: auto">
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
                    :items="calibrationAssetItems"
                    item-title="name"
                    item-value="id"
                    item-disabled="disabled"
                    :label="$t('modal.position_data.select.asset')"
                    variant="underlined"
                    class="mt-0 mx-4"
                  />

                  <v-select
                    v-model="selectedBytetrack"
                    :items="bytetrackRuns"
                    item-title="date"
                    item-value="id"
                    :label="$t('modal.position_data.select.bytetrack')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-select
                    v-model="selectedBallTracker"
                    :items="ballTrackerRuns"
                    item-title="date"
                    item-value="id"
                    clearable
                    :label="$t('modal.position_data.select.ball_tracker')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-select
                    v-model="areaSize"
                    :items="areaOptions"
                    item-title="title"
                    item-value="value"
                    :label="$t('modal.position_data.select.area_size')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-row class="justify-center my-2">
                    <div v-if="areaSize" style="position: relative; display: inline-block">
                      <img :src="mainPreview" style="height: 200px; display: block" />
                      <div v-if="cropPct" :style="cropOverlayStyle" />
                    </div>
                  </v-row>
                </template>

                <template v-else-if="mode.id === 'object_tracker'">
                  <v-select
                    v-model="selectedCalibrationAsset"
                    :items="calibrationAssetItems"
                    item-title="name"
                    item-value="id"
                    item-disabled="disabled"
                    :label="$t('modal.position_data.select.asset')"
                    variant="underlined"
                    class="mt-0 mx-4"
                  />

                  <v-select
                    v-model="selectedObjectTracker"
                    :items="objectTrackerRuns"
                    item-title="date"
                    item-value="id"
                    :label="$t('modal.position_data.select.object_tracker')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-select
                    v-model="selectedBallTracker"
                    :items="ballTrackerRuns"
                    item-title="date"
                    item-value="id"
                    clearable
                    :label="$t('modal.position_data.select.ball_tracker')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-select
                    v-model="areaSize"
                    :items="areaOptions"
                    item-title="title"
                    item-value="value"
                    :label="$t('modal.position_data.select.area_size')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-row class="justify-center my-2">
                    <div v-if="areaSize" style="position: relative; display: inline-block">
                      <img :src="mainPreview" style="height: 200px; display: block" />
                      <div v-if="cropPct" :style="cropOverlayStyle" />
                    </div>
                  </v-row>
                </template>

                <template v-else-if="mode.id === 'manual'">
                  <v-list density="compact" style="max-height: 210px; overflow-y: auto">
                    <v-list-item
                      v-for="data in positionDataStore.positionDataList"
                      :key="data.id"
                      class="mr-4"
                      :active="selectedPositionData && selectedPositionData.id === data.id"
                      @click="selectedPositionData = data.id"
                    >
                      <template #append>
                        <v-btn
                          v-if="canWrite"
                          size="x-small"
                          color="primary"
                          variant="plain"
                          class="mr-1"
                          @click.stop="showModalPositionDataRename = true"
                        >
                          <v-icon>mdi-pencil</v-icon>
                        </v-btn>

                        <v-btn
                          v-if="canWrite"
                          size="x-small"
                          color="red"
                          variant="plain"
                          class="mr-2"
                          @click.stop="positionDataStore.deletePositionData(data.id)"
                        >
                          <v-icon>mdi-delete</v-icon>
                        </v-btn>
                      </template>
                      <v-list-item-title>
                        {{ data.name }}
                      </v-list-item-title>

                      <ModalPositionDataRename
                        v-if="showModalPositionDataRename"
                        v-model="showModalPositionDataRename"
                        :positionDataId="data.id"
                      />
                    </v-list-item>
                  </v-list>

                  <v-select
                    v-model="areaSize"
                    :items="areaOptions"
                    item-title="title"
                    item-value="value"
                    :label="$t('modal.position_data.select.area_size')"
                    variant="underlined"
                    class="mt-2 mx-4"
                  />

                  <v-row class="justify-center my-2">
                    <div v-if="areaSize" style="position: relative; display: inline-block">
                      <img :src="mainPreview" style="height: 200px; display: block" />
                      <div v-if="cropPct" :style="cropOverlayStyle" />
                    </div>
                  </v-row>
                </template>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>

        <v-btn
          class="mt-2"
          @click="
            confirmSelection(
              selectedCalibrationAsset,
              selectedTrackerRun,
              selectedPositionData,
              areaSize
            )
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
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import { useUserStore } from "@/stores/user";
import ModalPositionDataRename from "./ModalPositionDataRename.vue";
import { useVisualizationStore } from "@/stores/visualization";

// Use global scope to avoid parent scope warning in dialogs/teleports
const { t } = useI18n({ useScope: "global" });

const playerStore = usePlayerStore();
const pluginRunStore = usePluginRunStore();
const pluginRunResultStore = usePluginRunResultStore();
const calibrationAssetStore = useCalibrationAssetStore();
const positionDataStore = usePositionDataStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const userStore = useUserStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

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
  { id: "object_tracker", name: t("modal.position_data.select.modes.object_tracker") },
  { id: "manual", name: t("modal.position_data.select.modes.manual") },
]);

const selectedCalibrationAsset = ref(null);
onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
  // Cheap call (no add_results) so already-finished runs are classified as
  // player- vs. ball-tracking runs via their result name (see objectTrackerRuns / ballTrackerRuns).
  pluginRunResultStore.fetchForVideo({ videoId: playerStore.videoId });
});

const IDENTITY_HOMOGRAPHY = [
  [1, 0, 0],
  [0, 1, 0],
  [0, 0, 1],
];
const isUncalibrated = (matrix) => JSON.stringify(matrix) === JSON.stringify(IDENTITY_HOMOGRAPHY);
const calibrationAssetItems = computed(() =>
  Object.values(calibrationAssetStore.calibrationAssetsList).map((asset) => {
    const uncalibrated = isUncalibrated(asset.homography_matrix);
    return {
      ...asset,
      disabled: uncalibrated,
      name: uncalibrated
        ? `${asset.name} (${t("modal.position_data.select.not_calibrated")})`
        : asset.name,
    };
  })
);

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

// A "real" player-tracking object_tracker run has a bytetrack tracker attached, so its
// result is named "bboxes" (see backend tasks/object_tracker.py). Ball-only runs (no
// tracker, ball-class filtered detections) are named "bboxes_ball" and are offered
// separately via ballTrackerRuns below.
const isBallTrackerRun = (pluginRunId) =>
  pluginRunResultStore.forPluginRun(pluginRunId).some((r) => r.name === "bboxes_ball");

const selectedObjectTracker = ref(null);
const objectTrackerRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "object_tracker" && e.status === "DONE" && !isBallTrackerRun(e.id))
    .map((pluginRun) => ({
      id: pluginRun.id,
      type: "Object Tracker",
      date: formatLocalDate(pluginRun.date),
    }));
});

const selectedBallTracker = ref(null);
const ballTrackerRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "object_tracker" && e.status === "DONE" && isBallTrackerRun(e.id))
    .map((pluginRun) => ({
      id: pluginRun.id,
      type: "Ball Tracker",
      date: formatLocalDate(pluginRun.date),
    }));
});

const selectedTrackerRun = computed(() =>
  selectedMode.value === "object_tracker" ? selectedObjectTracker.value : selectedBytetrack.value
);

const isButtonDisabled = computed(() => {
  if (selectedMode.value === "bytetrack") {
    return (
      selectedCalibrationAsset.value === null ||
      (selectedBytetrack.value === null && !selectedBallTracker.value) ||
      !areaSize.value
    );
  } else if (selectedMode.value === "object_tracker") {
    return (
      selectedCalibrationAsset.value === null ||
      (selectedObjectTracker.value === null && !selectedBallTracker.value) ||
      !areaSize.value
    );
  } else if (selectedMode.value === "manual") {
    return !selectedPositionData.value || !areaSize.value;
  }
  return true;
});

const confirmSelection = async (calibrationAssetId, trackerPluginId, positionDataId, areaSize) => {
  if (selectedMode.value === "bytetrack" || selectedMode.value === "object_tracker") {
    if (trackerPluginId) {
      await topViewStore.transformBBoxToPositionDataTopView(calibrationAssetId, trackerPluginId);
    }
    if (selectedBallTracker.value) {
      await topViewStore.mergeBallTracking(calibrationAssetId, selectedBallTracker.value);
    }
    const keys = topViewStore.sortedFrameKeys;
    if (keys.length > 0) {
      positionDataStore.setSelectedTimeRangeStart(keys[0]);
      positionDataStore.setSelectedTimeRangeEnd(keys[keys.length - 1]);
    }
    if (trackerPluginId) {
      visualizationStore.loadKpiData(trackerPluginId);
    }
  } else if (selectedMode.value === "manual") {
    positionDataStore.loadPositionData(positionDataId);
    visualizationStore.loadKpiData(positionDataId);
  }

  topViewStore.onSportChange(topViewStore.currentSport.title, areaSize);
  dialog.value = false;
};

const showModalPositionDataRename = ref(false);

const areaSize = ref(null);
const currentSportObj = computed(() => topViewStore.currentSport);
const areaOptions = computed(() => {
  const s = currentSportObj.value;
  if (!s || !s.areas) return [];
  return Object.keys(s.areas).map((areaKey) => ({
    title: s.areas[areaKey].title || areaKey,
    value: areaKey,
  }));
});

watch(
  () => topViewStore.currentSport.title,
  () => {
    areaSize.value = areaOptions.value.length > 0 ? areaOptions.value[0].value : null;
  },
  { immediate: true }
);

const mainPreview = computed(() => {
  return (
    currentSportObj.value.areas?.full?.image ||
    Object.values(currentSportObj.value.areas || {})[0]?.image ||
    null
  );
});

const cropPct = computed(() => {
  if (!areaSize.value) return { x: [0, 1], y: [0, 1] };
  const sportObj = currentSportObj.value;
  let tpl = sportObj?.areas?.[areaSize.value]?.templateCrop ?? sportObj?.areas?.full?.templateCrop;
  return { x: tpl.x, y: tpl.y };
});
const sportWidthRel = computed(() => {
  const sportObj = currentSportObj.value;
  return sportObj?.areas?.full?.widthRel ?? sportObj?.widthRel ?? 1;
});
const sportHeightRel = computed(() => {
  const sportObj = currentSportObj.value;
  return sportObj?.areas?.full?.heightRel ?? sportObj?.heightRel ?? 1;
});

const cropOverlayStyle = computed(() => {
  const crop = cropPct.value;
  if (!crop) return {};

  const leftRel = (1 - sportWidthRel.value) / 2 + crop.x[0] * sportWidthRel.value;
  const widthRel = (crop.x[1] - crop.x[0]) * sportWidthRel.value;
  const topRel = (1 - sportHeightRel.value) / 2 + crop.y[0] * sportHeightRel.value;
  const heightRel = (crop.y[1] - crop.y[0]) * sportHeightRel.value;

  return {
    position: "absolute",
    top: topRel * 100 + "%",
    left: leftRel * 100 + "%",
    width: Math.max(0, widthRel * 100) + "%",
    height: Math.max(0, heightRel * 100) + "%",
    border: "4px solid red",
    boxSizing: "border-box",
    pointerEvents: "none",
  };
});
</script>
