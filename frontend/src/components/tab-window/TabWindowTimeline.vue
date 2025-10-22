<template>
  <v-row
    v-if="!num_timelines"
    class="text-h6 text-grey font-weight-light mx-16 px-10"
    style="
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1.5;
      height: 25vh;
    "
    v-html="$t('visualization.timeline.not_available')"
  />

  <v-card v-else class="d-flex flex-column flex-nowrap px-2 mb-n2">
    <v-row>
      <v-col cols="9" offset="3" class="mt-2">
        <TimelineTimeSelector class="ml-n1" />
      </v-col>
    </v-row>

    <v-sheet class="px-4 mb-6 mt-2">
      <Timeline ref="timeline" :style="{ width: '100%' }" />
    </v-sheet>
  </v-card>
</template>

<script setup>
import { computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import Timeline from "@/components/timeline/Timeline.vue";
import TimelineTimeSelector from "@/components/timeline/TimelineTimeSelector.vue";

const playerStore = usePlayerStore();

const num_timelines = computed(() => playerStore.video?.num_timelines);
</script>
