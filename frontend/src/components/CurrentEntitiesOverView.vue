<template>
  <v-row align="center" justify="center" class="px-2 py-2">
    <v-col cols="12">
      <div class="pa-4">
        <div v-for="(item, i) in current_annotations" :key="i" class="my-2">
          <v-progress-linear :color="item.color" height="30" rounded
            :value="((time - item.start) / (item.end - item.start)) * 100">
            <v-tooltip top>
              <template v-slot:activator="{ on, attrs }">
                <span v-bind="attrs" v-on="on" class="mx-2" style="
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                  ">{{ item.timeline_name }} :: {{ item.name }}</span></template>
              <span>{{ item.timeline_name }} :: {{ item.name }}</span>
            </v-tooltip>
          </v-progress-linear>
        </div>
      </div>
    </v-col>
  </v-row>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { usePlayerStore } from '../stores/player';
import { useTimelineSegmentAnnotationStore } from '../stores/timeline_segment_annotation';
import { useAnnotationStore } from '../stores/annotation';
import { useTimelineSegmentStore } from '../stores/timeline_segment';
import { useTimelineStore } from '../stores/timeline';
import TimeMixin from '../mixins/time';
import { mapStores } from 'pinia';

export default {
  setup() {
    // Pinia Stores
    const playerStore = usePlayerStore();
    const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
    const annotationStore = useAnnotationStore();
    const timelineSegmentStore = useTimelineSegmentStore();
    const timelineStore = useTimelineStore();

    // Reaktive Variablen für Zeit und Annotationen
    const time = computed(() => playerStore.currentTime);
    const annotations = computed(() => {
      const annotationsMap = {};
      timelineSegmentAnnotationStore.all.forEach((annotation) => {
        const timelineSegment = timelineSegmentStore.get(annotation.timeline_segment_id);
        const annotationData = annotationStore.get(annotation.annotation_id);

        annotationsMap[annotation.id] = {
          name: annotationData ? annotationData.name : null,
          timeline_name: timelineStore.get(timelineSegment.timeline_id).name,
          color: annotationData ? annotationData.color : "white",
          id: annotation.id,
          start: timelineSegment ? timelineSegment.start : 0,
          end: timelineSegment ? timelineSegment.end : 0,
        };
      });
      return annotationsMap;
    });

    const annotationsByTime = computed(() => {
      let lut = {};
      for (let t = 0; t < Math.ceil(playerStore.videoDuration); t++) {
        lut[t] = [];
        for (const annotation of Object.values(annotations.value)) {
          if (annotation.start <= t && t < annotation.end) {
            lut[t].push(annotation.id);
          }
        }
      }
      return lut;
    });

    const current_annotations = computed(() => {
      const currentTime = Math.round(time.value);
      return annotationsByTime.value[currentTime]?.map((id) => annotations.value[id]) || [];
    });

    // Rückgabe von Computed Properties und Stores für das Template
    return {
      time,
      current_annotations,
      ...mapStores(usePlayerStore, useAnnotationStore, useTimelineStore, useTimelineSegmentAnnotationStore, useTimelineSegmentStore),
    };
  },
  mixins: [TimeMixin],
};
</script>
