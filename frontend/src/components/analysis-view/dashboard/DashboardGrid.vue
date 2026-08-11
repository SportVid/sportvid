<template>
  <div class="dashboard-grid-viewport">
    <div class="dashboard-grid" :class="{ 'dashboard-grid--editing': dashboardStore.editMode }">
      <div
        v-for="cell in allCells"
        :key="cell.id"
        class="dashboard-grid-item"
        :style="itemStyle(cell)"
      >
        <div
          class="dashboard-grid-cell-wrapper"
          :class="{ 'dashboard-grid-cell-wrapper--drop-target': cell.id === dragOverCellId }"
          :draggable="dashboardStore.editMode"
          :ref="(el) => setAnchorWrapperRef(el, cell)"
          @dragstart="onDragStart($event, cell.id)"
          @dragend="onDragEnd"
          @dragover="onDragOverCell($event, cell.id)"
          @drop="onDrop($event)"
        >
          <DashboardCell
            :cell="cell"
            :row-idx="realRowIdx(cell.id)"
            :is-loading="isLoading"
            :constrained="isConstrainedCell(cell)"
          />
          <!-- Overlay only — the real card underneath stays mounted the whole
               time, so the drag source is never removed from the DOM (that
               cancels native HTML5 drag) and no widget state is lost. -->
          <div v-if="cell.id === draggedCellId" class="dashboard-grid-ghost-overlay" />
        </div>
      </div>

      <div
        v-for="slot in addSlots"
        :key="slot.key"
        class="dashboard-grid-item"
        :style="{ gridRow: slot.rowIdx + 1, gridColumn: `${slot.colStart} / span ${slot.width}` }"
        @dragover.prevent="onDragOverAddSlot(slot.rowIdx)"
        @drop="onDropAddSlot($event, slot.rowIdx)"
      >
        <AddWidgetCard :row-idx="slot.rowIdx" :dragging="isDragging" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount } from "vue";
import { useDashboardLayoutStore, previewReorderedLayout } from "@/stores/dashboard_layout";
import DashboardCell from "@/components/analysis-view/dashboard/DashboardCell.vue";
import AddWidgetCard from "@/components/analysis-view/dashboard/AddWidgetCard.vue";

const props = defineProps({
  isLoading: { type: Boolean, default: false },
});

const dashboardStore = useDashboardLayoutStore();

const allCells = computed(() => dashboardStore.layout.rows.flatMap((row) => row.cells));

function computeSlots(rows) {
  const map = new Map();
  rows.forEach((row, rowIdx) => {
    let col = 1;
    row.cells.forEach((cell) => {
      map.set(cell.id, { rowIdx, colStart: col, width: cell.width });
      col += cell.width;
    });
  });
  return map;
}

const realSlots = computed(() => computeSlots(dashboardStore.layout.rows));
function realRowIdx(cellId) {
  return realSlots.value.get(cellId)?.rowIdx ?? 0;
}

// --- Row-height coupling: everything defers to the video's size ---------
//
// The video is the one true anchor: it must always render at exactly the
// size it'd have on its own (see VideoPlayer's own viewport-driven
// max-height) — never stretched by a neighboring topview/widget, in
// whichever row it ends up in. That size is also the ONE reference TopView
// and every tabwindow widget defer to: a cell only gets its own natural/max
// size when it's truly alone in its row (today's plain CSS Grid auto-row
// sizing, untouched); the moment it shares a row with anything else — the
// video, or another widget, e.g. KPI next to the heatmap — it's capped to
// the video's height instead and scrolls its content internally (TopView
// already ties its own content height to the video directly when position
// data is loaded — see topViewStore usage — so this cap mainly matters for
// its "no data selected" placeholder, and for widget/widget pairings).
//
// The video gets `align-self: start` so the grid's row-stretch never
// applies to it, regardless of how tall its row ends up — that alone
// guarantees its rendered height stays genuinely natural. A ResizeObserver
// feeds that natural height back in as the cap applied to every other
// non-solo cell, wherever it sits. TopView must NOT get the same
// align-self override: it needs to stay stretchable so it fills up to the
// video's height by default when they share a row (that's what makes its
// "no data" placeholder match the video's size), rather than sitting at
// its own, much shorter, natural height.
function isVideoCell(cell) {
  return cell.kind === "video";
}

