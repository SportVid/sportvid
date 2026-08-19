import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { defineStore } from "pinia";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";
import { useAnnotationStore } from "@/stores/annotation";
import { usePlayerStore } from "@/stores/player";

// ~60s of mock dialogue for exercising the Transcript/Wordcloud tab without waiting on a
// real Whisper run (see loadDemoTranscript below) -- same backdoor idea as
// events.js/_dummyEventsForSeed, purely client-side, no backend involved. Deliberately mixes:
//   - back-to-back segments (7000/9500) and gapped ones (silence in between), for the live
//     highlight/auto-scroll behaviour,
//   - a very short (19500-20000) and a very long segment, for text layout,
//   - German and English stopwords/filler words ("und", "der", "die", "das", "ist" /
//     "the", "and", "is"), for the wordcloud's stopword-language toggles,
//   - repeated vocabulary ("Ball", "Tor", "Spiel(er)", "Mannschaft"), so the wordcloud
//     actually has frequency differences to render.
const DEMO_TRANSCRIPT_SEGMENTS = [
  { start: 0, end: 2500, text: "Guten Tag und willkommen zur Analyse des heutigen Spiels." },
  { start: 3500, end: 7000, text: "Der Ball rollt schnell über das Spielfeld nach vorne." },
  { start: 7000, end: 9000, text: "Ein starker Pass von der Abwehr in die Mitte." },
  {
    start: 9500,
    end: 12000,
    text: "Der Spieler läuft schnell Richtung Tor und nimmt den Ball mit.",
  },
  { start: 12000, end: 13500, text: "Das war wirklich ein guter Pass." },
  {
    start: 14000,
    end: 19000,
    text:
      "Jetzt versucht der Stürmer den Ball ins Tor zu bringen, aber der Torwart hält stark " +
      "dagegen und pariert den Schuss in letzter Sekunde.",
  },
  { start: 19500, end: 20000, text: "Knapp daneben." },
  {
    start: 20500,
    end: 24000,
    text: "Die Mannschaft bleibt geduldig und baut das Spiel von hinten neu auf.",
  },
  {
    start: 24500,
    end: 27000,
    text: "Ein Foul wird gepfiffen, der Schiedsrichter zeigt auf den Elfmeterpunkt.",
  },
  { start: 27500, end: 31000, text: "This is an important moment in the match right now." },
  { start: 31500, end: 34000, text: "The player steps up and prepares to take the penalty." },
  { start: 34500, end: 36000, text: "Was für ein Moment für die Fans im Stadion." },
  {
    start: 36500,
    end: 41000,
    text: "Der Ball fliegt in die rechte Ecke und der Torwart kann nichts mehr machen, Tor!",
  },
  { start: 41500, end: 43000, text: "Ein fantastisches Tor in der zweiten Halbzeit." },
  {
    start: 43500,
    end: 47000,
    text: "Die Zuschauer jubeln lautstark und feiern den Torschützen ausgiebig.",
  },
  { start: 47500, end: 50000, text: "Der Ball liegt wieder im Anstoßkreis, das Spiel geht weiter." },
  {
    start: 50500,
    end: 54000,
    text: "Noch knapp zehn Minuten zu spielen in dieser spannenden Partie.",
  },
  {
    start: 54500,
    end: 58000,
    text: "Beide Mannschaften kämpfen jetzt um jeden einzelnen Ball auf dem Platz.",
  },
  { start: 58500, end: 60000, text: "Das war's fürs Erste, vielen Dank fürs Zuschauen." },
];

export const useTimelineSegmentAnnotationStore = defineStore("timelineSegmentAnnotation", () => {
  const timelineSegmentAnnotations = ref({});
  const isLoading = ref(false);

  // Backdoor for testing the Transcript/Wordcloud tab without a real Whisper run (see
  // TranscriptDataMenu.vue's "demo transcript" button, the only place this is called from) --
  // reset alongside the rest of the video-bound state in AnalysisView.vue's onBeforeUnmount
  // (mirrors eventsStore.resetEventData), not on every store refetch, so it survives an
  // unrelated plugin run finishing while it's being tested.
  const demoTranscriptActive = ref(false);
  const loadDemoTranscript = () => {
    demoTranscriptActive.value = true;
  };
  const resetDemoTranscript = () => {
    demoTranscriptActive.value = false;
  };

  const all = computed(() => Object.values(timelineSegmentAnnotations));

  const transcriptSegments = computed(() => {
    if (demoTranscriptActive.value) {
      return DEMO_TRANSCRIPT_SEGMENTS.map((segment, i) => ({
        id: i + 1,
        category: { name: "Transcript" },
        name: segment.text,
        start: segment.start,
        end: segment.end,
      }));
    }

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
          annotation = annotationStore.getAnnotation(segmentAnnotation.annotation_id);
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
    demoTranscriptActive,
    loadDemoTranscript,
    resetDemoTranscript,
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
