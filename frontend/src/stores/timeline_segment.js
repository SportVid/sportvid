import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";

import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";
import { useAnnotationStore } from "@/stores/annotation";
import { useTimelineStore } from "@/stores/timeline";
import { useShotStore } from "@/stores/shot";
import { usePlayerStore } from "@/stores/player";

export const useTimelineSegmentStore = () => {
  const timelineSegments = ref({});
  const timelineSegmentList = ref([]);
  const timelineSegmentListSelected = ref([]);
  const timelineSegmentByTime = ref({});

  const timelineSegmentListAdded = ref([]);
  const timelineSegmentListDeleted = ref([]);
  const isLoading = ref(false);

  const all = computed(() => timelineSegmentList.value.map((id) => timelineSegments.value[id]));

  const forTimeline = (timeline_id) => {
    return all.value.filter((e) => e.timeline_id === timeline_id).sort((a, b) => a.start - b.start);
  };

  const forTimelineTimeRange = (timeline_id, start, end) => {
    return forTimeline(timeline_id).filter(
      (e) => Math.min(e.end, end) - Math.max(e.start, start) > 0
    );
  };

  const forTime = (current_time) => {
    return all.value.filter((e) => e.start <= current_time && e.end >= current_time);
  };

  const get = (id) => timelineSegments.value[id];

  const selected = computed(() =>
    timelineSegmentListSelected.value.map((id) => timelineSegments.value[id])
  );

  const lastSelected = computed(() =>
    selected.value.length > 0 ? selected.value[selected.value.length - 1] : null
  );

  const forTimeLUT = (time) => {
    const timeSecond = Math.round(time);
    if (timelineSegmentByTime.value[timeSecond]) {
      return timelineSegmentByTime.value[timeSecond].map((id) => timelineSegments.value[id]);
    }
    return [];
  };

  const getPreviousOnTimeline = (id) => {
    const segment = get(id);
    const segments = forTimeline(segment.timeline_id)
      .filter((e) => e.end <= segment.start)
      .sort((a, b) => a.end - b.end);
    return segments.length > 0 ? segments[segments.length - 1] : null;
  };

  const getNextOnTimeline = (id) => {
    const segment = get(id);
    const segments = forTimeline(segment.timeline_id)
      .filter((e) => e.start >= segment.end)
      .sort((a, b) => a.end - b.end);
    return segments.length > 0 ? segments[0] : null;
  };

  const clearSelection = () => {
    timelineSegmentListSelected.value = [];
  };

  const addToSelection = (timelineSegmentId) => {
    timelineSegmentListSelected.value.push(timelineSegmentId);
  };

  const removeFromSelection = (timelineSegmentId) => {
    const index = timelineSegmentListSelected.value.findIndex((f) => f === timelineSegmentId);
    if (index >= 0) {
      timelineSegmentListSelected.value.splice(index, 1);
    }
  };

  const annotateSegments = async ({ timelineSegmentIds, annotations }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      timeline_segment_ids: timelineSegmentIds,
      annotations: annotations,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/segment/annotate`, params);
      if (res.data.status === "ok") {
        const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
        const annotationCategoryStore = useAnnotationCategoryStore();
        const annotationStore = useAnnotationStore();

        timelineSegmentAnnotationStore.deleteFromStore(
          res.data.timeline_segment_annotation_deleted
        );
        timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);

        annotationCategoryStore.addToStore(res.data.annotation_category_added);
        annotationStore.addToStore(res.data.annotation_added);

        const timelineStore = useTimelineStore();
        timelineSegmentIds.forEach((e) => {
          timelineStore.notifyChanges({
            timelineIds: [get(e).timeline_id],
          });
        });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const annotateRange = async ({ timelineId, annotations, start = null, end = null }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    if (!start) {
      const timelineStore = useTimelineStore();
      start = timelineStore.selectedTimeRangeStart;
    }
    if (!end) {
      const timelineStore = useTimelineStore();
      end = timelineStore.selectedTimeRangeEnd;
    }
    const params = {
      timeline_id: timelineId,
      annotations: annotations,
      start: start,
      end: end,
    };

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/timeline/segment/annotate/range`,
        params
      );
      if (res.data.status === "ok") {
        const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
        const annotationCategoryStore = useAnnotationCategoryStore();
        const annotationStore = useAnnotationStore();

        deleteFromStore(res.data.timeline_segment_deleted);
        addToStore(res.data.timeline_segment_added);

        annotationCategoryStore.addToStore(res.data.annotation_category_added);
        annotationStore.addToStore(res.data.annotation_added);

        timelineSegmentAnnotationStore.deleteFromStore(
          res.data.timeline_segment_annotation_deleted
        );
        timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);

        const timelineStore = useTimelineStore();
        timelineStore.notifyChanges({ timelineIds: [timelineId] });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const toggle = async ({ timelineSegmentId, annotationId }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      timeline_segment_id: timelineSegmentId,
      annotation_id: annotationId,
    };

    const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
    const annotationCategoryStore = useAnnotationCategoryStore();
    const annotationStore = useAnnotationStore();

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/timeline/segment/annotation/toggle`,
        params
      );
      if (res.data.status === "ok") {
        if ("annotation_added" in res.data) {
          annotationStore.addToStore(res.data.annotation_added);
        }
        if ("annotation_category_added" in res.data) {
          annotationCategoryStore.addToStore(res.data.annotation_category_added);
        }
        if ("timeline_segment_annotation_deleted" in res.data) {
          timelineSegmentAnnotationStore.deleteFromStore(
            res.data.timeline_segment_annotation_deleted
          );
        }
        if ("timeline_segment_annotation_added" in res.data) {
          timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);
        }

        const timelineStore = useTimelineStore();
        timelineStore.notifyChanges({
          timelineIds: [get(timelineSegmentId).timeline_id],
        });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const split = async ({ timelineSegmentId, time }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      timeline_segment_id: timelineSegmentId,
      time: time,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/segment/split`, params);
      if (res.data.status === "ok") {
        const timelineId = get(timelineSegmentId).timeline_id;
        const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();

        timelineSegmentAnnotationStore.deleteFromStore(
          res.data.timeline_segment_annotation_deleted
        );
        timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);
        deleteFromStore(res.data.timeline_segment_deleted);
        addToStore(res.data.timeline_segment_added);

        const timelineStore = useTimelineStore();
        timelineStore.notifyChanges({ timelineIds: [timelineId] });
      }
    } finally {
      isLoading.value = false;
    }
  };

  const merge = async ({ timelineSegmentIds }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      timeline_segment_ids: timelineSegmentIds,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/timeline/segment/merge`, params);
      if (res.data.status === "ok") {
        const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();

        timelineSegmentAnnotationStore.deleteFromStore(
          res.data.timeline_segment_annotation_deleted
        );
        timelineSegmentAnnotationStore.addToStore(res.data.timeline_segment_annotation_added);

        const timelineStore = useTimelineStore();
        const timelineIds = [...new Set(timelineSegmentIds.map((id) => get(id).timeline_id))];
        timelineStore.notifyChanges({ timelineIds: timelineIds });

        deleteFromStore(res.data.timeline_segment_deleted);
        addToStore(res.data.timeline_segment_added);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ timelineId, videoId, clear = true }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {};
    if (timelineId) {
      params.timeline_id = timelineId;
    }
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
      const res = await axios.get(`${config.API_LOCATION}/timeline/segment/list`, { params });
      if (res.data.status === "ok") {
        updateStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    timelineSegmentListSelected.value = [];
    timelineSegmentByTime.value = {};

    timelineSegmentListAdded.value = [];
    timelineSegmentListDeleted.value = [];
    timelineSegments.value = {};
    timelineSegmentList.value = [];
  };

  const addAnnotation = (annotations) => {
    annotations.forEach((e) => {
      timelineSegments.value[e.timelineSegmentId].annotation_ids.push(e.entry.id);
    });
  };

  const deleteAnnotation = (timeline_segment_annotations) => {
    timeline_segment_annotations.forEach((f) => {
      timelineSegmentList.value
        .map((id) => timelineSegments.value[id])
        .forEach((e) => {
          let index = e.annotation_ids.findIndex((k) => k === f);
          if (index >= 0) {
            e.annotation_ids.splice(index, 1);
          }
        });
    });
  };

  const addToStore = (timelineSegments) => {
    timelineSegments.forEach((e) => {
      timelineSegmentListAdded.value.push(e.id);
      timelineSegments.value[e.id] = e;
      timelineSegmentList.value.push(e.id);
    });
    timelineSegments = timelineSegments.sort((a, b) => {
      return a.start - b.start;
    });
    updateTimeStore();
  };

  const deleteTimeline = (timeline_id) => {
    const timeline_indexes = timelineSegmentList.value
      .map((id) => timelineSegments.value[id])
      .filter((e) => e.timeline_id === timeline_id);
    timeline_indexes.forEach((e) => {
      let segment_index = timelineSegmentList.value.findIndex((f) => f === e.id);
      timelineSegmentList.value.splice(segment_index, 1);
      Vue.delete(timelineSegments.value, e.id);
    });
    updateTimeStore();
  };

  const updateStore = (segments) => {
    segments.forEach((segment) => {
      if (!timelineSegments.value[segment.id]) {
        timelineSegments.value[segment.id] = segment;
        timelineSegmentList.value.push(segment.id);
      }
    });
    updateTimeStore();
  };

  const deleteFromStore = (ids) => {
    ids.forEach((id) => {
      delete timelineSegments.value[id];
      const index = timelineSegmentList.value.indexOf(id);
      if (index >= 0) timelineSegmentList.value.splice(index, 1);
    });
    updateTimeStore();
  };

  const updateTimeStore = () => {
    timelineSegmentByTime.value = {};
    all.value.forEach((e) => {
      for (let i = Math.floor(e.start); i < Math.ceil(e.end); i++) {
        if (!timelineSegmentByTime.value[i]) {
          timelineSegmentByTime.value[i] = [];
        }
        timelineSegmentByTime.value[i].push(e.id);
      }
    });
  };

  return {
    timelineSegments,
    timelineSegmentList,
    timelineSegmentListSelected,
    timelineSegmentByTime,
    timelineSegmentListAdded,
    timelineSegmentListDeleted,
    isLoading,
    all,
    forTimeline,
    forTimelineTimeRange,
    forTime,
    get,
    selected,
    lastSelected,
    forTimeLUT,
    getPreviousOnTimeline,
    getNextOnTimeline,
    clearSelection,
    addToSelection,
    removeFromSelection,
    annotateSegments,
    annotateRange,
    toggle,
    split,
    merge,
    fetchForVideo,
    clearStore,
    addAnnotation,
    deleteAnnotation,
    addToStore,
    deleteTimeline,
    updateStore,
    deleteFromStore,
    updateTimeStore,
  };
};