const videoCells = computed(() =>
  dashboardStore.layout.rows.flatMap((row) => row.cells.filter(isVideoCell))
);

const cellNaturalHeights = reactive({}); // cellId -> measured px height
const cellResizeObservers = new Map(); // cellId -> ResizeObserver

function setAnchorWrapperRef(el, cell) {
  const existing = cellResizeObservers.get(cell.id);
  if (existing) {
    existing.disconnect();
    cellResizeObservers.delete(cell.id);
  }
  if (!el || !isVideoCell(cell)) return;
  const ro = new ResizeObserver((entries) => {
    const h = entries[0]?.contentRect?.height;
    if (!h) return;
    // Deferred a frame rather than applied straight from the observer
    // callback — writing reactive state in here can trigger a re-layout
    // within the same ResizeObserver cycle (the widget's max-height
    // reacting to it, in turn nudging the grid), which is exactly what
    // produces the (benign, but noisy) "loop completed with undelivered
    // notifications" condition. Pushing the write to the next frame lets
    // this cycle finish cleanly first.
    requestAnimationFrame(() => {
      cellNaturalHeights[cell.id] = h;
    });
  });
  ro.observe(el);
  cellResizeObservers.set(cell.id, ro);
}

onBeforeUnmount(() => {
  cellResizeObservers.forEach((ro) => ro.disconnect());
  cellResizeObservers.clear();
});

// The single shared reference height every non-solo cell is capped to.
// null before the video's first measurement lands, or if it's been removed
// from the dashboard entirely — other cells fall back to their own natural
// size in that case, same as when they're alone in a row.
const anchorHeight = computed(() => {
  const heights = videoCells.value.map((c) => cellNaturalHeights[c.id]).filter((h) => h > 0);
  return heights.length ? Math.max(...heights) : null;
});

function sharesRow(cell) {
  return (dashboardStore.layout.rows[realRowIdx(cell.id)]?.cells.length ?? 0) > 1;
}

// Only meaningful outside edit mode — while editing, widgets render as
// WidgetPlaceholder (not their real, potentially-tall content), so there's
// nothing to cap yet.
function isConstrainedCell(cell) {
  if (dashboardStore.editMode || cell.kind !== "group") return false;
  return sharesRow(cell) && anchorHeight.value != null;
}

const draggedCellId = ref(null);
// Set synchronously (unlike draggedCellId below, which is deliberately
// deferred for the drag-image snapshot) so anything driven by "is a whole
// cell being dragged right now" — like hiding the add-slot's "+" — updates
// immediately everywhere, not just once the cursor reaches some target.
const wholeCellDragActive = ref(false);
const dragOverTargetIndex = ref(null);
// Whether the current hover target is "beside an existing cell" (true) or a
// brand-new empty row (false) — the shrinkToFit option moveCell gets on drop,
// and what the live preview below renders.
const dragOverShrink = ref(false);
// Set instead of dragOverShrink when hovering the *center* of an existing
// cell — the forceFullWidth option moveCell gets on drop, so the dragged
// cell takes over that whole row in one gesture instead of landing at half
// width and needing a separate manual expand afterwards.
const dragOverFullWidth = ref(false);
// Which existing cell (if any) the cursor is currently over — for the hover
// highlight.
const dragOverCellId = ref(null);

const previewLayout = computed(() => {
  if (!draggedCellId.value || dragOverTargetIndex.value === null) return null;
  return previewReorderedLayout(
    dashboardStore.layout,
    draggedCellId.value,
    dragOverTargetIndex.value,
    { shrinkToFit: dragOverShrink.value, forceFullWidth: dragOverFullWidth.value }
  );
});

const displayRows = computed(() => previewLayout.value?.rows ?? dashboardStore.layout.rows);
const displaySlots = computed(() => computeSlots(displayRows.value));

