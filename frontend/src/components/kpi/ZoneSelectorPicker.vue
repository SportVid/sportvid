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

      <!-- 3×3 grid: [corner|top-3|corner] / [left-3|pitch|right-5] / [corner|bottom-5|corner] -->
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
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  sport: { type: Object, required: true },
  areaSize: { type: String, default: "full" },
  mirrorXY: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

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

  // Draw selected cells or "all data" overlay
  const rgb = getComputedStyle(canvas).getPropertyValue("--v-theme-secondary").trim();
  const fillColor = `rgba(${rgb},0.5)`;
  const strokeColor = `rgba(${rgb},1)`;

  if (isAllData.value) {
    // All Data: fill entire image, one border around image
    ctx.fillStyle = fillColor;
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, w, h);
  } else if (selectedCellKeys.value.size === N_ROWS * N_COLS) {
    // Full Size: fill pitch area, one border around pitch
    ctx.fillStyle = fillColor;
    ctx.fillRect(al, at, aw, ah);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(al, at, aw, ah);
  } else {
    // Individual zones: fill each cell, draw contour around connected regions
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
    // Contour: only draw edges where neighbor is not selected
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const key of sel) {
      const [r, c] = key.split("_").map(Number);
      const x = al + TRANS_BOUNDS_5[c] * aw;
      const y = at + LONG_BOUNDS_5[r] * ah;
      const cw = (TRANS_BOUNDS_5[c + 1] - TRANS_BOUNDS_5[c]) * aw;
      const ch = (LONG_BOUNDS_5[r + 1] - LONG_BOUNDS_5[r]) * ah;
      if (!sel.has(cellKey(r - 1, c))) {
        ctx.moveTo(x, y);
        ctx.lineTo(x + cw, y);
      }
      if (!sel.has(cellKey(r + 1, c))) {
        ctx.moveTo(x, y + ch);
        ctx.lineTo(x + cw, y + ch);
      }
      if (!sel.has(cellKey(r, c - 1))) {
        ctx.moveTo(x, y);
        ctx.lineTo(x, y + ch);
      }
      if (!sel.has(cellKey(r, c + 1))) {
        ctx.moveTo(x + cw, y);
        ctx.lineTo(x + cw, y + ch);
      }
    }
    ctx.stroke();
  }

  // Draw hovered cell
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

function getCell(event) {
  const canvas = zoneCanvas.value;
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / (window.devicePixelRatio || 1) / rect.width;
  const scaleY = canvas.height / (window.devicePixelRatio || 1) / rect.height;
  const cx = (event.clientX - rect.left) * scaleX;
  const cy = (event.clientY - rect.top) * scaleY;
  const { left: al, top: at, width: aw, height: ah } = am.value;
  if (cx < al || cx > al + aw || cy < at || cy > at + ah) return null;

  // Find which cell boundary the click falls in
  let xRel = (cx - al) / aw;
  let yRel = (cy - at) / ah;
  if (props.mirrorXY) {
    xRel = 1 - xRel;
    yRel = 1 - yRel;
  }
  let c = N_COLS - 1;
  for (let j = 0; j < N_COLS; j++) {
    if (xRel < TRANS_BOUNDS_5[j + 1]) {
      c = j;
      break;
    }
  }
  let r = N_ROWS - 1;
  for (let i = 0; i < N_ROWS; i++) {
    if (yRel < LONG_BOUNDS_5[i + 1]) {
      r = i;
      break;
    }
  }
  return { r, c };
}

function onCanvasClick(event) {
  const cell = getCell(event);
  if (cell) toggleCell(cell.r, cell.c);
}

function onCanvasMouseMove(event) {
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
}

watch([selectedCellKeys, hoveredCell, pitchSize, isAllData, () => props.mirrorXY], () => renderCanvas());
watch(
  () => props.areaSize,
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
