<template>
  <div class="dashboard-grid">
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
</template>

<script setup>
import { ref, computed } from "vue";
import { useDashboardLayoutStore, previewReorderedLayout } from "@/stores/dashboard_layout";
import DashboardCell from "@/components/analysis-view/dashboard/DashboardCell.vue";
import AddWidgetCard from "@/components/analysis-view/dashboard/AddWidgetCard.vue";

defineProps({
  isLoading: { type: Boolean, default: false },
});

const dashboardStore = useDashboardLayoutStore();

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
  return previewReorderedLayout(dashboardStore.layout, draggedCellId.value, dragOverTargetIndex.value);
});

const displayRows = computed(() => previewLayout.value?.rows ?? dashboardStore.layout.rows);
const displaySlots = computed(() => computeSlots(displayRows.value));

const addSlots = computed(() => {
  if (!dashboardStore.editMode) return [];
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

function onDragStart(event, cellId) {
  draggedCellId.value = cellId;
  dragOverTargetIndex.value = null;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", cellId);
}

function onDragEnd() {
  draggedCellId.value = null;
  dragOverTargetIndex.value = null;
}

function onDragOverCell(event, cellId) {
  if (!draggedCellId.value) return;
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
  const draggedId = draggedCellId.value || event.dataTransfer.getData("text/plain");
  if (draggedId && dragOverTargetIndex.value !== null) {
    dashboardStore.moveCell(draggedId, dragOverTargetIndex.value);
  }
  draggedCellId.value = null;
  dragOverTargetIndex.value = null;
}

function onDragOverAddSlot(rowIdx) {
  if (!draggedCellId.value) return;
  dragOverTargetIndex.value = rowIdx === 0 ? dashboardStore.layout.rows[0].cells.length : flatCells().length;
}

function onDropAddSlot(event, rowIdx) {
  event.preventDefault();
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
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(340px, 1fr);
  gap: 16px;
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
  background: rgba(var(--v-theme-primary), 0.12);
}
</style>
