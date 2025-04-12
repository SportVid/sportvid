import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { defineStore } from "pinia";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";
import { useAnnotationStore } from "@/stores/annotation";
import { usePlayerStore } from "@/stores/player";

export const useTimelineSegmentAnnotationStore = defineStore("timelineSegmentAnnotation", () => {
  const timelineSegmentAnnotations = ref({});
  const isLoading = ref(false);

  const all = computed(() => Object.values(timelineSegmentAnnotations));

  const transcriptSegments = computed(() => {
    const annotationCategoryStore = useAnnotationCategoryStore();
    const segmentStore = useTimelineSegmentStore();
    const annotationStore = useAnnotationStore();

    return Object.values(timelineSegmentAnnotations)
      .map((segmentAnnotation, i) => {
        let segment = null;
        let start = 0;
        let end = 0;
        if (segmentAnnotation.timeline_segment_id) {
          segment = segmentStore.get(segmentAnnotation.timeline_segment_id);
          if (segment) {
            start = segment.start;
            end = segment.end;
          }
        }

        let annotation = null;
        if (segmentAnnotation.annotation_id) {
          annotation = annotationStore.get(segmentAnnotation.annotation_id);
        }

        let cat = null;
        if (annotation) {
          cat = annotationCategoryStore.get(annotation.category_id);
        }

        let name = annotation ? annotation.name : "";

        return { id: i + 1, category: cat, name, start, end };
      })
      .filter((segment) => segment.category && segment.category.name === "Transcript")
      .sort((a, b) => a.start - b.start)
      .map((segment, i) => {
        segment.id = i + 1;
        return segment;
      });
  });

  const forTimelineSegment = (timelineSegmentId) =>
    Object.values(timelineSegmentAnnotations).filter(
      (a) => a.timeline_segment_id === timelineSegmentId
    );

  const create = async ({ timelineSegmentId, annotationId }) => {
    if (isLoading.value) return;

    isLoading.value = true;

    const params = {
      timeline_segment_id: timelineSegmentId,
      annotation_id: annotationId,
    };

    const timelineSegmentStore = useTimelineSegmentStore();

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/timeline/segment/annotation/create`,
        params
      );

      if (res.data.status === "ok") {
        addToStore([res.data.entry]);
        timelineSegmentStore.addAnnotation([{ timelineSegmentId, entry: res.data.entry }]);
        return res.data.entry.id;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const remove = async (id) => {
    if (isLoading.value) return;

    isLoading.value = true;

    const params = { timeline_segment_annotation_id: id };
    const timelineSegmentStore = useTimelineSegmentStore();

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/timeline/segment/annotation/delete`,
        params
      );

      if (res.data.status === "ok") {
        deleteFromStore([id]);
        timelineSegmentStore.deleteAnnotation([id]);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId, clear = true }) => {
    if (isLoading.value) return;

    isLoading.value = true;

    const params = {};
    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const currentVideoId = playerStore.videoId;
      if (currentVideoId) {
        params.video_id = currentVideoId;
      }
    }

    if (clear) {
      clearStore();
    }

    try {
      const res = await axios.get(`${config.API_LOCATION}/timeline/segment/annotation/list`, {
        params,
      });

      if (res.data.status === "ok") {
        updateStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    Object.keys(timelineSegmentAnnotations).forEach((key) => {
      delete timelineSegmentAnnotations[key];
    });
  };

  const deleteFromStore = (ids) => {
    ids.forEach((id) => {
      delete timelineSegmentAnnotations[id];
    });
  };

  const addToStore = (annotations) => {
    annotations.forEach((e) => {
      timelineSegmentAnnotations[e.id] = e;
    });
  };

  const updateStore = (annotations) => {
    annotations.forEach((e) => {
      if (!(e.id in timelineSegmentAnnotations)) {
        timelineSegmentAnnotations[e.id] = e;
      }
    });
  };

  return {
    timelineSegmentAnnotations,
    isLoading,
    all,
    transcriptSegments,
    forTimelineSegment,
    create,
    remove,
    fetchForVideo,
    clearStore,
    deleteFromStore,
    addToStore,
    updateStore,
  };
});
