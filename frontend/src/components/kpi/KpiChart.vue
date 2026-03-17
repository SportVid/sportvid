<template>
  <div ref="plotContainer" style="width: 100%; min-height: 45vh"></div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import * as Plotly from "plotly.js-dist-min";
import { usePositionDataStore } from "@/stores/position_data";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";
import { usePlayerStore } from "@/stores/player";
import { useTabStore } from "@/stores/tabs";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";
import { getTimecode } from "@/plugins/time";

const positionDataStore = usePositionDataStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const playerStore = usePlayerStore();
const tabStore = useTabStore();
const { t } = useI18n();

const props = defineProps({
  selectedPlayerIds: { type: Set, required: true },
  selectedKpi: { type: String, default: "running_distance" },
  groupMode: { type: String, default: "player" },
  chartMode: { type: String, default: "cumulative" }, // "cumulative" | "windowed"
  windowSize: { type: Number, default: 1000 }, // ms for windowed mode
  windowFrames: { type: Number, default: 0 }, // frames for display label
  playerOptions: { type: Array, default: () => [] },
  playerColors: { type: Object, default: () => ({}) },
  selectedZones: { type: Array, default: () => [] },
});

const plotContainer = ref(null);
let plotInitialized = false;
let animFrameId = null;
let lastCurrentTime = null;

const selectedStart = computed(() => positionDataStore.selectedTimeRange.start);
const selectedEnd = computed(() => positionDataStore.selectedTimeRange.end);

const kpiLabel = computed(() => {
  const labels = {
    running_distance: t("visualization.kpi.kpi_selection.running_distance"),
    velocity_max: t("visualization.kpi.kpi_selection.velocity_max"),
    velocity_mean: t("visualization.kpi.kpi_selection.velocity_mean"),
    metabolic_work: t("visualization.kpi.kpi_selection.metabolic_work"),
  };
  return labels[props.selectedKpi] || props.selectedKpi;
});

const kpiUnit = computed(() => {
  const units = {
    running_distance: "m",
    velocity_max: "m/s",
    velocity_mean: "m/s",
    metabolic_work: "W/kg",
  };
  return units[props.selectedKpi] || "";
});

const formatWindowLabel = (ms) => {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const sec = ms / 1000;
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const min = Math.floor(sec / 60);
  const remSec = Math.round(sec % 60);
  return remSec > 0 ? `${min} min ${remSec}s` : `${min} min`;
};

const yAxisLabel = computed(() => {
  if (props.chartMode === "windowed") {
    return `${kpiLabel.value} / ${formatWindowLabel(props.windowSize)} (${kpiUnit.value})`;
  }
  return `${kpiLabel.value} (${kpiUnit.value})`;
});

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};

function isInAnyZone(x, y, zones) {
  if (!zones || zones.length === 0) return false;
  for (const z of zones) {
    if (x >= z.x0 && x <= z.x1 && y >= z.y0 && y <= z.y1) return true;
  }
  return false;
}

const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return `Team ${teamId}`;
};

/**
 * Compute raw per-frame-interval distance for each player within the selected time range.
 * Returns Map<player_id, { player_id, team_id, times[], distances[] }>
 */
function buildRawTimeSeries() {
  const allTimes = Object.keys(topViewStore.positionDataTopView)
    .map(Number)
    .sort((a, b) => a - b);

  const start = selectedStart.value;
  const end = selectedEnd.value;
  const timeRange = allTimes.filter((t) => t >= start && t <= end);
  if (timeRange.length < 2) return new Map();

  const fieldLength = playerStore.video.field_length;
  const fieldWidth = playerStore.video.field_width;

  const result = new Map();

  // Initialize all selected players with distance 0 at the first frame
  const firstFrame = timeRange[0];
  const firstPlayers = topViewStore.positionDataTopView[firstFrame];
  if (firstPlayers) {
    for (const cp of firstPlayers) {
      const pid = cp[0];
      const tid = cp[1];
      if (tid === 1) continue;
      if (!props.selectedPlayerIds.has(pid)) continue;
      if (
        (visualizationStore.showAggregatedFirst && cp[2] !== 1) ||
        (visualizationStore.showAggregatedSecond && cp[2] !== 2)
      )
        continue;
      result.set(pid, { player_id: pid, team_id: tid, times: [firstFrame], distances: [0] });
    }
  }

  for (let i = 1; i < timeRange.length; i++) {
    const tPrev = timeRange[i - 1];
    const tCurr = timeRange[i];
    const prevPlayers = topViewStore.positionDataTopView[tPrev];
    const currPlayers = topViewStore.positionDataTopView[tCurr];
    if (!prevPlayers || !currPlayers) continue;

    for (const cp of currPlayers) {
      const pid = cp[0];
      const tid = cp[1];
      if (tid === 1) continue;
      if (!props.selectedPlayerIds.has(pid)) continue;
      if (
        (visualizationStore.showAggregatedFirst && cp[2] !== 1) ||
        (visualizationStore.showAggregatedSecond && cp[2] !== 2)
      )
        continue;

      const pp = prevPlayers.find((p) => p[0] === pid);
      if (!pp) continue;
      if (!isInAnyZone(cp[3], cp[4], props.selectedZones)) continue;

      const dx = (cp[3] - pp[3]) * fieldLength;
      const dy = (cp[4] - pp[4]) * fieldWidth;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (!result.has(pid)) {
        result.set(pid, { player_id: pid, team_id: tid, times: [], distances: [] });
      }
      const entry = result.get(pid);
      entry.times.push(tCurr);
      entry.distances.push(dist);
    }
  }

  return result;
}

