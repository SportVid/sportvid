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
    v-html="$t('visualization.heatmap.not_selected')"
  />

  <v-card v-else class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <v-row align="center">
      <v-col cols="auto" class="mt-3 d-flex align-center flex-shrink-0" style="gap: 8px">
        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" style="height: 40px" class="ml-2 mt-n2" size="small">
              {{ topViewStore.currentSport.title }}
            </v-btn>
          </template>
          <v-list class="py-0" density="compact" width="115px">
            <v-menu location="end" open-on-hover v-for="sport in topViewStore.sports" :key="sport">
              <template #activator="{ props }">
                <v-list-item v-bind="props" class="menu-item">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ sport.title }}
                    <v-icon size="small">mdi-chevron-right</v-icon>
                  </v-list-item-title>
                </v-list-item>
              </template>
              <v-list class="py-0" density="compact">
                <v-list-item
                  v-for="(areaData, areaSize) in sport.areas"
                  :key="areaSize"
                  class="menu-item"
                  @click="topViewStore.onSportChange(sport.title, areaSize)"
                >
                  <v-list-item-title class="my-0">
                    {{ areaSize }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-list>
        </v-menu>

        <v-btn-toggle
          v-model="displayMode"
          color="primary"
          border
          mandatory
          elevation="2"
          style="height: 40px"
          class="mt-n2"
        >
          <v-btn value="heatmap" size="small">
            <v-icon>mdi-blur</v-icon>
          </v-btn>
          <v-btn value="movement" size="small">
            <v-icon>mdi-map-marker-path</v-icon>
          </v-btn>
        </v-btn-toggle>

        <v-menu location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" style="height: 40px" size="small" class="mt-n2">
              <v-icon>mdi-timer-sync-outline</v-icon>
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
              :disabled="!visualizationStore.halftimesExist"
              @click="selectHalftime(1)"
            >
              <v-list-item-title>
                {{ $t("visualization.time_selection.first_half") }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              :disabled="!visualizationStore.halftimesExist"
              @click="selectHalftime(2)"
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

    <v-row class="mt-2" justify="center">
      <div class="top-view-wrapper">
        <img
          ref="topViewElement"
          class="visualizer-image"
          :src="topViewStore.currentSport.areaImage"
          @load="onImageLoad"
          :style="{
            height: videoStore.videoSize.height + 'px',
            maxWidth: '100%',
          }"
        />

        <div
          v-if="displayMode === 'heatmap'"
          ref="heatmapContainer"
          :style="{
            position: 'absolute',
            top: '0px',
            left: '0px',
            width: localSize.width + 'px',
            height: localSize.height + 'px',
          }"
        ></div>

        <canvas
          v-if="displayMode === 'movement'"
          ref="movementCanvas"
          :width="localSize.width"
          :height="localSize.height"
          :style="{
            position: 'absolute',
            top: '0px',
            left: '0px',
            width: localSize.width + 'px',
            height: localSize.height + 'px',
          }"
        />
      </div>
    </v-row>

    <div class="chart-legend mt-6">
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
            backgroundColor: selectedPlayerIds.includes(p.playerId)
              ? toRgb(playerColors[p.playerId], 0)
              : toRgb(playerColors[p.playerId], 0.6),
            color: selectedPlayerIds.includes(p.playerId) ? '#fff' : '#222',
            borderColor: selectedPlayerIds.includes(p.playerId)
              ? toRgb(playerColors[p.playerId], 0)
              : toRgb(playerColors[p.playerId], 0.6),
          }"
          @click="togglePlayerId(p.playerId)"
        >
          {{ getPlayerNumber(p.playerId) }}
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, toRaw } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import RunningDistanceTimeSelector from "@/components/kpi/RunningDistanceTimeSelector.vue";
import h337 from "heatmap.js";
import { toRgb } from "@/plugins/helpers";
import { resampleApprox } from "@/plugins/draw/utils";
import { debounce } from "lodash";

const topViewStore = useTopViewStore();
const videoStore = useVideoStore();
const visualizationStore = useVisualizationStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const posdataWorkerStore = usePosdataWorkerStore();

const currentArea = computed(
  () => topViewStore.currentSport.areas?.[topViewStore.currentAreaSize] ?? {}
);

const displayMode = ref("heatmap");

const localSize = ref({ width: 0, height: 0 });
const topViewElement = ref(null);

const measureImage = () => {
  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    localSize.value = { width: rect.width, height: rect.height };
  }
};

