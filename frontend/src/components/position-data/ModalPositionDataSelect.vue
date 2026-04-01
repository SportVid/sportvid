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
                    :items="Object.values(calibrationAssetStore.calibrationAssetsList)"
                    item-title="name"
                    item-value="id"
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
              selectedBytetrack,
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
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import ModalPositionDataRename from "./ModalPositionDataRename.vue";
import { useVisualizationStore } from "@/stores/visualization";

const { t } = useI18n();

const playerStore = usePlayerStore();
const pluginRunStore = usePluginRunStore();
const calibrationAssetStore = useCalibrationAssetStore();
const positionDataStore = usePositionDataStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

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
    return (
      selectedCalibrationAsset.value === null || selectedBytetrack.value === null || !areaSize.value
    );
  } else if (selectedMode.value === "manual") {
    return !selectedPositionData.value || !areaSize.value;
  }
  return true;
});

const confirmSelection = (calibrationAssetId, bytetrackPluginId, positionDataId, areaSize) => {
  if (selectedMode.value === "bytetrack") {
    topViewStore.transformBBoxToPositionDataTopView(calibrationAssetId, bytetrackPluginId);
    const keys = topViewStore.sortedFrameKeys;
    if (keys.length > 0) {
      positionDataStore.setSelectedTimeRangeStart(keys[0]);
      positionDataStore.setSelectedTimeRangeEnd(keys[keys.length - 1]);
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
