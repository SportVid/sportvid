<template>
  <div v-if="!hasPositionData && posdataWorkerStore.isLoading" class="heatmap-loading-card">
    <div class="heatmap-spinner"><i class="mdi mdi-loading mdi-spin" /></div>
    <div class="heatmap-loading-text">
      {{
        posdataWorkerStore.loadProgress > 0 && posdataWorkerStore.loadProgress < 100
          ? `${posdataWorkerStore.loadProgress}%`
          : ""
      }}
    </div>
  </div>

  <PositionDataMenu
    v-else-if="!hasPositionData"
    :title="$t('analysis_view.visualization_tabs.heatmap')"
    icon="mdi-fire"
  />

  <div v-else class="d-flex flex-column flex-nowrap pa-4">
    <div class="card-header-zone">
      <v-row
        align="center"
        class="flex-nowrap mx-n4 mt-n8"
        style="width: 100%"
        data-tour="heatmap-controls-row"
      >
        <v-col
          cols="auto"
          class="d-flex align-center flex-shrink-0"
          style="gap: 12px"
          data-tour="heatmap-settings"
        >
          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                size="small"
                data-tour="heatmap-display-settings-btn"
                class="mt-n2"
              >
                <v-icon>mdi-menu</v-icon>
              </v-btn>
            </template>
            <v-list
              class="py-0"
              density="compact"
              width="190px"
              data-tour="heatmap-display-settings-list"
            >
              <v-list-item class="menu-item" @click="showModalPositionDataOffset = true">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.offset") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item class="menu-item" @click="topViewStore.viewMirrorXY">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.mirror_xy") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.mirrorXY,
                      'text-red': topViewStore.mirrorXY,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.heatmap.display_mode.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="120px">
                  <v-list-item class="menu-item" @click="displayMode = 'heatmap'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.heatmap.display_mode.heatmap") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': displayMode !== 'heatmap',
                          'text-red': displayMode === 'heatmap',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item class="menu-item" @click="displayMode = 'movement'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.heatmap.display_mode.movement") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': displayMode !== 'movement',
                          'text-red': displayMode === 'movement',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <v-list-item class="menu-item" @click="showModalPositionDataEntityColors = true">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.entity_colors") }}
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("position_data.display_settings.area_size") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact">
                  <v-list-item
                    v-for="(areaData, areaSize) in topViewStore.currentSport.areas"
                    :key="areaSize"
                    class="menu-item"
                    @click="topViewStore.onSportChange(topViewStore.currentSport.title, areaSize)"
                  >
                    <v-list-item-title class="my-0">
                      {{ areaData.title }}
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <!-- Soccer: full longitudinal/transverse grid picker -->
              <v-menu
                v-if="topViewStore.currentSport.key === 'soccer'"
                location="end"
                open-on-hover
              >
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("position_data.display_settings.set_zones.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="220px">
                  <v-list-item class="menu-item" @click.stop>
                    <v-list-item-title class="d-flex justify-space-between align-center">
                      {{ $t("position_data.display_settings.set_zones.longitudinal") }}
                      <v-btn-toggle
                        v-model="topViewStore.gridLongitudinal"
                        color="primary"
                        border
                        elevation="2"
                        mandatory
                        density="compact"
                        divided
                      >
                        <v-btn
                          v-for="opt in topViewStore.gridConfig.longitudinal.options"
                          :key="opt"
                          :value="opt"
                          size="x-small"
                          >{{ opt }}</v-btn
                        >
                      </v-btn-toggle>
                    </v-list-item-title>
                  </v-list-item>

                  <v-list-item class="menu-item" @click.stop>
                    <v-list-item-title class="d-flex justify-space-between align-center">
                      {{ $t("position_data.display_settings.set_zones.transverse") }}
                      <v-btn-toggle
                        v-model="topViewStore.gridTransverse"
                        color="primary"
                        border
                        elevation="2"
                        mandatory
                        density="compact"
                        divided
                      >
                        <v-btn
                          v-for="opt in topViewStore.gridConfig.transverse.options"
                          :key="opt"
                          :value="opt"
                          size="x-small"
                          >{{ opt }}</v-btn
                        >
                      </v-btn-toggle>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <!-- Handball / Basketball: single zone-overlay toggle -->
              <v-list-item
                v-else-if="
                  topViewStore.currentSport.key === 'handball' ||
                  topViewStore.currentSport.key === 'basketball'
                "
                class="menu-item"
                @click="topViewStore.toggleSportZones"
              >
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.toggle_zones") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.showSportZones,
                      'text-red': topViewStore.showSportZones,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("position_data.display_settings.position_data.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact">
                  <v-list-item
                    v-if="canWrite"
                    class="menu-item"
                    @click="showModalPositionDataUpload = true"
                  >
                    <v-list-item-title>
                      {{ $t("position_data.display_settings.position_data.upload") }}
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item class="menu-item" @click="showModalPositionDataSelect = true">
                    <v-list-item-title>
                      {{ $t("position_data.display_settings.position_data.select") }}
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </v-list>
          </v-menu>
          <ModalPositionDataUpload
            v-if="showModalPositionDataUpload"
            v-model="showModalPositionDataUpload"
          />
          <ModalPositionDataSelect
            v-if="showModalPositionDataSelect"
            v-model="showModalPositionDataSelect"
          />
          <ModalPositionDataEntityColors
            v-if="showModalPositionDataEntityColors"
            v-model="showModalPositionDataEntityColors"
          />
          <ModalPositionDataOffset
            v-if="showModalPositionDataOffset"
            v-model="showModalPositionDataOffset"
          />

          <v-btn size="small" @click="saveScreenshot" class="mt-n2">
            <v-icon>mdi-download</v-icon>
          </v-btn>

          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn v-bind="props" size="small" class="mr-2 mt-n2">
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
        <v-col class="pa-0" data-tour="heatmap-time-selector">
          <VisualizationTimeSelector class="ml-n2" />
        </v-col>
      </v-row>
    </div>

    <v-row justify="center">
      <div ref="heatmapFullscreenRoot" class="heatmap-fullscreen-root">
        <div
          class="top-view-wrapper"
          data-tour="heatmap-pitch"
          @mouseenter="hovering = true"
          @mouseleave="hovering = false"
        >
          <img
            ref="topViewElement"
            class="visualizer-image"
            :src="topViewStore.currentSport.areaImage"
            @load="onImageLoad"
            :style="
              isHeatmapFullscreen
                ? { maxHeight: '100vh' }
                : {
                    height: videoStore.videoSize.height + 'px',
                    maxWidth: '100%',
                  }
            "
          />

          <v-icon
            class="fullscreen-toggle"
            @click="toggleHeatmapFullscreen"
            :class="{ visible: hovering }"
          >
            {{ isHeatmapFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
          </v-icon>

          <!-- Fullscreen-only legend: the normal .chart-legend below the pitch (further down
          this template) sits outside the fullscreened element and is therefore hidden once
          fullscreen kicks in (see VideoPlayer.vue's fullscreen-controls for the same pattern) —
          this duplicates just the team/player toggles so filtering still works while fullscreen. -->
          <div
            v-if="isHeatmapFullscreen"
            class="fullscreen-controls"
            :class="{ visible: hovering }"
          >
            <div class="chart-legend" data-tour="heatmap-player-legend-fullscreen">
              <div v-for="(players, teamId) in teamGroups" :key="teamId" class="chart-legend-team">
                <div
                  class="team-dot"
                  :style="{
                    backgroundColor: isTeamFullySelected(teamId)
                      ? toRgb(visualizationStore.getTeamColor(teamId), 0)
                      : 'transparent',
                    color: isTeamFullySelected(teamId)
                      ? getContrastColor(visualizationStore.getTeamColor(teamId), 0)
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
                    color: getContrastColor(
                      playerColors[p.playerId],
                      selectedPlayerIds.includes(p.playerId) ? 0 : 0.6
                    ),
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
          </div>

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
      </div>
    </v-row>

    <div
      class="chart-legend mt-7"
      :class="{ 'chart-legend--dense': dense }"
      data-tour="heatmap-player-legend"
    >
      <div v-for="(players, teamId) in teamGroups" :key="teamId" class="chart-legend-team">
        <div
          class="team-dot"
          :style="{
            backgroundColor: isTeamFullySelected(teamId)
              ? toRgb(visualizationStore.getTeamColor(teamId), 0)
              : 'transparent',
            color: isTeamFullySelected(teamId)
              ? getContrastColor(visualizationStore.getTeamColor(teamId), 0)
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
            color: getContrastColor(
              playerColors[p.playerId],
              selectedPlayerIds.includes(p.playerId) ? 0 : 0.6
            ),
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, toRaw } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import { useUserStore } from "@/stores/user";
import VisualizationTimeSelector from "@/components/visualization/VisualizationTimeSelector.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataEntityColors from "@/components/position-data/ModalPositionDataEntityColors.vue";
import ModalPositionDataOffset from "@/components/position-data/ModalPositionDataOffset.vue";
import PositionDataMenu from "@/components/position-data/PositionDataMenu.vue";
import h337 from "heatmap.js";
import { toRgb, getContrastColor } from "@/plugins/helpers";
import { resampleApprox } from "@/plugins/draw/utils";
import { debounce } from "lodash";

defineProps({
  // True when this widget shares its row with video/topview and has been
  // height-capped to their size (see DashboardGrid) — squeeze the legend
  // into a single, horizontally-scrolling row instead of letting it wrap
  // to as many lines as it needs.
  dense: { type: Boolean, default: false },
});

const topViewStore = useTopViewStore();
const videoStore = useVideoStore();
const visualizationStore = useVisualizationStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const posdataWorkerStore = usePosdataWorkerStore();
const userStore = useUserStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const currentArea = computed(
  () => topViewStore.currentSport.areas?.[topViewStore.currentAreaSize] ?? {}
);

const displayMode = computed({
  get: () => visualizationStore.heatmapDisplayMode,
  set: (val) => {
    visualizationStore.heatmapDisplayMode = val;
  },
});

const showModalPositionDataSelect = ref(false);
const showModalPositionDataUpload = ref(false);
const showModalPositionDataEntityColors = ref(false);
const showModalPositionDataOffset = ref(false);

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
});
// The <img> only exists once position data has loaded (this whole branch is
// behind a v-else on hasPositionData, see template) — on a reload that can
// resolve well after this component's own onMounted already ran, so
// attaching the observer there (guarded on topViewElement.value) could
// silently no-op and never actually attach. Watching the ref instead reacts
// whenever the element actually (dis)appears, whether at mount or later.
watch(
  topViewElement,
  (el, oldEl) => {
    if (oldEl) resizeObserver.unobserve(oldEl);
    if (!el) return;
    resizeObserver.observe(el);
    nextTick(() => {
      measureImage();
      if (displayMode.value === "heatmap" && heatmapContainer.value) {
        createHeatmap();
      }
    });
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  window.removeEventListener("resize", measureImage);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
  triggerHeatmapCalc.cancel();
});

const hovering = ref(false);
const isHeatmapFullscreen = ref(false);
const heatmapFullscreenRoot = ref(null);
const toggleHeatmapFullscreen = () => {
  const root = heatmapFullscreenRoot.value;
  if (!document.fullscreenElement) {
    root.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
};
const onFullscreenChange = async () => {
  isHeatmapFullscreen.value = document.fullscreenElement === heatmapFullscreenRoot.value;
  await nextTick();
  measureImage();
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

const allFrameKeys = computed(() => topViewStore.sortedFrameKeys);

const selectHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  if (b) {
    positionDataStore.setSelectedTimeRangeStart(b.first);
    positionDataStore.setSelectedTimeRangeEnd(b.last);
  }
};

const selectedPlayerIds = computed({
  get: () => visualizationStore.heatmapSelectedPlayerIds,
  set: (val) => {
    visualizationStore.heatmapSelectedPlayerIds = val;
  },
});

const playerOptions = computed(() => topViewStore.precomputedPlayerList);

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
  if (!topViewStore.positionDataTopView || selectedPlayerIds.value.length === 0) {
    selectedPositions.value = [];
    return;
  }
  const rawCrop = toRaw(currentArea.value.templateCrop);
  const cropPct = rawCrop
    ? { x: [rawCrop.x[0], rawCrop.x[1]], y: [rawCrop.y[0], rawCrop.y[1]] }
    : { x: [0, 1], y: [0, 1] };
  try {
    const start = positionDataStore.selectedTimeRange.start;
    const end = positionDataStore.selectedTimeRange.end;
    const posData = topViewStore.getSubsetObject(start, end);
    const result = await posdataWorkerStore.calcHeatmapPoints(
      posData,
      selectedPlayerIds.value,
      start,
      end,
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
  const mirror = topViewStore.mirrorXY;
  const points = selectedPositions.value.map((pos) => {
    const xNorm = mirror ? 1 - pos[3] : pos[3];
    const yNorm = mirror ? 1 - pos[4] : pos[4];
    const x =
      xNorm * (localSize.value.width * area.widthRel) +
      ((1 - area.widthRel) / 2) * localSize.value.width;
    const y =
      yNorm * (localSize.value.height * area.heightRel) +
      ((1 - area.heightRel) / 2) * localSize.value.height;
    return { x: Math.round(x), y: Math.round(y), value: 1 };
  });

  heatmapInstance.setData({
    max: 10,
    data: points,
  });
}

function renderMovementToCanvas(canvas, targetW, targetH) {
  if (!canvas || !targetW || !targetH) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, targetW, targetH);

  if (selectedPositions.value.length === 0) return;

  const area = currentArea.value;
  const mirror = topViewStore.mirrorXY;
  const dotRadius = 6 * (targetW / localSize.value.width);
  const points = resampleApprox({ data: selectedPositions.value, targetSize: 5000 });

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
      const xNorm = mirror ? 1 - pos[3] : pos[3];
      const yNorm = mirror ? 1 - pos[4] : pos[4];
      const x = xNorm * (targetW * area.widthRel) + ((1 - area.widthRel) / 2) * targetW;
      const y = yNorm * (targetH * area.heightRel) + ((1 - area.heightRel) / 2) * targetH;
      ctx.moveTo(x + dotRadius, y);
      ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
    }
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function renderMovementCanvas() {
  const canvas = movementCanvas.value;
  if (!canvas || !localSize.value.width || !localSize.value.height) return;
  renderMovementToCanvas(canvas, localSize.value.width, localSize.value.height);
}

watch(
  [() => localSize.value.width, () => localSize.value.height, () => topViewStore.mirrorXY],
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

async function saveScreenshot() {
  const img = topViewElement.value;
  if (!img || !localSize.value.width || !localSize.value.height) return;
  const scale = 4;
  const targetW = localSize.value.width * scale;
  const targetH = localSize.value.height * scale;

  const finalCanvas = document.createElement("canvas");
  finalCanvas.width = targetW;
  finalCanvas.height = targetH;
  const ctx = finalCanvas.getContext("2d");
  ctx.drawImage(img, 0, 0, targetW, targetH);

  if (displayMode.value === "heatmap" && selectedPositions.value.length > 0) {
    const tempContainer = document.createElement("div");
    tempContainer.style.cssText = `position:fixed;left:${-(
      targetW + 10
    )}px;top:0;width:${targetW}px;height:${targetH}px;overflow:hidden;`;
    document.body.appendChild(tempContainer);
    const area = currentArea.value;
    const hiResHeatmap = h337.create({
      container: tempContainer,
      radius: 18 * scale,
      maxOpacity: 0.7,
      minOpacity: 0,
      blur: 0.7,
      gradient: { 0.2: "blue", 0.4: "cyan", 0.6: "lime", 0.8: "yellow", 1.0: "red" },
    });
    const mirrorShot = topViewStore.mirrorXY;
    const points = selectedPositions.value.map((pos) => ({
      x: Math.round(
        (mirrorShot ? 1 - pos[3] : pos[3]) * (targetW * area.widthRel) +
          ((1 - area.widthRel) / 2) * targetW
      ),
      y: Math.round(
        (mirrorShot ? 1 - pos[4] : pos[4]) * (targetH * area.heightRel) +
          ((1 - area.heightRel) / 2) * targetH
      ),
      value: 1,
    }));
    hiResHeatmap.setData({ max: 10, data: points });
    const heatmapCanvas = tempContainer.querySelector("canvas");
    if (heatmapCanvas) ctx.drawImage(heatmapCanvas, 0, 0);
    document.body.removeChild(tempContainer);
  } else if (displayMode.value === "movement") {
    const offscreen = document.createElement("canvas");
    offscreen.width = targetW;
    offscreen.height = targetH;
    renderMovementToCanvas(offscreen, targetW, targetH);
    ctx.drawImage(offscreen, 0, 0);
  }

  finalCanvas.toBlob((blob) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = "heatmap.png";
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  });
}
</script>

<style scoped>
.heatmap-loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 25vh;
}

.heatmap-spinner {
  font-size: 48px;
  color: rgb(var(--v-theme-primary));
}

.heatmap-loading-text {
  margin-top: 10px;
  font-size: 18px;
  color: rgb(var(--v-theme-primary));
}

.visualizer-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.card-header-zone {
  height: 56px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
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
  column-gap: 20px;
  row-gap: 8px;
  flex-wrap: wrap;
}

/* Squeezed next to video/topview: one row, horizontal scroll instead of
   wrapping to more lines than the capped height has room for. */
.chart-legend--dense {
  flex-wrap: nowrap;
  justify-content: flex-start;
  overflow-x: auto;
  padding-bottom: 4px;
}

.chart-legend-team {
  display: flex;
  align-items: center;
  gap: 5px;
}

.team-dot {
  height: 24px;
  border-radius: 50%;
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
  width: 24px;
  height: 24px;
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
}

.heatmap-fullscreen-root {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.fullscreen-toggle {
  position: absolute;
  top: 2px;
  right: 2px;
  color: white;
  font-size: 28px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-toggle.visible {
  opacity: 0.8;
}

.fullscreen-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 16px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-controls.visible {
  opacity: 1;
}

.fullscreen-controls .chart-legend {
  margin: 0;
}
</style>
