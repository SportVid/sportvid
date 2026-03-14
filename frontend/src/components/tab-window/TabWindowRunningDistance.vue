<template>
  <v-row v-if="videoStore.isLoading" class="loading-card">
    <div class="spinner">
      <i class="mdi mdi-loading mdi-spin" />
    </div>
    <div class="loading-text">{{ $t("loading_screen") }}</div>
  </v-row>

  <v-row
    v-else-if="!hasPositionData"
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
    <v-row align="center" class="flex-nowrap">
      <v-col cols="auto" class="mt-3 d-flex align-center flex-shrink-0" style="gap: 8px">
        <v-btn-toggle
          v-model="viewMode"
          color="primary"
          border
          mandatory
          elevation="2"
          style="height: 40px"
          class="ml-2 mt-n2"
          density="compact"
        >
          <v-btn value="table" size="small">
            <v-icon size="small">mdi-table</v-icon>
          </v-btn>

          <v-btn value="chart" size="small">
            <v-icon size="small">mdi-chart-line</v-icon>
          </v-btn>
        </v-btn-toggle>

        <v-btn-toggle
          v-model="groupMode"
          color="primary"
          border
          mandatory
          elevation="2"
          style="height: 40px"
          density="compact"
          class="mt-n2"
        >
          <v-btn value="player" size="small">
            <v-icon size="small">mdi-account</v-icon>
          </v-btn>

          <v-btn value="team" size="small">
            <v-icon size="small">mdi-account-group</v-icon>
          </v-btn>
        </v-btn-toggle>

        <v-menu location="bottom" :close-on-content-click="false">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" style="height: 40px" class="mt-n2">
              {{ $t("visualization.running_distance.kpi_selection.title") }}
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" width="300px">
            <template v-for="option in kpiOptions" :key="option.id">
              <v-list-item class="menu-item" @click="toggleKpi(option)">
                <v-list-item-title class="d-flex align-center" style="gap: 4px">
                  <template v-if="option.id === 'running_distance_interval'">
                    <i18n-t
                      keypath="visualization.running_distance.kpi_selection.running_distance_interval"
                      tag="span"
                      class="flex-grow-1"
                    >
                      <template #frames>
                        <input
                          v-model.number="windowFrames"
                          type="number"
                          min="1"
                          class="inline-frame-input"
                          :style="{ width: inputWidth }"
                          @click.stop
                          @keydown.stop
                          @blur="onFrameInputBlur"
                        />
                      </template>
                    </i18n-t>
                  </template>
                  <span v-else class="flex-grow-1">
                    {{ $t(`visualization.running_distance.kpi_selection.${option.id}`) }}
                  </span>
                  <v-icon v-if="isKpiSelected(option)" size="small">mdi-check</v-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
          </v-list>
        </v-menu>

        <v-menu location="bottom" :close-on-content-click="false">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" style="height: 40px" class="mt-n2">
              {{ $t("visualization.running_distance.zone_selection.title") }}
            </v-btn>
          </template>

          <ZoneSelectorPicker
            v-model="selectedZones"
            :sport="topViewStore.currentSport"
            :area-size="topViewStore.currentAreaSize"
          />
        </v-menu>

        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" style="height: 40px" class="mt-n2">
              <v-icon size="small">mdi-timer-sync-outline</v-icon>
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" width="250px">
            <v-list-item
              class="menu-item"
              @click="positionDataStore.setSelectedTimeRangeStart(playerStore.currentTime)"
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.sync_start") }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="positionDataStore.setSelectedTimeRangeEnd(playerStore.currentTime)"
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.sync_end") }}
              </v-list-item-title>
            </v-list-item>

            <v-divider />

            <v-list-item
              class="menu-item"
              @click="
                positionDataStore.setSelectedTimeRangeStart(allFrameKeys[0]);
                positionDataStore.setSelectedTimeRangeEnd(allFrameKeys[allFrameKeys.length - 1]);
              "
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.full_match") }}
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
              <v-list-item-title>
                {{ $t("visualization.time_selection.first_half") }}
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
              <v-list-item-title>
                {{ $t("visualization.time_selection.second_half") }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
      <v-col class="mt-2">
        <RunningDistanceTimeSelector class="ml-n1" />
      </v-col>
    </v-row>

    <div
      v-if="viewMode === 'table' && groupMode === 'player'"
      class="team-tables d-flex flex-wrap justify-space-around"
    >
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
          :headers="playerHeaders"
          :items="teamPlayers"
          :items-per-page="-1"
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

          <template #body.append>
            <tr
              :style="{
                fontWeight: 'bold',
                backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.45),
              }"
            >
              <td>{{ $t("visualization.running_distance.player_view.best") }}</td>
              <td>{{ getTeamBest(teamPlayers) }}</td>
            </tr>
            <tr
              :style="{
                fontWeight: 'bold',
                backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.45),
              }"
            >
              <td>{{ $t("visualization.running_distance.player_view.total") }}</td>
              <td>{{ getTeamTotal(teamPlayers) }}</td>
            </tr>
          </template>
        </v-data-table>
      </v-card>
    </div>

    <div
      v-else-if="viewMode === 'table' && groupMode === 'team'"
      class="team-tables d-flex flex-wrap justify-space-around"
    >
      <v-card
        v-for="row in runningDistanceTeamAggregated"
        :key="row.team_id"
        class="team-card pa-4 ma-2"
        outlined
        :style="{ backgroundColor: toRgb(visualizationStore.getTeamColor(row.team_id), 0.8) }"
      >
        <v-card-title class="text-center mt-n1">{{ getTeamName(row.team_id) }}</v-card-title>

        <v-data-table
          color="primary"
          :headers="teamHeaders"
          :items="[row]"
          :items-per-page="-1"
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
                {{ item[col.key] }}
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-card>
    </div>

    <div v-else-if="viewMode === 'chart'" class="px-2 mt-2">
      <KpiChart
        :selectedPlayerIds="selectedPlayerIds"
        :selectedKpi="chartKpi"
        :groupMode="groupMode"
        :chartMode="chartMode"
        :windowSize="chartWindowSize"
        :windowFrames="windowFrames"
        :playerOptions="playerOptions"
        :playerColors="playerColors"
        :selectedZones="selectedZones"
      />

      <div v-if="groupMode === 'player'" class="chart-legend mt-2">
        <div v-for="(players, teamId) in teamGroups" :key="teamId" class="chart-legend-team">
          <div
            class="team-dot"
            :style="{
              backgroundColor: isTeamFullySelected(teamId)
                ? toRgb(visualizationStore.getTeamColor(teamId), 0)
                : 'transparent',
              color: isTeamFullySelected(teamId)
                ? '#fff'
                : toRgb(visualizationStore.getTeamColor(teamId), 0),
              borderColor: toRgb(visualizationStore.getTeamColor(teamId), 0),
            }"
            @click="toggleTeam(teamId)"
          >
            {{ getTeamName(teamId) }}
          </div>
          <span class="chart-legend-sep">|</span>
          <div
            v-for="p in players"
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
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, toRaw } from "vue";
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import RunningDistanceTimeSelector from "../kpi/RunningDistanceTimeSelector.vue";
import KpiChart from "../kpi/KpiChart.vue";
import ZoneSelectorPicker from "../kpi/ZoneSelectorPicker.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";
import { debounce } from "lodash";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();
const posdataWorkerStore = usePosdataWorkerStore();
const videoStore = useVideoStore();

