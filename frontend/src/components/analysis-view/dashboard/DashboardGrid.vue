<template>
  <div class="dashboard-grid-viewport" ref="viewportRef" :style="viewportStyle">
    <div class="dashboard-grid" ref="gridRef" :style="{ transform: `scale(${scale})` }">
      <div
        v-for="cell in allCells"
        :key="cell.id"
        class="dashboard-grid-item"
        :style="itemStyle(cell.id)"
      >
        <div
          class="dashboard-grid-cell-wrapper"
          :draggable="dashboardStore.editMode"
          @dragstart="onDragStart($event, cell.id)"
          @dragend="onDragEnd"
          @dragover="onDragOverCell($event, cell.id)"
          @drop="onDrop($event, cell.id)"
        >
          <DashboardCell :cell="cell" :row-idx="realRowIdx(cell.id)" :is-loading="isLoading" />
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
        <AddWidgetCard :row-idx="slot.rowIdx" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useDashboardLayoutStore, previewReorderedLayout } from "@/stores/dashboard_layout";
import DashboardCell from "@/components/analysis-view/dashboard/DashboardCell.vue";
import AddWidgetCard from "@/components/analysis-view/dashboard/AddWidgetCard.vue";

const props = defineProps({
  isLoading: { type: Boolean, default: false },
});

const dashboardStore = useDashboardLayoutStore();

// Scales the whole 2x2 grid down uniformly (same aspect ratio, cards
// untouched internally) so it always fits the viewport height without
// the page scrolling. Only ever shrinks — never scales above 1.
const viewportRef = ref(null);
const gridRef = ref(null);
const scale = ref(1);
const scaledHeight = ref(null);
const VIEWPORT_BOTTOM_MARGIN = 24;

function updateScale() {
  const viewportEl = viewportRef.value;
  const gridEl = gridRef.value;
  if (!viewportEl || !gridEl) return;

  // Only shrink to fit while arranging (edit mode) — outside of that the
  // dashboard keeps its normal card size, scrolling if needed as before.
  if (!dashboardStore.editMode) {
    scale.value = 1;
    scaledHeight.value = null;
    return;
  }

  const naturalWidth = gridEl.offsetWidth;
  const naturalHeight = gridEl.offsetHeight;
  if (!naturalWidth || !naturalHeight) return;

  const availableWidth = viewportEl.clientWidth;
  const top = viewportEl.getBoundingClientRect().top;
  // AppFooter isn't registered with Vuetify's layout system (no `app` prop),
  // so it sits in normal flow below this content instead of being offset
  // for automatically — account for it manually or it forces page scroll.
  const footerHeight = document.querySelector(".v-footer")?.offsetHeight ?? 0;
  const availableHeight = window.innerHeight - top - footerHeight - VIEWPORT_BOTTOM_MARGIN;

  const nextScale = Math.min(1, availableWidth / naturalWidth, availableHeight / naturalHeight);
  scale.value = nextScale > 0 ? nextScale : 1;
  scaledHeight.value = naturalHeight * scale.value;
}

const viewportStyle = computed(() => ({
  height: scaledHeight.value != null ? `${scaledHeight.value}px` : "auto",
}));

let resizeObserver;
let rafId = null;
// Deferring to the next frame breaks the synchronous read-write cycle that
// otherwise trips the browser's (harmless but noisy) "ResizeObserver loop
// completed with undelivered notifications" warning.
function scheduleUpdateScale() {
  if (rafId !== null) return;
  rafId = requestAnimationFrame(() => {
    rafId = null;
    updateScale();
  });
}

onMounted(() => {
  updateScale();
  resizeObserver = new ResizeObserver(() => scheduleUpdateScale());
  if (gridRef.value) resizeObserver.observe(gridRef.value);
  window.addEventListener("resize", scheduleUpdateScale);
});
onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  if (rafId !== null) cancelAnimationFrame(rafId);
  window.removeEventListener("resize", scheduleUpdateScale);
});

watch(
  () => [props.isLoading, dashboardStore.editMode],
  () => nextTick(scheduleUpdateScale)
);

// The v-for source stays derived from the *committed* layout only, so a live
// drag preview never changes this array's order — that's what lets Vue
// reuse (rather than remount) each widget's component instance while cells
// reflow around it.
const allCells = computed(() => [
  ...dashboardStore.layout.rows[0].cells,
  ...dashboardStore.layout.rows[1].cells,
]);

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

const draggedCellId = ref(null);
const dragOverTargetIndex = ref(null);

const previewLayout = computed(() => {
  if (!draggedCellId.value || dragOverTargetIndex.value === null) return null;
  return previewReorderedLayout(
    dashboardStore.layout,
    draggedCellId.value,
    dragOverTargetIndex.value
  );
});

const displayRows = computed(() => previewLayout.value?.rows ?? dashboardStore.layout.rows);
const displaySlots = computed(() => computeSlots(displayRows.value));

const addSlots = computed(() => {
  if (!dashboardStore.editMode) return [];
  // Nothing left to place anywhere on the dashboard — hide the empty
  // add-slot entirely instead of showing a "+" that can't do anything.
  // Exception: a tab is actively being dragged out of its card — the slot
  // must stay as a drop target even though availableWidgetIds is still 0
  // (the widget isn't "removed" until the drop actually happens).
  if (dashboardStore.availableWidgetIds.length === 0 && !dashboardStore.draggedTab) return [];
  const slots = [];
  displayRows.value.forEach((row, rowIdx) => {
    const used = row.cells.reduce((sum, cell) => sum + cell.width, 0);
    if (used < 2) {
      slots.push({ key: `add-${rowIdx}`, rowIdx, colStart: used + 1, width: 2 - used });
    }
  });
  return slots;
});