const onImageLoad = () => {
  nextTick(() => measureImage());
};

const resizeObserver = new ResizeObserver(() => {
  measureImage();
});

onMounted(() => {
  window.addEventListener("resize", measureImage);
  if (topViewElement.value) {
    resizeObserver.observe(topViewElement.value);
  }
  nextTick(() => {
    measureImage();
    if (displayMode.value === "heatmap" && heatmapContainer.value) {
      createHeatmap();
    }
  });
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", measureImage);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
  triggerHeatmapCalc.cancel();
});

const allFrameKeys = computed(() => topViewStore.sortedFrameKeys);

const selectHalftime = (half) => {
  const entries = Object.entries(topViewStore.positionDataTopView);
  let first = null;
  let last = null;
  for (const [timeKey, players] of entries) {
    const t = Number(timeKey);
    if (players.some((p) => p[2] === half)) {
      if (first === null || t < first) first = t;
      if (last === null || t > last) last = t;
    }
  }
  if (first !== null && last !== null) {
    positionDataStore.setSelectedTimeRangeStart(first);
    positionDataStore.setSelectedTimeRangeEnd(last);
  }
};

const selectedPlayerIds = ref([]);

const playerOptions = computed(() => {
  // Sample a few frames to find all players (avoids iterating all ~135k frames)
  const keys = Object.keys(topViewStore.positionDataTopView);
  if (!keys.length) return [];
  const seen = new Map();
  const step = Math.max(1, Math.floor(keys.length / 10));
  for (let i = 0; i < keys.length; i += step) {
    const players = topViewStore.positionDataTopView[keys[i]];
    if (!players) continue;
    for (const p of players) {
      if (p[1] !== 1 && !seen.has(p[0])) {
        seen.set(p[0], { playerId: p[0], teamId: p[1] });
      }
    }
  }
  // Also check last frame
  const last = topViewStore.positionDataTopView[keys[keys.length - 1]];
  if (last) {
    for (const p of last) {
      if (p[1] !== 1 && !seen.has(p[0])) {
        seen.set(p[0], { playerId: p[0], teamId: p[1] });
      }
    }
  }
  return Array.from(seen.values()).sort((a, b) => a.playerId - b.playerId);
});

const playerColors = computed(() => {
  const map = {};
  for (const p of playerOptions.value) {
    map[p.playerId] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});

const teamGroups = computed(() => {
  const groups = {};
  for (const p of playerOptions.value) {
    if (!groups[p.teamId]) groups[p.teamId] = [];
    groups[p.teamId].push(p);
  }
  return groups;
});

function togglePlayerId(playerId) {
  if (selectedPlayerIds.value.includes(playerId)) {
    selectedPlayerIds.value = selectedPlayerIds.value.filter((id) => id !== playerId);
  } else {
    selectedPlayerIds.value = [...selectedPlayerIds.value, playerId];
  }
}

const toggleTeam = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  const allSelected = teamPlayerIds.every((pid) => selectedPlayerIds.value.includes(pid));
  if (allSelected) {
    selectedPlayerIds.value = selectedPlayerIds.value.filter((id) => !teamPlayerIds.includes(id));
  } else {
    const newIds = [...selectedPlayerIds.value];
    teamPlayerIds.forEach((pid) => {
      if (!newIds.includes(pid)) newIds.push(pid);
    });
    selectedPlayerIds.value = newIds;
  }
};

const isTeamFullySelected = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  return (
    teamPlayerIds.length > 0 && teamPlayerIds.every((pid) => selectedPlayerIds.value.includes(pid))
  );
};

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};

const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return teamId;
};

const selectedPositions = ref([]);

const triggerHeatmapCalc = debounce(async () => {
  const posData = toRaw(topViewStore.positionDataTopView);
  if (!posData || !Object.keys(posData).length || selectedPlayerIds.value.length === 0) {
    selectedPositions.value = [];
    return;
  }
  const rawCrop = toRaw(currentArea.value.templateCrop);
  const cropPct = rawCrop
    ? { x: [rawCrop.x[0], rawCrop.x[1]], y: [rawCrop.y[0], rawCrop.y[1]] }
    : { x: [0, 1], y: [0, 1] };
  try {
    const result = await posdataWorkerStore.calcHeatmapPoints(
      posData,
      selectedPlayerIds.value,
      positionDataStore.selectedTimeRange.start,
      positionDataStore.selectedTimeRange.end,
      cropPct
    );
    selectedPositions.value = result;
  } catch (err) {
    console.error("Worker heatmap calc failed:", err);
    selectedPositions.value = [];
  }
}, 200);

