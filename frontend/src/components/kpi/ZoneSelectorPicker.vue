<template>
  <v-card elevation="2">
    <div class="zone-picker">
      <div class="zone-picker-header">
        <v-btn size="small" variant="tonal" color="primary" @click="selectAll">
          {{ $t("visualization.kpi.zone_selection.full_size") }}
        </v-btn>
        <v-btn size="small" variant="tonal" color="primary" @click="toggleAllData">
          {{ $t("visualization.kpi.zone_selection.all_data") }}
        </v-btn>
        <v-btn size="small" variant="tonal" color="primary" @click="clearAll">
          {{ $t("visualization.kpi.zone_selection.clear") }}
        </v-btn>
      </div>

      <!-- Handball: football-style grid with row/col band buttons -->
      <template v-if="isHandball">
        <div class="zone-grid zone-grid-handball">
          <!-- [0,0] left: 3 row bands -->
          <div class="side-bands" :style="{ paddingTop: am.top + 'px' }">
            <button
              v-for="(band, i) in HB_ROW_BANDS"
              :key="i"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isHbRowBandSelected(band.zoneIds) }"
              :style="{ height: (band.y1 - band.y0) * am.height + 'px' }"
              @click="toggleHbRowBand(band.zoneIds)"
            />
          </div>
          <!-- [0,1] pitch image + canvas -->
          <div style="position: relative; line-height: 0">
            <img ref="pitchImg" :src="imgSrc" @load="onImgLoad" class="zone-pitch-img" />
            <canvas
              ref="zoneCanvas"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%"
              @click="onCanvasClick"
              @mousemove="onCanvasMouseMove"
              @mouseleave="onCanvasLeave"
            />
          </div>
          <!-- [1,0] empty corner -->
          <div />
          <!-- [1,1] bottom: 4 col bands (2 per half) -->
          <div class="top-bands" :style="{ paddingLeft: am.left + 'px' }">
            <button
              v-for="(band, j) in HB_COL_BANDS"
              :key="j"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isHbColBandSelected(band.half, band.zoneIds) }"
              :style="{ width: (band.x1 - band.x0) * am.width + 'px' }"
              @click="toggleHbColBand(band.half, band.zoneIds)"
            />
          </div>
        </div>
      </template>

      <!-- Basketball: handball-style grid with row/col band buttons -->
      <template v-else-if="isBasketball">
        <div class="zone-grid zone-grid-handball">
          <!-- left: 5 row bands -->
          <div class="side-bands" :style="{ paddingTop: am.top + 'px' }">
            <button
              v-for="(band, i) in BB_ROW_BANDS"
              :key="i"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isBbRowBandSelected(band.zoneIds) }"
              :style="{ height: (band.y1 - band.y0) * am.height + 'px' }"
              @click="toggleBbRowBand(band.zoneIds)"
            />
          </div>
          <!-- pitch image + canvas -->
          <div style="position: relative; line-height: 0">
            <img ref="pitchImg" :src="imgSrc" @load="onImgLoad" class="zone-pitch-img" />
            <canvas
              ref="zoneCanvas"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%"
              @click="onCanvasClick"
              @mousemove="onCanvasMouseMove"
              @mouseleave="onCanvasLeave"
            />
          </div>
          <!-- empty corner -->
          <div />
          <!-- bottom: 4 col bands (2 per half) -->
          <div class="top-bands" :style="{ paddingLeft: am.left + 'px' }">
            <button
              v-for="(band, j) in BB_COL_BANDS"
              :key="j"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isBbColBandSelected(band.half, band.zoneIds) }"
              :style="{ width: (band.x1 - band.x0) * am.width + 'px' }"
              @click="toggleBbColBand(band.half, band.zoneIds)"
            />
          </div>
        </div>
      </template>

      <!-- Soccer: 3×3 grid with band buttons -->
      <template v-else>
        <div class="zone-grid">
          <!-- [0,0] corner -->
          <div />

          <!-- [0,1] top: 3-split transverse -->
          <div class="top-bands" :style="{ paddingLeft: am.left + 'px' }">
            <button
              v-for="(band, j) in TRANS_BANDS_3"
              :key="j"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isColBandSelected(band.cols) }"
              :style="{ width: (band.x1 - band.x0) * am.width + 'px' }"
              @click="toggleColBand(band.cols)"
            />
          </div>

          <!-- [0,2] corner -->
          <div />

          <!-- [1,0] left: 3-split longitudinal -->
          <div class="side-bands" :style="{ paddingTop: am.top + 'px' }">
            <button
              v-for="(band, i) in LONG_BANDS_3"
              :key="i"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isRowBandSelected(band.rows) }"
              :style="{ height: (band.y1 - band.y0) * am.height + 'px' }"
              @click="toggleRowBand(band.rows)"
            />
          </div>

          <!-- [1,1] pitch image + canvas overlay -->
          <div style="position: relative; line-height: 0">
            <img ref="pitchImg" :src="imgSrc" @load="onImgLoad" class="zone-pitch-img" />
            <canvas
              ref="zoneCanvas"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%"
              @click="onCanvasClick"
              @mousemove="onCanvasMouseMove"
              @mouseleave="onCanvasLeave"
            />
          </div>

          <!-- [1,2] right: 5-split longitudinal -->
          <div class="side-bands" :style="{ paddingTop: am.top + 'px' }">
            <button
              v-for="(band, i) in LONG_BANDS_5"
              :key="i"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isRowBandSelected(band.rows) }"
              :style="{ height: (band.y1 - band.y0) * am.height + 'px' }"
              @click="toggleRowBand(band.rows)"
            />
          </div>

          <!-- [2,0] corner -->
          <div />

          <!-- [2,1] bottom: 5-split transverse -->
          <div class="top-bands" :style="{ paddingLeft: am.left + 'px' }">
            <button
              v-for="(band, j) in TRANS_BANDS_5"
              :key="j"
              class="zone-band-btn"
              :class="{ 'zone-band-active': isColBandSelected(band.cols) }"
              :style="{ width: (band.x1 - band.x0) * am.width + 'px' }"
              @click="toggleColBand(band.cols)"
            />
          </div>

          <!-- [2,2] corner -->
          <div />
        </div>
      </template>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import {
  HANDBALL_ZONES,
  BASKETBALL_ZONES,
  getSportZonePolygon,
  isInSportZone,
} from "@/plugins/sport_zones";

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  sport: { type: Object, required: true },
  areaSize: { type: String, default: "full" },
  mirrorXY: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);
