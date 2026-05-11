<template>
  <div v-if="!hasPositionData && posdataWorkerStore.isLoading" class="kpi-loading-card">
    <div class="kpi-spinner"><i class="mdi mdi-loading mdi-spin" /></div>
    <div class="kpi-loading-text">
      {{
        posdataWorkerStore.loadProgress > 0 && posdataWorkerStore.loadProgress < 100
          ? `${posdataWorkerStore.loadProgress}%`
          : ""
      }}
    </div>
  </div>

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
    v-html="$t('visualization.kpi.posdata_not_selected')"
  />

  <div v-else-if="!hasKpiData && visualizationStore.isLoadingKpi" class="kpi-loading-card">
    <div class="kpi-spinner"><i class="mdi mdi-loading mdi-spin" /></div>
  </div>

  <v-row
    v-else-if="!hasKpiData"
    class="text-h6 text-grey font-weight-light mx-16 px-10"
    style="
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1.5;
      height: 25vh;
    "
    v-html="$t('visualization.kpi.kpi_not_selected')"
  />

  <v-card v-else class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <v-row align="center" class="flex-nowrap" data-tour="kpi-controls-row">
      <v-col cols="auto" class="mt-3 d-flex align-center flex-shrink-0" style="gap: 8px" data-tour="kpi-settings">
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

        <v-menu v-model="kpiMenuOpen" location="bottom" :close-on-content-click="false">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" style="height: 40px" class="mt-n2">
              {{ $t("visualization.kpi.kpi_selection.title") }}
            </v-btn>
          </template>

          <v-list class="py-0" density="compact" :width="viewMode === 'chart' ? '160px' : '280px'">
            <!-- Chart mode: nested submenu per KPI group -->
            <template v-if="viewMode === 'chart'">
              <template v-for="group in chartKpiGroups" :key="group.key">
                <v-menu location="end" open-on-hover>
                  <template #activator="{ props: groupProps }">
                    <v-list-item v-bind="groupProps" class="menu-item">
                      <v-list-item-title class="d-flex justify-space-between">
                        {{ $t(group.labelKey) }}
                        <tab-window-icon>mdi-chevron-right</tab-window-icon>
                      </v-list-item-title>
                    </v-list-item>
                  </template>
                  <v-list class="py-0" density="compact" :width="group.chartWidth">
                    <template v-for="option in group.options" :key="option.id">
                      <v-list-item class="menu-item" @click="toggleKpi(option)">
                        <v-list-item-title class="d-flex justify-space-between">
                          <template v-if="option.mode === 'windowed'">
                            <span class="d-flex align-center" style="gap: 2px">
                              <span v-html="splitWindowedLabel(option.id).before" />
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
                              <span v-html="splitWindowedLabel(option.id).after" />
                            </span>
                          </template>
                          <span
                            v-else
                            v-html="$t(`visualization.kpi.kpi_selection.${option.id}`)"
                          />
                          <tab-window-icon
                            :class="{
                              'text-disabled': !isKpiSelected(option),
                              'text-red': isKpiSelected(option),
                            }"
                          >
                            mdi-check
                          </tab-window-icon>
                        </v-list-item-title>
                      </v-list-item>
                    </template>
                  </v-list>
                </v-menu>
              </template>
            </template>

            <!-- Table mode: flat list -->
            <template v-else>
              <template v-for="option in kpiOptions" :key="option.id">
                <v-list-item class="menu-item" @click="toggleKpi(option)">
                  <v-list-item-title class="d-flex justify-space-between">
                    <span v-html="$t(`visualization.kpi.kpi_selection.${option.id}`)" />
                    <tab-window-icon
                      :class="{
                        'text-disabled': !isKpiSelected(option),
                        'text-red': isKpiSelected(option),
                      }"
                    >
                      mdi-check
                    </tab-window-icon>
                  </v-list-item-title>
                </v-list-item>
              </template>
            </template>
          </v-list>
        </v-menu>

        <v-menu location="bottom" :close-on-content-click="false">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" style="height: 40px" class="mt-n2">
              {{ $t("visualization.kpi.zone_selection.title") }}
            </v-btn>
          </template>

          <ZoneSelectorPicker
            v-model="selectedZones"
            :sport="topViewStore.currentSport"
            :area-size="topViewStore.currentAreaSize"
            :mirror-x-y="topViewStore.mirrorXY"
          />
        </v-menu>

        <v-btn
          v-if="viewMode === 'chart'"
          style="height: 40px"
          size="small"
          class="mt-n2"
          @click="kpiChartRef?.saveChart()"
        >
          <v-icon>mdi-download</v-icon>
        </v-btn>

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
        <VisualizationTimeSelector class="ml-n1" />
      </v-col>
    </v-row>

    <div v-if="viewMode === 'table'" data-tour="kpi-table-view">
    <div
      v-if="groupMode === 'player'"
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
                {{
                  col.key === "player_id" ? getPlayerNumber(item[col.key]) : item[col.key] ?? "-"
                }}
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
              <td>{{ $t("visualization.kpi.player_view.best") }}</td>
              <td v-for="col in playerHeaders.slice(1)" :key="col.key">
                {{ getColBest(teamPlayers, col.key) }}
              </td>
            </tr>
            <tr
              :style="{
                fontWeight: 'bold',
                backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.45),
              }"
            >
              <td>{{ $t("visualization.kpi.player_view.total") }}</td>
              <td v-for="col in playerHeaders.slice(1)" :key="col.key">
                {{ getColTotal(teamPlayers, col.key) }}
              </td>
            </tr>
          </template>

          <template #header.velocity_max="{ column }">
            <span v-html="column.title" />
          </template>
          <template #header.metabolic_work="{ column }">
            <span v-html="column.title" />
          </template>
          <template #header.centroid_distance_max="{ column }">
            <span v-html="column.title" />
          </template>
        </v-data-table>
      </v-card>
    </div>

    <div
      v-else
      class="team-tables d-flex flex-wrap justify-space-around"
    >
      <v-card
        v-for="teamRow in runningDistanceTeamAggregated"
        :key="teamRow.team_id"
        class="team-card pa-4 ma-2"
        outlined
        :style="{ backgroundColor: toRgb(visualizationStore.getTeamColor(teamRow.team_id), 0.8) }"
      >
        <v-card-title class="text-center mt-n1">{{ getTeamName(teamRow.team_id) }}</v-card-title>

        <div class="player-selector mb-3">
          <div
            v-for="p in playerOptions.filter((p) => p.teamId == teamRow.team_id)"
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
          :headers="teamHeaders"
          :items="teamRow.rows"
          :items-per-page="-1"
          class="elevation-2"
          hide-default-footer
          density="compact"
        >
          <template #item="{ item }">
            <tr
              :style="{
                backgroundColor: toRgb(visualizationStore.getTeamColor(teamRow.team_id), 0.6),
              }"
            >
              <td><span v-html="item.label" /></td>
              <td>{{ item.total ?? "-" }}</td>
              <td>{{ item.avg ?? "-" }}</td>
            </tr>
          </template>
        </v-data-table>
      </v-card>
    </div>
    </div>

    <div v-else-if="viewMode === 'chart'" class="px-2 mt-2" data-tour="kpi-chart-view">
      <KpiChart
        ref="kpiChartRef"
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

      <div class="chart-legend mt-2">
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
import { ref, computed, watch, toRaw, onBeforeUnmount } from "vue";
// viewMode is driven by tabStore.kpiViewMode so the tutorial can switch views externally
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import { useTabStore } from "@/stores/tabs";
import VisualizationTimeSelector from "@/components/visualization/VisualizationTimeSelector.vue";
import KpiChart from "@/components/kpi/KpiChart.vue";
import ZoneSelectorPicker from "@/components/kpi/ZoneSelectorPicker.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";
import { debounce } from "lodash";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const posdataWorkerStore = usePosdataWorkerStore();
const tabStore = useTabStore();

