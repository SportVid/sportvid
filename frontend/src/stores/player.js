import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";

export const usePlayerStore = defineStore(
  "player",
  () => {
    const videoElement = ref(null);

    const video = ref(null);
    const currentTime = ref(0.0);
    const targetTime = ref(0.0);
    const playing = ref(false);
    const ended = ref(false);
    const isSynced = ref(true);

    const isMuted = ref(false);
    const volume = ref(100);
    const previousVolume = ref(100);
    const changeVolume = () => {
      if (videoElement.value) {
        videoElement.value.volume = volume.value / 100;
      }
    };
    const toggleMute = () => {
      if (isMuted.value) {
        volume.value = previousVolume.value;
      } else {
        previousVolume.value = volume.value;
        volume.value = 0;
      }
      isMuted.value = !isMuted.value;
      changeVolume();
    };
    const volumeIcon = computed(() => {
      if (volume.value > 66) return "mdi-volume-high";
      if (volume.value > 33) return "mdi-volume-medium";
      if (volume.value > 0) return "mdi-volume-low";
      return "mdi-volume-mute";
    });

    const syncTime = ref(true);

    const selectedTimeRange = ref({
      start: 0,
      end: 0,
    });
    const isLoading = ref(false);

    const videoDuration = computed(() => {
      return video.value && "duration" in video.value ? video.value.duration : 0.0;
    });

    const videoFPS = computed(() => {
      return video.value && "fps" in video.value ? video.value.fps : 24;
    });

    const videoName = computed(() => {
      return video.value && "name" in video.value ? video.value.name : "";
    });

    const videoId = computed(() => {
      return video.value && "id" in video.value ? video.value.id : null;
    });

    const videoUrl = computed(() => {
      return video.value && "url" in video.value ? video.value.url : null;
    });

    const clearStore = () => {
      video.value = null;
      currentTime.value = 0.0;
      targetTime.value = 0.0;
      playing.value = false;
      ended.value = false;
      selectedTimeRange.value.start = 0;
      selectedTimeRange.value.end = 0;
    };

    const setSelectedTimeRangeStart = (time) => {
      selectedTimeRange.value.start = time;
    };

    const setSelectedTimeRangeEnd = (time) => {
      selectedTimeRange.value.end = time;
    };

    const toggleSliderSync = () => {
      isSynced.value = !isSynced.value;
    };

    const setTargetTime = (time) => {
      targetTime.value = time;
      // targetTime.value = Math.round(time * 100) / 100;
    };

    const setCurrentTime = (time) => {
      currentTime.value = time;
      // currentTime.value = Math.round(time * 100) / 100;
    };

    const setEnded = (endedValue) => {
      ended.value = endedValue;
    };

    const toggleSyncTime = () => {
      syncTime.value = !syncTime.value;
    };

    const setPlaying = (playingValue) => {
      playing.value = playingValue;
    };

    const togglePlaying = () => {
      playing.value = !playing.value;
    };

    const fetchVideo = async ({ videoId }) => {
      if (isLoading.value) {
        return;
      }
      isLoading.value = true;

      const params = { id: videoId };
      try {
        const res = await axios.get(`${config.API_LOCATION}/video/get`, { params });
        if (res.data.status === "ok") {
          video.value = res.data.entry;
          selectedTimeRange.value.end = videoDuration.value;
        }
      } finally {
        isLoading.value = false;
      }
    };

    const roundTimeToFPS = (time, fps) => {
      const frameDuration = 1 / fps;
      const frame = Math.round(time / frameDuration) * frameDuration;
      return parseFloat(frame.toFixed(3));
    };

    return {
      videoElement,
      video,
      currentTime,
      targetTime,
      playing,
      ended,
      syncTime,
      selectedTimeRange,
      isLoading,
      videoDuration,
      videoFPS,
      videoName,
      videoId,
      videoUrl,
      isSynced,
      clearStore,
      setSelectedTimeRangeStart,
      setSelectedTimeRangeEnd,
      setTargetTime,
      setCurrentTime,
      setEnded,
      toggleSyncTime,
      setPlaying,
      togglePlaying,
      fetchVideo,
      toggleSliderSync,
      roundTimeToFPS,
      isMuted,
      volume,
      previousVolume,
      volumeIcon,
      changeVolume,
      toggleMute,
    };
  },
  {
    persist: {
      pick: ["previousVolume", "isMuted"],
      storage: localStorage,
    },
  }
);