const { t } = useI18n();

// ── Sport-specific zone support ───────────────────────────────────────────────

const isHandball = computed(() => props.sport?.key === 'handball');
const isBasketball = computed(() => props.sport?.key === 'basketball');
const isSportSpecific = computed(() => isHandball.value || isBasketball.value);

const currentSportZones = computed(() =>
  isHandball.value ? HANDBALL_ZONES : isBasketball.value ? BASKETBALL_ZONES : []
);

// ── Basketball zone selection (per-half, like handball) ──────────────────────

// Row bands go top-to-bottom in canvas coordinates (y=0 = visual top, y=1 = visual bottom)
const BB_ROW_BANDS = [
  { y0: 0,    y1: 0.06, zoneIds: [2] },
  { y0: 0.06, y1: 0.34, zoneIds: [5, 8] },
  { y0: 0.34, y1: 0.66, zoneIds: [0, 4, 7] },
  { y0: 0.66, y1: 0.94, zoneIds: [3, 6] },
  { y0: 0.94, y1: 1,    zoneIds: [1] },
];
// Split at x=0.29 (3-point break mark); corners (1,2) belong to the outer (3pt) band
const BB_COL_BANDS = [
  { x0: 0,    x1: 0.29, half: 0, zoneIds: [0, 3, 4, 5] },
  { x0: 0.29, x1: 0.5,  half: 0, zoneIds: [1, 2, 6, 7, 8] },
  { x0: 0.5,  x1: 0.71, half: 1, zoneIds: [1, 2, 6, 7, 8] },
  { x0: 0.71, x1: 1,    half: 1, zoneIds: [0, 3, 4, 5] },
];

const selectedBbKeys = computed(() => {
  const set = new Set();
  for (const z of props.modelValue) {
    if (z.sportZone && z.sportKey === 'basketball' && z.half !== undefined)
      set.add(`h${z.half}_z${z.zoneId}`);
  }
  return set;
});

const isBbZoneSelected = (half, zoneId) => selectedBbKeys.value.has(`h${half}_z${zoneId}`);

