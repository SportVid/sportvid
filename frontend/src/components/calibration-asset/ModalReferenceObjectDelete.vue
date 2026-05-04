<template>
  <svg
    :width="topViewStore.topViewSize.width"
    :height="topViewStore.topViewSize.height"
    style="position: absolute; top: 0; left: 0; pointer-events: none"
  >
    <circle
      v-if="props.object.compAreaCoordsRel.length === 1 && dialog"
      v-click-outside="() => (dialog = false)"
      :key="'delete-' + props.object.id"
      :cx="
        (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
        props.object.compAreaCoordsRel[0].x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width
      "
      :cy="
        (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
        props.object.compAreaCoordsRel[0].y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height
      "
      r="12"
      fill="none"
      style="cursor: pointer; pointer-events: all"
      @click="deleteReferenceObject(props.object.id)"
      class="delete-marker-position"
    />
    <text
      v-if="props.object.compAreaCoordsRel.length === 1 && dialog"
      v-click-outside="() => (dialog = false)"
      :x="
        (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
        props.object.compAreaCoordsRel[0].x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width
      "
      :y="
        (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
        props.object.compAreaCoordsRel[0].y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
        6
      "
      text-anchor="middle"
      font-size="16"
      fill="red"
    >
      ✕
    </text>

    <line
      v-if="props.object.compAreaCoordsRel.length === 2 && dialog"
      v-click-outside="() => (dialog = false)"
      :key="'delete-' + props.object.id"
      :x1="
        (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
        props.object.compAreaCoordsRel[0].x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width
      "
      :y1="
        (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
        props.object.compAreaCoordsRel[0].y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height
      "
      :x2="
        (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
        props.object.compAreaCoordsRel[1].x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width
      "
      :y2="
        (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
        props.object.compAreaCoordsRel[1].y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height
      "
      stroke-width="12"
      fill="none"
      style="cursor: pointer; pointer-events: all"
      @click="deleteReferenceObject(props.object.id)"
      class="delete-segment-position"
    />
    <text
      v-if="props.object.compAreaCoordsRel.length === 2 && dialog"
      v-click-outside="() => (dialog = false)"
      :x="
        ((isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
          props.object.compAreaCoordsRel[0].x *
            (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
          ((isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
            props.object.compAreaCoordsRel[1].x *
              (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width)) /
        2
      "
      :y="
        ((isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
          props.object.compAreaCoordsRel[0].y *
            (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
          ((isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
            props.object.compAreaCoordsRel[1].y *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height)) /
          2 +
        5
      "
      text-anchor="middle"
      font-size="16"
      fill="red"
    >
      ✕
    </text>

    <path
      v-if="props.object.compAreaCoordsRel.length > 2 && dialog"
      v-click-outside="() => (dialog = false)"
      :key="'delete-' + props.object.id"
      :d="
        (() => {
          const toScreen = (p) => ({
            x:
              (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
              p.x * (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width,
            y:
              (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
              p.y * (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height,
          });

          const points = props.object.compAreaCoordsRel.map(toScreen);

          let d = `M ${points[0].x} ${points[0].y}`;

          for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[i === 0 ? 0 : i - 1];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1];

            const c1x = p1.x + (p2.x - p0.x) / 6;
            const c1y = p1.y + (p2.y - p0.y) / 6;
            const c2x = p2.x - (p3.x - p1.x) / 6;
            const c2y = p2.y - (p3.y - p1.y) / 6;

            d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
          }

          return d;
        })()
      "
      stroke-width="12"
      fill="none"
      style="cursor: pointer; pointer-events: all"
      @click="deleteReferenceObject(props.object.id)"
      class="delete-segment-position"
    />
    <text
      v-if="props.object.compAreaCoordsRel.length > 2 && dialog"
      v-click-outside="() => (dialog = false)"
      :x="
        (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
        props.object.compAreaCoordsRel[2].x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width
      "
      :y="
        (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
        props.object.compAreaCoordsRel[2].y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
        6
      "
      text-anchor="middle"
      font-size="16"
      fill="red"
    >
      ✕
    </text>
  </svg>
</template>

<script setup>
import { ref, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  object: { type: Object, required: true },
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue"]);

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

const deleteReferenceObject = (id) => {
  calibrationAssetStore.deleteCustomMarker(id);
  dialog.value = false;
};
</script>

<style scoped>
.menu-item {
  cursor: pointer;
}

.menu-item .v-list-item-title {
  font-size: 10px;
}

.delete-marker-position:hover {
  fill: red;
  fill-opacity: 0.2;
}

.delete-segment-position:hover {
  stroke: red;
  stroke-opacity: 0.2;
}
</style>
