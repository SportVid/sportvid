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
  velocityUnit: { type: String, default: "kmh" }, // 'kmh' | 'ms'
});

const velocityUnitHtml = computed(() =>
  props.velocityUnit === "kmh" ? "km⋅h<sup>-1</sup>" : "m⋅s<sup>-1</sup>"
);

const plotContainer = ref(null);
let plotInitialized = false;
let animFrameId = null;
let lastCurrentTime = null;

const selectedStart = computed(() => positionDataStore.selectedTimeRange.start);
const selectedEnd = computed(() => positionDataStore.selectedTimeRange.end);

const kpiLabel = computed(() => {
  if (props.selectedKpi === "running_distance") return t("visualization.kpi.kpi_label.distance");
  if (props.selectedKpi === "velocity") {
    if (props.chartMode === "windowed")
      return t("visualization.kpi.kpi_label.velocity_max_with_unit", { unit: velocityUnitHtml.value });
    return t("visualization.kpi.kpi_label.velocity_with_unit", { unit: velocityUnitHtml.value });
  }
  if (props.selectedKpi === "velocity_max")
    return t("visualization.kpi.kpi_label.velocity_max_with_unit", { unit: velocityUnitHtml.value });
  if (props.selectedKpi === "metabolic_work") return t("visualization.kpi.kpi_label.metabolic_work");
  if (props.selectedKpi === "equivalent_distance") return t("visualization.kpi.kpi_label.equivalent_distance");
  if (props.selectedKpi === "centroid_distance") {
    if (props.chartMode === "windowed") return t("visualization.kpi.kpi_label.centroid_distance_max");
    return t("visualization.kpi.kpi_label.centroid_distance");
  }
  return props.selectedKpi;
});

