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
    <v-row align="center">
      <v-col cols="3" class="mt-3 d-flex align-center" style="gap: 8px">
        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" style="height: 40px; flex: 1">
              <v-icon left>mdi-cog</v-icon>
              {{ $t("modal.timeline.options") }}
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" width="150px">
            <v-menu location="end" open-on-hover>
              <template #activator="{ props }">
                <v-list-item v-bind="props" class="menu-item">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.time_selection.title") }}
                    <v-icon>mdi-chevron-right</v-icon>
                  </v-list-item-title>
                </v-list-item>
              </template>

              <v-list class="py-0" density="compact" width="150px">
                <v-list-item
                  class="menu-item"
                  @click="
                    positionDataStore.setSelectedTimeRangeStart(allFrameKeys[0]);
                    positionDataStore.setSelectedTimeRangeEnd(
                      allFrameKeys[allFrameKeys.length - 1]
                    );
                  "
                >
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.time_selection.full_match") }}
                  </v-list-item-title>
                </v-list-item>

                <v-list-item
                  class="menu-item"
                  @click="
                    positionDataStore.setSelectedTimeRangeStart(findFirstFrameWithHalftime(1));
                    positionDataStore.setSelectedTimeRangeEnd(findLastFrameWithHalftime(1));
                  "
                  :disabled="!visualizationStore.halftimesExist"
                >
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.time_selection.first_half") }}
                  </v-list-item-title>
                </v-list-item>

                <v-list-item
                  class="menu-item"
                  @click="
                    positionDataStore.setSelectedTimeRangeStart(findFirstFrameWithHalftime(2));
                    positionDataStore.setSelectedTimeRangeEnd(findLastFrameWithHalftime(2));
                  "
                  :disabled="!visualizationStore.halftimesExist"
                >
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.time_selection.second_half") }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>

            <v-menu location="end" open-on-hover>
              <template #activator="{ props }">
                <v-list-item v-bind="props" class="menu-item">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.kpi_selection.title") }}
                    <v-icon>mdi-chevron-right</v-icon>
                  </v-list-item-title>
                </v-list-item>
              </template>

              <v-list class="py-0" density="compact" width="175px">
                <v-list-item class="menu-item" @click="">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.kpi_selection.running_distance") }}
                    <tab-window-icon> mdi-check </tab-window-icon>
                  </v-list-item-title>
                </v-list-item>

                <v-list-item class="menu-item" @click="">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.kpi_selection.velocity_max") }}
                    <tab-window-icon> mdi-check </tab-window-icon>
                  </v-list-item-title>
                </v-list-item>

                <v-list-item class="menu-item" @click="">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.kpi_selection.velocity_mean") }}
                    <tab-window-icon> mdi-check </tab-window-icon>
                  </v-list-item-title>
                </v-list-item>

                <v-list-item class="menu-item" @click="">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("data.options.kpi_selection.metabolic_power") }}
                    <tab-window-icon> mdi-check </tab-window-icon>
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-list>
        </v-menu>

        <v-btn-toggle
          v-model="viewMode"
          color="primary"
          border
          mandatory
          elevation="2"
          style="height: 40px"
        >
          <v-btn value="table">
            <v-icon>mdi-table</v-icon>
          </v-btn>

          <v-btn value="chart">
            <v-icon>mdi-chart-line</v-icon>
          </v-btn>
        </v-btn-toggle>

        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" style="height: 40px">
              <v-icon left>mdi-link</v-icon>
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" width="250px">
            <v-list-item
              class="menu-item"
              @click="positionDataStore.setSelectedTimeRangeStart(playerStore.currentTime)"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.time_sync.sync_start") }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="positionDataStore.setSelectedTimeRangeEnd(playerStore.currentTime)"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("data.time_sync.sync_end") }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
      <v-col cols="9" class="mt-2">
        <RunningDistanceTimeSelector class="ml-n1" />
      </v-col>
    </v-row>

    <div v-if="viewMode === 'table'" class="team-tables d-flex flex-wrap justify-space-around">
      <v-card
        v-for="(teamPlayers, teamId) in runningDistanceTeamItems"
        :key="teamId"
        class="team-card pa-4 ma-2"
        outlined
        :style="{ backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.8) }"
      >
        <v-card-title class="text-center mt-n1">{{ getTeamName(teamId) }}</v-card-title>

        <div class="player-selector mb-3">
          <div
            v-for="p in playerOptions.filter((p) => p.teamId == teamId)"
            :key="p.playerId"
            class="player-dot"
            :style="{
              backgroundColor: selectedPlayerIds.has(p.playerId)
                ? toRgb(playerColors[p.playerId], 0)
                : toRgb(playerColors[p.playerId], 0.6),
              color: selectedPlayerIds.has(p.playerId) ? '#fff' : '#222',
              borderColor: selectedPlayerIds.has(p.playerId)
                ? toRgb(playerColors[p.playerId], 0)
                : toRgb(playerColors[p.playerId], 0.6),
            }"
            @click="togglePlayerId(p.playerId)"
          >
            {{ getPlayerNumber(p.playerId) }}
          </div>
        </div>

        <v-data-table
          color="primary"
          :headers="headers"
          :items="teamPlayers"
          class="elevation-2"
          hide-default-footer
          density="compact"
        >
          <template #item="{ item, columns }">
            <tr
              :style="{
                backgroundColor: toRgb(visualizationStore.getTeamColor(item.team_id), 0.6),
              }"
            >
              <td v-for="col in columns" :key="col.key">
                {{ col.key === "player_id" ? getPlayerNumber(item[col.key]) : item[col.key] }}
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-card>
    </div>

    <div v-else class="d-flex align-center justify-center" style="min-height: 25vh">
      <span class="text-h6 text-grey font-weight-light">
        {{ $t("data.options.view.chart_placeholder") }}
      </span>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import RunningDistanceTimeSelector from "../kpi/RunningDistanceTimeSelector.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();

