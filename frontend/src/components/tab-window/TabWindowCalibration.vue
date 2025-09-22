<template>
  <CalibrationAssetMenu v-if="calibrationAssetStore.marker.length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row ref="container" class="mt-1 fullscreen-container" justify="center">
      <div style="position: relative; display: inline-block">
        <img
          ref="topViewElement"
          class="image"
          :src="topViewStore.currentSport.pitchImage"
          @load="updateTopViewSize"
          :style="{
            maxHeight: maxVideoHeight * 100 + 'vh',
            height: videoStore.videoSize.height + 'px',
          }"
        />

        <v-btn
          icon="mdi-fullscreen"
          variant="tonal"
          size="small"
          class="fullscreen-btn"
          @click="toggleFullscreen"
        />

        <div
          v-if="calibrationAssetStore.isAddingReferenceMarker"
          ref="overlayMarker"
          @click="calibrationAssetStore.setReferenceMarker"
          :style="{
            position: 'absolute',
            background: 'rgba(255, 255, 255, 0.5)',
            border: '4px solid red',
            cursor: 'crosshair',
            top: '0px',
            left: '0px',
            width: topViewStore.topViewSize.width + 'px',
            height: topViewStore.topViewSize.height + 'px',
          }"
        />

        <v-btn
          v-for="m in calibrationAssetStore.filteredReferenceMarker"
          v-show="topViewStore.showItems"
          :key="m.id"
          :disabled="calibrationAssetStore.isAddingReferenceMarker"
          :color="m.active || calibrationAssetStore.hoveredVideoMarker === m.id ? 'red' : 'grey'"
          icon="mdi-circle"
          variant="plain"
          density="compact"
          @click="(event) => calibrationAssetStore.toggleReferenceMarker(event, m.id)"
          @contextmenu.prevent="openDeleteModal(m)"
          :style="{
            position: 'absolute',
            transform: 'translate(-50%, -50%)',
            top:
              m.compAreaCoordsRel.y *
                (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
              'px',
            left:
              m.compAreaCoordsRel.x *
                (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
              'px',
          }"
        />
        <ModalReferenceMarkerDelete
          v-if="showModalReferenceMarkerDelete"
          v-model="showModalReferenceMarkerDelete"
          :marker="selectedReferenceMarker"
        />

        <v-btn
          v-for="m in calibrationAssetStore.filteredReferenceMarker"
          v-show="showDeleteButton"
          :key="'delete-' + m.id"
          color="red"
          icon="mdi-close"
          variant="plain"
          density="compact"
          @click="calibrationAssetStore.deleteReferenceMarker(m.id)"
          class="delete-marker-position"
          :style="{
            position: 'absolute',
            transform: 'translate(-50%, -50%)',
            top:
              m.compAreaCoordsRel.y *
                (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
              'px',
            left:
              m.compAreaCoordsRel.x *
                (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
              'px',
          }"
        />

        <div
          v-for="point in calibrationAssetStore.topViewMarkerProjection"
          v-show="calibrationAssetStore.showVideoMarker"
          :key="point"
          :style="{
            position: 'absolute',
            width: '5px',
            height: '5px',
            backgroundColor: 'blue',
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            top: point.y * topViewStore.topViewSize.height + 'px',
            left: point.x * topViewStore.topViewSize.width + 'px',
            pointerEvents: 'none',
          }"
        />
      </div>
    </v-row>

    <v-row
      ref="videoControl"
      class="video-control mt-6 mb-0 justify-center align-center"
      style="height: 60px"
      data-tour="calibration-asset-edit-row"
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

        <v-list class="py-0" density="compact">
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
        <v-list class="py-0" density="compact" width="220px">
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

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("calibration_asset.marker.add_ref_marker.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact" width="225px">
              <v-list-item class="menu-item" @click="addReferenceMarker">
                <v-list-item-title>
                  {{ $t("calibration_asset.marker.add_ref_marker.custom_marker") }}
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <div style="max-height: 160px; overflow-y: auto">
                <v-list-item
                  v-for="m in calibrationAssetStore.markerTemplate.filter((m) => !m.set)"
                  :key="m.id"
                  class="menu-item"
                  @click="addTemplateReferenceMarker(m)"
                >
                  <v-list-item-title>
                    {{ m.name }}
                  </v-list-item-title>
                </v-list-item>
              </div>
            </v-list>
          </v-menu>

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
import CalibrationAssetMenu from "@/components/calibration-asset/CalibrationAssetMenu.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSave from "@/components/calibration-asset/ModalCalibrationAssetSave.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import ModalCalibrationAssetUpdate from "@/components/calibration-asset/ModalCalibrationAssetUpdate.vue";
import ModalReferenceMarkerDelete from "@/components/calibration-asset/ModalReferenceMarkerDelete.vue";

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
const updateTopViewSize = async () => {
  await nextTick();
  await waitForStableElement(topViewElement);

  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    topViewStore.setTopViewSize({
      width: rect.width,
      height: rect.height,
      top: rect.top,
      left: rect.left,
    });
  }
};
function waitForStableElement(elRef) {
  return new Promise((resolve) => {
    let lastRect = null;
    let stableCounter = 0;

    const check = () => {
      const el = elRef.value;
      if (!el) {
        requestAnimationFrame(check);
        return;
      }

      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0 || rect.top === 0 || rect.left === 0) {
        requestAnimationFrame(check);
        return;
      }

      if (
        lastRect &&
        rect.top === lastRect.top &&
        rect.left === lastRect.left &&
        rect.width === lastRect.width &&
        rect.height === lastRect.height
      ) {
        stableCounter++;
      } else {
        stableCounter = 0;
      }

      lastRect = rect;

      if (stableCounter >= 3) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };

    check();
  });
}
const resizeObserver = new ResizeObserver(() => {
  updateTopViewSize();
});
onMounted(() => {
  window.addEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.observe(topViewElement.value);
    updateTopViewSize();
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
});

const showModalCalibrationAssetCreate = ref(false);
const showModalCalibrationAssetSave = ref(false);
const showModalCalibrationAssetSelect = ref(false);
const showModalCalibrationAssetUpdate = ref(false);

const showModalReferenceMarkerDelete = ref(false);
const selectedReferenceMarker = ref(null);
const openDeleteModal = (marker) => {
  selectedReferenceMarker.value = marker;
  showModalReferenceMarkerDelete.value = true;
};

const showDeleteButton = ref(false);
const addReferenceMarker = () => {
  if (showDeleteButton.value) {
    showDeleteButton.value = false;
  }
  nextTick(() => {
    calibrationAssetStore.addReferenceMarker();
  });
};
const addTemplateReferenceMarker = (marker) => {
  if (showDeleteButton.value) {
    showDeleteButton.value = false;
  }
  nextTick(() => {
    calibrationAssetStore.addTemplateReferenceMarker(marker);
  });
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

const container = ref(null);
const toggleFullscreen = () => {
  const el = container.value;
  if (!el) return;

  if (!document.fullscreenElement) {
    el.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
};
</script>

<style scoped>
.image {
  max-width: 100%;
  object-fit: cover;
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

.fullscreen-container {
  position: relative;
}

.fullscreen-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.fullscreen-container:hover .fullscreen-btn {
  opacity: 1;
}
</style>