const { t } = useI18n();

const kpiChartRef = ref(null);

// Split a windowed locale string at the {frames} placeholder so each half
// can be rendered with v-html (preserving <sub>/<sup> tags).
const splitWindowedLabel = (optionId) => {
  const SENTINEL = "\u0001";
  const msg = t(`visualization.kpi.kpi_selection.${optionId}`, { frames: SENTINEL });
  const idx = msg.indexOf(SENTINEL);
  if (idx === -1) return { before: msg, after: "" };
  return { before: msg.slice(0, idx), after: msg.slice(idx + 1) };
};

const viewMode = computed({
  get: () => tabStore.kpiViewMode,
  set: (val) => { tabStore.kpiViewMode = val; },
});
const groupMode = ref("player");

// Initialize with all 25 pitch zones selected (full pitch)
const LONG_BOUNDS = [0, 0.2025, 0.365, 0.635, 0.7955, 1];
const TRANS_BOUNDS = [0, 0.1575, 0.33, 0.67, 0.8425, 1];
const initialZones = [];
for (let r = 0; r < 5; r++) {
  for (let c = 0; c < 5; c++) {
    initialZones.push({
      x0: TRANS_BOUNDS[c],
      y0: LONG_BOUNDS[r],
      x1: TRANS_BOUNDS[c + 1],
      y1: LONG_BOUNDS[r + 1],
    });
  }
}
const selectedZones = ref(initialZones);