function emitBbKeys(keySet) {
  const zones = [];
  for (const key of keySet) {
    const m = key.match(/^h(\d)_z(\d+)$/);
    if (m) zones.push({ sportZone: true, sportKey: 'basketball', zoneId: +m[2], half: +m[1] });
  }
  emit('update:modelValue', zones);
}

function toggleBbZone(half, zoneId) {
  const cur = new Set(selectedBbKeys.value);
  const key = `h${half}_z${zoneId}`;
  if (cur.has(key)) cur.delete(key); else cur.add(key);
  emitBbKeys(cur);
}

function toggleBbRowBand(zoneIds) {
  const keys = [];
  for (let h = 0; h < 2; h++) for (const z of zoneIds) keys.push(`h${h}_z${z}`);
  const cur = new Set(selectedBbKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k)); else keys.forEach((k) => cur.add(k));
  emitBbKeys(cur);
}

function toggleBbColBand(half, zoneIds) {
  const keys = zoneIds.map((z) => `h${half}_z${z}`);
  const cur = new Set(selectedBbKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k)); else keys.forEach((k) => cur.add(k));
  emitBbKeys(cur);
}

const isBbRowBandSelected = (zoneIds) => {
  if (isAllData.value) return true;
  for (let h = 0; h < 2; h++) for (const z of zoneIds)
    if (!selectedBbKeys.value.has(`h${h}_z${z}`)) return false;
  return true;
};

const isBbColBandSelected = (half, zoneIds) => {
  if (isAllData.value) return true;
  return zoneIds.every((z) => selectedBbKeys.value.has(`h${half}_z${z}`));
};

// ── Handball zone selection (per-half, football-style) ───────────────────────

// Structural band definitions matching sport_zones.js constants
// HB_GOAL_YL=0.425, HB_GOAL_YH=0.575, HB_CORNER_X=0.2125
const HB_ROW_BANDS = [
  { y0: 0,     y1: 0.425, zoneIds: [0, 1] },
  { y0: 0.425, y1: 0.575, zoneIds: [2] },
  { y0: 0.575, y1: 1,     zoneIds: [3, 4] },
];
const HB_COL_BANDS = [
  { x0: 0,      x1: 0.2125, half: 0, zoneIds: [0, 4] },
  { x0: 0.2125, x1: 0.5,    half: 0, zoneIds: [1, 2, 3] },
  { x0: 0.5,    x1: 0.7875, half: 1, zoneIds: [1, 2, 3] },
  { x0: 0.7875, x1: 1,      half: 1, zoneIds: [0, 4] },
];

// Set of "h{half}_z{zoneId}" keys for selected handball zones
const selectedHbKeys = computed(() => {
  const set = new Set();
  for (const z of props.modelValue) {
    if (z.sportZone && z.sportKey === 'handball' && z.half !== undefined)
      set.add(`h${z.half}_z${z.zoneId}`);
  }
  return set;
});

const isHbZoneSelected = (half, zoneId) => selectedHbKeys.value.has(`h${half}_z${zoneId}`);

function emitHbKeys(keySet) {
  const zones = [];
  for (const key of keySet) {
    const m = key.match(/^h(\d)_z(\d)$/);
    if (m) zones.push({ sportZone: true, sportKey: 'handball', zoneId: +m[2], half: +m[1] });
  }
  emit('update:modelValue', zones);
}

function toggleHbZone(half, zoneId) {
  const cur = new Set(selectedHbKeys.value);
  const key = `h${half}_z${zoneId}`;
  if (cur.has(key)) cur.delete(key); else cur.add(key);
  emitHbKeys(cur);
}

function toggleHbRowBand(zoneIds) {
  const keys = [];
  for (let h = 0; h < 2; h++) for (const z of zoneIds) keys.push(`h${h}_z${z}`);
  const cur = new Set(selectedHbKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k)); else keys.forEach((k) => cur.add(k));
  emitHbKeys(cur);
}

function toggleHbColBand(half, zoneIds) {
  const keys = zoneIds.map((z) => `h${half}_z${z}`);
  const cur = new Set(selectedHbKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k)); else keys.forEach((k) => cur.add(k));
  emitHbKeys(cur);
}

const isHbRowBandSelected = (zoneIds) => {
  if (isAllData.value) return true;
  for (let h = 0; h < 2; h++) for (const z of zoneIds)
    if (!selectedHbKeys.value.has(`h${h}_z${z}`)) return false;
  return true;
};

