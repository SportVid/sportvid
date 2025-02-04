import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { defineStore } from "pinia";

import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useTimelineStore } from "@/stores/timeline";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useShotStore = defineStore("shot", () => {
  const isLoading = ref(false);
  const selectedShots = ref(null);
  const playerStore = usePlayerStore();

  const shotsList = computed(() => {
    const timelineStore = useTimelineStore();
    const playerStore = usePlayerStore();

    let timeline = timelineStore.forVideo(playerStore.videoId).filter((e) => {
      return e.type == "ANNOTATION";
    });

    if (timeline.length) {
      return timeline.map((e) => ({
        index: e.id,
        name: e.name,
      }));
    }

    return [];
  });

  const shots = computed(() => {
    const pluginRunStore = usePluginRunStore();
    const pluginRunResultStore = usePluginRunResultStore();
    const timelineStore = useTimelineStore();
    const timelineSegmentStore = useTimelineSegmentStore();
    const playerStore = usePlayerStore();

    let results = [];
    let currentSelectedShots = selectedShots.value;

    if (!currentSelectedShots) {
      let timeline = timelineStore.forVideo(playerStore.videoId).filter((e) => {
        return e.type == "ANNOTATION";
      });

      if (!timeline.length) {
        console.error("Shots: No annotation timeline");
        return results;
      }
      currentSelectedShots = timeline[0].id;
    }

    results = timelineSegmentStore.forTimeline(currentSelectedShots).map((e) => ({
      start: e.start,
      end: e.end,
    }));

    let thumbnail = pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type == "thumbnail" && e.status == "DONE")
      .map((e) => {
        e.results = pluginRunResultStore.forPluginRun(e.id);
        return e;
      })
      .sort((a, b) => new Date(b.date) - new Date(a.date));

    if (!thumbnail.length) {
      console.error("Shots: No thumbnail run");
      return [];
    }

    thumbnail = thumbnail.at(0); // Use latest thumbnails

    let thumbnailList = [];
    let deltaTime = 0.2;
    if (
      "results" in thumbnail &&
      thumbnail.results.length > 0 &&
      "data" in thumbnail.results[0]
    ) {
      deltaTime = thumbnail.results[0].data.images[0].delta_time;
      thumbnailList = thumbnail.results[0].data.images.map((e) => {
        return (
          config.THUMBNAIL_LOCATION +
          `/${e.id.substr(0, 2)}/${e.id.substr(2, 2)}/${e.id}.${e.ext}`
        );
      });
    }

    return results.map((e, i) => ({
      id: i + 1,
      start: e.start,
      end: e.end,
      thumbnails: [
        thumbnailList[
          Math.min(Math.ceil(e.start / deltaTime), thumbnailList.length - 1)
        ],
        thumbnailList[
          Math.round((e.start + (e.end - e.start) / 2) / deltaTime)
        ],
        thumbnailList[Math.floor(e.end / deltaTime)],
      ],
    }));
  });

  const setSelectedShots = async ({ videoId = null, shotTimeline = null }) => {
    selectedShots.value = shotTimeline;

    if (isLoading.value) return;
    isLoading.value = true;

    let params = { timeline_id: shotTimeline };
    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const currentVideoId = playerStore.videoId;
      if (currentVideoId) {
        params.video_id = currentVideoId;
      }
    }

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/video/analysis/setselectedshots`,
        params
      );
      if (res.data.status === "ok") {
        console.log("Selected shots set successfully.");
      }
    } catch (err) {
      console.error("Error setting selected shots:", err);
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId = null }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    let params = {};
    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const currentVideoId = playerStore.videoId;
      if (currentVideoId) {
        params.video_id = currentVideoId;
      }
    }

    try {
      const res = await axios.get(`${config.API_LOCATION}/video/analysis/get`, {
        params,
      });
      if (res.data.status === "ok") {
        let fetchedSelectedShots = res.data.entry.selected_shots;

        if (!fetchedSelectedShots) {
          const timelineStore = useTimelineStore();
          let timeline = timelineStore
            .forVideo(playerStore.videoId)
            .filter((e) => e.type == "ANNOTATION");

          if (!timeline.length) {
            console.error("Shots: No annotation timeline");
            return;
          }
          fetchedSelectedShots = timeline[0].id;
        }

        selectedShots.value = fetchedSelectedShots;
        console.log("Selected shots:", selectedShots.value);
      }
    } catch (err) {
      console.error("Error fetching data for video:", err);
    } finally {
      isLoading.value = false;
    }
  };

  return {
    isLoading,
    selectedShots,
    shotsList,
    shots,
    setSelectedShots,
    fetchForVideo,
  };
});