function itemStyle(cellId) {
  const slot = displaySlots.value.get(cellId);
  if (!slot) return {};
  return {
    gridRow: slot.rowIdx + 1,
    gridColumn: `${slot.colStart} / span ${slot.width}`,
  };
}

function flatCells() {
  return [...dashboardStore.layout.rows[0].cells, ...dashboardStore.layout.rows[1].cells];
}

// Holds the off-screen drag-ghost clone (see onDragStart) until onDragEnd —
// removing it any earlier risks the browser not having captured its
// snapshot yet and silently falling back to the default, full-size ghost.
let dragImageClone = null;

function onDragStart(event, cellId) {
  draggedCellId.value = cellId;
  dragOverTargetIndex.value = null;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", cellId);

  // The browser's default drag-ghost snapshot ignores the ancestor
  // transform:scale() applied while arranging (edit mode), so it renders
  // the card at its full, un-scaled size — much bigger than what's on
  // screen. Feed it a clone with that same scale applied directly on
  // itself (browsers do respect an element's own transform, just not an
  // inherited one) so the ghost matches the current edit-mode size.
  if (scale.value !== 1) {
    const sourceEl = event.currentTarget;
    const rect = sourceEl.getBoundingClientRect();
    const clone = sourceEl.cloneNode(true);
    clone.style.position = "fixed";
    clone.style.top = "0";
    clone.style.left = "-9999px";
    clone.style.margin = "0";
    clone.style.width = `${sourceEl.offsetWidth}px`;
    clone.style.height = `${sourceEl.offsetHeight}px`;
    clone.style.transform = `scale(${scale.value})`;
    clone.style.transformOrigin = "top left";
    clone.style.pointerEvents = "none";
    document.body.appendChild(clone);
    event.dataTransfer.setDragImage(clone, event.clientX - rect.left, event.clientY - rect.top);
    dragImageClone = clone;
  }
}

function onDragEnd() {
  draggedCellId.value = null;
  dragOverTargetIndex.value = null;
  dragImageClone?.remove();
  dragImageClone = null;
}

function onDragOverCell(event, cellId) {
  // Reacts to a whole-cell drag *or* a tab being dragged over another card
  // (to insert it as a new cell there, pushing others aside) — a tab
  // dropped precisely on a group cell's own pill list is handled separately
  // by that cell's onTabRowDrop (and stops propagation before it gets here).
  if (!draggedCellId.value && !dashboardStore.draggedTab) return;
  // Always keep the zone valid (preventDefault) so the browser still fires
  // `drop` here — this fires even on the dragged cell's own (live-reflowed)
  // ghost slot, since it visually follows the cursor to the drop target.
  // Only recompute the target index for a *different* (bystander) cell.
  event.preventDefault();
  if (draggedCellId.value === cellId) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const midpoint = rect.left + rect.width / 2;
  const side = event.clientX < midpoint ? "left" : "right";
  const targetIdx = flatCells().findIndex((c) => c.id === cellId);
  dragOverTargetIndex.value = side === "right" ? targetIdx + 1 : targetIdx;
}

function onDrop(event, cellId) {
  event.preventDefault();
  if (dashboardStore.draggedTab) {
    const { cellId: sourceCellId, widgetId } = dashboardStore.draggedTab;
    if (dragOverTargetIndex.value !== null) {
      dashboardStore.moveWidgetToNewCell(sourceCellId, widgetId, dragOverTargetIndex.value);
    }
    dashboardStore.endTabDrag();
    dragOverTargetIndex.value = null;
    return;
  }
  const draggedId = draggedCellId.value || event.dataTransfer.getData("text/plain");
  if (draggedId && dragOverTargetIndex.value !== null) {
    dashboardStore.moveCell(draggedId, dragOverTargetIndex.value);
  }
  draggedCellId.value = null;
  dragOverTargetIndex.value = null;
}

function onDragOverAddSlot(rowIdx) {
  if (!draggedCellId.value) return;
  dragOverTargetIndex.value =
    rowIdx === 0 ? dashboardStore.layout.rows[0].cells.length : flatCells().length;
}

function onDropAddSlot(event, rowIdx) {
  event.preventDefault();
  if (dashboardStore.draggedTab) {
    const { cellId: sourceCellId, widgetId } = dashboardStore.draggedTab;
    dashboardStore.removeWidget(sourceCellId, widgetId);
    dashboardStore.addGroupWidget(rowIdx, widgetId);
    dashboardStore.endTabDrag();
    return;
  }
  const draggedId = draggedCellId.value || event.dataTransfer.getData("text/plain");
  if (draggedId) {
    const insertAt = rowIdx === 0 ? dashboardStore.layout.rows[0].cells.length : flatCells().length;
    dashboardStore.moveCell(draggedId, insertAt);
  }
  draggedCellId.value = null;
  dragOverTargetIndex.value = null;
}
</script>

<style scoped>
.dashboard-grid-viewport {
  width: 100%;
  overflow: hidden;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(340px, 1fr);
  gap: 16px;
  transform-origin: top center;
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