const isHbColBandSelected = (half, zoneIds) => {
  if (isAllData.value) return true;
  return zoneIds.every((z) => selectedHbKeys.value.has(`h${half}_z${z}`));
};

// ── "All Data" marker zone (passes everything, including outside pitch) ──────
const ALL_DATA_ZONE = { x0: -Infinity, y0: -Infinity, x1: Infinity, y1: Infinity, allData: true };

const isAllData = computed(
  () => props.modelValue.length === 1 && props.modelValue[0].allData === true
);

function toggleAllData() {
  if (isAllData.value) {
    clearAll();
  } else {
    emit("update:modelValue", [ALL_DATA_ZONE]);
  }
}

// ── Zone grid definition from gridConfig ─────────────────────────────────────
// Longitudinal = horizontal dividers (splits rows along Y)
// Transverse   = vertical dividers (splits cols along X)

const LONG_BOUNDS_3 = [0, 0.2025, 0.7955, 1];
const LONG_BOUNDS_5 = [0, 0.2025, 0.365, 0.635, 0.7955, 1];
const TRANS_BOUNDS_3 = [0, 0.33, 0.67, 1];
const TRANS_BOUNDS_5 = [0, 0.1575, 0.33, 0.67, 0.8425, 1];

// 5×5 cell grid uses 5-split boundaries
const N_ROWS = 5;
const N_COLS = 5;

// Map a band boundary range to the 5-split cell indices whose center falls inside it
function boundsToIndices(bandY0, bandY1, cellBounds) {
  const out = [];
  for (let i = 0; i < cellBounds.length - 1; i++) {
    const center = (cellBounds[i] + cellBounds[i + 1]) / 2;
    if (center >= bandY0 && center < bandY1) out.push(i);
  }
  return out;
}

// Build band descriptors: {y0, y1, rows} or {x0, x1, cols}
function buildLongBands(bounds) {
  return Array.from({ length: bounds.length - 1 }, (_, i) => ({
    y0: bounds[i],
    y1: bounds[i + 1],
    rows: boundsToIndices(bounds[i], bounds[i + 1], LONG_BOUNDS_5),
  }));
}
function buildTransBands(bounds) {
  return Array.from({ length: bounds.length - 1 }, (_, i) => ({
    x0: bounds[i],
    x1: bounds[i + 1],
    cols: boundsToIndices(bounds[i], bounds[i + 1], TRANS_BOUNDS_5),
  }));
}

const LONG_BANDS_3 = buildLongBands(LONG_BOUNDS_3);
const LONG_BANDS_5 = buildLongBands(LONG_BOUNDS_5);
const TRANS_BANDS_3 = buildTransBands(TRANS_BOUNDS_3);
const TRANS_BANDS_5 = buildTransBands(TRANS_BOUNDS_5);

// ── Cell-based zone model ────────────────────────────────────────────────────

const cellKey = (r, c) => `${r}_${c}`;

function cellToZone(r, c) {
  return {
    x0: TRANS_BOUNDS_5[c],
    y0: LONG_BOUNDS_5[r],
    x1: TRANS_BOUNDS_5[c + 1],
    y1: LONG_BOUNDS_5[r + 1],
  };
}

// Parse modelValue → Set of "r_c" keys by matching against known boundaries
const EPS = 1e-5;
const selectedCellKeys = computed(() => {
  const set = new Set();
  for (const z of props.modelValue) {
    const r = LONG_BOUNDS_5.findIndex((b) => Math.abs(b - z.y0) < EPS);
    const c = TRANS_BOUNDS_5.findIndex((b) => Math.abs(b - z.x0) < EPS);
    if (r >= 0 && r < N_ROWS && c >= 0 && c < N_COLS) set.add(cellKey(r, c));
  }
  return set;
});

function emitCells(keySet) {
  const zones = [];
  for (const key of keySet) {
    const [r, c] = key.split("_").map(Number);
    zones.push(cellToZone(r, c));
  }
  emit("update:modelValue", zones);
}

