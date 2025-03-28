<template>
  <div
    ref="overlayReferenceMarker"
    class="overlay-reference-marker"
    @click="calibrationAssetStore.setVideoMarker"
  >
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
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

onMounted(() => {
  updateVideoSize();
  window.addEventListener("click", handleClickOverlayReferenceMarker);
  window.addEventListener("resize", updateVideoSize);
});

onUnmounted(() => {
  window.removeEventListener("click", handleClickOverlayReferenceMarker);
  window.removeEventListener("resize", updateVideoSize);
});
</script>

<style>
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
