import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { Buffer } from "buffer";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { useAnnotationStore } from "./annotation";
import { useAnnotationCategoryStore } from "./annotation_category";
import { useTimelineStore } from "./timeline";
import { useTimelineSegmentStore } from "./timeline_segment";
import { useTimelineSegmentAnnotationStore } from "./timeline_segment_annotation";
import { usePluginRunStore } from "./plugin_run";
import { usePluginRunResultStore } from "./plugin_run_result";
import { useShortcutStore } from "./shortcut";
import { useAnnotationShortcutStore } from "./annotation_shortcut";
import { useClusterTimelineItemStore } from "./cluster_timeline_item";
import { useShotStore } from "./shot";
import { de } from "vis";
import { re } from "mathjs";

export const useVideoStore = defineStore("video", () => {
  const userStore = useUserStore();

  const videos = ref({});
  const videoList = ref([]);
  const isLoading = ref(false);
  const uploadSuccess = ref(false);
  const deleteSuccess = ref(false);
  const renameSuccess = ref(false);

  const all = computed(() => videoList.value.map((id) => videos.value[id]));
  const get = computed(() => {
    return (id) => videos.value[id];
  });

  const clearStore = () => {
    videos.value = {};
    videoList.value = [];
  };

  const deleteFromStore = (ids) => {
    ids.forEach((id) => {
      let index = videoList.value.findIndex((f) => f === id);
      videoList.value.splice(index, 1);
      delete videos.value[id];
      deleteSuccess.value = true;
    });
  };

  const addToStore = (video) => {
    videos.value[video.id] = video;
    videoList.value.push(video.id);
    uploadSuccess.value = true;
  };

  const replaceStore = (newVideos) => {
    videos.value = {};
    videoList.value = [];
    newVideos.forEach((e) => {
      videos.value[e.id] = e;
      videoList.value.push(e.id);
    });
  };

  const fetch = async ({
    videoId,
    includeTimeline = true,
    includeAnnotation = true,
    includeAnalyser = true,
    includeShortcut = true,
    includeClusterTimelineItem = true,
    addResults = true,
  }) => {
    isLoading.value = true;
    let promises = [];

    const playerStore = usePlayerStore();
    const annotationCategoryStore = useAnnotationCategoryStore();
    const annotationStore = useAnnotationStore();
    const timelineStore = useTimelineStore();
    const timelineSegmentStore = useTimelineSegmentStore();
    const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
    const pluginRunStore = usePluginRunStore();
    const pluginRunResultStore = usePluginRunResultStore();
    const shortcutStore = useShortcutStore();
    const annotationShortcutStore = useAnnotationShortcutStore();
    const clusterTimelineItemStore = useClusterTimelineItemStore();
    const shotStore = useShotStore();

    playerStore.clearStore();
    promises.push(playerStore.fetchVideo({ videoId }));

    if (includeAnnotation) {
      annotationCategoryStore.clearStore();
      annotationStore.clearStore();
      promises.push(annotationCategoryStore.fetchForVideo({ videoId }));
      promises.push(annotationStore.fetchForVideo({ videoId }));
    }

    if (includeAnalyser && !includeTimeline) {
      pluginRunStore.clearStore();
      pluginRunResultStore.clearStore();
      promises.push(pluginRunStore.fetchForVideo({ videoId, addResults }));
      promises.push(pluginRunResultStore.fetchForVideo({ videoId, addResults }));
    }

    if (includeAnalyser && includeTimeline) {
      pluginRunStore.clearStore();
      pluginRunResultStore.clearStore();
      const pluginRunPromises = [
        pluginRunResultStore.fetchForVideo({ videoId, addResults }),
        pluginRunStore.fetchForVideo({ videoId, addResults }),
      ];
      promises.push(...pluginRunPromises);
      await Promise.all(pluginRunPromises);

      const timelinePromises = [
        timelineStore.fetchForVideo({ videoId }),
        timelineSegmentStore.fetchForVideo({ videoId }),
        timelineSegmentAnnotationStore.fetchForVideo({ videoId }),
      ];

      promises.push(...timelinePromises);
    }

    promises.push(shotStore.fetchForVideo({ videoId }));

    if (includeShortcut) {
      shortcutStore.clearStore();
      annotationShortcutStore.clearStore();
      promises.push(shortcutStore.fetchForVideo({ videoId }));
      promises.push(annotationShortcutStore.fetchForVideo({ videoId }));
    }

    if (includeClusterTimelineItem) {
      clusterTimelineItemStore.clearStore();
      promises.push(clusterTimelineItemStore.fetchAll(videoId));
    }

    return Promise.all(promises).finally(() => {
      isLoading.value = false;
    });
  };

  const fetchAll = async () => {
    if (isLoading.value) return;
    if (userStore.loggedIn === false) return;

    isLoading.value = true;

    try {
      const res = await axios.get(`${config.API_LOCATION}/video/list`);
      if (res.data.status === "ok") {
        replaceStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const rename = async ({ videoId, name }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = { id: videoId, name };
    const newVideos = { ...videos.value };
    newVideos[videoId].name = name;
    videos.value = newVideos;

    try {
      const res = await axios.post(`${config.API_LOCATION}/video/rename`, params);
      if (res.data.status === "ok") {
        renameSuccess.value = true;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const deleteVideo = async (videoId) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = { id: videoId };

    try {
      const res = await axios.post(`${config.API_LOCATION}/video/delete`, params);
      if (res.data.status === "ok") {
        deleteFromStore([videoId]);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const exportVideo = async ({ format, parameters = [], videoId = null }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const formData = new FormData();
    formData.append("format", format);
    let jsonParameters = [];
    parameters.forEach((p) => {
      if ("file" in p) {
        formData.append(`file_${p.name}`, p.file);
      } else {
        jsonParameters.push(p);
      }
    });
    formData.append("parameters", JSON.stringify(jsonParameters));

    let video_id = videoId || usePlayerStore().videoId;
    formData.append("video_id", video_id);

    try {
      const res = await axios.post(`${config.API_LOCATION}/video/export`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (res.data.status === "ok") {
        handleExportFile(res.data, video_id);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const handleExportFile = (data, videoId) => {
    if (data.extension === "zip") {
      const filecontent = Buffer.from(data.file, "base64");
      let blob = new Blob([filecontent], { type: "application/zip" });
      let link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `timelines.${data.extension}`;
      link.click();
    } else if (data.extension === "csv" || data.extension === "eaf") {
      let blob = new Blob([data.file], { type: `text/${data.extension}` });
      let link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `${videoId}.${data.extension}`;
      link.click();
    }
  };

  const videoSize = ref({ width: 0, height: 0, top: 0, left: 0 });

  const setVideoSize = (size) => {
    videoSize.value = size;
  };

  return {
    videos,
    videoList,
    isLoading,
    all,
    get,
    clearStore,
    deleteFromStore,
    addToStore,
    replaceStore,
    fetch,
    fetchAll,
    rename,
    deleteVideo,
    exportVideo,
    videoSize,
    setVideoSize,
    uploadSuccess,
    deleteSuccess,
    renameSuccess,
  };
});