// Whether a whole cell or a tab is currently being dragged — used to keep
// add-slots available as drop targets regardless of availableWidgetIds, and
// to hide their "+" affordance in that case (it's a drop target then, not
// an "add a new widget" button).
const isDragging = computed(() => wholeCellDragActive.value || !!dashboardStore.draggedTab);

const addSlots = computed(() => {
  if (!dashboardStore.editMode) return [];
  // Nothing left to place anywhere on the dashboard — hide the empty
  // add-slot entirely instead of showing a "+" that can't do anything.
  // Exception: a whole cell or a tab is actively being dragged — the slot
  // must stay as a drop target regardless (to reposition an existing cell
  // there, or because a dragged-out tab isn't "removed" until it's dropped).
  if (dashboardStore.availableWidgetIds.length === 0 && !isDragging.value) return [];
  const slots = [];
  displayRows.value.forEach((row, rowIdx) => {
    const used = row.cells.reduce((sum, cell) => sum + cell.width, 0);
    if (used < 2) {
      slots.push({ key: `add-${rowIdx}`, rowIdx, colStart: used + 1, width: 2 - used });
    }
  });
  // Every existing row is full — offer a brand-new row instead of capping
  // the dashboard at whatever rows already exist.
  if (slots.length === 0) {
    slots.push({
      key: `add-${displayRows.value.length}`,
      rowIdx: displayRows.value.length,
      colStart: 1,
      width: 2,
    });
  }
  return slots;
});

function itemStyle(cell) {
  const slot = displaySlots.value.get(cell.id);
  if (!slot) return {};
  const style = {
    gridRow: slot.rowIdx + 1,
    gridColumn: `${slot.colStart} / span ${slot.width}`,
  };

  if (!dashboardStore.editMode) {
    if (isVideoCell(cell)) {
      style.alignSelf = "start";
    } else if ((cell.kind === "topview" || cell.kind === "group") && sharesRow(cell)) {
      if (anchorHeight.value) style.maxHeight = `${anchorHeight.value}px`;
    }
  }

  return style;
}

function flatCells() {
  return dashboardStore.layout.rows.flatMap((row) => row.cells);
}

// Flat-list insertion index for an add-slot sitting at the end of `rowIdx`
// (or for a brand-new row past the current last one) — the sum of all
// cells in rows up to and including it, row-major order.
function insertIndexForRow(rowIdx) {
  const rows = dashboardStore.layout.rows;
  let idx = 0;
  for (let i = 0; i <= rowIdx && i < rows.length; i++) {
    idx += rows[i].cells.length;
  }
  return idx;
}

function onDragStart(event, cellId) {
  wholeCellDragActive.value = true;
  dragOverTargetIndex.value = null;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", cellId);
  // No custom drag image — cards render at natural size in edit mode now
  // (no CSS-transform scaling to fight), so the browser's default snapshot
  // of the dragged wrapper follows the cursor and matches on-screen size.
  // That snapshot is taken synchronously right after dragstart fires, before
  // any queued macrotask — so deferring the ghost-overlay-triggering state
  // change here (instead of setting it immediately) keeps the real card
  // content in the captured snapshot rather than the overlay that replaces
  // it a moment later.
  setTimeout(() => {
    draggedCellId.value = cellId;
  }, 0);
}

