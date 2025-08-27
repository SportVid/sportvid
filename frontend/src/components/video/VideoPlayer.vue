<template>
  <v-container ref="videoContainer" class="d-flex flex-column">
    <v-row justify="center">
      <div style="position: relative; display: inline-block">
        <video
          class="video"
          ref="videoElement"
          @play="onPlay"
          @pause="onPause"
          @ended="onEnded"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="updateVideoSize"
          :src="playerStore.videoUrl"
          :style="{
            maxHeight: maxVideoHeight * 100 + 'vh',
          }"
        />
        <div
          v-for="position in bboxesStore.bboxDataInterpolated[playerStore.currentTime]"
          v-show="playerStore.showBoundingBox"
          :key="position"
          :style="{
            position: 'absolute',
            top: position[6] * videoStore.videoSize.height + 'px',
            left: position[5] * videoStore.videoSize.width + 'px',
            width: position[7] * videoStore.videoSize.width + 'px',
            height: position[8] * videoStore.videoSize.height + 'px',
            border: `2px solid ${position[1]}`,
          }"
          @click="openEditBBox(position)"
        >
          <v-tooltip
            activator="parent"
            location="top"
            class="bounding-box-tooltip"
            :style="{ '--tooltip-bg': toRgb(position[1], 0.7) }"
            interactive
          >
            <div>
              <!-- <div><strong>player_id:</strong> {{ position[0] }}</div>
            <div><strong>team_id:</strong> {{ position[1] }}</div> -->
              <div v-for="(value, index) in position" :key="key">
                <strong>{{ labels[index] }}:</strong> {{ value }}
              </div>
            </div>
          </v-tooltip>
          <div class="bounding-box-player-id" :style="{ color: position[1] }">
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

    <ModalBBoxUpdate v-model="editDialog" :bbox="editBBox" @update="updateBBox" />

    <v-row ref="videoControl" class="video-control mt-6">
      <v-btn @click="deltaSeek(-1)" size="small">
        <v-icon>mdi-skip-backward</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(-(1 / playerStore.videoFPS))" size="small">
        <v-icon>mdi-skip-previous</v-icon>
      </v-btn>

      <v-btn @click="toggle" size="small">
        <v-icon v-if="ended">mdi-restart</v-icon>
        <v-icon v-else-if="playing">mdi-pause</v-icon>
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
import { throttle } from "lodash";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useBboxesStore } from "@/stores/bboxes";
import { getTimecode } from "@/plugins/time";
import ModalBBoxUpdate from "./ModalBboxUpdate.vue";
import { toRgb } from "@/plugins/helpers";

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();

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

let animationFrameId = null;
const throttledUpdateTime = throttle((currentTime) => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
  animationFrameId = requestAnimationFrame(() => {
    playerStore.setCurrentTime(Math.round(currentTime * 1000));
  });
}, 1 / playerStore.videoFPS);
const onTimeUpdate = (event) => {
  throttledUpdateTime(event.target.currentTime);
  playerStore.setEnded(event.target.ended);
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

const ended = computed(() => playerStore.ended);
const playing = computed(() => playerStore.playing);
const toggle = () => playerStore.togglePlaying();
watch(playing, (isPlaying) => {
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
function updateBBox({ player_id, team_id, updateSamePlayerId, updateSameTeamId }) {
  if (!editBBox.value) return;

  let allBboxes = null;
  if (updateSamePlayerId || updateSameTeamId) {
    allBboxes = [];
    Object.values(bboxesStore.bboxDataInterpolated).forEach((arr) => {
      if (Array.isArray(arr)) allBboxes.push(...arr);
    });
  }

  if (updateSamePlayerId && allBboxes) {
    const oldPlayerId = String(editBBox.value.player_id);
    allBboxes.forEach((bbox) => {
      if (String(bbox.player_id) === oldPlayerId) bbox.player_id = player_id;
    });
  } else {
    editBBox.value.player_id = player_id;
  }

  if (updateSameTeamId && allBboxes) {
    const oldTeamId = String(editBBox.value.team_id);
    allBboxes.forEach((bbox) => {
      if (String(bbox.team_id) === oldTeamId) bbox.team_id = team_id;
    });
  } else {
    editBBox.value.team_id = team_id;
  }
}
function updateBBoxBackend({ player_id, team_id, updateSamePlayerId, updateSameTeamId }) {
  if (!editBBox.value) return;

  const bboxes = bboxesStore.bboxDataActive;

  if (updateSamePlayerId) {
    const oldPlayerId = String(editBBox.value.player_id);
    bboxes.forEach((bbox) => {
      if (String(bbox.player_id) === oldPlayerId) bbox.player_id = player_id;
    });
  } else {
    const bbox = bboxes.find(
      (b) =>
        String(b.player_id) === String(editBBox.value.player_id) &&
        String(b.image_id) === String(editBBox.value.image_id)
    );
    if (bbox) bbox.player_id = player_id;
  }

  if (updateSameTeamId) {
    const oldTeamId = String(editBBox.value.team_id);
    bboxes.forEach((bbox) => {
      if (String(bbox.team_id) === oldTeamId) bbox.team_id = team_id;
    });
  } else {
    const bbox = bboxes.find(
      (b) =>
        String(b.team_id) === String(editBBox.value.team_id) &&
        String(b.image_id) === String(editBBox.value.image_id)
    );
    if (bbox) bbox.team_id = team_id;
  }

  // Nach Änderung: Interpolierte Daten neu berechnen
  const _bboxDataInterpolated = bboxesStore.interpolateBboxData(bboxes, playerStore.videoFPS, 30);
  bboxesStore.bboxDataInterpolated = groupDataByTime(_bboxDataInterpolated);

  // Backend-Update -> siehe calibrationAssetStore.updateCalibrationAsset
}
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
</style>
