<template>
  <CalibrationAssetMenu v-if="calibrationAssetStore.marker.length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row ref="container" class="mt-1" justify="center">
      <div
        ref="topViewDiv"
        class="top-view-wrapper"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
      >
        <img
          ref="topViewElement"
          class="visualizer-image"
          :src="topViewStore.currentSport.pitchImage"
          @load="updateTopViewSize"
          :style="
            isTopViewFullscreen
              ? {
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                }
              : {
                  maxHeight: maxVideoHeight * 100 + 'vh',
                  height: videoStore.videoSize.height + 'px',
                }
          "
        />

        <v-icon
          class="fullscreen-toggle"
          @click="toggleTopViewFullscreen"
          :class="{ visible: hovering }"
        >
          {{ isTopViewFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
        </v-icon>

        <div
          v-if="calibrationAssetStore.isAddingReferenceMarker"
          ref="overlayMarker"
          @click="calibrationAssetStore.setReferenceMarker"
          :style="{
            position: 'absolute',
            background: 'rgba(255, 255, 255, 0.5)',
            border: '4px solid red',
            cursor: 'crosshair',
            top: isTopViewFullscreen ? topViewStore.topViewSize.top + 'px' : '0px',
            left: isTopViewFullscreen ? topViewStore.topViewSize.left + 'px' : '0px',
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
            top: isTopViewFullscreen
              ? topViewStore.topViewSize.top +
                m.compAreaCoordsRel.y *
                  (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px'
              : m.compAreaCoordsRel.y *
                  (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px',
            left: isTopViewFullscreen
              ? topViewStore.topViewSize.left +
                m.compAreaCoordsRel.x *
                  (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                'px'
              : m.compAreaCoordsRel.x *
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
            top: isTopViewFullscreen
              ? topViewStore.topViewSize.top +
                m.compAreaCoordsRel.y *
                  (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px'
              : m.compAreaCoordsRel.y *
                  (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px',
            left: isTopViewFullscreen
              ? topViewStore.topViewSize.left +
                m.compAreaCoordsRel.x *
                  (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                'px'
              : m.compAreaCoordsRel.x *
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
            top: isTopViewFullscreen
              ? topViewStore.topViewSize.top + point.y * topViewStore.topViewSize.height + 'px'
              : point.y * topViewStore.topViewSize.height + 'px',
            left: isTopViewFullscreen
              ? topViewStore.topViewSize.left + point.y * topViewStore.topViewSize.height + 'px'
              : point.y * topViewStore.topViewSize.height + 'px',
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

      <v-tooltip
        v-if="
          calibrationAssetStore.timeChangeConflict &&
          calibrationAssetStore.videoMarkerTime !== playerStore.currentTime
        "
        class="time-conflict-tooltip"
        :text="
          $t('calibration_asset.time-conflict', {
            time: getTimecode(calibrationAssetStore.videoMarkerTime ?? 0),
          })
        "
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" color="warning" size="small" class="ml-2 mt-1"
            >mdi-information-outline</v-icon
          >
        </template>
      </v-tooltip>
    </v-row>
  </v-container>

  <v-snackbar color="accent" timeout="3000" v-model="showVideoMarkerActionSnackbar">
    <div class="d-flex justify-center">
      <snackbar-icon-warning />
      <span class="text-h6">{{ videoMarkerActionMessage }}</span>
    </div>
  </v-snackbar>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { getTimecode } from "@/plugins/time";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import CalibrationAssetMenu from "@/components/calibration-asset/CalibrationAssetMenu.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSave from "@/components/calibration-asset/ModalCalibrationAssetSave.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import ModalCalibrationAssetUpdate from "@/components/calibration-asset/ModalCalibrationAssetUpdate.vue";
import ModalReferenceMarkerDelete from "@/components/calibration-asset/ModalReferenceMarkerDelete.vue";

const { t } = useI18n();

const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();
const videoStore = useVideoStore();
const playerStore = usePlayerStore();

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

const hovering = ref(false);
const topViewDiv = ref(null);
const isTopViewFullscreen = ref(false);
const toggleTopViewFullscreen = () => {
  const div = topViewDiv.value;
  if (!document.fullscreenElement) {
    div.requestFullscreen?.();
    playerStore.isSynced = false;
  } else {
    document.exitFullscreen?.();
  }
};

const onFullscreenChange = async () => {
  const isTopViewFullscreenPrev = isTopViewFullscreen.value;
  isTopViewFullscreen.value = document.fullscreenElement === topViewDiv.value;

  if (isTopViewFullscreenPrev === true || isTopViewFullscreen.value === true) {
    await nextTick();
    if (topViewElement.value) {
      const rect = topViewElement.value.getBoundingClientRect();
      topViewStore.setTopViewSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  }
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

watch(
  () => playerStore.currentTime,
  (newTime, oldTime) => {
    if (oldTime === undefined || newTime === oldTime || calibrationAssetStore.timeChangeConflict)
      return;

    const hasVideoCoords = calibrationAssetStore.marker.some((m) => {
      const v = m.videoCoordsRel;
      return v && (v.x !== null || v.y !== null);
    });

    if (hasVideoCoords) {
      calibrationAssetStore.timeChangeConflict = true;
      showVideoMarkerActionSnackbar.value = true;
      calibrationAssetStore.videoMarkerTime = oldTime;
    }
  }
);

const showVideoMarkerActionSnackbar = ref(false);
const videoMarkerActionMessage = ref("");
const resetVideoMarkerActionSnackbar = async () => {
  showVideoMarkerActionSnackbar.value = false;
  await nextTick();
  showVideoMarkerActionSnackbar.value = true;
};
watch([() => calibrationAssetStore.timeChangeConflict], ([warning]) => {
  if (warning === true) {
    videoMarkerActionMessage.value = t("modal.calibration_asset.video_marker.warning", {
      time: getTimecode(calibrationAssetStore.videoMarkerTime ?? 0),
    });
    resetVideoMarkerActionSnackbar();
  }
});
</script>

<style scoped>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
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

.top-view-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-toggle {
  position: absolute;
  top: 2px;
  right: 2px;
  color: white;
  font-size: 28px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-toggle.visible {
  opacity: 0.8;
}

.fullscreen-controls {
  position: absolute;
  left: 0;
  width: 100%;
  padding: 16px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  display: flex;
  flex-direction: column;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-controls.visible {
  opacity: 1;
}

.time-conflict-tooltip ::v-deep .v-overlay__content {
  background-color: rgb(var(--v-theme-accent));
}
</style>
