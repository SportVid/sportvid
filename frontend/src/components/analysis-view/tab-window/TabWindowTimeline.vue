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
    <v-row align="center">
      <v-col cols="3" class="mt-1 d-flex justify-end" style="margin: 0px; padding: 0px">
        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" style="height: 40px" size="small">
              <v-icon>mdi-timer-sync-outline</v-icon>
            </v-btn>
          </template>
          <v-list class="py-0" density="compact" width="250px">
            <v-list-item
              class="menu-item"
              @click="playerStore.setSelectedTimeRangeStart(playerStore.currentTime)"
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.sync_start") }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="playerStore.setSelectedTimeRangeEnd(playerStore.currentTime)"
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.sync_end") }}
              </v-list-item-title>
            </v-list-item>

            <v-divider />

            <v-list-item
              class="menu-item"
              @click="
                playerStore.setSelectedTimeRangeStart(0);
                playerStore.setSelectedTimeRangeEnd(playerStore.videoDuration);
              "
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.full_video") }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
      <v-col cols="9" class="mt-2">
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

<style scoped>
.menu-item {
  cursor: pointer;
}
.menu-item:hover {
  background-color: #f0f0f0;
}
.menu-item .v-list-item-title {
  font-size: 12px;
}
</style>