const selectAll = () => {
  if (isHandball.value) {
    const zones = [];
    for (let h = 0; h < 2; h++)
      for (let i = 0; i < 5; i++)
        zones.push({ sportZone: true, sportKey: 'handball', zoneId: i, half: h });
    emit('update:modelValue', zones);
    return;
  }
  if (isBasketball.value) {
    const zones = [];
    for (let h = 0; h < 2; h++)
      for (const z of BASKETBALL_ZONES)
        zones.push({ sportZone: true, sportKey: 'basketball', zoneId: z.id, half: h });
    emit('update:modelValue', zones);
    return;
  }
  const all = new Set();
  for (let r = 0; r < N_ROWS; r++) for (let c = 0; c < N_COLS; c++) all.add(cellKey(r, c));
  emitCells(all);
};
const clearAll = () => emit("update:modelValue", []);

function toggleCell(r, c) {
  const cur = new Set(selectedCellKeys.value);
  const key = cellKey(r, c);
  if (cur.has(key)) cur.delete(key);
  else cur.add(key);
  emitCells(cur);
}

function toggleColBand(cols) {
  const effectiveCols = props.mirrorXY ? cols.map((c) => N_COLS - 1 - c) : cols;
  const keys = [];
  for (let r = 0; r < N_ROWS; r++) for (const c of effectiveCols) keys.push(cellKey(r, c));
  const cur = new Set(selectedCellKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k));
  else keys.forEach((k) => cur.add(k));
  emitCells(cur);
}

function toggleRowBand(rows) {
  const effectiveRows = props.mirrorXY ? rows.map((r) => N_ROWS - 1 - r) : rows;
  const keys = [];
  for (const r of effectiveRows) for (let c = 0; c < N_COLS; c++) keys.push(cellKey(r, c));
  const cur = new Set(selectedCellKeys.value);
  const allSel = keys.every((k) => cur.has(k));
  if (allSel) keys.forEach((k) => cur.delete(k));
  else keys.forEach((k) => cur.add(k));
  emitCells(cur);
}

const isColBandSelected = (cols) => {
  if (isAllData.value) return true;
  const effectiveCols = props.mirrorXY ? cols.map((c) => N_COLS - 1 - c) : cols;
  for (let r = 0; r < N_ROWS; r++)
    for (const c of effectiveCols) if (!selectedCellKeys.value.has(cellKey(r, c))) return false;
  return effectiveCols.length > 0;
};

const isRowBandSelected = (rows) => {
  if (isAllData.value) return true;
  const effectiveRows = props.mirrorXY ? rows.map((r) => N_ROWS - 1 - r) : rows;
  for (const r of effectiveRows)
    for (let c = 0; c < N_COLS; c++) if (!selectedCellKeys.value.has(cellKey(r, c))) return false;
  return effectiveRows.length > 0;
};

// ── Pitch image & area metrics ───────────────────────────────────────────────

const pitchImg = ref(null);
const zoneCanvas = ref(null);
const pitchSize = ref({ width: 0, height: 0 });
const am = ref({ left: 0, top: 0, width: 0, height: 0 });

const currentArea = computed(
  () => props.sport.areas?.[props.areaSize] ?? props.sport.areas?.full ?? {}
);
const imgSrc = computed(() => currentArea.value.image ?? props.sport.areaImage);

const measurePitch = () => {
  const img = pitchImg.value;
  if (!img || !img.naturalWidth) return;
  const rect = img.getBoundingClientRect();
  if (!rect.width || !rect.height) return;

  const scaleX = rect.width / img.naturalWidth;
  const scaleY = rect.height / img.naturalHeight;
  const wRel = currentArea.value.widthRel ?? 1;
  const hRel = currentArea.value.heightRel ?? 1;

  pitchSize.value = { width: rect.width, height: rect.height };
  am.value = {
    left: ((1 - wRel) / 2) * img.naturalWidth * scaleX,
    top: ((1 - hRel) / 2) * img.naturalHeight * scaleY,
    width: img.naturalWidth * wRel * scaleX,
    height: img.naturalHeight * hRel * scaleY,
  };
  renderCanvas();
};

const onImgLoad = () => requestAnimationFrame(() => nextTick(() => measurePitch()));

const resizeObserver = new ResizeObserver(() => measurePitch());
onMounted(() => {
  nextTick(() => {
    if (pitchImg.value) {
      resizeObserver.observe(pitchImg.value);
      if (pitchImg.value.complete && pitchImg.value.naturalWidth) measurePitch();
    }
  });
});
onBeforeUnmount(() => resizeObserver.disconnect());

// ── Canvas rendering ─────────────────────────────────────────────────────────

