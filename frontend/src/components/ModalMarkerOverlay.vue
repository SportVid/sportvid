<template>
  <div
    ref="overlayReferenceMarker"
    class="overlay-reference-marker"
    @click="setVideoMarker"
    @mousemove="onMouseMove"
    @mouseleave="hideZoom"
  >
    <div style="position: relative; display: inline-block; transform: scale(1.15)">
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

    <canvas
      v-show="showZoom"
      :width="zoomSize"
      :height="zoomSize"
      ref="zoomCanvas"
      :style="{
        position: 'fixed',
        left: zoomCanvasLeft + 'px',
        top: zoomCanvasTop + 'px',
        border: '2px solid black',
        borderRadius: '4px',
        pointerEvents: 'none',
        background: '#000',
      }"
    />
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onBeforeUnmount } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";

const calibrationAssetStore = useCalibrationAssetStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();

const overlayReferenceMarker = ref(null);

const videoOverlayElement = ref(null);

const seekToCurrentTime = () => {
  if (videoOverlayElement.value) {
    videoOverlayElement.value.currentTime = playerStore.currentTime;
  }
};

const setVideoMarker = (event) => {
  const rect = videoOverlayElement.value?.getBoundingClientRect();
  if (!rect) return;
  const normX = (event.clientX - rect.left) / rect.width;
  const normY = (event.clientY - rect.top) / rect.height;
  calibrationAssetStore.setVideoMarker({ x: normX, y: normY });
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

const zoomCanvas = ref(null);
const zoomCanvasLeft = ref(0);
const zoomCanvasTop = ref(0);

const showZoom = ref(false);
const zoomSize = 120;
const zoomScale = ref(2.5);
const zoomPos = ref({ x: 0, y: 0 });

const onMouseMove = (event) => {
  const rect = videoOverlayElement.value?.getBoundingClientRect();
  if (!rect || !videoOverlayElement.value) {
    hideZoom();
    return;
  }

  const localX = event.clientX - rect.left;
  const localY = event.clientY - rect.top;

  if (localX < 0 || localY < 0 || localX > rect.width || localY > rect.height) {
    hideZoom();
    return;
  }

  showZoom.value = true;
  zoomPos.value = { x: localX, y: localY };

  zoomCanvasLeft.value = event.clientX - 60;

  const margin = -86 + 150;
  if (event.clientY - 150 < margin) {
    zoomCanvasTop.value = event.clientY + 30;
  } else {
    zoomCanvasTop.value = event.clientY - 150;
  }

  drawZoom();
};

const drawZoom = () => {
  const cv = zoomCanvas.value;
  const vid = videoOverlayElement.value;
  if (!cv || !vid) return;
  const ctx = cv.getContext("2d");
  if (!ctx) return;

  const rect = vid.getBoundingClientRect();

  const videoW = vid.videoWidth || rect.width;
  const videoH = vid.videoHeight || rect.height;
  const scaleFactorX = videoW / rect.width;
  const scaleFactorY = videoH / rect.height;

  const srcHalfW = zoomSize / zoomScale.value / 2;
  const srcHalfH = zoomSize / zoomScale.value / 2;

  const centerX = zoomPos.value.x * scaleFactorX;
  const centerY = zoomPos.value.y * scaleFactorY;

  let sx = centerX - srcHalfW;
  let sy = centerY - srcHalfH;
  let sw = srcHalfW * 2;
  let sh = srcHalfH * 2;

  if (sx < 0) sx = 0;
  if (sy < 0) sy = 0;
  if (sx + sw > videoW) sx = videoW - sw;
  if (sy + sh > videoH) sy = videoH - sh;

  ctx.clearRect(0, 0, zoomSize, zoomSize);
  try {
    ctx.drawImage(vid, sx, sy, sw, sh, 0, 0, zoomSize, zoomSize);
    ctx.strokeStyle = "rgba(255,255,255,0.8)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(zoomSize / 2, 0);
    ctx.lineTo(zoomSize / 2, zoomSize);
    ctx.moveTo(0, zoomSize / 2);
    ctx.lineTo(zoomSize, zoomSize / 2);
    ctx.stroke();
  } catch (e) {}
};

const hideZoom = () => {
  showZoom.value = false;
};

onBeforeUnmount(() => {
  hideZoom();
});
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
