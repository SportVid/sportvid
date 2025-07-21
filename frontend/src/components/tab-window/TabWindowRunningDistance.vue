<template>
  <v-row
    v-if="!hasPositionData"
    class="text-h6 text-grey font-weight-light mx-16 px-10"
    style="
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1.5;
      height: 25vh;
    "
    v-html="$t('visualization.running_distance.not_selected')"
  />

  <v-card v-else class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <RunningDistanceTimeSelector
      class="ml-n1"
      :duration="maxFrameIndex"
      v-model:start="selectedStartFrame"
      v-model:end="selectedEndFrame"
    />

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
import { ref, computed, watch } from "vue";
import { useVisualizationStore } from "@/stores/visualization";
import { useBboxesStore } from "@/stores/bboxes";
import { usePlayerStore } from "@/stores/player";

import RunningDistanceTimeSelector from "../visualization/RunningDistanceTimeSelector.vue";
import { useI18n } from "vue-i18n";

const bboxesStore = useBboxesStore();
const playerStore = usePlayerStore();
const visualizationStore = useVisualizationStore();

const { t } = useI18n();

const allFrameKeys = computed(() =>
  Object.keys(bboxesStore.bboxDataTopView)
    .map(Number)
    .sort((a, b) => a - b)
);
const selectedStartFrame = ref(0);
const selectedEndFrame = ref(0);
const maxFrameIndex = ref(0);
watch(
  () => allFrameKeys.value,
  (keys) => {
    selectedStartFrame.value = keys[0];
    selectedEndFrame.value = keys[keys.length - 1];
    maxFrameIndex.value = keys[keys.length - 1];
  }
);

function findFirstFrameWithHalftime(halfId) {
  return allFrameKeys.value.find((frame) =>
    bboxesStore.bboxDataTopView[frame]?.some((p) => p.halftime_id === halfId)
  );
}
function findLastFrameWithHalftime(halfId) {
  const reversed = [...allFrameKeys.value].reverse();
  return reversed.find((frame) =>
    bboxesStore.bboxDataTopView[frame]?.some((p) => p.halftime_id === halfId)
  );
}
watch(
  () => [
    visualizationStore.showAggregatedFull,
    visualizationStore.showAggregatedFirst,
    visualizationStore.showAggregatedSecond,
  ],
  ([full, first, second]) => {
    if (full) {
      selectedStartFrame.value = allFrameKeys.value[0];
      selectedEndFrame.value = allFrameKeys.value[allFrameKeys.value.length - 1];
    } else if (first) {
      selectedStartFrame.value = findFirstFrameWithHalftime("hf_1");
      selectedEndFrame.value = findLastFrameWithHalftime("hf_1");
    } else if (second) {
      selectedStartFrame.value = findFirstFrameWithHalftime("hf_2");
      selectedEndFrame.value = findLastFrameWithHalftime("hf_2");
    }
  },
  { immediate: true }
);

const headers = [
  { title: t("visualization.running_distance.id"), key: "ref_id" },
  { title: t("visualization.running_distance.team"), key: "team_id" },
  { title: t("visualization.running_distance.distance"), key: "distance" },
  { title: "", key: "settings", sortable: false, align: "end", width: "1px" },
];

const items = computed(() => {
  const distancesByRefId = new Map();

  const allTimes = Object.keys(bboxesStore.bboxDataTopView)
    .map(Number)
    .sort((a, b) => a - b);

  const currentTime = playerStore.currentTime;

  const timeRange = allTimes.filter(
    (t) =>
      t >= selectedStartFrame.value &&
      t <= selectedEndFrame.value &&
      (!visualizationStore.showProgress || t <= currentTime)
  );

  const allPlayersSet = new Map();

  for (const frame of allTimes) {
    const players = bboxesStore.bboxDataTopView[frame];
    if (!players) continue;
    for (const p of players) {
      if (
        (visualizationStore.showAggregatedFirst && p.halftime_id !== "hf_1") ||
        (visualizationStore.showAggregatedSecond && p.halftime_id !== "hf_2")
      ) {
        continue;
      }
      if (!allPlayersSet.has(p.ref_id)) {
        allPlayersSet.set(p.ref_id, {
          ref_id: p.ref_id,
          team_id: p.team_id ?? "-",
        });
      }
    }
  }
  for (const player of allPlayersSet.values()) {
    distancesByRefId.set(player.ref_id, {
      ...player,
      distance: 0,
    });
  }

  if (timeRange.length > 1) {
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

        const dx = (currPlayer.new_x - prevPlayer.new_x) * playerStore.video.field_length;
        const dy = (currPlayer.new_y - prevPlayer.new_y) * playerStore.video.field_width;
        const dist = Math.sqrt(dx * dx + dy * dy);

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
  }
  return Array.from(distancesByRefId.values())
    .map((item) => ({
      ...item,
      distance: item.distance.toFixed(2),
    }))
    .sort((a, b) => a.ref_id - b.ref_id);
});

const hasPositionData = computed(() => {
  return Object.keys(bboxesStore.bboxDataTopView).length > 0;
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