// Switching the *applied* hover target (and so the reflow) waits for this
// dwell time, restarted every time a dragover resolves to a *different*
// target than the one currently applied — and dropped altogether if the
// cursor comes back to the applied target before it elapses. Two dragover
// events a few ms apart for a cursor sitting right on the boundary between
// two hit zones — natural sub-pixel jitter, or the browser's own periodic
// dragover ticks — used to flip the applied target back and forth on every
// tick, reflowing the grid each time: that's the flicker, and it also meant
// a drop could land on whichever target happened to be applied at that
// exact instant rather than the one the user was visually settled on.
// Requiring the *same new* target to keep reappearing for a short stretch
// before it's applied filters that out, while staying effectively instant
// for a deliberate, sustained hover.
const HOVER_DWELL_MS = 100;
let hoverSwitchTimer = null;
let pendingHoverKey = null;
let appliedHoverKey = null;
function cancelPendingHoverSwitch() {
  if (hoverSwitchTimer !== null) {
    clearTimeout(hoverSwitchTimer);
    hoverSwitchTimer = null;
  }
  pendingHoverKey = null;
}
function resetHoverTracking() {
  cancelPendingHoverSwitch();
  appliedHoverKey = null;
}
// `apply` runs once `key` has been the resolved target continuously for
// HOVER_DWELL_MS — never sooner, and never at all if the cursor moves off
// it (or back to the already-applied key) before then.
function requestHoverSwitch(key, apply) {
  if (key === appliedHoverKey) {
    cancelPendingHoverSwitch();
    return;
  }
  if (key === pendingHoverKey) return;
  cancelPendingHoverSwitch();
  pendingHoverKey = key;
  hoverSwitchTimer = setTimeout(() => {
    hoverSwitchTimer = null;
    pendingHoverKey = null;
    appliedHoverKey = key;
    apply();
  }, HOVER_DWELL_MS);
}

function onDragEnd() {
  draggedCellId.value = null;
  wholeCellDragActive.value = false;
  dragOverTargetIndex.value = null;
  dragOverShrink.value = false;
  dragOverFullWidth.value = false;
  dragOverCellId.value = null;
  resetHoverTracking();
}

// Hovering an existing cell is split into three horizontal zones: its left
// edge and right edge each target "insert beside it, on that side" (same as
// before), but the middle now targets "take over this cell's whole row" —
// so a group cell can be dropped straight at full width in one gesture
// instead of always landing at half width and needing a separate manual
// expand afterwards.
const EDGE_ZONE = 0.3;

function onDragOverCell(event, cellId) {
  // Reacts to a whole-cell drag *or* a tab being dragged over another card
  // (to insert it as a new cell there, pushing others aside) — a tab
  // dropped precisely on a group cell's own pill list is handled separately
  // by that cell's onTabRowDrop (and stops propagation before it gets here).
  if (!draggedCellId.value && !dashboardStore.draggedTab) return;
  // Always keep the zone valid (preventDefault) so the browser still fires
  // `drop` here.
  event.preventDefault();
  if (draggedCellId.value === cellId) return;

  const rect = event.currentTarget.getBoundingClientRect();
  const relX = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0.5;
  const idx = flatCells().findIndex((c) => c.id === cellId);

  let zone, targetIdx;
  if (relX < EDGE_ZONE) {
    zone = "left";
    targetIdx = idx;
  } else if (relX > 1 - EDGE_ZONE) {
    zone = "right";
    targetIdx = idx + 1;
  } else {
    zone = "full";
    const slot = realSlots.value.get(cellId);
    targetIdx = insertIndexForRow((slot?.rowIdx ?? 1) - 1);
  }

  requestHoverSwitch(`cell:${zone}:${cellId}`, () => {
    dragOverTargetIndex.value = targetIdx;
    dragOverCellId.value = cellId;
    dragOverShrink.value = zone !== "full";
    dragOverFullWidth.value = zone === "full";
  });
}

function onDrop(event) {
  event.preventDefault();
  if (dashboardStore.draggedTab) {
    const { cellId: sourceCellId, widgetId } = dashboardStore.draggedTab;
    if (dragOverTargetIndex.value !== null) {
      dashboardStore.moveWidgetToNewCell(sourceCellId, widgetId, dragOverTargetIndex.value);
    }
    dashboardStore.endTabDrag();
    dragOverTargetIndex.value = null;
    dragOverCellId.value = null;
    resetHoverTracking();
    return;
  }
  const draggedId = draggedCellId.value || event.dataTransfer.getData("text/plain");
  if (draggedId && dragOverTargetIndex.value !== null) {
    // Dropped directly onto an existing cell — either beside it (shrinking
    // a full-width cell so it actually lands there) or, if the center zone
    // was hovered, forcing the dragged cell to full width instead.
    dashboardStore.moveCell(draggedId, dragOverTargetIndex.value, {
      shrinkToFit: dragOverShrink.value,
      forceFullWidth: dragOverFullWidth.value,
    });
  }
  draggedCellId.value = null;
  wholeCellDragActive.value = false;
  dragOverTargetIndex.value = null;
  dragOverShrink.value = false;
  dragOverFullWidth.value = false;
  dragOverCellId.value = null;
  resetHoverTracking();
}

