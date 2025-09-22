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
          class="video"
          ref="videoElement"
          @play="onPlay"
          @pause="onPause"
          @ended="onEnded"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="updateVideoSize"
          :src="playerStore.videoUrl"
          :style="
            isVideoFullscreen
              ? { width: '100%', height: '100%', objectFit: 'contain' }
              : { maxHeight: maxVideoHeight * 100 + 'vh' }
          "
        />

        <v-icon
          class="fullscreen-toggle"
          @click="toggleVideoFullscreen"
          :class="{ visible: hovering }"
        >
          {{ isVideoFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
        </v-icon>

        <!-- Fullscreen Controls -->
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

        <div
          v-for="position in bboxesStore.bboxDataInterpolated[currentFrameKey]"
          v-show="bboxesStore.showBoundingBox"
          :key="position"
          :style="{
            position: 'absolute',
            top: position[7] * videoStore.videoSize.height + 'px',
            left: position[6] * videoStore.videoSize.width + 'px',
            width: position[8] * videoStore.videoSize.width + 'px',
            height: position[9] * videoStore.videoSize.height + 'px',
            border: `2px solid ${visualizationStore.getTeamColor(position[1])}`,
          }"
          @click="openEditBBox(position)"
        >
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
            :style="{ color: visualizationStore.getTeamColor(position[1]) }"
          >
            {{ position[0] }}
          </div>
        </div>

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

      <!-- <v-btn @click="toggleSyncTime()" size="small">
        <v-icon v-if="syncTime"> mdi-link</v-icon>
        <v-icon v-else> mdi-link-off</v-icon>
      </v-btn> -->

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

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
const visualizationStore = useVisualizationStore();

const labels = [
  "player_id",
  "team_id",
  "game_section",
  "pos_x",
  "pos_y",
  "x_norm",
  "y_norm",
  "w_norm",
  "h_norm",
  "det_score",
];

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
  () => calibrationAssetStore.isAnyReferenceMarkerActive,
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
  isVideoFullscreen.value = document.fullscreenElement === videoDiv.value;
  updateVideoSize();
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});
</script>

<style scoped>
.video {
  object-fit: cover;
  max-width: 100%;
}
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

.bounding-box-tooltip ::v-deep .v-overlay__content {
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

.bounding-box-player-id {
  position: absolute;
  left: 50%;
  bottom: -20px;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}

.video-wrapper {
  position: relative;
  display: inline-block;
}

.fullscreen-toggle {
  position: absolute;
  top: 12px;
  right: 12px;
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

.fullscreen-toggle {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 11;
}
</style>
