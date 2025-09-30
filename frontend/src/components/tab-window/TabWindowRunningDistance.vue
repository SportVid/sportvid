<template>
  <!-- <v-row
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
  /> -->

  <v-card class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <RunningDistanceTimeSelector class="ml-n1" />

    <div class="player-selector mt-2">
      <div
        v-for="playerId in playerOptions"
        :key="playerId"
        class="player-dot"
        :style="{
          backgroundColor: selectedPlayerIds.has(playerId)
            ? toRgb(playerColors[playerId], 0)
            : toRgb(playerColors[playerId], 0.7),
          color: selectedPlayerIds.has(playerId) ? '#fff' : '#222',
          borderColor: selectedPlayerIds.has(playerId)
            ? toRgb(playerColors[playerId], 0)
            : toRgb(playerColors[playerId], 0.7),
        }"
        @click="togglePlayerId(playerId)"
      >
        {{ playerId }}
      </div>
    </div>

    <v-data-table
      color="primary"
      :items-per-page="-1"
      :headers="headers"
      :items="runningDistanceItems"
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
            backgroundColor: toRgb(visualizationStore.getTeamColor(item.team_id), 0.7),
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
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import RunningDistanceTimeSelector from "../visualization/RunningDistanceTimeSelector.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const positionDataStore = usePositionDataStore();

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
    topViewStore.positionDataTopView[frame]?.some((p) => p[2] === halfId)
  );
}
function findLastFrameWithHalftime(halfId) {
  const reversed = [...allFrameKeys.value].reverse();
  return reversed.find((frame) =>
    topViewStore.positionDataTopView[frame]?.some((p) => p[2] === halfId)
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
      selectedStartFrame.value = findFirstFrameWithHalftime(1);
      selectedEndFrame.value = findLastFrameWithHalftime(1);
    } else if (second) {
      selectedStartFrame.value = findFirstFrameWithHalftime(2);
      selectedEndFrame.value = findLastFrameWithHalftime(2);
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

const playerOptions = ref(new Set());
const selectedPlayerIds = ref(new Set());
const playerColors = ref({});
watch(
  () => topViewStore.positionDataTopView,
  (newVal) => {
    const all = Object.values(newVal)
      .flat()
      .filter((p) => p[1] !== 1);

    selectedPlayerIds.value = new Set(all.map((p) => p[0]).sort((a, b) => a - b));
    playerOptions.value = Array.from(selectedPlayerIds.value);

    const map = {};
    all.forEach((p) => {
      map[p[0]] = visualizationStore.getTeamColor(p[1]);
    });
    playerColors.value = map;
  },
  { immediate: true, deep: true }
);
const togglePlayerId = (playerId) => {
  const newSet = new Set(selectedPlayerIds.value);
  if (newSet.has(playerId)) {
    newSet.delete(playerId);
  } else {
    newSet.add(playerId);
  }
  selectedPlayerIds.value = newSet;
};

const runningDistanceItems = computed(() => {
  return positionDataStore.calculateRunningDistances(
    selectedPlayerIds.value,
    selectedStartFrame.value,
    selectedEndFrame.value
  );
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

.player-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: center;
  margin: 12px 0 8px 0;
}
.player-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s;
  user-select: none;
}
.player-dot.selected {
  border: 2px solid;
}
</style>
