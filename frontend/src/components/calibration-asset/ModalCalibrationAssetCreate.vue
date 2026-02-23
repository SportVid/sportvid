<template>
  <v-dialog v-model="dialog" width="800px">
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
        <v-col>
          <v-row class="mt-1">
            <v-select
              v-model="sport"
              :items="topViewStore.sports.map((sport) => sport.title)"
              :label="$t('modal.calibration_asset.create.sport')"
              variant="underlined"
              class="mr-6"
            />
            <v-select
              v-model="areaSize"
              :items="areaOptions"
              :label="$t('modal.calibration_asset.create.area_size')"
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
              @click="createCalibrationAsset(sport, areaSize, objectType)"
              :disabled="!sport || !areaSize || !objectType"
              size="small"
              class="mt-4"
            >
              {{ $t("button.create") }}
            </v-btn>
          </v-row>

          <v-row class="mt-4 justify-center">
            <div v-if="areaSize" style="position: relative; display: inline-block">
              <img :src="mainPreview" style="height: 250px; display: block" />
              <div v-if="cropPct" :style="cropOverlayStyle" />
            </div>
          </v-row>
        </v-col>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from "vue";
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
const areaSize = ref(null);
const areaOptions = computed(() => {
  if (!sport.value) return [];
  const s = topViewStore.sports.find((x) => x.title === sport.value);
  if (!s || !s.areaImages) return [];
  return Object.keys(s.areaImages);
});

watch(sport, () => {
  areaSize.value = areaOptions.value.length > 0 ? areaOptions.value[0] : null;
});

const currentSportObj = computed(
  () => topViewStore.sports.find((x) => x.title === sport.value) || null
);
const mainPreview = computed(() => {
  return (
    currentSportObj.value.areaImages?.full ||
    Object.values(currentSportObj.value.areaImages || {})[0] ||
    null
  );
});

const cropPct = computed(() => {
  if (!areaSize.value) return { x: [0, 1], y: [0, 1] };
  const sportObj =
    topViewStore.sports.find((x) => x.title === sport.value) || currentSportObj.value;
  let tpl = sportObj?.templateCrops?.[areaSize.value] ?? sportObj?.templateCrops?.full;
  if (!tpl) return { x: [0, 1], y: [0, 1] };
  if (Array.isArray(tpl)) return { x: tpl, y: [0, 1] };
  return { x: tpl.x ?? [0, 1], y: tpl.y ?? [0, 1] };
});

const objectType = ref(null);
const objectTypes = [
  { value: "marker", title: "Marker" },
  { value: "segment", title: "Segment" },
];

const createCalibrationAsset = (sport, areaSize, objectType) => {
  calibrationAssetStore.createCalibrationAsset({
    sport: sport,
    areaSize: areaSize,
    objectType: objectType,
  });
  dialog.value = false;
};

const sportWidthRel = computed(() => currentSportObj.value?.widthRel ?? 1);
const sportHeightRel = computed(() => currentSportObj.value?.heightRel ?? 1);

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
