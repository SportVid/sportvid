<template>
  <ModalCalibrationAssetMenu v-if="calibrationAssetStore.marker.length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
      <img
        ref="topViewElement"
        class="image"
        :src="topViewStore.currentSport.pitchImage"
        @load="onImageLoad"
        :style="{
          maxHeight: maxVideoHeight * 100 + 'vh',
          height: videoStore.videoSize.height + 'px',
        }"
      />

      <div
        v-if="calibrationAssetStore.isAddingReferenceMarker"
        ref="overlayMarker"
        class="overlay-marker"
        @click="calibrationAssetStore.setReferenceMarker"
        :style="{
          top: topViewStore.topViewSize.top + 'px',
          left: topViewStore.topViewSize.left + 'px',
          width: topViewStore.topViewSize.width + 'px',
          height: topViewStore.topViewSize.height + 'px',
        }"
      />

      <v-btn
        v-for="m in filteredReferenceMarker"
        v-show="topViewStore.showItems"
        :key="m.id"
        :disabled="calibrationAssetStore.isAddingReferenceMarker"
        :color="m.active || calibrationAssetStore.hoveredVideoMarker === m.id ? 'red' : 'grey'"
        icon="mdi-circle"
        variant="plain"
        density="compact"
        @click="(event) => calibrationAssetStore.toggleReferenceMarker(event, m.id)"
        :style="{
          top:
            m.compAreaCoordsRel.y *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            (topViewStore.topViewSize.top +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height) +
            'px',
          left:
            m.compAreaCoordsRel.x *
              (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            (topViewStore.topViewSize.left +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width) +
            'px',
        }"
        class="marker-position"
      />

      <v-btn
        v-for="m in filteredReferenceMarker"
        v-show="showDeleteButton"
        :key="'delete-' + m.id"
        color="red"
        icon="mdi-close"
        variant="plain"
        density="compact"
        @click="calibrationAssetStore.deleteReferenceMarker(m.id)"
        :style="{
          top:
            m.compAreaCoordsRel.y *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            (topViewStore.topViewSize.top +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height) +
            'px',
          left:
            m.compAreaCoordsRel.x *
              (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            (topViewStore.topViewSize.left +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width) +
            'px',
        }"
        class="delete-marker-position"
      />

      <div
        v-for="point in calibrationAssetStore.topViewMarkerProjection"
        v-show="calibrationAssetStore.showVideoMarker"
        :key="point"
        :style="{
          top: point.y * topViewStore.topViewSize.height + topViewStore.topViewSize.top + 'px',
          left: point.x * topViewStore.topViewSize.width + topViewStore.topViewSize.left + 'px',
        }"
        class="field-marker-position"
      />
    </v-row>

    <v-row
      ref="videoControl"
      class="video-control mt-6 mb-0 justify-center align-center"
      style="height: 60px"
    >
      <v-menu location="top start">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ topViewStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item
            v-for="item in topViewStore.sports"
            :key="item"
            class="menu-item"
            v-on:click="topViewStore.onSportChange(item.title)"
          >
            <v-list-item-title>
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu location="top center">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("calibration_asset.title") }}
          </v-btn>
        </template>

        <v-list class="py-0" width="200px" density="compact">
          <v-list-item class="menu-item" @click="showModalCalibrationAssetCreate = true">
            <v-list-item-title>
              {{ $t("calibration_asset.create") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            class="menu-item"
            v-if="!calibrationAssetStore.calibrationAssetId"
            @click="showModalCalibrationAssetSave = true"
          >
            <v-list-item-title>
              {{ $t("calibration_asset.save") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            class="menu-item"
            v-if="calibrationAssetStore.calibrationAssetId"
            @click="showModalCalibrationAssetUpdate = true"
          >
            <v-list-item-title>
              {{ $t("calibration_asset.update") }}
            </v-list-item-title>
          </v-list-item>
          <v-list-item class="menu-item" @click="showModalCalibrationAssetSelect = true">
            <v-list-item-title>
              {{ $t("calibration_asset.select") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <ModalCalibrationAssetCreate
        v-if="showModalCalibrationAssetCreate"
        v-model="showModalCalibrationAssetCreate"
      />
      <ModalCalibrationAssetSave
        v-if="showModalCalibrationAssetSave"
        v-model="showModalCalibrationAssetSave"
      />
      <ModalCalibrationAssetSelect
        v-if="showModalCalibrationAssetSelect"
        v-model="showModalCalibrationAssetSelect"
      />
      <ModalCalibrationAssetUpdate
        v-if="showModalCalibrationAssetUpdate"
        v-model="showModalCalibrationAssetUpdate"
      />

      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("calibration_asset.marker.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="200px">
          <v-list-item class="menu-item" @click="calibrationAssetStore.toggleVideoMarker">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("calibration_asset.marker.view_vid_marker") }}
              <v-icon
                :class="{
                  'text-disabled': !calibrationAssetStore.showVideoMarker,
                  'text-red': calibrationAssetStore.showVideoMarker,
                }"
                class="mb-1"
                size="small"
              >
                mdi-check
              </v-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="addReferenceMarker">
            <v-list-item-title>
              {{ $t("calibration_asset.marker.add_ref_marker") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="showDeleteButton = !showDeleteButton">
            <v-list-item-title>
              {{ $t("calibration_asset.marker.delete_ref_marker") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useVideoStore } from "@/stores/video";
import ModalCalibrationAssetMenu from "@/components/calibration-asset/ModalCalibrationAssetMenu.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSave from "@/components/calibration-asset/ModalCalibrationAssetSave.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import ModalCalibrationAssetUpdate from "@/components/calibration-asset/ModalCalibrationAssetUpdate.vue";

const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();
const videoStore = useVideoStore();

const props = defineProps({
  showItems: {
    type: Boolean,
    default: false,
  },
});

const topViewElement = ref(null);
const updateTopViewSize = () => {
  nextTick(() => {
    if (topViewElement.value) {
      const rect = topViewElement.value.getBoundingClientRect();
      topViewStore.setTopViewSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  });
};
onMounted(() => {
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
  updateTopViewSize();
  window.addEventListener("resize", updateTopViewSize);
  window.addEventListener("scroll", updateTopViewSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  window.removeEventListener("scroll", updateTopViewSize);
});

const showModalCalibrationAssetCreate = ref(false);
const showModalCalibrationAssetSave = ref(false);
const showModalCalibrationAssetSelect = ref(false);
const showModalCalibrationAssetUpdate = ref(false);

const filteredReferenceMarker = computed(() => calibrationAssetStore.filteredReferenceMarker);

const showDeleteButton = ref(false);
const addReferenceMarker = () => {
  if (showDeleteButton.value) {
    showDeleteButton.value = false;
    nextTick(() => {
      calibrationAssetStore.addReferenceMarker();
    });
  } else {
    calibrationAssetStore.addReferenceMarker();
  }
};

const overlayMarker = ref(null);
const handleClickOverlayMarker = (event) => {
  if (!calibrationAssetStore.isAddingReferenceMarker || !overlayMarker.value) return;
  if (!overlayMarker.value.contains(event.target)) return;
};
onMounted(() => {
  window.addEventListener("click", handleClickOverlayMarker);
});
onBeforeUnmount(() => {
  window.removeEventListener("click", handleClickOverlayMarker);
});

const maxVideoHeight = ref(0);
const videoControl = ref(null);
const updateMaxHeight = () => {
  if (!videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight - 104 - 32 - videoControl.value.$el.offsetHeight - 60) / window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});
</script>

<style scoped>
.image {
  max-width: 100%;
  object-fit: cover;
}

.marker-position {
  position: fixed;
  transform: translate(-50%, -50%);
  z-index: 1000;
}

.delete-marker-position {
  position: fixed;
  transform: translate(-50%, -50%);
  z-index: 1001;
}

.delete-marker-position .v-icon {
  transform: scale(0.7);
}

.delete-marker-position:hover {
  border: 1px red solid;
}

.video-control {
  gap: 5px;
}

.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}

.overlay-marker {
  position: fixed;
  background: rgba(255, 255, 255, 0.5);
  z-index: 5;
  border: 4px solid red;
  cursor: crosshair;
}

.field-marker-position {
  position: fixed;
  width: 5px;
  height: 5px;
  background-color: blue;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 1001;
}

/* .overlay-container {
  position: relative;
}
.video-overlay {
  position: absolute;
  object-fit: cover;
  z-index: 1;
} */
</style>
