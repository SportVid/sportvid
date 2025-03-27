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
        v-for="(position, index) in markerStore.positionsNested[sliderValue]"
        v-show="bboxesStore.showBoundingBox"
        :key="index"
        class="bounding-box-position"
        :style="{
          top: position.bbox_top * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: position.bbox_left * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          width: position.bbox_width * videoStore.videoSize.width + 'px',
          height: position.bbox_height * videoStore.videoSize.height + 'px',
          border: `2px solid ${position.team}`,
        }"
      /> -->
      <div
        v-for="(position, index) in bboxData.filter((p) => p.time === playerStore.currentTime)"
        v-show="bboxesStore.showBoundingBox"
        :key="index"
        class="bounding-box-position"
        :style="{
          top: position.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: position.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          width: position.w * videoStore.videoSize.width + 'px',
          height: position.h * videoStore.videoSize.height + 'px',
          border: `2px solid red`,
        }"
      />
    </v-row>

    <v-row ref="videoControl" class="video-control mt-6">
      <v-btn @click="deltaSeek(-1)" size="small">
        <v-icon>mdi-skip-backward</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(-(1 / playerStore.videoFPS))" size="small">
        <v-icon>mdi-skip-previous</v-icon>
      </v-btn>

      <v-btn @click="toggle" size="small">
        <v-icon v-if="ended"> mdi-restart</v-icon>
        <v-icon v-else-if="playing"> mdi-pause</v-icon>
        <v-icon v-else> mdi-play</v-icon>
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
        {{ getTimecode(currentTime) }}
      </div>

      <v-menu offset-y top>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ currentSpeed.title }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item v-for="(item, index) in speeds" :key="index" class="speed-item">
            <v-list-item-title v-on:click="onSpeedChange(index)">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn @click="onToggleVolume" size="small">
        <v-icon v-if="volume > 66">mdi-volume-high</v-icon>
        <v-icon v-else-if="volume > 33">mdi-volume-medium</v-icon>
        <v-icon v-else-if="volume > 0">mdi-volume-low</v-icon>
        <v-icon v-else-if="volume == 0">mdi-volume-mute</v-icon>
      </v-btn>

      <div style="width: 13%; min-width: 80px">
        <v-slider
          v-model="volume"
          @update:model-value="onVolumeChange"
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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useMarkerStore } from "@/stores/marker";
import { useBboxesStore } from "@/stores/bboxes";
import { getTimecode } from "@/plugins/time";

const videoElement = ref(null);
const videoContainer = ref(null);

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const markerStore = useMarkerStore();
const bboxesStore = useBboxesStore();

const volume = ref(playerStore.volume);
const ended = computed(() => playerStore.ended);
const currentTime = computed(() => playerStore.currentTime);
const duration = computed(() => playerStore.videoDuration);
const syncTime = computed(() => playerStore.syncTime);
const playing = computed(() => playerStore.playing);
const targetTime = computed(() => playerStore.targetTime);

const progress = ref(0);
const bboxData = ref([]);
let updateTimer = null;

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

const deltaSeek = (delta) => {
  if (videoElement.value) {
    const newTime = videoElement.value.currentTime + delta;
    playerStore.setCurrentTime(newTime);
    videoElement.value.currentTime = newTime;
  }
};

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

const onTimeUpdate = (event) => {
  playerStore.setCurrentTime(
    playerStore.roundTimeToFPS(event.target.currentTime, playerStore.videoFPS)
  );

  playerStore.setEnded(event.target.ended);
};

const onProgressChange = (percentage) => {
  if (videoElement.value) {
    const targetTime = playerStore.roundTimeToFPS(
      (playerStore.videoDuration * percentage) / 100,
      playerStore.videoFPS
    );
    playerStore.currentTime = targetTime;
    videoElement.value.currentTime = targetTime;
  }
};

const onSpeedChange = (idx) => {
  currentSpeed.value = speeds[idx];
  if (videoElement.value) {
    videoElement.value.playbackRate = currentSpeed.value.value;
  }
};

const onVolumeChange = (newVolume) => playerStore.setVolume(newVolume);

const toggle = () => playerStore.togglePlaying();
const toggleSyncTime = () => playerStore.toggleSyncTime();
const onToggleVolume = () => playerStore.toggleMute();

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

const updateVideoSize = () => {
  nextTick(() => {
    if (videoElement.value) {
      const rect = videoElement.value.getBoundingClientRect();
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

const handleResize = () => {
  updateVideoSize();
};

onMounted(() => {
  updateVideoSize();
  startUpdatingTime();
  nextTick(() => {
    bboxData.value = bboxesStore.bboxData.filter(
      (position) => position.time === playerStore.currentTime
    );
  });
  window.addEventListener("resize", handleResize);
  window.addEventListener("scroll", handleResize);
});

onUnmounted(() => {
  stopUpdatingTime();
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("scroll", handleResize);
});

watch(playing, (isPlaying) => {
  if (videoElement.value) {
    if (isPlaying) {
      videoElement.value.volume = volume.value / 100;
      videoElement.value.play();
    } else {
      videoElement.value.pause();
    }
  }
});

watch(volume, (newVolume) => {
  if (videoElement.value) {
    videoElement.value.volume = newVolume / 100;
  }
});

watch(
  () => markerStore.isAnyMarkerActive,
  async (newVal) => {
    if (!newVal) {
      await nextTick();
      updateVideoSize();
    }
  }
);

watch(targetTime, (newTargetTime) => {
  if (videoElement.value) {
    const roundedTargetTime = playerStore.roundTimeToFPS(newTargetTime, playerStore.videoFPS);
    playerStore.currentTime = roundedTargetTime;
  }
});

watch(
  () => playerStore.currentTime,
  (newTime) => {
    progress.value = (newTime / playerStore.videoDuration) * 100;
    nextTick(() => {
      bboxData.value = bboxesStore.bboxData.filter((position) => position.time === newTime);
    });
  }
);

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

watch(progress, (newProgress) => {
  if (videoElement.value) {
    const newTime = (playerStore.videoDuration * newProgress) / 100;
    playerStore.setCurrentTime(newTime);
  }
});

const maxVideoHeight = ref(0);
const videoSlider = ref(null);
const videoControl = ref(null);

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

watch(() => window.innerHeight, updateMaxHeight);
</script>

<style>
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
</style>