const hoveredCell = ref(null);
const hoveredBbZone = ref(null);  // basketball: { half, zoneId }
const hoveredHbZone = ref(null);  // handball:   { half, zoneId }

function renderCanvas() {
  const canvas = zoneCanvas.value;
  if (!canvas) return;
  const { width: w, height: h } = pitchSize.value;
  if (!w || !h) return;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  if (props.mirrorXY) {
    ctx.translate(w, h);
    ctx.scale(-1, -1);
  }

  const { left: al, top: at, width: aw, height: ah } = am.value;
  if (!aw || !ah) return;

  const rgb = getComputedStyle(canvas).getPropertyValue("--v-theme-secondary").trim();
  const fillColor = `rgba(${rgb},0.45)`;
  const strokeColor = `rgba(${rgb},1)`;

  // ── Handball zone rendering (per-half) ───────────────────────────────────
  if (isHandball.value) {
    const toCanvasPt = ([nx, ny]) => [al + nx * aw, at + ny * ah];
    const drawPoly = (poly) => {
      if (poly.length < 2) return;
      const [x0, y0] = toCanvasPt(poly[0]);
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      for (let i = 1; i < poly.length; i++) {
        const [xi, yi] = toCanvasPt(poly[i]);
        ctx.lineTo(xi, yi);
      }
      ctx.closePath();
    };

    if (isAllData.value) {
      ctx.fillStyle = fillColor;
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(0, 0, w, h);
    } else {
      for (let half = 0; half < 2; half++) {
        for (const zone of currentSportZones.value) {
          const poly = getSportZonePolygon('handball', zone.id, half);
          const selected = isHbZoneSelected(half, zone.id);
          drawPoly(poly);
          if (selected) { ctx.fillStyle = fillColor; ctx.fill(); }
          ctx.strokeStyle = selected ? strokeColor : 'rgba(80,80,80,0.35)';
          ctx.lineWidth = selected ? 1.5 : 0.7;
          ctx.stroke();
        }
      }
    }

    // Hover highlight
    if (hoveredHbZone.value !== null) {
      const poly = getSportZonePolygon('handball', hoveredHbZone.value.zoneId, hoveredHbZone.value.half);
      drawPoly(poly);
      ctx.fillStyle = `rgba(${rgb},0.2)`;
      ctx.fill();
    }
    return;
  }

  // ── Basketball zone rendering (per-half, like handball) ──────────────────
  if (isBasketball.value) {
    const toCanvasPt = ([nx, ny]) => [al + nx * aw, at + ny * ah];
    const drawPoly = (poly) => {
      if (poly.length < 2) return;
      const [x0, y0] = toCanvasPt(poly[0]);
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      for (let i = 1; i < poly.length; i++) {
        const [xi, yi] = toCanvasPt(poly[i]);
        ctx.lineTo(xi, yi);
      }
      ctx.closePath();
    };

    if (isAllData.value) {
      ctx.fillStyle = fillColor;
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(0, 0, w, h);
    } else {
      for (let half = 0; half < 2; half++) {
        for (const zone of BASKETBALL_ZONES) {
          const poly = getSportZonePolygon('basketball', zone.id, half);
          const selected = isBbZoneSelected(half, zone.id);
          drawPoly(poly);
          if (selected) { ctx.fillStyle = fillColor; ctx.fill(); }
          ctx.strokeStyle = selected ? strokeColor : 'rgba(80,80,80,0.35)';
          ctx.lineWidth = selected ? 1.5 : 0.7;
          ctx.stroke();
        }
      }
    }

    if (hoveredBbZone.value !== null) {
      const poly = getSportZonePolygon('basketball', hoveredBbZone.value.zoneId, hoveredBbZone.value.half);
      drawPoly(poly);
      ctx.fillStyle = `rgba(${rgb},0.2)`;
      ctx.fill();
    }
    return;
  }

  // ── Soccer rectangular grid rendering ─────────────────────────────────────

  // Draw non-uniform grid lines (5-split boundaries)
  ctx.strokeStyle = "rgba(80,80,80,0.45)";
  ctx.lineWidth = 0.8;
  for (const xRel of TRANS_BOUNDS_5) {
    const x = al + xRel * aw;
    ctx.beginPath();
    ctx.moveTo(x, at);
    ctx.lineTo(x, at + ah);
    ctx.stroke();
  }
  for (const yRel of LONG_BOUNDS_5) {
    const y = at + yRel * ah;
    ctx.beginPath();
    ctx.moveTo(al, y);
    ctx.lineTo(al + aw, y);
    ctx.stroke();
  }

  if (isAllData.value) {
    ctx.fillStyle = fillColor;
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, w, h);
  } else if (selectedCellKeys.value.size === N_ROWS * N_COLS) {
    ctx.fillStyle = fillColor;
    ctx.fillRect(al, at, aw, ah);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(al, at, aw, ah);
  } else {
    const sel = selectedCellKeys.value;
    for (const key of sel) {
      const [r, c] = key.split("_").map(Number);
      const x = al + TRANS_BOUNDS_5[c] * aw;
      const y = at + LONG_BOUNDS_5[r] * ah;
      const cw = (TRANS_BOUNDS_5[c + 1] - TRANS_BOUNDS_5[c]) * aw;
      const ch = (LONG_BOUNDS_5[r + 1] - LONG_BOUNDS_5[r]) * ah;
      ctx.fillStyle = fillColor;
      ctx.fillRect(x, y, cw, ch);
    }
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const key of sel) {
      const [r, c] = key.split("_").map(Number);
      const x = al + TRANS_BOUNDS_5[c] * aw;
      const y = at + LONG_BOUNDS_5[r] * ah;
      const cw = (TRANS_BOUNDS_5[c + 1] - TRANS_BOUNDS_5[c]) * aw;
      const ch = (LONG_BOUNDS_5[r + 1] - LONG_BOUNDS_5[r]) * ah;
      if (!sel.has(cellKey(r - 1, c))) { ctx.moveTo(x, y); ctx.lineTo(x + cw, y); }
      if (!sel.has(cellKey(r + 1, c))) { ctx.moveTo(x, y + ch); ctx.lineTo(x + cw, y + ch); }
      if (!sel.has(cellKey(r, c - 1))) { ctx.moveTo(x, y); ctx.lineTo(x, y + ch); }
      if (!sel.has(cellKey(r, c + 1))) { ctx.moveTo(x + cw, y); ctx.lineTo(x + cw, y + ch); }
    }
    ctx.stroke();
  }

  if (hoveredCell.value) {
    const { r, c } = hoveredCell.value;
    const x = al + TRANS_BOUNDS_5[c] * aw;
    const y = at + LONG_BOUNDS_5[r] * ah;
    const cw = (TRANS_BOUNDS_5[c + 1] - TRANS_BOUNDS_5[c]) * aw;
    const ch = (LONG_BOUNDS_5[r + 1] - LONG_BOUNDS_5[r]) * ah;
    ctx.fillStyle = `rgba(${rgb},0.25)`;
    ctx.fillRect(x, y, cw, ch);
  }
}

