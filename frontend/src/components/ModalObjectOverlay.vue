<template>
  <div
    class="overlay-reference-object"
    @click="setVideoObject"
    @mousemove="onMouseMove"
    @mouseleave="hideZoom"
  >
    <div style="position: relative; display: inline-block; transform: scale(1.15)">
      <video
        class="video-overlay"
        ref="videoOverlayElement"
        @loadedmetadata="seekToCurrentTime"
        :style="{
          width: videoStore.videoSize.width + 'px',
          height: videoStore.videoSize.height + 'px',
        }"
      />

      <!-- <div
        v-for="m in calibrationAssetStore.filteredVideoObject"
        v-show="calibrationAssetStore.showVideoAsset"
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
        @mouseenter="calibrationAssetStore.hoveredVideoObject = m.id"
        @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
      /> -->
      <svg
        :width="videoStore.videoSize.width"
        :height="videoStore.videoSize.height"
        style="position: absolute; top: 0; left: 0; pointer-events: none"
      >
        <template v-for="m in calibrationAssetStore.filteredVideoObject">
          <circle
            v-if="m.videoCoordsRel.length === 1"
            :key="m.id"
            :cx="m.videoCoordsRel[0].x * videoStore.videoSize.width"
            :cy="m.videoCoordsRel[0].y * videoStore.videoSize.height"
            r="8"
            :fill="calibrationAssetStore.objectColorMap[m.id] ?? 'red'"
            fill-opacity="0.8"
          />

          <line
            v-if="m.videoCoordsRel.length === 2"
            :key="m.id"
            :x1="m.videoCoordsRel[0].x * videoStore.videoSize.width"
            :y1="m.videoCoordsRel[0].y * videoStore.videoSize.height"
            :x2="m.videoCoordsRel[1].x * videoStore.videoSize.width"
            :y2="m.videoCoordsRel[1].y * videoStore.videoSize.height"
            stroke-width="8"
            :stroke="calibrationAssetStore.objectColorMap[m.id] ?? 'red'"
            stroke-opacity="0.8"
          />

          <path
            v-if="m.videoCoordsRel.length > 2"
            :key="m.id"
            :d="
              (() => {
                const points = m.videoCoordsRel.map((p) => ({
                  x: p.x * videoStore.videoSize.width,
                  y: p.y * videoStore.videoSize.height,
                }));
                let d = `M ${points[0].x} ${points[0].y}`;
                for (let i = 1; i < points.length; i++) {
                  d += ` L ${points[i].x} ${points[i].y}`;
                }
                return d;
              })()
            "
            :stroke="calibrationAssetStore.objectColorMap[m.id] ?? 'red'"
            stroke-width="8"
            stroke-opacity="0.8"
            fill="none"
          />
        </template>

        <template v-for="(point, index) in currentSegmentPoints" :key="index">
          <circle
            :cx="point.x * videoStore.videoSize.width"
            :cy="point.y * videoStore.videoSize.height"
            r="8"
            fill="red"
          />
        </template>
      </svg>
    </div>

    <v-btn
      v-if="calibrationAssetStore.calibrationAssetType === 'segment'"
      @click="finishSegment"
      :disabled="currentSegmentPoints.length < 2"
      style="position: absolute; bottom: 25px; right: 25px"
    >
      {{ $t("button.save") }}
    </v-btn>

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
import Hls from "hls.js";

const calibrationAssetStore = useCalibrationAssetStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();

const videoOverlayElement = ref(null);

const seekToCurrentTime = () => {
  if (videoOverlayElement.value) {
    videoOverlayElement.value.currentTime = playerStore.currentTime / 1000;
  }
};

const currentSegmentPoints = ref([]);
const setVideoObject = (event) => {
  const rect = videoOverlayElement.value?.getBoundingClientRect();
  if (!rect) return;

  if (calibrationAssetStore.timeChangeConflict) {
    calibrationAssetStore.calibrationAssetObjects.forEach((m) => {
      m.videoCoordsRel = [{ x: null, y: null, z: null }];
    });
    calibrationAssetStore.timeChangeConflict = false;
  }

  const normX = (event.clientX - rect.left) / rect.width;
  const normY = (event.clientY - rect.top) / rect.height;

  if (calibrationAssetStore.calibrationAssetType === "marker") {
    calibrationAssetStore.setVideoObject([{ x: normX, y: normY }]);
  } else if (calibrationAssetStore.calibrationAssetType === "segment") {
    currentSegmentPoints.value.push({ x: normX, y: normY });
  }
};
const finishSegment = () => {
  if (currentSegmentPoints.value.length > 1) {
    calibrationAssetStore.setVideoObject(currentSegmentPoints.value);
    currentSegmentPoints.value = [];
  }
};
watch(
  () => currentSegmentPoints.value,
  (nww) => {
    console.log("segemtnpoints", nww);
  },
  { deep: true }
);

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
  () => calibrationAssetStore.isAnyReferenceObjectActive,
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

let hlsOverlay = null;
function tarGzUrlToHlsUrl(tarUrl) {
  const url = new URL(tarUrl);

  // Dateiname extrahieren
  const parts = url.pathname.split("/");
  const fileName = parts.pop(); // <hash>.tar.gz
  const id = fileName.replace(/\.tar\.gz$/, "");

  // Neuer Pfad: nested id/<id>.m3u8 (HLS index)
  parts.push(id, `${id}.m3u8`);
  url.pathname = parts.join("/");

  return url.toString();
}
watch(
  () => playerStore.videoUrl,
  async (url) => {
    await nextTick();
    if (!url || !videoOverlayElement.value) return;

    const video = videoOverlayElement.value;
    const hlsUrl = tarGzUrlToHlsUrl(url);

    if (!hlsUrl) return;

    if (hlsOverlay) {
      try {
        hlsOverlay.destroy();
      } catch (e) {
        console.error("Failed to destroy existing hls instance", e);
      }
      hlsOverlay = null;
      try {
        video.src = "";
      } catch (e) {}
    }

    if (Hls.isSupported()) {
      hlsOverlay = new Hls();
      hlsOverlay.loadSource(hlsUrl);
      hlsOverlay.attachMedia(video);

      hlsOverlay.on(Hls.Events.MANIFEST_PARSED, () => {
        updateVideoSize();
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.overlay-reference-object {
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
