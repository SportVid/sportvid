<template>
  <v-container class="d-flex flex-column">
    <v-row ref="videocontainer" class="video-container">
      <video 
        controls
        class="video-player" 
        ref="video"
        :src="playerStore.videoUrl"
      >
        <!-- <source src="" type="video/mp4" /> -->
      </video>
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
      <v-btn @click="toggleSyncTime()" size="small">
        <v-icon v-if="syncTime"> mdi-link</v-icon>
        <v-icon v-else> mdi-link-off</v-icon>
      </v-btn>
      <div class="time-code flex-grow-1 flex-shrink-0">
        <!-- {{ getTimecode(currentTime) }} -->
          CurrentTime
      </div>

      <v-menu offset-y top>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ currentSpeed.title }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item v-for="(item, index) in speeds" :key="index">
            <v-list-item-title v-on:click="onSpeedChange(index)">{{
              item.title
            }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn @click="onToggleVolume" size="small">
        <v-icon v-if="volume > 66"> mdi-volume-high </v-icon>
        <v-icon v-else-if="volume > 33"> mdi-volume-medium </v-icon>
        <v-icon v-else-if="volume > 0"> mdi-volume-low </v-icon>
        <v-icon v-else-if="volume == 0"> mdi-volume-mute </v-icon>
      </v-btn>
      <v-slider
        :value="volume"
        @input="onVolumeChange"
        max="100" 
        min="0" 
        hide-details
        color="primary"
        :thumb-size="15"
      ></v-slider>
    </v-row>

    <v-row>
      <v-slider
        class="progress-bar"
        hide-details
        color="primary"
        :thumb-size="15"
        ></v-slider>
    </v-row>
  </v-container>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { usePlayerStore } from "@/stores/player";
 import { getDisplayTime, getTimecode } from "@/plugins/time";

export default {
  setup() {
    const videoElement = ref(null);
    const videoContainer = ref(null);

    const playerStore = usePlayerStore();

    const currentSpeed = ref({ title: '1.00', value: 1.0 });
    const speeds = [
      { title: '0.25', value: 0.25 },
      { title: '0.50', value: 0.5 },
      { title: '0.75', value: 0.75 },
      { title: '1.00', value: 1.0 },
      { title: '1.25', value: 1.25 },
      { title: '1.50', value: 1.5 },
      { title: '1.75', value: 1.75 },
      { title: '2.00', value: 2.0 },
    ];

    let observer = null;
    const threshold = 0.1;

    const toggleStickyVideo = ([entry]) => {
      if (videoElement.value) {
        videoElement.value.classList.toggle('sticky-video', entry.intersectionRatio < threshold);
      }
    };

    onMounted(() => {
      if (videoContainer.value) {
        observer = new IntersectionObserver(toggleStickyVideo, { threshold: [threshold] });
        observer.observe(videoContainer.value);
      }
    });

    onBeforeUnmount(() => {
      if (observer) {
        observer.disconnect();
      }
    });

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
    const onVolumeChange = (volume) => playerStore.setVolume(volume);

    const onLoadedData = () => playerStore.setLoadedData(true);
    const onCanPlay = () => playerStore.setCanPlay(true);

    const progress = computed(() => {
      if (duration.value <= 0) return 0;
      return playerStore.currentTime / playerStore.videoDuration;
    });

    const volume = computed(() => playerStore.volume);
    const ended = computed(() => playerStore.ended);
    const currentTime = computed(() => playerStore.currentTime);
    const duration = computed(() => playerStore.videoDuration);
    const syncTime = computed(() => playerStore.syncTime);
    const playing = computed(() => playerStore.playing);
    const targetTime = computed(() => playerStore.targetTime);

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

    return {
      videoElement,
      videoContainer,
      currentSpeed,
      speeds,
      progress,
      volume,
      ended,
      currentTime,
      duration,
      playing,
      toggle,
      toggleSyncTime,
      deltaSeek,
      onEnded,
      onPause,
      onPlay,
      onTimeUpdate,
      onSeek,
      onSpeedChange,
      onToggleVolume,
      onVolumeChange,
      onLoadedData,
      onCanPlay,
      getDisplayTime,
      getTimecode,
      playerStore
    };
  },
};
</script>

<style>
.sticky-video {
  position: fixed;
  height: auto !important;
  width: 15vw !important;
  z-index: 3;
  min-height: unset !important;
  top: 80px;
  right: 15px;
}
.video-player {
  max-width: 100%;
  height: 100%;
  max-height: 100%;
  min-height: 480px;
  background-color: black;
}

.video-control {
  gap: 5px;
  /* margin-top: 5px;
  margin-bottom: 0px; */
  /* max-width: 100%; */
}

.video-control > .progress-bar {
  margin-top: auto;
  margin-bottom: auto;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
}

.video-container {
  background-color: black;
  justify-content: center;
  max-height: 100%;
  min-height: 480px;
}
</style>