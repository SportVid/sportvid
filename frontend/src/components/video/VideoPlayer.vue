<template>
  <v-container ref="videoContainer" class="d-flex flex-column">
    <v-row justify="center">
      <div
        ref="videoDiv"
        class="video-wrapper"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
      >
        <video
          ref="videoElement"
          @play="onPlay"
          @pause="onPause"
          @ended="onEnded"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="updateVideoSize"
          :style="
            isVideoFullscreen
              ? { maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }
              : {
                  maxHeight: maxVideoHeight * 100 + 'vh',
                  maxWidth: '100%',
                }
          "
        />

        <v-icon
          class="fullscreen-toggle"
          @click="toggleVideoFullscreen"
          :class="{ visible: hovering }"
        >
          {{ isVideoFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
        </v-icon>

        <div v-if="isVideoFullscreen" class="fullscreen-controls" :class="{ visible: hovering }">
          <div class="controls-top">
            <v-icon @click="togglePlaying" class="control-icon">
              <template v-if="videoEnded">mdi-restart</template>
              <template v-else-if="videoPlaying">mdi-pause</template>
              <template v-else>mdi-play</template>
            </v-icon>
            <div class="time-code">{{ getTimecode(playerStore.currentTime) }}</div>
          </div>

          <v-slider
            v-model="progress"
            @update:model-value="onProgressChange"
            hide-details
            color="white"
            :thumb-size="15"
            :step="1000 / playerStore.videoFPS"
            min="0"
            :max="playerStore.videoDuration"
          />
        </div>

        <!-- <div
          v-for="position in bboxesStore.bboxDataInterpolated[currentFrameKey]"
          v-show="bboxesStore.showBoundingBox"
          :key="position"
          :style="{
            position: 'absolute',
            top: isVideoFullscreen
              ? videoStore.videoSize.top + position[7] * videoStore.videoSize.height + 'px'
              : position[7] * videoStore.videoSize.height + 'px',
            left: isVideoFullscreen
              ? videoStore.videoSize.left + position[6] * videoStore.videoSize.width + 'px'
              : position[6] * videoStore.videoSize.width + 'px',
            width: position[8] * videoStore.videoSize.width + 'px',
            height: position[9] * videoStore.videoSize.height + 'px',
            border: `2px solid ${visualizationStore.getTeamColor(position[1])}`,
          }"
        >
        </div> -->

        <div
          v-for="position in bboxesStore.bboxDataInterpolated[currentFrameKey]"
          v-show="bboxesStore.showBoundingBox"
          :key="position"
          :style="getEllipseSvg(position).style"
          @click="openEditBBox(position)"
        >
          <svg class="player-ellipse">
            <path
              :d="getEllipseSvg(position).arc"
              :stroke="getEllipseSvg(position).color"
              stroke-width="2"
              fill="none"
              stroke-linecap="round"
            />
          </svg>
          <v-tooltip
            activator="parent"
            location="top"
            class="bounding-box-tooltip"
            :style="{ '--tooltip-bg': toRgb(visualizationStore.getTeamColor(position[1]), 0.7) }"
            interactive
          >
            <div>
              <div>
                <strong>{{ $t("modal.bounding_box.tooltip.box_id") }}: {{ position[5] }}</strong>
              </div>
              <v-divider class="my-1" />
              <div>{{ $t("modal.bounding_box.tooltip.player_id") }}: {{ position[0] }}</div>
              <div>{{ $t("modal.bounding_box.tooltip.team_id") }}: {{ position[1] }}</div>
            </div>
          </v-tooltip>
          <div
            class="bounding-box-player-id"
            :style="{
              color: visualizationStore.getTeamColor(position[1]),
            }"
          >
            {{ position[0] }}
          </div>
        </div>

        <!-- <div
          v-for="o in calibrationAssetStore.filteredVideoObject"
          v-show="calibrationAssetStore.showVideoAsset"
          :key="o.id"
          :style="{
            position: 'absolute',
            width: '12px',
            height: '12px',
            backgroundColor: 'red',
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            top: isVideoFullscreen
              ? videoStore.videoSize.top + o.videoCoordsRel.y * videoStore.videoSize.height + 'px'
              : o.videoCoordsRel.y * videoStore.videoSize.height + 'px',
            left: isVideoFullscreen
              ? videoStore.videoSize.left + o.videoCoordsRel.x * videoStore.videoSize.width + 'px'
              : o.videoCoordsRel.x * videoStore.videoSize.width + 'px',
          }"
          @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
          @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
        /> -->
        <svg
          :width="videoStore.videoSize.width"
          :height="videoStore.videoSize.height"
          style="position: absolute; top: 0; left: 0; pointer-events: none"
        >
          <template v-for="o in calibrationAssetStore.filteredVideoObject">
            <circle
              v-if="o.videoCoordsRel.length === 1"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :cx="o.videoCoordsRel[0].x * videoStore.videoSize.width"
              :cy="o.videoCoordsRel[0].y * videoStore.videoSize.height"
              r="8"
              fill="red"
              fill-opacity="0.8"
              style="pointer-events: all"
              @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
              @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
            />

            <line
              v-if="o.videoCoordsRel.length === 2"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :x1="o.videoCoordsRel[0].x * videoStore.videoSize.width"
              :y1="o.videoCoordsRel[0].y * videoStore.videoSize.height"
              :x2="o.videoCoordsRel[1].x * videoStore.videoSize.width"
              :y2="o.videoCoordsRel[1].y * videoStore.videoSize.height"
              stroke-width="8"
              stroke="red"
              stroke-opacity="0.8"
              fill="none"
              style="pointer-events: all"
              @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
              @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
            />

            <path
              v-if="o.videoCoordsRel.length > 2"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :d="
                (() => {
                  const points = o.videoCoordsRel.map((p) => ({
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
              stroke="red"
              stroke-width="8"
              stroke-opacity="0.8"
              fill="none"
              style="pointer-events: all"
              @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
              @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
            />
          </template>
        </svg>

        <svg
          :width="videoStore.videoSize.width"
          :height="videoStore.videoSize.height"
          style="position: absolute; top: 0; left: 0; pointer-events: none"
        >
          <template v-for="o in calibrationAssetStore.videoObjectReprojection">
            <circle
              v-if="o.length === 1"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :cx="
                (isVideoFullscreen ? videoStore.videoSize.left : 0) +
                o[0].x * videoStore.videoSize.width +
                'px'
              "
              :cy="
                (isVideoFullscreen ? videoStore.videoSize.top : 0) +
                o[0].y * videoStore.videoSize.height +
                'px'
              "
              r="3"
              fill="blue"
              style="pointer-events: none"
            />

            <line
              v-if="o.length === 2"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :x1="
                (isVideoFullscreen ? videoStore.videoSize.left : 0) +
                o[0].x * videoStore.videoSize.width +
                'px'
              "
              :y1="
                (isVideoFullscreen ? videoStore.videoSize.top : 0) +
                o[0].y * videoStore.videoSize.height +
                'px'
              "
              :x2="
                (isVideoFullscreen ? videoStore.videoSize.left : 0) +
                o[1].x * videoStore.videoSize.width +
                'px'
              "
              :y2="
                (isVideoFullscreen ? videoStore.videoSize.top : 0) +
                o[1].y * videoStore.videoSize.height +
                'px'
              "
              stroke-width="3"
              stroke="blue"
              fill="none"
              style="pointer-events: none"
            />

            <path
              v-if="o.length > 2"
              v-show="calibrationAssetStore.showVideoAsset"
              :key="o.id"
              :d="
                (() => {
                  const points = o.map((p) => ({
                    x:
                      (isVideoFullscreen ? videoStore.videoSize.left : 0) +
                      p.x * videoStore.videoSize.width,
                    y:
                      (isVideoFullscreen ? videoStore.videoSize.top : 0) +
                      p.y * videoStore.videoSize.height,
                  }));
                  let d = `M ${points[0].x} ${points[0].y}`;
                  for (let i = 1; i < points.length; i++) {
                    d += ` L ${points[i].x} ${points[i].y}`;
                  }
                  return d;
                })()
              "
              stroke="blue"
              stroke-width="3"
              fill="none"
              style="pointer-events: none"
            />
          </template>
        </svg>
      </div>
    </v-row>

    <ModalBBoxUpdate v-model="editDialog" :bbox="editBBox" />

    <v-row ref="videoControl" class="video-control mt-6">
      <v-btn @click="deltaSeek(-1)" size="small">
        <v-icon>mdi-skip-backward</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(-(1 / playerStore.videoFPS))" size="small">
        <v-icon>mdi-skip-previous</v-icon>
      </v-btn>

      <v-btn @click="togglePlaying" size="small">
        <v-icon v-if="videoEnded">mdi-restart</v-icon>
        <v-icon v-else-if="videoPlaying">mdi-pause</v-icon>
        <v-icon v-else>mdi-play</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(1 / playerStore.videoFPS)" size="small">
        <v-icon> mdi-skip-next</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(1)" size="small">
        <v-icon> mdi-skip-forward</v-icon>
      </v-btn>

      <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
        {{ getTimecode(playerStore.currentTime) }}
      </div>

      <v-menu offset-y top>
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ currentSpeed.title }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item v-for="(item, index) in speeds" :key="item" class="speed-item">
            <v-list-item-title v-on:click="onSpeedChange(index)">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn @click="playerStore.toggleMute" size="small">
        <v-icon>{{ playerStore.isMuted ? "mdi-volume-mute" : playerStore.volumeIcon }}</v-icon>
      </v-btn>

      <div style="width: 13%; min-width: 80px">
        <v-slider
          v-model="playerStore.volume"
          @update:model-value="playerStore.changeVolume"
          max="100"
          min="0"
          hide-details
          color="primary"
          :thumb-size="15"
        />
      </div>
    </v-row>

    <v-row ref="videoSlider">
      <v-slider
        v-model="progress"
        @update:model-value="onProgressChange"
        hide-details
        color="primary"
        :thumb-size="15"
        :step="1000 / playerStore.videoFPS"
        min="0"
        :max="playerStore.videoDuration"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useBboxesStore } from "@/stores/bboxes";
import { useVisualizationStore } from "@/stores/visualization";
import { getTimecode } from "@/plugins/time";
import ModalBBoxUpdate from "./ModalBboxUpdate.vue";
import { toRgb } from "@/plugins/helpers";
import Hls from "hls.js";

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
const visualizationStore = useVisualizationStore();

const videoContainer = ref(null);
const videoElement = ref(null);
onMounted(() => {
  if (videoElement.value) playerStore.videoElement = videoElement.value;
});

const onTimeUpdate = (event) => {
  const videoTimeMs = Math.round(event.target.currentTime * 1000);
  const frameKeys = [];
  for (let t = 0; t <= playerStore.videoDuration * 1000; t += 1000 / playerStore.videoFPS) {
    frameKeys.push(Math.round(t));
  }
  const closestFrame = frameKeys.reduce(
    (prev, curr) => (Math.abs(curr - videoTimeMs) < Math.abs(prev - videoTimeMs) ? curr : prev),
    frameKeys[0]
  );

  playerStore.setCurrentTime(closestFrame);
};
const deltaSeek = (delta) => {
  if (videoElement.value) {
    const newTime = videoElement.value.currentTime + delta;
    playerStore.setCurrentTime(newTime * 1000);
    videoElement.value.currentTime = newTime;
  }
};

const targetTime = computed(() => playerStore.targetTime);
const onProgressChange = (time) => {
  if (videoElement.value) {
    const targetTime = Math.round(time);
    progress.value = targetTime;
    playerStore.setCurrentTime(targetTime);
    videoElement.value.currentTime = targetTime / 1000;
  }
};
watch(targetTime, (newTargetTime) => {
  if (videoElement.value) {
    playerStore.currentTime = Math.round(newTargetTime);
  }
});

let updateTimer = null;
const startUpdatingTime = () => {
  if (updateTimer) clearInterval(updateTimer);

  const interval = 1 / (playerStore.videoFPS * 1000);

  updateTimer = setInterval(() => {
    if (videoElement.value) {
      playerStore.setCurrentTime(Math.round(videoElement.value.currentTime * 1000));
    }
  }, interval);
};
const stopUpdatingTime = () => {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
  }
};
onMounted(() => {
  startUpdatingTime();
});
onBeforeUnmount(() => {
  stopUpdatingTime();
});
watch(
  () => playerStore.playing,
  (isPlaying) => {
    if (isPlaying) {
      startUpdatingTime();
    } else {
      stopUpdatingTime();
    }
  }
);

const onPlay = () => {
  startUpdatingTime();
  playerStore.setEnded(false);
  playerStore.setPlaying(true);
};
const onPause = () => {
  stopUpdatingTime();
  playerStore.setPlaying(false);
};
const onEnded = () => {
  stopUpdatingTime();
  playerStore.setPlaying(false);
  playerStore.setEnded(true);
};

const progress = ref(0);
watch(
  () => playerStore.currentTime,
  (newTime) => {
    progress.value = newTime;
  }
);

watch(
  () => playerStore.volume,
  () => {
    if (playerStore.videoElement) {
      playerStore.videoElement.volume = playerStore.volume / 100;
    }
  }
);

const videoEnded = computed(() => playerStore.ended);
const videoPlaying = computed(() => playerStore.playing);
const togglePlaying = () => playerStore.togglePlaying();
watch(videoPlaying, (isPlaying) => {
  if (videoElement.value) {
    isPlaying ? videoElement.value.play() : videoElement.value.pause();
  }
});

const currentSpeed = ref({ title: "1.00", value: 1.0 });
const speeds = [
  { title: "0.25", value: 0.25 },
  { title: "0.50", value: 0.5 },
  { title: "0.75", value: 0.75 },
  { title: "1.00", value: 1.0 },
  { title: "1.25", value: 1.25 },
  { title: "1.50", value: 1.5 },
  { title: "1.75", value: 1.75 },
  { title: "2.00", value: 2.0 },
];
const onSpeedChange = (idx) => {
  currentSpeed.value = speeds[idx];
  if (videoElement.value) {
    videoElement.value.playbackRate = currentSpeed.value.value;
  }
};

const updateVideoSize = () => {
  nextTick(() => {
    if (videoElement.value) {
      const rect = videoElement.value.getBoundingClientRect();
      videoStore.setVideoSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  });
};
onMounted(() => {
  updateVideoSize();
  window.addEventListener("resize", updateVideoSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateVideoSize);
});
watch(
  () => calibrationAssetStore.isAnyReferenceObjectActive,
  async (newVal) => {
    if (!newVal) {
      await nextTick();
      updateVideoSize();
    }
  }
);

const videoSlider = ref(null);
const videoControl = ref(null);
const maxVideoHeight = ref(0);
const updateMaxHeight = () => {
  if (!videoSlider.value || !videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight -
      104 -
      32 -
      videoSlider.value.$el.offsetHeight -
      videoControl.value.$el.offsetHeight -
      60) /
    window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);

const editDialog = ref(false);
const editBBox = ref(null);
function openEditBBox(bbox) {
  editBBox.value = bbox;
  editDialog.value = true;
}

const currentFrameKey = computed(() => {
  return Object.keys(bboxesStore.bboxDataInterpolated)
    .map(Number)
    .sort((a, b) => a - b)
    .reduce(
      (prev, key) => (key <= playerStore.currentTime ? key : prev),
      Object.keys(bboxesStore.bboxDataInterpolated)[0]
    );
});

const hovering = ref(false);
const videoDiv = ref(null);
const isVideoFullscreen = ref(false);
const toggleVideoFullscreen = () => {
  const div = videoDiv.value;
  if (!document.fullscreenElement) {
    div.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
};
const onFullscreenChange = () => {
  const isVideoFullscreenPrev = isVideoFullscreen.value;
  isVideoFullscreen.value = document.fullscreenElement === videoDiv.value;

  if (isVideoFullscreenPrev === true || isVideoFullscreen.value === true) {
    updateVideoSize();
  }
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

const getEllipseSvg = (position) => {
  const x = position[6];
  const y = position[7];
  const w = position[8];
  const h = position[9];

  const vid = videoStore.videoSize;

  const color = visualizationStore.getTeamColor(position[1]);

  // via SoccerNet
  const ellipseWidth = w * vid.width;
  const ellipseHeight = ellipseWidth * 0.35;

  const centerX = (x + w / 2) * vid.width + (isVideoFullscreen.value ? vid.left : 0);
  const centerY =
    (y + h) * vid.height +
    (isVideoFullscreen.value ? vid.top : 0) -
    ellipseHeight * (0.1 + (1 - (y + h)) * 1.5);

  const left = centerX - ellipseWidth;
  const top = centerY - ellipseHeight;

  const rx = ellipseWidth;
  const ry = ellipseHeight;

  const startAngle = (-45 * Math.PI) / 180;
  const endAngle = (235 * Math.PI) / 180;

  const sx = rx + rx * Math.cos(startAngle);
  const sy = ry + ry * Math.sin(startAngle);

  const ex = rx + rx * Math.cos(endAngle);
  const ey = ry + ry * Math.sin(endAngle);

  const arcPath = `M ${sx},${sy} A ${rx} ${ry} 0 1 1 ${ex},${ey}`;

  return {
    style: {
      position: "absolute",
      left: left + "px",
      top: top + "px",
      width: ellipseWidth * 2 + "px",
      height: ellipseHeight * 2 + "px",
      overflow: "visible",
      zIndex: 12,
      cursor: isVideoFullscreen.value ? "default" : "pointer",
    },
    arc: arcPath,
    color,
    centerX,
    centerY,
  };
};

function tarGzUrlToHlsUrl(tarUrl) {
  const url = new URL(tarUrl);

  // Dateiname extrahieren
  const parts = url.pathname.split("/");
  const fileName = parts.pop(); // <hash>.tar.gz
  const id = fileName.replace(/\.tar\.gz$/, "");

  // Neuer Pfad
  parts.push(id, `${id}.m3u8`);
  url.pathname = parts.join("/");

  return url.toString();
}
let hls = null;
watch(
  () => playerStore.videoUrl,
  (url) => {
    if (!url || !videoElement.value) return;

    const video = videoElement.value;
    const hlsUrl = tarGzUrlToHlsUrl(url);
    console.log("hls url", hlsUrl);

    if (!hlsUrl) return;

    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 30,
        maxBufferLength: 5,
        maxMaxBufferLength: 60,
      });

      hls.loadSource(hlsUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        updateVideoSize();
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari
      video.src = hlsUrl;
    }
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  if (hls) {
    hls.destroy();
    hls = null;
  }
});
</script>

<style scoped>
.video-control {
  gap: 5px;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
}

.speed-item {
  cursor: pointer;
}

.speed-item:hover {
  background-color: #f0f0f0;
}

.bounding-box-tooltip ::v-deep(.v-overlay__content) {
  background-color: var(--tooltip-bg);
  border-radius: 2px;
  font-size: 0.7rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
  padding: 5px 10px;
  color: #222;
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

.bounding-box-player-id-old {
  position: absolute;
  left: 50%;
  bottom: -20px;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}

.bounding-box-player-id {
  position: absolute;
  left: 50%;
  bottom: -25px;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}

.video-wrapper {
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
  bottom: 0;
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

.fullscreen-controls .controls-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fullscreen-controls .control-icon {
  color: white;
  font-size: 28px;
  cursor: pointer;
}

.fullscreen-controls .time-code {
  color: white;
  font-size: 0.9rem;
  font-weight: 500;
}

.player-ellipse {
  width: 100%;
  height: 100%;
}
</style>
