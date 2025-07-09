<template>
  <div
    ref="overlayReferenceMarker"
    class="overlay-reference-marker"
    @click="calibrationAssetStore.setVideoMarker"
  >
    <div style="position: relative; display: inline-block">
      <video
        class="video-overlay"
        ref="videoOverlayElement"
        :src="playerStore.videoUrl"
        @loadedmetadata="seekToCurrentTime"
        :style="{
          width: videoStore.videoSize.width + 'px',
          height: videoStore.videoSize.height + 'px',
        }"
      />

      <div
        v-for="m in calibrationAssetStore.filteredVideoMarker"
        v-show="calibrationAssetStore.showVideoMarker"
        :key="m.id"
        :style="{
          position: 'absolute',
          width: '12px',
          height: '12px',
          backgroundColor: 'red',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          top: m.videoCoordsRel.y * videoStore.videoSize.height + 'px',
          left: m.videoCoordsRel.x * videoStore.videoSize.width + 'px',
        }"
        @mouseenter="calibrationAssetStore.hoveredVideoMarker = m.id"
        @mouseleave="calibrationAssetStore.hoveredVideoMarker = null"
      />

      <div
        v-for="point in calibrationAssetStore.videoMarkerReprojection"
        v-show="calibrationAssetStore.showVideoMarker"
        :key="point"
        :style="{
          position: 'absolute',
          width: '5px',
          height: '5px',
          backgroundColor: 'blue',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          top: point.y * videoStore.videoSize.height + 'px',
          left: point.x * videoStore.videoSize.width + 'px',
        }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";

const calibrationAssetStore = useCalibrationAssetStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();

const marker = computed(() => calibrationAssetStore.marker);
const overlayReferenceMarker = ref(null);

const videoOverlayElement = ref(null);

const handleClickOverlayReferenceMarker = (event) => {
  const activeMarker = marker.value.find((m) => m.active);
  if (!activeMarker || !overlayReferenceMarker.value) return;
  if (!overlayReferenceMarker.value.contains(event.target)) return;
};

const seekToCurrentTime = () => {
  if (videoOverlayElement.value) {
    videoOverlayElement.value.currentTime = playerStore.currentTime;
  }
};

const updateVideoSize = () => {
  nextTick(() => {
    if (videoOverlayElement.value) {
      const rect = videoOverlayElement.value.getBoundingClientRect();
      const size = {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      };
      videoStore.setVideoSize(size);
    }
  });
};
watch(
  () => calibrationAssetStore.isAnyReferenceMarkerActive,
  (active) => {
    if (active) {
      updateVideoSize();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.overlay-reference-marker {
  position: fixed;
  top: 64px;
  left: 0;
  width: 100%;
  height: calc(100vh - 64px);
  background: rgba(255, 255, 255);
  z-index: 5;
  pointer-events: auto;
  border: 4px solid red;
  cursor: crosshair;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-overlay {
  object-fit: cover;
}
</style>
