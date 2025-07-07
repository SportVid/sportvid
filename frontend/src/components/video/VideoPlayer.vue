<template>
  <v-container ref="videoContainer" class="d-flex flex-column">
    <v-row justify="center">
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
      <!-- <div
        v-for="(position, index) in bboxesStore.bboxData.filter((p) => p.time === playerStore.currentTime)"
        v-show="playerStore.showBoundingBox"
        :key="index"
        class="bounding-box-position"
        :style="{
          top: position.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: position.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          width: position.w * videoStore.videoSize.width + 'px',
          height: position.h * videoStore.videoSize.height + 'px',
          border: `2px solid red`,
        }"
      /> -->
      <div
        v-for="position in bboxesStore.bboxDataInterpolated[playerStore.currentTime]"
        v-show="playerStore.showBoundingBox"
        :key="position.id"
        class="bounding-box-position"
        :style="{
          top: position.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: position.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          width: position.w * videoStore.videoSize.width + 'px',
          height: position.h * videoStore.videoSize.height + 'px',
          border: `2px solid red`,
        }"
        @click="openEditBBox(position)"
      >
        <v-tooltip activator="parent" location="top" class="bounding-box-tooltip">
          <!-- <div><strong>ref_id:</strong> {{ position.ref_id }}</div>
          <div><strong>team_id:</strong> red</div> -->
          <div v-for="(value, key) in position" :key="key">
            <strong>{{ key }}:</strong> {{ value }}
          </div>
        </v-tooltip>
        <div class="bounding-box-ref-id">
          {{ position.ref_id }}
        </div>
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
        :step="100 / (playerStore.videoFPS * playerStore.videoDuration)"
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

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();

const videoContainer = ref(null);
const videoElement = ref(null);
onMounted(() => {
  if (videoElement.value) playerStore.videoElement = videoElement.value;
});

// const throttledUpdateTime = throttle((currentTime) => {
//   playerStore.setCurrentTime(playerStore.roundTimeToFPS(currentTime, playerStore.videoFPS));
// }, 40);
let animationFrameId = null;
const throttledUpdateTime = throttle((currentTime) => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
  animationFrameId = requestAnimationFrame(() => {
    playerStore.setCurrentTime(playerStore.roundTimeToFPS(currentTime, playerStore.videoFPS));
  });
}, (1 / playerStore.videoFPS) * 1000);
const onTimeUpdate = (event) => {
  throttledUpdateTime(event.target.currentTime);
  playerStore.setEnded(event.target.ended);
};
// const onTimeUpdate = (event) => {
//   playerStore.setCurrentTime(
//     playerStore.roundTimeToFPS(event.target.currentTime, playerStore.videoFPS)
//   );
//   playerStore.setEnded(event.target.ended);
// };
const deltaSeek = (delta) => {
  if (videoElement.value) {
    const newTime = videoElement.value.currentTime + delta;
    playerStore.setCurrentTime(newTime);
    videoElement.value.currentTime = newTime;
  }
};

const targetTime = computed(() => playerStore.targetTime);
const onProgressChange = (percentage) => {
  if (videoElement.value) {
    const targetTime = playerStore.roundTimeToFPS(
      (playerStore.videoDuration * percentage) / 100,
      playerStore.videoFPS
    );
    playerStore.setCurrentTime(targetTime);
    videoElement.value.currentTime = targetTime;
  }
};
watch(targetTime, (newTargetTime) => {
  if (videoElement.value) {
    const roundedTargetTime = playerStore.roundTimeToFPS(newTargetTime, playerStore.videoFPS);
    playerStore.currentTime = roundedTargetTime;
  }
});

let updateTimer = null;
const startUpdatingTime = () => {
  if (updateTimer) clearInterval(updateTimer);

  const interval = (1 / playerStore.videoFPS) * 1000;

  updateTimer = setInterval(() => {
    if (videoElement.value) {
      playerStore.setCurrentTime(
        playerStore.roundTimeToFPS(videoElement.value.currentTime, playerStore.videoFPS)
      );
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
    progress.value = (newTime / playerStore.videoDuration) * 100;
  }
);
watch(progress, (newProgress) => {
  if (videoElement.value) {
    const newTime = (playerStore.videoDuration * newProgress) / 100;
    playerStore.setCurrentTime(playerStore.roundTimeToFPS(newTime, playerStore.videoFPS));
  }
});

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

// const syncTime = computed(() => playerStore.syncTime);
// const toggleSyncTime = () => playerStore.toggleSyncTime();

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
  window.addEventListener("scroll", updateVideoSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateVideoSize);
  window.removeEventListener("scroll", updateVideoSize);
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
function updateBBox({ ref_id, team_id, updateAllRefId, updateAllTeamId }) {
  if (!editBBox.value) return;

  let allBboxes = null;
  if (updateAllRefId || updateAllTeamId) {
    allBboxes = [];
    Object.values(bboxesStore.bboxDataInterpolated).forEach((arr) => {
      if (Array.isArray(arr)) allBboxes.push(...arr);
    });
  }

  if (updateAllRefId && allBboxes) {
    const oldRefId = String(editBBox.value.ref_id);
    allBboxes.forEach((bbox) => {
      if (String(bbox.ref_id) === oldRefId) bbox.ref_id = ref_id;
    });
  } else {
    editBBox.value.ref_id = ref_id;
  }

  if (updateAllTeamId && allBboxes) {
    const oldTeamId = String(editBBox.value.team_id);
    allBboxes.forEach((bbox) => {
      if (String(bbox.team_id) === oldTeamId) bbox.team_id = team_id;
    });
  } else {
    editBBox.value.team_id = team_id;
  }
}
function updateBBoxBackend({ ref_id, team_id, updateAllRefId, updateAllTeamId }) {
  if (!editBBox.value) return;

  const bboxes = bboxesStore.bboxData;

  if (updateAllRefId) {
    const oldRefId = String(editBBox.value.ref_id);
    bboxes.forEach((bbox) => {
      if (String(bbox.ref_id) === oldRefId) bbox.ref_id = ref_id;
    });
  } else {
    const bbox = bboxes.find(
      (b) =>
        String(b.ref_id) === String(editBBox.value.ref_id) &&
        String(b.image_id) === String(editBBox.value.image_id)
    );
    if (bbox) bbox.ref_id = ref_id;
  }

  if (updateAllTeamId) {
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

.bounding-box-position {
  position: fixed;
  z-index: 1000;
}

.bounding-box-tooltip ::v-deep .v-overlay__content {
  background: rgb(var(--v-theme-primary));
  border-radius: 2px;
  font-size: 0.7rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
  padding: 5px 10px;
  color: #fff;
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

.bounding-box-ref-id {
  position: absolute;
  left: 50%;
  bottom: -20px;
  transform: translateX(-50%);
  color: red;
  font-size: 0.8rem;
  pointer-events: none;
  z-index: 1100;
}
</style>