const { t } = useI18n();

const viewMode = ref("table");
const groupMode = ref("player");

// Initialize with all 25 pitch zones selected (full pitch)
const LONG_BOUNDS = [0, 0.2025, 0.365, 0.635, 0.7955, 1];
const TRANS_BOUNDS = [0, 0.1575, 0.33, 0.67, 0.8425, 1];
const initialZones = [];
for (let r = 0; r < 5; r++) {
  for (let c = 0; c < 5; c++) {
    initialZones.push({ x0: TRANS_BOUNDS[c], y0: LONG_BOUNDS[r], x1: TRANS_BOUNDS[c + 1], y1: LONG_BOUNDS[r + 1] });
  }
}
const selectedZones = ref(initialZones);

const kpiOptions = [
  { id: "running_distance_cumulative", kpi: "running_distance", mode: "cumulative" },
  { id: "running_distance_interval", kpi: "running_distance", mode: "windowed" },
  { id: "velocity_max", kpi: "velocity_max", mode: "cumulative" },
  { id: "velocity_mean", kpi: "velocity_mean", mode: "cumulative" },
  { id: "metabolic_work", kpi: "metabolic_work", mode: "cumulative" },
];

// Chart mode: single selected option (includes mode + window info)
const selectedKpiId = ref("running_distance_cumulative");
// Table mode: set of KPI ids (independent selection)
const selectedKpis = ref(new Set(["running_distance_cumulative"]));

