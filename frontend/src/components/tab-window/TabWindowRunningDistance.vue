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

      <template #item="{ item, columns }">
        <tr
          :style="{
            backgroundColor: toRgb(item.team_id, 0.7),
          }"
        >
          <td v-for="col in columns" :key="col.key">
            {{ item[col.key] }}
          </td>
        </tr>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useVisualizationStore } from "@/stores/visualization";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import RunningDistanceTimeSelector from "../visualization/RunningDistanceTimeSelector.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

const { t } = useI18n();

const allFrameKeys = computed(() =>
  Object.keys(topViewStore.positionDataTopView)
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
    topViewStore.positionDataTopView[frame]?.some((p) => p[4] === halfId)
  );
}
function findLastFrameWithHalftime(halfId) {
  const reversed = [...allFrameKeys.value].reverse();
  return reversed.find((frame) =>
    topViewStore.positionDataTopView[frame]?.some((p) => p[4] === halfId)
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
      selectedStartFrame.value = findFirstFrameWithHalftime("firstHalf");
      selectedEndFrame.value = findLastFrameWithHalftime("firstHalf");
    } else if (second) {
      selectedStartFrame.value = findFirstFrameWithHalftime("secondHalf");
      selectedEndFrame.value = findLastFrameWithHalftime("secondHalf");
    }
  },
  { immediate: true }
);

const headers = [
  { title: t("visualization.running_distance.player_id"), key: "player_id" },
  { title: t("visualization.running_distance.team_id"), key: "team_id" },
  { title: t("visualization.running_distance.distance"), key: "distance" },
  { title: "", key: "settings", sortable: false, align: "end", width: "1px" },
];

const items = computed(() => {
  const distancesByPlayerId = new Map();

  const allTimes = Object.keys(topViewStore.positionDataTopView).map(Number);

  const timeRange = allTimes.filter(
    (t) =>
      t >= selectedStartFrame.value &&
      t <= selectedEndFrame.value &&
      (!visualizationStore.showProgress || t <= playerStore.currentTime)
  );

  const allPlayersSet = new Map();

  for (const frame of allTimes) {
    const players = topViewStore.positionDataTopView[frame];
    if (!players) continue;
    for (const p of players) {
      if (p[1] === "#000000") continue;
      if (
        (visualizationStore.showAggregatedFirst && p[4] !== 1) ||
        (visualizationStore.showAggregatedSecond && p[4] !== 2)
      ) {
        continue;
      }
      if (!allPlayersSet.has(p[0])) {
        allPlayersSet.set(p[0], {
          player_id: p[0],
          team_id: p[1],
        });
      }
    }
  }
  for (const player of allPlayersSet.values()) {
    distancesByPlayerId.set(player.player_id, {
      ...player,
      distance: 0,
    });
  }

  if (timeRange.length > 1) {
    for (let i = 1; i < timeRange.length; i++) {
      const tPrev = timeRange[i - 1];
      const tCurr = timeRange[i];

      const playersPrev = topViewStore.positionDataTopView[tPrev];
      const playersCurr = topViewStore.positionDataTopView[tCurr];

      if (!playersPrev || !playersCurr) continue;

      for (const currPlayer of playersCurr) {
        if (currPlayer[1] === "#000000") continue;

        const prevPlayer = playersPrev.find((p) => p[0] === currPlayer[0]);
        if (!prevPlayer) continue;

        if (
          (visualizationStore.showAggregatedFirst && currPlayer[4] !== 1) ||
          (visualizationStore.showAggregatedSecond && currPlayer[4] !== 2)
        ) {
          continue;
        }

        const dx = (currPlayer[2] - prevPlayer[2]) * playerStore.video.field_length;
        const dy = (currPlayer[3] - prevPlayer[3]) * playerStore.video.field_width;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (!distancesByPlayerId.has(currPlayer[0])) {
          distancesByPlayerId.set(currPlayer[0], {
            player_id: currPlayer[0],
            team_id: currPlayer[1],
            distance: 0,
          });
        }

        distancesByPlayerId.get(currPlayer[0]).distance += dist;
      }
    }
  }
  return Array.from(distancesByPlayerId.values())
    .map((item) => ({
      ...item,
      distance: item.distance.toFixed(2),
    }))
    .sort((a, b) => a.player_id - b.player_id);
});

const hasPositionData = computed(() => {
  return Object.keys(topViewStore.positionDataTopView).length > 0;
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