// ── Canvas interaction ────────────────────────────────────────────────────────

function _canvasNormCoords(event) {
  const canvas = zoneCanvas.value;
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / (window.devicePixelRatio || 1) / rect.width;
  const scaleY = canvas.height / (window.devicePixelRatio || 1) / rect.height;
  const cx = (event.clientX - rect.left) * scaleX;
  const cy = (event.clientY - rect.top) * scaleY;
  const { left: al, top: at, width: aw, height: ah } = am.value;
  if (!aw || !ah) return null;
  let xRel = (cx - al) / aw;
  let yRel = (cy - at) / ah;
  if (props.mirrorXY) { xRel = 1 - xRel; yRel = 1 - yRel; }
  return { xRel, yRel, inArea: cx >= al && cx <= al + aw && cy >= at && cy <= at + ah };
}

function getBbZoneAtPoint(xRel, yRel) {
  const half = xRel <= 0.5 ? 0 : 1;
  for (const zone of BASKETBALL_ZONES) {
    if (isInSportZone('basketball', zone.id, xRel, yRel, half)) return { half, zoneId: zone.id };
  }
  return null;
}

function getHbZoneAtPoint(xRel, yRel) {
  const half = xRel <= 0.5 ? 0 : 1;
  for (const zone of currentSportZones.value) {
    if (isInSportZone('handball', zone.id, xRel, yRel, half)) return { half, zoneId: zone.id };
  }
  return null;
}