// User-configurable interval in frames (default: 10)
const windowFrames = ref(10);

const onFrameInputBlur = () => {
  if (!windowFrames.value || windowFrames.value < 1 || isNaN(windowFrames.value)) {
    windowFrames.value = 10;
  }
};

const inputWidth = computed(() => {
  const digits = String(windowFrames.value || "").length || 1;
  return `${Math.max(2, digits + 1)}ch`;
});

const frameDurationMs = computed(() => {
  const fps = playerStore.videoFPS || 25;
  return 1000 / fps;
});

const chartWindowSize = computed(() => {
  return Math.max(1, windowFrames.value) * frameDurationMs.value;
});

const windowTimeLabel = computed(() => {
  const totalMs = chartWindowSize.value;
  if (totalMs < 1000) return `${Math.round(totalMs)} ms`;
  const totalSec = totalMs / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(1)}s`;
  const min = Math.floor(totalSec / 60);
  const sec = Math.round(totalSec % 60);
  return sec > 0 ? `${min} min ${sec}s` : `${min} min`;
});

const selectedKpiOption = computed(
  () => kpiOptions.find((o) => o.id === selectedKpiId.value) || kpiOptions[0]
);
const chartKpi = computed(() => selectedKpiOption.value.kpi);
const chartMode = computed(() => selectedKpiOption.value.mode);

const isKpiSelected = (option) => {
  if (viewMode.value === "chart") {
    return selectedKpiId.value === option.id;
  }
  return selectedKpis.value.has(option.id);
};

const toggleKpi = (option) => {
  if (viewMode.value === "chart") {
    selectedKpiId.value = option.id;
  } else {
    // Table: multi select by id, keep at least one
    const newSet = new Set(selectedKpis.value);
    if (newSet.has(option.id)) {
      if (newSet.size > 1) newSet.delete(option.id);
    } else {
      newSet.add(option.id);
    }
    selectedKpis.value = newSet;
  }
};

const allFrameKeys = computed(() => topViewStore.sortedFrameKeys);
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

const playerHeaders = [
  { title: t("visualization.running_distance.player_view.player_id"), key: "player_id" },
  { title: t("visualization.running_distance.player_view.distance"), key: "distance" },
];

const teamHeaders = [
  { title: t("visualization.running_distance.team_view.total_distance"), key: "total_distance" },
  { title: t("visualization.running_distance.team_view.avg_distance"), key: "avg_distance" },
  { title: t("visualization.running_distance.team_view.player_count"), key: "player_count" },
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

const teamGroups = computed(() => {
  const groups = {};
  for (const p of playerOptions.value) {
    if (!groups[p.teamId]) groups[p.teamId] = [];
    groups[p.teamId].push(p);
  }
  return groups;
});

const toggleTeam = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  const allSelected = teamPlayerIds.every((pid) => selectedPlayerIds.value.has(pid));
  const newSet = new Set(selectedPlayerIds.value);
  if (allSelected) {
    teamPlayerIds.forEach((pid) => newSet.delete(pid));
  } else {
    teamPlayerIds.forEach((pid) => newSet.add(pid));
  }
  selectedPlayerIds.value = newSet;
};

const isTeamFullySelected = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  return teamPlayerIds.length > 0 && teamPlayerIds.every((pid) => selectedPlayerIds.value.has(pid));
};

const runningDistanceItems = ref([]);
const isComputingDistance = ref(false);

const triggerDistanceCalc = debounce(async () => {
  const posData = toRaw(topViewStore.positionDataTopView);
  if (!posData || !Object.keys(posData).length) {
    runningDistanceItems.value = [];
    return;
  }
  isComputingDistance.value = true;
  try {
    const result = await posdataWorkerStore.calcRunningDistances(
      posData,
      [...selectedPlayerIds.value],
      selectedStartFrame.value,
      selectedEndFrame.value,
      playerStore.video?.field_length || 105,
      playerStore.video?.field_width || 68,
      selectedZones.value
    );
    runningDistanceItems.value = result;
  } catch (err) {
    console.error("Worker distance calc failed, using fallback:", err);
    runningDistanceItems.value = positionDataStore.calculateRunningDistances(
      selectedPlayerIds.value,
      selectedStartFrame.value,
      selectedEndFrame.value,
      selectedZones.value
    );
  } finally {
    isComputingDistance.value = false;
  }
}, 150);

watch(
  [selectedPlayerIds, selectedStartFrame, selectedEndFrame, () => topViewStore.positionDataTopView, selectedZones],
  () => triggerDistanceCalc(),
  { immediate: true }
);
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

const runningDistanceTeamAggregated = computed(() => {
  const result = [];
  for (const [teamId, players] of Object.entries(runningDistanceTeamItems.value)) {
    const total = players.reduce((sum, p) => sum + p.distance, 0);
    const count = players.length;
    result.push({
      team_id: teamId,
      total_distance: parseFloat(total.toFixed(1)),
      avg_distance: count > 0 ? parseFloat((total / count).toFixed(1)) : 0,
      player_count: count,
    });
  }
  return result;
});

const hasPositionData = computed(() => topViewStore.sortedFrameKeys.length > 0);

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

const getTeamBest = (teamPlayers) => {
  if (!teamPlayers || teamPlayers.length === 0) return 0;
  return Math.max(...teamPlayers.map((p) => p.distance));
};

const getTeamTotal = (teamPlayers) => {
  if (!teamPlayers || teamPlayers.length === 0) return 0;
  return parseFloat(teamPlayers.reduce((sum, p) => sum + p.distance, 0).toFixed(1));
};

const findFirstFrameWithHalftime = (half) => {
  let first = null;
  for (const [timeKey, players] of Object.entries(topViewStore.positionDataTopView)) {
    const t = Number(timeKey);
    if (players.some((p) => p[2] === half)) {
      if (first === null || t < first) first = t;
    }
  }
  return first ?? 0;
};

const findLastFrameWithHalftime = (half) => {
  let last = null;
  for (const [timeKey, players] of Object.entries(topViewStore.positionDataTopView)) {
    const t = Number(timeKey);
    if (players.some((p) => p[2] === half)) {
      if (last === null || t > last) last = t;
    }
  }
  return last ?? 0;
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

.inline-frame-input {
  min-width: 2ch;
  text-align: center;
  border: none;
  border-bottom: 1.5px solid rgba(var(--v-theme-primary));
  outline: none;
  font-size: 12px;
  padding: 0 2px;
  background: transparent;
  -moz-appearance: textfield;
}
.inline-frame-input::-webkit-outer-spin-button,
.inline-frame-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.inline-frame-input:focus {
  border-bottom-color: #1976d2;
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

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 40px;
  flex-wrap: wrap;
}

.chart-legend-team {
  display: flex;
  align-items: center;
  gap: 5px;
}

.team-dot {
  height: 28px;
  border-radius: 14px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.7rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s, color 0.2s;
  user-select: none;
  white-space: nowrap;
}
.team-dot:hover {
  opacity: 0.8;
}

.chart-legend-sep {
  color: #ccc;
  font-size: 18px;
  margin: 0 2px;
  user-select: none;
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.spinner {
  font-size: 48px;
  color: #ac1414;
}

.loading-text {
  margin-top: 10px;
  font-size: 18px;
}
</style>