/**
 * Convert raw per-frame distances into cumulative distances.
 */
function toCumulative(rawMap) {
  const result = new Map();
  for (const [pid, series] of rawMap) {
    const cumDist = [];
    let sum = 0;
    for (const d of series.distances) {
      sum += d;
      cumDist.push(sum);
    }
    result.set(pid, { ...series, distances: cumDist });
  }
  return result;
}

/**
 * Fixed-interval step function:
 * - Divide the FULL selected time range into intervals of windowSize ms
 * - Sum player distances within each interval
 * - Assign that sum to EVERY frame in the time range for that interval
 * - Intervals where the player has no data get value 0
 */
function toWindowed(rawMap, windowSize) {
  // Get ALL frame timestamps in the selected range
  const allTimes = Object.keys(topViewStore.positionDataTopView)
    .map(Number)
    .sort((a, b) => a - b);
  const start = selectedStart.value;
  const end = selectedEnd.value;
  const fullTimeRange = allTimes.filter((t) => t >= start && t <= end);
  if (fullTimeRange.length === 0) return new Map();

  const rangeStart = fullTimeRange[0];

  // Build a lookup: for each player, which distances at which times
  const playerDistLookup = new Map(); // pid -> Map<time, distance>
  for (const [pid, series] of rawMap) {
    const lookup = new Map();
    for (let i = 0; i < series.times.length; i++) {
      lookup.set(series.times[i], series.distances[i]);
    }
    playerDistLookup.set(pid, lookup);
  }

  const result = new Map();
  for (const [pid, series] of rawMap) {
    const distLookup = playerDistLookup.get(pid);

    // First pass: sum distances per interval across ALL frames
    const intervalSums = new Map(); // intervalIndex -> sum
    for (const t of fullTimeRange) {
      const idx = Math.floor((t - rangeStart) / windowSize);
      const dist = distLookup.get(t) || 0;
      intervalSums.set(idx, (intervalSums.get(idx) || 0) + dist);
    }

    // Second pass: assign the interval's value to every frame in the full range
    const outTimes = [];
    const outDistances = [];
    for (const t of fullTimeRange) {
      const idx = Math.floor((t - rangeStart) / windowSize);
      outTimes.push(t);
      outDistances.push(parseFloat((intervalSums.get(idx) || 0).toFixed(2)));
    }

    result.set(pid, {
      player_id: series.player_id,
      team_id: series.team_id,
      times: outTimes,
      distances: outDistances,
    });
  }
  return result;
}

const chartData = computed(() => {
  const rawMap = buildRawTimeSeries();
  const seriesMap =
    props.chartMode === "windowed" ? toWindowed(rawMap, props.windowSize) : toCumulative(rawMap);

  if (props.groupMode === "team") {
    // Aggregate per team
    const teamMap = new Map();
    for (const [, series] of seriesMap) {
      const tid = series.team_id;
      if (!teamMap.has(tid)) {
        teamMap.set(tid, {
          team_id: tid,
          times: series.times.slice(),
          totalDistances: series.distances.slice(),
          count: 1,
        });
      } else {
        const team = teamMap.get(tid);
        team.count++;
        for (let i = 0; i < series.distances.length; i++) {
          if (i < team.totalDistances.length) {
            team.totalDistances[i] += series.distances[i];
          }
        }
        if (series.times.length > team.times.length) {
          team.times = series.times.slice();
        }
      }
    }

    const traces = [];
    for (const [teamId, team] of teamMap) {
      const color = toRgb(visualizationStore.getTeamColor(teamId), 0);
      traces.push({
        x: team.times,
        y: team.totalDistances.map((d) => parseFloat(d.toFixed(2))),
        type: "scatter",
        mode: "lines",
        name: getTeamName(teamId),
        line: { color, width: 2 },
        hovertemplate: "%{y:.2f} " + kpiUnit.value + "<extra>" + getTeamName(teamId) + "</extra>",
      });
    }
    return traces;
  } else {
    // Per player
    const traces = [];
    for (const [playerId, series] of seriesMap) {
      const color = toRgb(props.playerColors[playerId] || "#888888", 0);
      traces.push({
        x: series.times,
        y: series.distances.map((d) => parseFloat(d.toFixed(2))),
        type: "scatter",
        mode: "lines",
        name: `#${getPlayerNumber(playerId)}`,
        line: { color, width: 1.5 },
        hovertemplate:
          "%{y:.2f} " + kpiUnit.value + "<extra>#" + getPlayerNumber(playerId) + "</extra>",
      });
    }
    return traces;
  }
});

