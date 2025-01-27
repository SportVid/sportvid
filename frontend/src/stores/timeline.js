import { ref, computed } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useTimelineStore = defineStore("timeline", () => {
  const timelines = ref({});
  const timelineList = ref([]);
  const timelineListSelected = ref([]);
  const timelineListAdded = ref([]);
  const timelineListDeleted = ref([]);
  const timelineListChanged = ref([]);
  const timelineSelectedTimeRange = ref({
    start: null,
    end: null,
  });
  const visualizationData = ref(null);
  const isLoading = ref(false);

  const getVisualizationData = computed(() => visualizationData.value);
  const selectedTimeRangeStart = computed(() => {
    if (
      timelineSelectedTimeRange.value.start === null ||
      timelineSelectedTimeRange.value.end === null
    ) {
      return null;
    }
    return Math.min(
      timelineSelectedTimeRange.value.start,
      timelineSelectedTimeRange.value.end
    );
  });
  const selectedTimeRangeEnd = computed(() => {
    if (
      timelineSelectedTimeRange.value.start === null ||
      timelineSelectedTimeRange.value.end === null
    ) {
      return null;
    }
    return Math.max(
      timelineSelectedTimeRange.value.start,
      timelineSelectedTimeRange.value.end
    );
  });
  const forVideo = computed(() => {
    return (videoId) => {
      return timelineList.value
        .map((id) => timelines.value[id])
        .filter((e) => e.video_id === videoId);
    };
  });
  const all = computed(() => Object.values(timelines.value));
  const added = computed(() => timelineListAdded.value.map((data) => [
    data[0],
    timelines.value[data[1]],
  ]));
  const deleted = computed(() => timelineListDeleted.value);
  const changed = computed(() => timelineListChanged.value.map((data) => [
    data[0],
    timelines.value[data[1]],
  ]));
  const get = computed(() => {
    return (id) => {
      return timelines.value[id];
    };
  });
  const getLatest = computed(() => () => {
    const id = timelineListAdded.value.at(-1)[1];
    return timelines.value[id];
  });
  const segmentPosition = computed(() => {
    return (segmentId) => {
      let result = null;
      timelineList.value
        .map((id) => timelines.value[id])
        .forEach((timeline, timelinePos) => {
          if (timeline.segments != null) {
            timeline.segments.forEach((segment, segmentPos) => {
              if (segment.id === segmentId) {
                result = { timeline: timelinePos, segment: segmentPos };
              }
            });
          }
        });
      return result;
    };
  });
  const getSegmentByPosition = computed(() => {
    return (timelinePos, segmentPos) => {
      let result = null;
      timelineList.value
        .map((id) => timelines.value[id])
        .forEach((timeline, iTimelinePos) => {
          if (timeline.segments != null && timelinePos === iTimelinePos) {
            timeline.segments.forEach((segment, iSegmentPos) => {
              if (iSegmentPos === segmentPos) {
                result = segment.id;
              }
            });
          }
        });
      return result;
    };
  });

  const selected = computed(() => timelineListSelected.value.map((id) => timelines.value[id]));
  const lastSelected = computed(() => {
    if (timelineListSelected.value.length <= 0) {
      return null;
    }
    return timelineListSelected.value.map((id) => timelines.value[id])[
      timelineListSelected.value.length - 1
    ];
  });
  const getPrevious = computed(() => {
    return (id) => {
      if (!id) {
        return all.value.sort((a, b) => a.order - b.order)[0];
      }
      const timeline = timelines.value[id];
      const timelinesList = all.value
        .sort((a, b) => a.order - b.order)
        .filter((e) => e.order < timeline.order);
      if (timelinesList.length <= 0) {
        return null;
      }
      return timelinesList[timelinesList.length - 1];
    };
  });
  const getNext = computed(() => {
    return (id) => {
      if (!id) {
        return all.value.sort((a, b) => a.order - b.order)[0];
      }
      const timeline = timelines.value[id];
      const timelinesList = all.value
        .sort((a, b) => a.order - b.order)
        .filter((e) => e.order > timeline.order);
      if (timelinesList.length <= 0) {
        return null;
      }
      return timelinesList[0];
    };
  });

  const setVisualizationData = (data) => {
    visualizationData.value = data;
  };

  const setSelectedTimeRangeStart = (time) => {
    timelineSelectedTimeRange.value.start = time;
  };

  const setSelectedTimeRangeEnd = (time) => {
    timelineSelectedTimeRange.value.end = time;
  };

  const clearSelection = () => {
    timelineListSelected.value = [];
  };

  const addToSelection = (timelineId) => {
    timelineListSelected.value.push(timelineId);
  };

  const removeFromSelection = (timelineId) => {
    let segment_index = timelineListSelected.value.findIndex(
      (f) => f === timelineId
    );
    timelineListSelected.value.splice(segment_index, 1);
  };

  const fetchAll = async ({ addResultsType = false }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;
    let params = { add_results_type: addResultsType };

    try {
      const res = await axios.get(`${config.API_LOCATION}/timeline/list_all`, { params });
      if (res.data.status === "ok") {
        updateStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId = null, clear = true }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {};
    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const videoId = playerStore.videoId;
      if (videoId) {
        params.video_id = videoId;
      }
    }
    if (clear) {
      clearStore();
    }

    try {
      const res = await axios.get(`${config.API_LOCATION}/timeline/list`, { params });
      if (res.data.status === "ok") {
        updateStore(res.data.entries);
        // Load plugin run results
        const pluginRunResultStore = usePluginRunResultStore();
        res.data.entries.forEach((timeline) => {
          if (!('plugin' in timeline) && timeline.type == "PLUGIN_RESULT" && "plugin_run_result_id" in timeline) {
            const result = pluginRunResultStore.get(timeline.plugin_run_result_id);
            if (result) {
              timeline.plugin = { data: result.data, type: result.type };
            }
          }
        });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const duplicate = async ({ id, name = null, includeannotations = true }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      id: id,
      name: name,
      include_annotations: includeannotations,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/duplicate`, params);
      if (res.data.status === "ok") {
        const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
        timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);

        const timelineSegmentStore = useTimelineSegmentStore();
        timelineSegmentStore.addToStore(res.data.timeline_segment_added);

        addToStore(res.data.timeline_added);

        notifyChanges({
          timelineIds: [res.data.timeline_added.map((e) => e.id)],
        });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const create = async ({ name, videoId = null }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      name: name,
    };

    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const videoId = playerStore.videoId;
      if (videoId) {
        params.video_id = videoId;
      }
    }

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/create`, params);
      if (res.data.status === "ok") {
        addToStore(res.data.timeline_added);

        const timelineSegmentStore = useTimelineSegmentStore();
        timelineSegmentStore.addToStore(res.data.timeline_segment_added);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const importEAF = async (params) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const formData = new FormData();

    // use video id or take it from the current video
    const playerStore = usePlayerStore();
    const videoId = playerStore.videoId;
    formData.append("file", params.importfile);
    formData.append("video_id", videoId);

    try {
      await axios.post(`${config.API_LOCATION}/timeline/import/eaf`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    } finally {
      isLoading.value = false;
    }
  };

  const deleteTimeline = async (timeline_id) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      id: timeline_id,
    };

    // update own store
    deleteFromStore([timeline_id]);

    // update all segments
    const timelineSegmentStore = useTimelineSegmentStore();
    timelineSegmentStore.deleteTimeline(timeline_id);

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/delete`, params);
      if (res.data.status === "ok") {
        // commit("delete", timeline_id);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const rename = async ({ timelineId, name }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      id: timelineId,
      name: name,
    };

    const newTimelines = { ...timelines.value };
    newTimelines[timelineId].name = name;
    timelines.value = newTimelines;

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/rename`, params);
      if (res.data.status === "ok") {
        // commit("rename", { timelineId, name });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const changeVisualization = async ({ timelineId, visualization, colormap = null, colormap_inverse = false }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      id: timelineId,
      visualization: visualization,
      colormap: colormap,
      colormap_inverse: colormap_inverse,
    };

    const newTimelines = { ...timelines.value };
    newTimelines[timelineId].visualization = visualization;
    newTimelines[timelineId].colormap = colormap;
    newTimelines[timelineId].colormap_inverse = colormap_inverse;
    timelines.value = newTimelines;

    timelineListChanged.value.push([Date.now(), timelineId]);

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/changevisualization`, params);
      if (res.data.status === "ok") {
        // commit("changevisualization", { timelineId, visualization });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const setParent = async ({ timelineId, parentId }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      timelineId: timelineId,
      parentId: parentId,
    };

    if (!parentId) {
      params.parentId = null;
    }

    const newTimelines = { ...timelines.value };
    newTimelines[timelineId].parent_id = parentId;
    timelines.value = newTimelines;

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/setparent`, params);
      if (res.data.status === "ok") {
        // commit("setParent", { timelineId, parentId });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const setCollapse = async ({ timelineId, collapse }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      timelineId: timelineId,
      collapse: collapse,
    };

    const newTimelines = { ...timelines.value };
    newTimelines[timelineId].collapse = collapse;
    timelines.value = newTimelines;
    updateVisibleStore();

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/setcollapse`, params);
      if (res.data.status === "ok") {
        // commit("setCollapse", { timelineId, collapse });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const setOrder = async ({ order }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {
      order: order,
    };

    timelineList.value = order;

    timelineList.value.forEach((id, i) => {
      timelines.value[id].order = i;
    });

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/setorder`, params);
      if (res.data.status === "ok") {
        // commit("setorder", { order });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const notifyChanges = ({ timelineIds }) => {
    timelineIds.forEach((id) => {
      timelineListChanged.value.push([Date.now(), id]);
    });
  };

  const addToStore = (timelines) => {
    timelines.forEach((e) => {
      timelineListAdded.value.push([Date.now(), e.id]);
      timelines.value[e.id] = e;
      timelineList.value.push(e.id);
    });
    updateVisibleStore();
  };

  const updateStore = (timelines) => {
    timelines.forEach((e) => {
      if (!(e.id in timelines.value)) {
        timelineListAdded.value.push([Date.now(), e.id]);
        timelines.value[e.id] = e;
        timelineList.value.push(e.id);
      }
    });
    updateVisibleStore();
  };

  const updateVisibleStore = () => {
    const parentCollapsed = (e) => {
      if (!e.parent_id) {
        return false;
      }

      let parent_id = e.parent_id;

      while (parent_id != null) {
        let parent = get(parent_id);
        parent_id = parent.parent_id;
        if (parent.collapse) {
          return true;
        }
      }

      return false;
    };
    timelineList.value.map((e) => {
      timelines.value[e].visible = !parentCollapsed(timelines.value[e]);
      return e;
    });
  };

  const clearStore = () => {
    timelineListSelected.value = [];
    timelineListAdded.value = [];
    timelineListDeleted.value = [];
    timelineListChanged.value = [];
    Object.keys(timelines.value).forEach((key) => {
      delete timelines.value[key];
    });
    timelineList.value = [];
  };

  const deleteFromStore = (ids) => {
    ids.forEach((id) => {
      timelineListDeleted.value.push([Date.now(), id]);
      let index = timelineList.value.findIndex((f) => f === id);
      timelineList.value.splice(index, 1);
      delete timelines.value[id];
    });
    updateVisibleStore();
  };

  return {
    timelines,
    timelineList,
    timelineListSelected,
    timelineListAdded,
    timelineListDeleted,
    timelineListChanged,
    timelineSelectedTimeRange,
    visualizationData,
    isLoading,
    getVisualizationData,
    selectedTimeRangeStart,
    selectedTimeRangeEnd,
    forVideo,
    all,
    added,
    deleted,
    changed,
    get,
    getLatest,
    segmentPosition,
    getSegmentByPosition,
    selected,
    lastSelected,
    getPrevious,
    getNext,
    setVisualizationData,
    setSelectedTimeRangeStart,
    setSelectedTimeRangeEnd,
    clearSelection,
    addToSelection,
    removeFromSelection,
    fetchAll,
    fetchForVideo,
    duplicate,
    create,
    importEAF,
    deleteTimeline,
    rename,
    changeVisualization,
    setParent,
    setCollapse,
    setOrder,
    notifyChanges,
    addToStore,
    updateStore,
    updateVisibleStore,
    clearStore,
    deleteFromStore,
  };
});