function onDragOverAddSlot(rowIdx) {
  if (!draggedCellId.value) return;
  requestHoverSwitch(`row:${rowIdx}`, () => {
    dragOverTargetIndex.value = insertIndexForRow(rowIdx);
    // An add-slot is never an existing cell.
    dragOverCellId.value = null;
    // Only an existing (partially filled) row has a cell to sit beside —
    // the brand-new-row slot is empty, so nothing to shrink for.
    dragOverShrink.value = rowIdx < dashboardStore.layout.rows.length;
    dragOverFullWidth.value = false;
  });
}

function onDropAddSlot(event, rowIdx) {
  event.preventDefault();
  if (dashboardStore.draggedTab) {
    const { cellId: sourceCellId, widgetId } = dashboardStore.draggedTab;
    dashboardStore.removeWidget(sourceCellId, widgetId);
    dashboardStore.addGroupWidget(rowIdx, widgetId);
    dashboardStore.endTabDrag();
    resetHoverTracking();
    return;
  }
  const draggedId = draggedCellId.value || event.dataTransfer.getData("text/plain");
  if (draggedId) {
    // Only shrink-to-fit when the slot belongs to an existing (partially
    // filled) row — the brand-new-row slot has nothing to sit beside.
    const isNewRow = rowIdx >= dashboardStore.layout.rows.length;
    dashboardStore.moveCell(draggedId, insertIndexForRow(rowIdx), { shrinkToFit: !isNewRow });
  }
  draggedCellId.value = null;
  wholeCellDragActive.value = false;
  dragOverTargetIndex.value = null;
  dragOverShrink.value = false;
  dragOverFullWidth.value = false;
  dragOverCellId.value = null;
  resetHoverTracking();
}
</script>

<style scoped>
.dashboard-grid-viewport {
  width: 100%;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  /* `auto`, not `1fr` — without a definite height on this grid container
     (it just grows to fit its content), CSS Grid ties all `1fr` auto-rows
     together via a shared flex-fraction: the tallest row's content ends up
     stretching *every* row to match, even ones with nothing to do with it
     (e.g. the video/topview row getting pulled taller by an unrelated,
     much-taller widget row below). `auto` sizes each row purely to its own
     content again, with the 340px floor as the only constraint shared
     across rows. */
  grid-auto-rows: minmax(340px, auto);
  gap: 16px;
}

/* A fixed (not scaled-to-fit-the-viewport) shrink while arranging — with any
   number of rows now possible, keeping cards full-size would mean at most
   ~2 rows fit on screen at once. Narrowing the grid's own width and
   shrinking the row height keeps each card's proportions closer to a
   landscape rectangle, like outside edit mode, instead of just flattening
   it (full width, shorter height). */
.dashboard-grid--editing {
  width: 65%;
  margin: 0 auto;
  grid-auto-rows: minmax(250px, 1fr);
  gap: 10px;
}

.dashboard-grid-item {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  transition: grid-row 0.15s ease, grid-column 0.15s ease;
}

.dashboard-grid-cell-wrapper {
  position: relative;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.dashboard-grid-cell-wrapper--drop-target {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: -3px;
  border-radius: 8px;
}

.dashboard-grid-ghost-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  pointer-events: none;
  border: 3px dashed rgb(var(--v-theme-primary));
  border-radius: 8px;
  /* Fully opaque — this covers the real (still-mounted) card underneath so
     the slot reads as genuinely empty while it's picked up or hovered as
     a drop target, instead of a tinted preview of its content. */
  background: rgb(var(--v-theme-surface));
}
</style>