// Maps kpi_names (from kpi_computation meta_data) → display options per view mode.
const KPI_CONFIG = {
  distance_covered: {
    labelKey: "visualization.kpi.kpi_selection.group_distance",
    chartWidth: "230px",
    chart: [
      { id: "running_distance_frame", kpi: "running_distance", mode: "per_frame" },
      { id: "running_distance_interval", kpi: "running_distance", mode: "windowed" },
      { id: "running_distance_cumulative", kpi: "running_distance", mode: "cumulative" },
    ],
    table: [{ id: "running_distance_cumulative", kpi: "running_distance", mode: "cumulative" }],
  },
  velocity: {
    labelKey: "visualization.kpi.kpi_selection.group_velocity",
    chartWidth: "260px",
    chart: [
      { id: "velocity_frame", kpi: "velocity", mode: "per_frame" },
      { id: "velocity_interval", kpi: "velocity", mode: "windowed" },
    ],
    table: [{ id: "velocity_max", kpi: "velocity_max", mode: "cumulative" }],
  },
  metabolic_power: {
    labelKey: "visualization.kpi.kpi_selection.group_metabolic_work",
    chartWidth: "290px",
    chart: [
      { id: "metabolic_work_frame", kpi: "metabolic_work", mode: "per_frame" },
      { id: "metabolic_work_interval", kpi: "metabolic_work", mode: "windowed" },
      { id: "metabolic_work_cumulative", kpi: "metabolic_work", mode: "cumulative" },
    ],
    table: [{ id: "metabolic_work_cumulative", kpi: "metabolic_work", mode: "cumulative" }],
  },
  equivalent_distance: {
    labelKey: "visualization.kpi.kpi_selection.group_equivalent_distance",
    chartWidth: "310px",
    chart: [
      { id: "equivalent_distance_frame", kpi: "equivalent_distance", mode: "per_frame" },
      { id: "equivalent_distance_interval", kpi: "equivalent_distance", mode: "windowed" },
      { id: "equivalent_distance_cumulative", kpi: "equivalent_distance", mode: "cumulative" },
    ],
    table: [
      { id: "equivalent_distance_cumulative", kpi: "equivalent_distance", mode: "cumulative" },
    ],
  },
  centroid_distance: {
    labelKey: "visualization.kpi.kpi_selection.group_centroid_distance",
    chartWidth: "290px",
    chart: [
      { id: "centroid_distance_frame", kpi: "centroid_distance", mode: "per_frame" },
      { id: "centroid_distance_interval", kpi: "centroid_distance", mode: "windowed" },
    ],
    table: [{ id: "centroid_distance_max", kpi: "centroid_distance_max", mode: "table_max" }],
  },
};

// For table mode: flat list of table options for available KPI names
const kpiOptions = computed(() => {
  const names = visualizationStore.kpiNames;
  if (!names || !names.length) return [];
  return names.flatMap((name) => KPI_CONFIG[name]?.table || []);
});