const chartLayout = computed(() => ({
  xaxis: {
    range: [selectedStart.value, selectedEnd.value],
    tickvals: computeTickVals(),
    ticktext: computeTickVals().map(() => ""),
    ticks: "outside",
    ticklen: 5,
    tickwidth: 1,
    tickcolor: "#000",
    showline: true,
    linecolor: "#000",
    linewidth: 1,
    showgrid: false,
    fixedrange: true,
    mirror: false,
    showticklabels: false,
  },
  yaxis: {
    title: { text: yAxisLabel.value, standoff: 15 },
    ticks: "outside",
    ticklen: 5,
    tickwidth: 1,
    tickcolor: "#000",
    showline: true,
    linecolor: "#000",
    linewidth: 1,
    showgrid: false,
    fixedrange: true,
    mirror: false,
  },
  showlegend: false,
  legend: { orientation: "h", y: -0.15 },
  hovermode: "x unified",
  margin: { l: 70, r: 30, t: 20, b: 50 },
  paper_bgcolor: "white",
  plot_bgcolor: "white",
  shapes: currentTimeShape(),
  annotations: computeTimeAnnotations(),
  dragmode: false,
}));

function computeTickVals() {
  const start = selectedStart.value;
  const end = selectedEnd.value;
  const range = end - start;
  const numTicks = 5;
  const step = range / numTicks;
  const vals = [];
  for (let i = 0; i <= numTicks; i++) {
    vals.push(start + step * i);
  }
  return vals;
}

function computeTimeAnnotations() {
  const vals = computeTickVals();
  return vals.map((v, index) => {
    let xanchor;
    if (index === 0) {
      xanchor = "left";
    } else if (index === vals.length - 1) {
      xanchor = "right";
    } else {
      xanchor = "center";
    }
    return {
      x: v,
      y: 0,
      xref: "x",
      yref: "paper",
      text: getTimecode(Math.round(v), 3),
      showarrow: false,
      xanchor: xanchor,
      yanchor: "top",
      yshift: -8,
      font: {
        family: "Courier New",
        size: 12,
      },
    };
  });
}

function currentTimeShape() {
  const time = playerStore.currentTime;
  if (time == null) return [];
  return [
    {
      type: "line",
      x0: time,
      x1: time,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: { color: "rgba(0, 0, 0, 0.5)", width: 2, dash: "dot" },
    },
  ];
}

function renderPlot() {
  if (!plotContainer.value) return;
  Plotly.newPlot(plotContainer.value, chartData.value, chartLayout.value, {
    responsive: true,
    displayModeBar: false,
    scrollZoom: false,
    doubleClick: false,
  });
  plotInitialized = true;

  // Click to seek
  plotContainer.value.on("plotly_click", (eventData) => {
    if (eventData.points && eventData.points.length > 0) {
      const xCoordinate = eventData.points[0].x;
      playerStore.setTargetTime(xCoordinate);
    }
  });
}

function updatePlot() {
  if (!plotContainer.value || !plotInitialized) return;
  Plotly.react(plotContainer.value, chartData.value, chartLayout.value, {
    responsive: true,
    displayModeBar: false,
    scrollZoom: false,
    doubleClick: false,
  });
}

function updateTimeMarker() {
  if (!plotContainer.value || !plotInitialized) return;
  const time = playerStore.currentTime;
  if (time === lastCurrentTime) return;
  lastCurrentTime = time;
  Plotly.relayout(plotContainer.value, { shapes: currentTimeShape() });
}

function animLoop() {
  updateTimeMarker();
  animFrameId = requestAnimationFrame(animLoop);
}

// Watch data changes
watch(
  [chartData, chartLayout],
  () => {
    nextTick(() => updatePlot());
  },
  { deep: true }
);

// Watch time range to fully re-render
watch(
  () => [selectedStart.value, selectedEnd.value],
  () => nextTick(() => updatePlot())
);

// Watch tab switch to resize
watch(
  () => tabStore.visualizationTabId,
  () => {
    nextTick(() => {
      if (plotContainer.value && plotInitialized) {
        Plotly.Plots.resize(plotContainer.value);
      }
    });
  }
);

onMounted(() => {
  nextTick(() => renderPlot());
  animFrameId = requestAnimationFrame(animLoop);
});

onBeforeUnmount(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId);
  if (plotContainer.value && plotInitialized) {
    Plotly.purge(plotContainer.value);
  }
});
</script>
