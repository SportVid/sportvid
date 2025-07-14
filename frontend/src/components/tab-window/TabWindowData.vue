<template>
  <v-card class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <TableTimeSelector class="ml-n1" />

    <v-data-table
      color="primary"
      :items-per-page="-1"
      :headers="headers"
      :items="items"
      class="elevation-2 my-2"
      hide-default-footer
    >
      <template #header.settings>
        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon variant="text" size="small" color="primary">
              <v-icon>mdi-cog</v-icon>
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" width="220">
            <v-list-item class="menu-item" @click="visualizationStore.viewAggregatedFull">
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.options.aggregated_full") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !visualizationStore.showAggregatedFull,
                    'text-red': visualizationStore.showAggregatedFull,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="visualizationStore.viewAggregatedFirst"
              :disabled="!visualizationStore.halftimesExist"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.options.aggregated_first") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !visualizationStore.showAggregatedFirst,
                    'text-red': visualizationStore.showAggregatedFirst,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="visualizationStore.viewAggregatedSecond"
              :disabled="!visualizationStore.halftimesExist"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.options.aggregated_second") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !visualizationStore.showAggregatedSecond,
                    'text-red': visualizationStore.showAggregatedSecond,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>

            <v-list-item class="menu-item" @click="visualizationStore.viewProgress">
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.options.progress") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !visualizationStore.showProgress,
                    'text-red': visualizationStore.showProgress,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup>
import { computed } from "vue";
import { useVisualizationStore } from "@/stores/visualization";
import { useBboxesStore } from "@/stores/bboxes";
import { usePlayerStore } from "@/stores/player";
import { distance } from "mathjs";
import TableTimeSelector from "../visualization/TableTimeSelector.vue";

const bboxesStore = useBboxesStore();
const playerStore = usePlayerStore();
const visualizationStore = useVisualizationStore();

const headers = [
  { title: "ID", key: "ref_id" },
  { title: "Mannschaft", key: "team_id" },
  { title: "Distance [m]", key: "distance" },
  { title: "", key: "settings", sortable: false, align: "end", width: "1px" },
];

const items = computed(() => {
  const distancesByRefId = new Map();

  const allTimes = Object.keys(bboxesStore.bboxDataTopView)
    .map(Number)
    .sort((a, b) => a - b);

  const currentTime = computed(() => playerStore.currentTime);

  let timeRange = allTimes;

  if (visualizationStore.showProgress) {
    timeRange = allTimes.filter((t) => t <= currentTime.value);
  }

  if (timeRange.length < 2) {
    return [];
  }

  for (let i = 1; i < timeRange.length; i++) {
    const tPrev = timeRange[i - 1];
    const tCurr = timeRange[i];

    const playersPrev = bboxesStore.bboxDataTopView[tPrev];
    const playersCurr = bboxesStore.bboxDataTopView[tCurr];

    if (!playersPrev || !playersCurr) continue;

    for (const currPlayer of playersCurr) {
      const prevPlayer = playersPrev.find((p) => p.ref_id === currPlayer.ref_id);
      if (!prevPlayer) continue;

      if (
        (visualizationStore.showAggregatedFirst && currPlayer.halftime_id !== "hf_1") ||
        (visualizationStore.showAggregatedSecond && currPlayer.halftime_id !== "hf_2")
      ) {
        continue;
      }

      const dist = distance(
        [currPlayer.new_x, currPlayer.new_y],
        [prevPlayer.new_x, prevPlayer.new_y]
      );

      if (!distancesByRefId.has(currPlayer.ref_id)) {
        distancesByRefId.set(currPlayer.ref_id, {
          ref_id: currPlayer.ref_id,
          team_id: currPlayer.team_id ?? "-",
          distance: 0,
        });
      }

      distancesByRefId.get(currPlayer.ref_id).distance += dist;
    }
  }

  return Array.from(distancesByRefId.values())
    .map((item) => ({
      ...item,
      distance: item.distance.toFixed(2),
    }))
    .sort((a, b) => a.ref_id - b.ref_id);
});
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