function getCell(event) {
  const coords = _canvasNormCoords(event);
  if (!coords || !coords.inArea) return null;
  const { xRel, yRel } = coords;
  let c = N_COLS - 1;
  for (let j = 0; j < N_COLS; j++) {
    if (xRel < TRANS_BOUNDS_5[j + 1]) { c = j; break; }
  }
  let r = N_ROWS - 1;
  for (let i = 0; i < N_ROWS; i++) {
    if (yRel < LONG_BOUNDS_5[i + 1]) { r = i; break; }
  }
  return { r, c };
}

function onCanvasClick(event) {
  const coords = _canvasNormCoords(event);
  if (!coords) return;
  if (isHandball.value) {
    const z = getHbZoneAtPoint(coords.xRel, coords.yRel);
    if (z !== null) toggleHbZone(z.half, z.zoneId);
    return;
  }
  if (isBasketball.value) {
    const z = getBbZoneAtPoint(coords.xRel, coords.yRel);
    if (z !== null) toggleBbZone(z.half, z.zoneId);
    return;
  }
  const cell = getCell(event);
  if (cell) toggleCell(cell.r, cell.c);
}

function onCanvasMouseMove(event) {
  const coords = _canvasNormCoords(event);
  if (isHandball.value) {
    const z = coords ? getHbZoneAtPoint(coords.xRel, coords.yRel) : null;
    const prev = hoveredHbZone.value;
    const changed = (z === null) !== (prev === null) ||
      (z && prev && (z.half !== prev.half || z.zoneId !== prev.zoneId));
    if (changed) {
      hoveredHbZone.value = z;
      if (zoneCanvas.value) zoneCanvas.value.style.cursor = z ? 'pointer' : 'default';
    }
    return;
  }
  if (isBasketball.value) {
    const z = coords ? getBbZoneAtPoint(coords.xRel, coords.yRel) : null;
    const prev = hoveredBbZone.value;
    const changed = (z === null) !== (prev === null) ||
      (z && prev && (z.half !== prev.half || z.zoneId !== prev.zoneId));
    if (changed) {
      hoveredBbZone.value = z;
      if (zoneCanvas.value) zoneCanvas.value.style.cursor = z ? 'pointer' : 'default';
    }
    return;
  }
  const cell = getCell(event);
  const cur = hoveredCell.value;
  const changed =
    (cell === null) !== (cur === null) || (cell && cur && (cell.r !== cur.r || cell.c !== cur.c));
  if (changed) {
    hoveredCell.value = cell;
    if (zoneCanvas.value) zoneCanvas.value.style.cursor = cell ? "pointer" : "default";
  }
}

function onCanvasLeave() {
  hoveredCell.value = null;
  hoveredBbZone.value = null;
  hoveredHbZone.value = null;
}

watch(
  [selectedCellKeys, hoveredCell, pitchSize, isAllData, () => props.mirrorXY,
   selectedBbKeys, hoveredBbZone, selectedHbKeys, hoveredHbZone],
  () => renderCanvas()
);
watch(
  () => props.areaSize,
  () => nextTick(() => measurePitch())
);
watch(
  () => props.sport?.key,
  () => nextTick(() => measurePitch())
);
</script>

<style scoped>
.zone-picker {
  padding: 12px;
}

.zone-picker-header {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 10px;
}

.zone-grid {
  display: grid;
  grid-template-columns: 14px auto 14px;
  grid-template-rows: 14px auto 14px;
  gap: 2px;
}

.zone-grid-handball {
  grid-template-columns: 14px auto;
  grid-template-rows: auto 14px;
}

.top-bands {
  display: flex;
  height: 14px;
  box-sizing: border-box;
}

.side-bands {
  display: flex;
  flex-direction: column;
  width: 14px;
  box-sizing: border-box;
}

.zone-pitch-img {
  display: block;
  height: 40vh;
  width: auto;
}

.zone-band-btn {
  display: block;
  flex-shrink: 0;
  background: #e0e0e0;
  border: 1px solid #bbb;
  cursor: pointer;
  padding: 0;
  box-sizing: border-box;
  transition: background 0.12s;
}

.zone-band-btn:hover {
  background: rgba(var(--v-theme-secondary), 0.25);
  border-color: rgba(var(--v-theme-secondary), 0.6);
}

.zone-band-active {
  background: rgba(var(--v-theme-secondary), 1) !important;
  border-color: rgba(var(--v-theme-secondary), 1) !important;
}

</style>