const kpiUnit = computed(() => {
  const velUnit = props.velocityUnit === "kmh" ? "km/h" : "m/s";
  const units = {
    running_distance: "m",
    velocity_max: velUnit,
    velocity: velUnit,
    metabolic_work: "J/kg",
    equivalent_distance: "m",
    centroid_distance: "m",
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
    return `${kpiLabel.value} / ${formatWindowLabel(props.windowSize)}`;
  }
  return kpiLabel.value;
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
 * Build per-frame raw values from kpiData for each selected player.
 * Returns Map<pid, { player_id, team_id, times[], values[] }>
 * - running_distance: incremental distance per frame (diff of cumulative dist values)
 * - velocity_max: per-frame velocity
 * - metabolic_work: per-frame metabolic power * dt (incremental work)
 */
function buildRawTimeSeries() {
  const rawKpiData = visualizationStore.kpiData;
  if (!rawKpiData || !Object.keys(rawKpiData).length) return new Map();

  const start = selectedStart.value;
  const end = selectedEnd.value;
  const zones = props.selectedZones;
  const dt = 1 / (playerStore.videoFPS || 25);

  const frameKeys = Object.keys(rawKpiData)
    .map(Number)
    .filter((t) => t >= start && t <= end)
    .sort((a, b) => a - b);

  if (frameKeys.length < 2) return new Map();

  const playerSeries = new Map();

  for (const t of frameKeys) {
    const players = rawKpiData[t] || [];
    const posPlayers = topViewStore.getFrameAt(t);
    const posMap = {};
    for (const p of posPlayers) posMap[p[0]] = p;

    for (const p of players) {
      // [pid, tid, dist_inc, dist_cum, vel, metpow, metpow_cum, equiv_dist_inc, equiv_dist_cum, cent_dist]
      const pid = p[0];
      const tid = p[1];
      const dist_inc = p[2];
      const vel = p[4];
      const metpow = p[5];
      const equiv_dist_inc = p[7];
      const cent_dist = p[9];

      if (tid === 1 || tid === 2) continue; // skip ball and ref
      if (!props.selectedPlayerIds.has(pid)) continue;

      const pp = posMap[pid];
      const inZone = pp ? isInAnyZone(pp[3], pp[4], zones) : true;

      if (!playerSeries.has(pid)) {
        playerSeries.set(pid, { player_id: pid, team_id: tid, times: [], values: [] });
      }
      const series = playerSeries.get(pid);

      if (props.selectedKpi === "running_distance") {
        if (dist_inc != null) {
          series.times.push(t);
          series.values.push(inZone && dist_inc > 0 ? dist_inc : 0);
        }
      } else if (props.selectedKpi === "velocity_max" || props.selectedKpi === "velocity") {
        if (vel != null && inZone) {
          const factor = props.velocityUnit === "kmh" ? 3.6 : 1.0;
          series.times.push(t);
          series.values.push(vel * factor);
        }
      } else if (props.selectedKpi === "metabolic_work") {
        if (metpow != null && inZone) {
          series.times.push(t);
          series.values.push(metpow * dt);
        }
      } else if (props.selectedKpi === "equivalent_distance") {
        if (equiv_dist_inc != null) {
          series.times.push(t);
          series.values.push(inZone && equiv_dist_inc > 0 ? equiv_dist_inc : 0);
        }
      } else if (props.selectedKpi === "centroid_distance") {
        if (cent_dist != null) {
          series.times.push(t);
          series.values.push(cent_dist);
        }
      }
    }
  }

  return playerSeries;
}

/**
 * Accumulate values over time.
 * - running_distance / metabolic_work: running sum
 * - velocity_max: keep per-frame values as-is (velocity profile over time)
 */
function toCumulative(rawMap) {
  if (props.selectedKpi === "velocity_max" || props.selectedKpi === "velocity" || props.selectedKpi === "centroid_distance") return rawMap;

  const result = new Map();
  for (const [pid, series] of rawMap) {
    let sum = 0;
    const cumValues = series.values.map((v) => {
      sum += v;
      return parseFloat(sum.toFixed(3));
    });
    result.set(pid, { ...series, values: cumValues });
  }
  return result;
}

/**
 * Fixed-interval step function for running_distance (windowed mode).
 * Divides the full selected time range into intervals of windowSize ms,
 * sums incremental distances per interval, assigns that sum to every frame in the interval.
 */
function toWindowed(rawMap, windowSize) {
  const allTimes = topViewStore.sortedFrameKeys;
  const start = selectedStart.value;
  const end = selectedEnd.value;
  const fullTimeRange = allTimes.filter((t) => t >= start && t <= end);
  if (fullTimeRange.length === 0) return new Map();

  const rangeStart = fullTimeRange[0];

  const playerValLookup = new Map();
  for (const [pid, series] of rawMap) {
    const lookup = new Map();
    for (let i = 0; i < series.times.length; i++) {
      lookup.set(series.times[i], series.values[i]);
    }
    playerValLookup.set(pid, lookup);
  }

  const result = new Map();
  for (const [pid, series] of rawMap) {
    const valLookup = playerValLookup.get(pid);

    const intervalSums = new Map();
    for (const t of fullTimeRange) {
      const idx = Math.floor((t - rangeStart) / windowSize);
      const v = valLookup.get(t) || 0;
      if (props.selectedKpi === "velocity" || props.selectedKpi === "centroid_distance") {
        intervalSums.set(idx, Math.max(intervalSums.get(idx) ?? 0, v));
      } else {
        intervalSums.set(idx, (intervalSums.get(idx) || 0) + v);
      }
    }

    const outTimes = [];
    const outValues = [];
    for (const t of fullTimeRange) {
      const idx = Math.floor((t - rangeStart) / windowSize);
      outTimes.push(t);
      outValues.push(parseFloat((intervalSums.get(idx) || 0).toFixed(2)));
    }

    result.set(pid, {
      player_id: series.player_id,
      team_id: series.team_id,
      times: outTimes,
      values: outValues,
    });
  }
  return result;
}

const MAX_CHART_POINTS = 3000;

function strideDownsample(times, values) {
  if (times.length <= MAX_CHART_POINTS) return { times, values };
  const stride = Math.ceil(times.length / MAX_CHART_POINTS);
  const t = [];
  const v = [];
  for (let i = 0; i < times.length; i += stride) {
    t.push(times[i]);
    v.push(values[i]);
  }
  return { times: t, values: v };
}

function buildChartTraces() {
  const rawMap = buildRawTimeSeries();
  const seriesMap =
    props.chartMode === "windowed"
      ? toWindowed(rawMap, props.windowSize)
      : props.chartMode === "per_frame"
      ? rawMap
      : toCumulative(rawMap);

  if (props.groupMode === "team") {
    const teamMap = new Map();
    for (const [, series] of seriesMap) {
      const tid = series.team_id;
      if (!teamMap.has(tid)) {
        teamMap.set(tid, { team_id: tid, timeValues: new Map() });
      }
      const teamData = teamMap.get(tid);
      for (let i = 0; i < series.times.length; i++) {
        const t = series.times[i];
        const v = series.values[i];
        if (props.selectedKpi === "velocity_max") {
          teamData.timeValues.set(t, Math.max(teamData.timeValues.get(t) ?? 0, v));
        } else {
          teamData.timeValues.set(t, (teamData.timeValues.get(t) ?? 0) + v);
        }
      }
    }

    const traces = [];
    for (const [teamId, team] of teamMap) {
      const sortedTimes = [...team.timeValues.keys()].sort((a, b) => a - b);
      const allValues = sortedTimes.map((t) => parseFloat((team.timeValues.get(t) || 0).toFixed(2)));
      const { times, values } = strideDownsample(sortedTimes, allValues);
      const color = toRgb(visualizationStore.getTeamColor(teamId), 0);
      traces.push({
        x: times,
        y: values,
        type: "scatter",
        mode: "lines",
        name: getTeamName(teamId),
        line: { color, width: 2 },
        hovertemplate: "%{y:.2f} " + kpiUnit.value + "<extra>" + getTeamName(teamId) + "</extra>",
      });
    }
    return traces;
  } else {
    const traces = [];
    for (const [playerId, series] of seriesMap) {
      const allValues = series.values.map((v) => parseFloat(v.toFixed(2)));
      const { times, values } = strideDownsample(series.times, allValues);
      const color = toRgb(props.playerColors[playerId] || "#888888", 0);
      traces.push({
        x: times,
        y: values,
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
}

const chartData = computed(() => buildChartTraces());

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

watch([chartData, chartLayout], () => {
  nextTick(() => updatePlot());
});

watch(
  () => [selectedStart.value, selectedEnd.value],
  () => nextTick(() => updatePlot())
);

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

defineExpose({ saveChart });

async function saveChart() {
  if (!plotContainer.value || !plotInitialized) return;
  try {
    const dataUrl = await Plotly.toImage(plotContainer.value, {
      format: "png",
      width: 1920,
      height: 1080,
    });
    const link = document.createElement("a");
    link.download = "kpi_chart.png";
    link.href = dataUrl;
    link.click();
  } catch (e) {
    console.error("Chart export failed:", e);
  }
}
</script>