const { t } = useI18n();

const viewMode = ref("table");

const allFrameKeys = computed(() =>
  Object.keys(topViewStore.positionDataTopView)
    .map(Number)
    .sort((a, b) => a - b)
);
const selectedStartFrame = computed(() => positionDataStore.selectedTimeRange.start);
const selectedEndFrame = computed(() => positionDataStore.selectedTimeRange.end);
const maxFrameIndex = ref(0);
watch(
  () => allFrameKeys.value,
  (keys) => {
    selectedStartFrame.value = keys[0];
    selectedEndFrame.value = keys[keys.length - 1];
    maxFrameIndex.value = keys[keys.length - 1];
  }
);

const headers = [
  { title: t("visualization.running_distance.player_id"), key: "player_id" },
  { title: t("visualization.running_distance.distance"), key: "distance" },
];

const playerOptions = ref([]);
const selectedPlayerIds = ref(new Set());
const playerColors = ref({});
watch(
  () => topViewStore.positionDataTopView,
  (newVal) => {
    const all = Object.values(newVal)
      .flat()
      .filter((p) => p[1] !== 1);

    selectedPlayerIds.value = new Set(all.map((p) => p[0]).sort((a, b) => a - b));
    playerOptions.value = all
      .map((p) => ({ playerId: p[0], teamId: p[1] }))
      .filter((v, i, a) => a.findIndex((x) => x.playerId === v.playerId) === i)
      .sort((a, b) => a.playerId - b.playerId);

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
const runningDistanceTeamItems = computed(() => {
  const grouped = {};
  playerOptions.value.forEach((p) => {
    if (!grouped[p.teamId]) grouped[p.teamId] = [];
  });
  runningDistanceItems.value.forEach((item) => {
    if (!grouped[item.team_id]) grouped[item.team_id] = [];
    grouped[item.team_id].push(item);
  });
  return grouped;
});

const hasPositionData = computed(() => {
  return Object.keys(topViewStore.positionDataTopView).length > 0;
});

const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return teamId;
};

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};
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
  margin-bottom: 8px;
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

.team-tables {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: flex-start;
}

.team-card {
  flex: 1 1 300px;
  max-width: 45%;
}
</style>