watch(
  [
    selectedPlayerIds,
    () => positionDataStore.selectedTimeRange.start,
    () => positionDataStore.selectedTimeRange.end,
    () => currentArea.value.templateCrop,
    () => topViewStore.positionDataTopView,
  ],
  () => triggerHeatmapCalc(),
  { immediate: true }
);

const movementCanvas = ref(null);
const heatmapContainer = ref(null);
let heatmapInstance = null;

function createHeatmap() {
  if (!heatmapContainer.value) return;
  if (heatmapContainer.value.offsetWidth === 0 || heatmapContainer.value.offsetHeight === 0) return;

  heatmapContainer.value.innerHTML = "";

  heatmapInstance = h337.create({
    container: heatmapContainer.value,
    radius: 18,
    maxOpacity: 0.7,
    minOpacity: 0,
    blur: 0.7,
    gradient: {
      0.2: "blue",
      0.4: "cyan",
      0.6: "lime",
      0.8: "yellow",
      1.0: "red",
    },
  });

  heatmapContainer.value.style.position = "absolute";
}

function renderHeatmap() {
  if (!heatmapInstance || !localSize.value.width || !localSize.value.height) return;

  const area = currentArea.value;
  const points = selectedPositions.value.map((pos) => {
    const x =
      pos[3] * (localSize.value.width * area.widthRel) +
      ((1 - area.widthRel) / 2) * localSize.value.width;
    const y =
      pos[4] * (localSize.value.height * area.heightRel) +
      ((1 - area.heightRel) / 2) * localSize.value.height;
    return { x: Math.round(x), y: Math.round(y), value: 1 };
  });

  heatmapInstance.setData({
    max: 10,
    data: points,
  });
}

function renderMovementCanvas() {
  const canvas = movementCanvas.value;
  if (!canvas || !localSize.value.width || !localSize.value.height) return;

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (selectedPositions.value.length === 0) return;

  const area = currentArea.value;
  const points = resampleApprox({ data: selectedPositions.value, targetSize: 5000 });

  // Group by teamId for batch drawing
  const byTeam = {};
  for (const pos of points) {
    const teamId = pos[1];
    if (!byTeam[teamId]) byTeam[teamId] = [];
    byTeam[teamId].push(pos);
  }

  for (const [teamId, positions] of Object.entries(byTeam)) {
    ctx.fillStyle = visualizationStore.getTeamColor(teamId);
    ctx.globalAlpha = 0.7;
    ctx.beginPath();
    for (const pos of positions) {
      const x =
        pos[3] * (localSize.value.width * area.widthRel) +
        ((1 - area.widthRel) / 2) * localSize.value.width;
      const y =
        pos[4] * (localSize.value.height * area.heightRel) +
        ((1 - area.heightRel) / 2) * localSize.value.height;
      ctx.moveTo(x + 6, y);
      ctx.arc(x, y, 6, 0, Math.PI * 2);
    }
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

watch([() => localSize.value.width, () => localSize.value.height], () => {
  if (displayMode.value === "heatmap") {
    nextTick(() => {
      createHeatmap();
      nextTick(() => renderHeatmap());
    });
  } else if (displayMode.value === "movement") {
    nextTick(() => renderMovementCanvas());
  }
});

watch(selectedPositions, () => {
  if (displayMode.value === "heatmap") {
    if (!heatmapInstance) createHeatmap();
    renderHeatmap();
  } else if (displayMode.value === "movement") {
    nextTick(() => renderMovementCanvas());
  }
});

watch(
  () => topViewStore.currentAreaSize,
  () => {
    if (displayMode.value === "heatmap") {
      nextTick(() => {
        createHeatmap();
        nextTick(() => renderHeatmap());
      });
    } else if (displayMode.value === "movement") {
      nextTick(() => renderMovementCanvas());
    }
  }
);

watch(displayMode, (mode) => {
  if (mode === "heatmap") {
    nextTick(() => {
      createHeatmap();
      nextTick(() => renderHeatmap());
    });
  } else if (mode === "movement") {
    nextTick(() => renderMovementCanvas());
  }
});

const hasPositionData = computed(() => topViewStore.sortedFrameKeys.length > 0);
</script>

<style scoped>
.visualizer-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  column-gap: 40px;
  row-gap: 8px;
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

.top-view-wrapper {
  position: relative;
  overflow: hidden;
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
