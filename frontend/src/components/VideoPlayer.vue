<template>
  <v-container class="d-flex flex-column">
    <v-row ref="videoContainer">
      <video
        class="video-video"
        ref="videoElement"
        v-on:play="onPlay"
        v-on:pause="onPause"
        v-on:ended="onEnded"
        v-on:canplay="onCanPlay"
        v-on:loadeddata="onLoadedData"
        v-on:timeupdate="onTimeUpdate"
        @loadedmetadata="updateVideoSize"
        :src="playerStore.videoUrl"
      />

      <!-- <div
        v-for="(position, index) in markerStore.positionsNested[sliderValue]"
        v-show="markerStore.showBoundingBox"
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
      <!-- <div
        v-for="(position, index) in markerStore.positionsFlat.filter(
          (p) => p.image_id === sliderValue
        )"
        v-show="markerStore.showBoundingBox"
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
      <!-- <div
        v-for="(position, index) in bboxes.value.filter((p) => p.image_id === sliderValue)"
        v-show="markerStore.showBoundingBox"
        :key="index"
        class="bounding-box-position"
        :style="{
          top: position.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: position.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          width: position.w * videoStore.videoSize.width + 'px',
          height: position.h * videoStore.videoSize.height + 'px',
          border: `2px solid ${position.team}`,
        }"
      /> -->
    </v-row>

    <v-row class="video-control mt-6">
      <v-btn @click="deltaSeek(-1)" size="small">
        <v-icon>mdi-skip-backward</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(-0.01)" size="small">
        <v-icon>mdi-skip-previous</v-icon>
      </v-btn>

      <v-btn @click="toggle" size="small">
        <v-icon v-if="ended"> mdi-restart</v-icon>
        <v-icon v-else-if="playing"> mdi-pause</v-icon>
        <v-icon v-else> mdi-play</v-icon>
      </v-btn>

      <v-btn @click="deltaSeek(0.01)" size="small">
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

    <v-row>
      <v-slider
        v-model="progress"
        @update:model-value="onSeek"
        hide-details
        color="primary"
        :thumb-size="15"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick, onBeforeUnmount } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useMarkerStore } from "@/stores/marker";
import { useBBoxesStore } from "@/stores/bboxes";
import { getTimecode } from "@/plugins/time";

const emit = defineEmits();

const videoElement = ref(null);
const videoContainer = ref(null);

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const markerStore = useMarkerStore();
const bboxesStore = useBBoxesStore();

const volume = computed(() => playerStore.volume);
const ended = computed(() => playerStore.ended);
const currentTime = computed(() => playerStore.currentTime);
const duration = computed(() => playerStore.videoDuration);
const syncTime = computed(() => playerStore.syncTime);
const playing = computed(() => playerStore.playing);
const targetTime = computed(() => playerStore.targetTime);

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

const toggle = () => playerStore.togglePlaying();
const toggleSyncTime = () => playerStore.toggleSyncTime();

const deltaSeek = (delta) => {
  if (videoElement.value) {
    const newTime = videoElement.value.currentTime + delta;
    playerStore.setCurrentTime(newTime);
    videoElement.value.currentTime = newTime;
  }
};

const onEnded = () => {
  playerStore.setEnded(true);
  playerStore.setPlaying(false);
};

const onPause = () => {
  playerStore.setPlaying(false);
};

const onPlay = () => {
  playerStore.setEnded(false);
  playerStore.setPlaying(true);
};

const onTimeUpdate = (event) => {
  playerStore.setCurrentTime(event.target.currentTime);
  playerStore.setEnded(event.target.ended);
};

const onSeek = (percentage) => {
  if (videoElement.value) {
    const targetTime = (duration.value * percentage) / 100;
    videoElement.value.currentTime = targetTime;
  }
};

const onSpeedChange = (idx) => {
  currentSpeed.value = speeds[idx];
  if (videoElement.value) {
    videoElement.value.playbackRate = currentSpeed.value.value;
  }
};

const onToggleVolume = () => playerStore.toggleMute();
const onVolumeChange = (newVolume) => playerStore.setVolume(newVolume);

const onLoadedData = () => {
  emit("loadedData");
};

const onCanPlay = () => {
  emit("canPlay");
};

const progress = computed(() => {
  if (duration.value <= 0) return 0;
  return (playerStore.currentTime / playerStore.videoDuration) * 100;
});

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

const currentFrame = ref(0);
const updateFrame = (newIndex) => {
  currentFrame.value = newIndex;
};
const sliderValue = computed({
  get: () => {
    return Math.round(currentTime.value);
  },
  set: (value) => {
    currentFrame.value = value;
    updateFrame(value);
  },
});

onMounted(() => {
  updateVideoSize();
  window.addEventListener("resize", handleResize);
  window.addEventListener("scroll", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("scroll", handleResize);
});

// in bboxes store get bboxData element
// watch(
//   () => bboxesStore.bboxData,
//   async (hasNewBboxData) => {
//     if (hasNewBboxData) {
//       const allBboxes = bboxesStore.bboxData?.[0]?.results?.[0]?.data?.bboxes;
//       console.log("New bbox data", allBboxes);
//     }
//   }
// );
const bboxes = computed(() => {
  return bboxesStore.bboxData?.[0]?.results?.[0]?.data?.bboxes;
});

onMounted(() => {
  if (bboxes.value) {
    console.log("test_value", bboxes.value);
  } else {
    console.log("Bboxes are not available yet.");
  }
});

// watch(progress, (newProgress) => {
//   progress.value = newProgress;
//   emit("update-slider", newProgress);
// });
// watch(progress, (newProgress) => {
//   if (playerStore.isSynced) {
//     const newTime = (playerStore.videoDuration * newProgress) / 100;
//     playerStore.setCurrentTime(newTime);
//   }
// });

// watch(() => playerStore.currentTime, (newTime) => {
//   if (!playerStore.isSynced) {
//     const newProgress = (newTime / playerStore.videoDuration) * 100;
//     progress.value = newProgress;
//   }
// });

watch(targetTime, (newTargetTime) => {
  const delta = 1 / playerStore.videoFPS;
  if (syncTime.value && videoElement.value) {
    videoElement.value.currentTime = newTargetTime + delta;
  }
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
</script>

<style>
.video-video {
  width: 100%;
  object-fit: cover;
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