// For chart mode: grouped structure for nested submenu
const chartKpiGroups = computed(() => {
  const names = visualizationStore.kpiNames;
  if (!names || !names.length) return [];
  return names
    .filter((name) => KPI_CONFIG[name])
    .map((name) => ({
      key: name,
      labelKey: KPI_CONFIG[name].labelKey,
      chartWidth: KPI_CONFIG[name].chartWidth,
      options: KPI_CONFIG[name].chart,
    }));
});

// Chart mode: single selected option (includes mode + window info)
const selectedKpiId = ref("running_distance_frame");
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

const allChartOptions = computed(() => chartKpiGroups.value.flatMap((g) => g.options));

const selectedKpiOption = computed(
  () => allChartOptions.value.find((o) => o.id === selectedKpiId.value) || allChartOptions.value[0]
);
const chartKpi = computed(() => selectedKpiOption.value?.kpi);
const chartMode = computed(() => selectedKpiOption.value?.mode);

const kpiMenuOpen = ref(false);

const isKpiSelected = (option) => {
  if (viewMode.value === "chart") {
    return selectedKpiId.value === option.id;
  }
  return selectedKpis.value.has(option.id);
};

const toggleKpi = (option) => {
  if (viewMode.value === "chart") {
    selectedKpiId.value = option.id;
    kpiMenuOpen.value = false;
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

const playerHeaders = computed(() => {
  const cols = [{ title: t("visualization.kpi.player_view.player_id"), key: "player_id" }];
  if (selectedKpis.value.has("running_distance_cumulative")) {
    cols.push({ title: t("visualization.kpi.kpi_label.distance"), key: "distance" });
  }
  if (selectedKpis.value.has("velocity_max")) {
    cols.push({ title: t("visualization.kpi.kpi_label.velocity_max"), key: "velocity_max" });
  }
  if (selectedKpis.value.has("metabolic_work_cumulative")) {
    cols.push({ title: t("visualization.kpi.kpi_label.metabolic_work"), key: "metabolic_work" });
  }
  if (selectedKpis.value.has("equivalent_distance_cumulative")) {
    cols.push({
      title: t("visualization.kpi.kpi_label.equivalent_distance"),
      key: "equivalent_distance",
    });
  }
  if (selectedKpis.value.has("centroid_distance_max")) {
    cols.push({
      title: t("visualization.kpi.kpi_label.centroid_distance_max"),
      key: "centroid_distance_max",
    });
  }
  return cols;
});

const teamHeaders = computed(() => [
  { title: t("visualization.kpi.team_view.kpi"), key: "label" },
  { title: t("visualization.kpi.team_view.total"), key: "total" },
  { title: t("visualization.kpi.team_view.average"), key: "avg" },
]);

const playerOptions = computed(() => topViewStore.precomputedPlayerList);
const selectedPlayerIds = ref(new Set());
watch(
  playerOptions,
  (list) => {
    selectedPlayerIds.value = new Set(list.map((p) => p.playerId));
  },
  { immediate: true }
);
const playerColors = computed(() => {
  const map = {};
  for (const p of playerOptions.value) {
    map[p.playerId] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});
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

const isInAnyZone = (x, y, zones) => {
  if (!zones || zones.length === 0) return false;
  for (const z of zones) {
    if (x >= z.x0 && x <= z.x1 && y >= z.y0 && y <= z.y1) return true;
  }
  return false;
};

const kpiItems = ref([]);
const _triggerKpiCalc = debounce(async () => {
  const rawKpiData = toRaw(visualizationStore.kpiData);
  if (!rawKpiData || typeof rawKpiData !== "object" || !Object.keys(rawKpiData).length) {
    kpiItems.value = [];
    return;
  }
  const startMs = selectedStartFrame.value;
  const endMs = selectedEndFrame.value;
  const posData = topViewStore.getSubsetObject(startMs, endMs);
  try {
    const result = await posdataWorkerStore.calcKpiAggregation(
      rawKpiData,
      posData,
      selectedPlayerIds.value,
      startMs,
      endMs,
      toRaw(selectedZones.value),
      visualizationStore.kpiFramerate || 25
    );
    kpiItems.value = result;
  } catch (err) {
    console.error("Worker KPI aggregation failed:", err);
    kpiItems.value = [];
  }
}, 150);
watch(
  [
    selectedPlayerIds,
    selectedStartFrame,
    selectedEndFrame,
    selectedZones,
    () => visualizationStore.kpiData,
  ],
  () => _triggerKpiCalc(),
  { immediate: true }
);
onBeforeUnmount(() => _triggerKpiCalc.cancel());

const runningDistanceTeamItems = computed(() => {
  const grouped = {};
  playerOptions.value.forEach((p) => {
    if (!grouped[p.teamId]) grouped[p.teamId] = [];
  });

  const kpiMap = {};
  kpiItems.value.forEach((item) => {
    kpiMap[item.player_id] = item;
  });

  playerOptions.value.forEach((p) => {
    if (!selectedPlayerIds.value.has(p.playerId)) return;
    const kpiItem = kpiMap[p.playerId];
    grouped[p.teamId].push(
      kpiItem
        ? { ...kpiItem, team_id: p.teamId }
        : {
            player_id: p.playerId,
            team_id: p.teamId,
            distance: null,
            velocity_max: null,
            metabolic_work: null,
            equivalent_distance: null,
            centroid_distance_max: null,
          }
    );
  });

  return grouped;
});

const runningDistanceTeamAggregated = computed(() => {
  const result = [];
  for (const [teamId, players] of Object.entries(runningDistanceTeamItems.value)) {
    const rows = [];

    if (selectedKpis.value.has("running_distance_cumulative")) {
      const vals = players.map((p) => p.distance).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.distance"), total, avg });
    }

    if (selectedKpis.value.has("velocity_max")) {
      const vals = players.map((p) => p.velocity_max).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(Math.max(...vals).toFixed(2)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.velocity_max"), total, avg });
    }

    if (selectedKpis.value.has("metabolic_work_cumulative")) {
      const vals = players.map((p) => p.metabolic_work).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.metabolic_work"), total, avg });
    }

    if (selectedKpis.value.has("equivalent_distance_cumulative")) {
      const vals = players.map((p) => p.equivalent_distance).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.equivalent_distance"), total, avg });
    }

    if (selectedKpis.value.has("centroid_distance_max")) {
      const vals = players.map((p) => p.centroid_distance_max).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(Math.max(...vals).toFixed(2)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.centroid_distance_max"), total, avg });
    }

    result.push({ team_id: teamId, rows });
  }
  return result;
});

const hasPositionData = computed(() => topViewStore.sortedFrameKeys.length > 0);

const hasKpiData = computed(
  () =>
    visualizationStore.kpiData != null &&
    typeof visualizationStore.kpiData === "object" &&
    Object.keys(visualizationStore.kpiData).length > 0
);

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

const getColBest = (players, colKey) => {
  if (!players || !players.length) return "-";
  const vals = players.map((p) => p[colKey]).filter((v) => v != null);
  if (!vals.length) return "-";
  return parseFloat(Math.max(...vals).toFixed(2));
};

const getColTotal = (players, colKey) => {
  if (!players || !players.length) return "-";
  const vals = players.map((p) => p[colKey]).filter((v) => v != null);
  if (!vals.length) return "-";
  if (colKey === "velocity_max" || colKey === "centroid_distance_max") {
    return parseFloat(Math.max(...vals).toFixed(2));
  }
  return parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1));
};

const findFirstFrameWithHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  return b ? b.first : 0;
};

const findLastFrameWithHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  return b ? b.last : 0;
};
</script>

<style scoped>
.kpi-loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 25vh;
}

.kpi-spinner {
  font-size: 48px;
  color: rgb(var(--v-theme-primary));
}

.kpi-loading-text {
  margin-top: 10px;
  font-size: 18px;
  color: rgb(var(--v-theme-primary));
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
  appearance: textfield;
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
</style>
