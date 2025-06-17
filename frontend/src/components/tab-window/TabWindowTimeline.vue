<template>
  <v-card class="d-flex flex-column flex-nowrap px-2 mb-n2">
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
import Timeline from "@/components/timeline/Timeline.vue";
import TimelineTimeSelector from "@/components/timeline/TimelineTimeSelector.vue";
</script>
