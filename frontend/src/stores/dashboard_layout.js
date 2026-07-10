import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import { dashboardWidgetIds, isTaggableWidget } from "@/config/dashboardWidgets";

function rowWidth(row) {
  return row.cells.reduce((sum, cell) => sum + cell.width, 0);
}

// Greedily packs `cells` (in order) into 2 rows of capacity 2, using `widths`
// as each cell's desired width. Returns null if it doesn't fit.
function packRows(cells, widths) {
  const rows = [[], []];
  const fill = [0, 0];
  let ri = 0;
  for (let i = 0; i < cells.length; i++) {
    const w = widths[i];
    while (ri < 2 && fill[ri] + w > 2) ri++;
    if (ri >= 2) return null;
    rows[ri].push({ cell: cells[i], width: w });
    fill[ri] += w;
    if (fill[ri] >= 2) ri++;
  }
  return rows;
}

// Repacks a flat, ordered list of cells into the 2-row grid. Tries each
// group cell's current (preferred) width first; if that doesn't fit, falls
// back to shrinking every group cell to width 1 — this is what makes a
// full-width group automatically split when something is dropped beside it,
// and what pushes a displaced cell down into the other row.
function repackFlat(flatCells) {
  const preferred = flatCells.map((c) => (c.kind === "group" ? c.width : 1));
  let packed = packRows(flatCells, preferred);
  if (!packed) {
    const shrunk = flatCells.map(() => 1);
    packed = packRows(flatCells, shrunk);
  }
  if (!packed) return null;

  packed.forEach((row) =>
    row.forEach(({ cell, width }) => {
      cell.width = width;
    })
  );
  return [{ cells: packed[0].map((e) => e.cell) }, { cells: packed[1].map((e) => e.cell) }];
}

function cloneCellPure(cell) {
  return cell.kind === "group" ? { ...cell, widgets: [...cell.widgets] } : { ...cell };
}

// Same greedy packing as packRows, but never mutates its input — returns
// fresh clones with `.width` applied. Kept separate from packRows/repackFlat
// (which mutate in place) so the live-drag preview below can never corrupt
// the committed store state, even mid-gesture.
function packRowsPure(cells, widths) {
  const rows = [[], []];
  const fill = [0, 0];
  let ri = 0;
  for (let i = 0; i < cells.length; i++) {
    const w = widths[i];
    while (ri < 2 && fill[ri] + w > 2) ri++;
    if (ri >= 2) return null;
    const clone = cloneCellPure(cells[i]);
    clone.width = w;
    rows[ri].push(clone);
    fill[ri] += w;
    if (fill[ri] >= 2) ri++;
  }
  return rows;
}

// Pure: computes what the layout would look like if `cellId` were moved to
// `targetIndex` in the flat, row-major cell order (interpreted against that
// order *before* removal) — without mutating `layout`. Used for a
// non-committing live-drag preview; the actual move still goes through
// `moveCell` on drop.
export function previewReorderedLayout(layout, cellId, targetIndex) {
  const flat = [...layout.rows[0].cells, ...layout.rows[1].cells];
  const fromIdx = flat.findIndex((c) => c.id === cellId);
  if (fromIdx === -1) return null;

  const working = [...flat];
  const [cell] = working.splice(fromIdx, 1);
  let insertAt = targetIndex;
  if (fromIdx < insertAt) insertAt -= 1;
  insertAt = Math.max(0, Math.min(insertAt, working.length));
  working.splice(insertAt, 0, cell);

  const preferred = working.map((c) => (c.kind === "group" ? c.width : 1));
  let packed = packRowsPure(working, preferred);
  if (!packed) {
    const shrunk = working.map(() => 1);
    packed = packRowsPure(working, shrunk);
  }
  if (!packed) return null;
  return { rows: [{ cells: packed[0] }, { cells: packed[1] }] };
}

function defaultLayout() {
  return {
    rows: [
      {
        cells: [
          { id: crypto.randomUUID(), kind: "video", width: 1 },
          { id: crypto.randomUUID(), kind: "topview", width: 1 },
        ],
      },
      {
        cells: [
          {
            id: crypto.randomUUID(),
            kind: "group",
            widgets: ["timeline", "events", "heatmap", "kpi"],
            activeId: "timeline",
            width: 2,
          },
        ],
      },
    ],
  };
}

function sanitizeLayout(raw) {
  if (!raw || !Array.isArray(raw.rows) || raw.rows.length === 0) {
    return defaultLayout();
  }

  const seenWidgetIds = new Set();
  const rows = [];

  for (let i = 0; i < 2; i++) {
    const rawRow = raw.rows[i];
    const cells = [];
    let widthSum = 0;

    if (rawRow && Array.isArray(rawRow.cells)) {
      for (const rawCell of rawRow.cells) {
        if (!rawCell || typeof rawCell !== "object") continue;
        if (widthSum >= 2) break;

        if (rawCell.kind === "video" || rawCell.kind === "topview") {
          if (seenWidgetIds.has(rawCell.kind)) continue;
          if (widthSum + 1 > 2) continue;
          cells.push({
            id: typeof rawCell.id === "string" ? rawCell.id : crypto.randomUUID(),
            kind: rawCell.kind,
            width: 1,
          });
          widthSum += 1;
          seenWidgetIds.add(rawCell.kind);
        } else if (rawCell.kind === "group") {
          const rawWidgets = Array.isArray(rawCell.widgets) ? rawCell.widgets : [];
          const widgets = [
            ...new Set(rawWidgets.filter((w) => isTaggableWidget(w) && !seenWidgetIds.has(w))),
          ];
          if (widgets.length === 0) continue;

          const width = rawCell.width === 2 ? 2 : 1;
          if (widthSum + width > 2) continue;

          const activeId = widgets.includes(rawCell.activeId) ? rawCell.activeId : widgets[0];
          cells.push({
            id: typeof rawCell.id === "string" ? rawCell.id : crypto.randomUUID(),
            kind: "group",
            widgets,
            activeId,
            width,
          });
          widthSum += width;
          widgets.forEach((w) => seenWidgetIds.add(w));
        }
      }
    }

    rows.push({ cells });
  }

  const hasVideo = rows.some((row) => row.cells.some((cell) => cell.kind === "video"));
  if (!hasVideo) {
    const targetRow = rows.find((row) => rowWidth(row) < 2);
    if (!targetRow) {
      return defaultLayout();
    }
    targetRow.cells.unshift({ id: crypto.randomUUID(), kind: "video", width: 1 });
  }

  return { rows };
}

export const useDashboardLayoutStore = defineStore(
  "dashboard_layout",
  () => {
    const userStore = useUserStore();

    const editMode = ref(false);
    const layout = ref(defaultLayout());
    // Bumped whenever a group's active tab changes, so widget components can
    // trigger a resize/redraw without depending on the removed global tab id.
    const groupActiveTick = ref(0);
    // Ephemeral UI state (like editMode) for the tab-pill drag gesture —
    // which single widget is currently being dragged out of its group cell.
    const draggedTab = ref(null); // { cellId, widgetId } | null

    function startTabDrag(cellId, widgetId) {
      draggedTab.value = { cellId, widgetId };
    }

    function endTabDrag() {
      draggedTab.value = null;
    }

    const placedWidgetIds = computed(() => {
      const ids = new Set();
      for (const row of layout.value.rows) {
        for (const cell of row.cells) {
          if (cell.kind === "video" || cell.kind === "topview") {
            ids.add(cell.kind);
          } else if (cell.kind === "group") {
            cell.widgets.forEach((w) => ids.add(w));
          }
        }
      }
      return ids;
    });

    const availableWidgetIds = computed(() =>
      dashboardWidgetIds.filter((id) => !placedWidgetIds.value.has(id))
    );

    function findCell(cellId) {
      for (let rowIdx = 0; rowIdx < layout.value.rows.length; rowIdx++) {
        const row = layout.value.rows[rowIdx];
        const cellIdx = row.cells.findIndex((c) => c.id === cellId);
        if (cellIdx !== -1) {
          return { rowIdx, cellIdx, row, cell: row.cells[cellIdx] };
        }
      }
      return null;
    }

    function initFromUser() {
      layout.value = sanitizeLayout(userStore.dashboardLayout);
    }

    function resetToDefault() {
      layout.value = defaultLayout();
    }

    function addSolo(rowIdx, kind) {
      if (kind !== "topview") return;
      const row = layout.value.rows[rowIdx];
      if (!row) return;
      if (placedWidgetIds.value.has(kind)) return;
      if (row.cells.length === 0) {
        row.cells.push({ id: crypto.randomUUID(), kind, width: 1 });
      } else if (row.cells.length === 1) {
        if (row.cells[0].width === 2) splitRow(rowIdx);
        row.cells.push({ id: crypto.randomUUID(), kind, width: 1 });
      }
    }

    function addGroupWidget(rowIdx, id) {
      if (!isTaggableWidget(id)) return;
      const row = layout.value.rows[rowIdx];
      if (!row) return;
      if (placedWidgetIds.value.has(id)) return;

      if (row.cells.length === 0) {
        row.cells.push({
          id: crypto.randomUUID(),
          kind: "group",
          widgets: [id],
          activeId: id,
          width: 2,
        });
      } else if (row.cells.length === 1) {
        if (row.cells[0].width === 2) splitRow(rowIdx);
        row.cells.push({
          id: crypto.randomUUID(),
          kind: "group",
          widgets: [id],
          activeId: id,
          width: 1,
        });
      }
    }

    function addTabToGroup(cellId, id) {
      if (!isTaggableWidget(id)) return;
      if (placedWidgetIds.value.has(id)) return;
      const found = findCell(cellId);
      if (!found || found.cell.kind !== "group") return;
      found.cell.widgets.push(id);
      found.cell.activeId = id;
      groupActiveTick.value++;
    }

    function removeWidget(cellId, widgetId = null) {
      const found = findCell(cellId);
      if (!found) return;
      const { row, cellIdx, cell } = found;

      if (cell.kind === "video") return;

      if (cell.kind === "group" && widgetId) {
        const idx = cell.widgets.indexOf(widgetId);
        if (idx === -1) return;
        cell.widgets.splice(idx, 1);
        if (cell.widgets.length === 0) {
          row.cells.splice(cellIdx, 1);
        } else if (cell.activeId === widgetId) {
          cell.activeId = cell.widgets[0];
          groupActiveTick.value++;
        }
        return;
      }

      row.cells.splice(cellIdx, 1);
    }

    function setGroupActive(cellId, id) {
      const found = findCell(cellId);
      if (!found || found.cell.kind !== "group") return;
      if (!found.cell.widgets.includes(id)) return;
      found.cell.activeId = id;
      groupActiveTick.value++;
    }

    function expandToFull(cellId) {
      const found = findCell(cellId);
      if (!found) return;
      const { row, cell } = found;
      if (cell.kind !== "group") return;
      if (row.cells.length !== 1 || cell.width !== 1) return;
      cell.width = 2;
    }

    function splitRow(rowIdx) {
      const row = layout.value.rows[rowIdx];
      if (!row) return;
      if (row.cells.length !== 1 || row.cells[0].width !== 2) return;
      row.cells[0].width = 1;
    }

    // Reorders the grid by moving `cellId` to `targetIndex` in the flat,
    // row-major cell order, then repacks rows/widths around that order.
    // `targetIndex` is interpreted against the flat list *before* removal.
    // Video can be moved like any other tile — it just can't be removed
    // (see removeWidget).
    function moveCell(cellId, targetIndex) {
      const flat = [...layout.value.rows[0].cells, ...layout.value.rows[1].cells];
      const fromIdx = flat.findIndex((c) => c.id === cellId);
      if (fromIdx === -1) return;

      const [cell] = flat.splice(fromIdx, 1);
      let insertAt = targetIndex;
      if (fromIdx < insertAt) insertAt -= 1;
      insertAt = Math.max(0, Math.min(insertAt, flat.length));
      flat.splice(insertAt, 0, cell);

      const repacked = repackFlat(flat);
      if (!repacked) return;
      layout.value.rows[0].cells = repacked[0].cells;
      layout.value.rows[1].cells = repacked[1].cells;
      groupActiveTick.value++;
    }

    // Extracts `widgetId` out of its current group cell and inserts it as a
    // brand-new one-widget cell at `targetIndex` in the flat, row-major cell
    // order (mirrors moveCell's insert/repack, but for a widget that doesn't
    // have its own cell yet). Checks the repack succeeds *before* touching
    // the source cell, so a "no room anywhere" drop leaves everything
    // untouched instead of losing the widget.
    function moveWidgetToNewCell(sourceCellId, widgetId, targetIndex) {
      const flat = [...layout.value.rows[0].cells, ...layout.value.rows[1].cells];
      const newCell = {
        id: crypto.randomUUID(),
        kind: "group",
        widgets: [widgetId],
        activeId: widgetId,
        width: 1,
      };
      const insertAt = Math.max(0, Math.min(targetIndex, flat.length));
      flat.splice(insertAt, 0, newCell);

      const repacked = repackFlat(flat);
      if (!repacked) return;

      removeWidget(sourceCellId, widgetId);
      layout.value.rows[0].cells = repacked[0].cells;
      layout.value.rows[1].cells = repacked[1].cells;
      groupActiveTick.value++;
    }

    // Reorders widgets within a single group cell's tab list — targetIndex
    // is interpreted against the list *before* removal, same convention as
    // moveCell/previewReorderedLayout.
    function moveWidgetWithinGroup(cellId, widgetId, targetIndex) {
      const found = findCell(cellId);
      if (!found || found.cell.kind !== "group") return;
      const widgets = found.cell.widgets;
      const fromIdx = widgets.indexOf(widgetId);
      if (fromIdx === -1) return;
      widgets.splice(fromIdx, 1);
      let insertAt = targetIndex;
      if (fromIdx < insertAt) insertAt -= 1;
      insertAt = Math.max(0, Math.min(insertAt, widgets.length));
      widgets.splice(insertAt, 0, widgetId);
    }

    function activateWidget(id) {
      for (const row of layout.value.rows) {
        for (const cell of row.cells) {
          if (cell.kind === "group" && cell.widgets.includes(id)) {
            setGroupActive(cell.id, id);
            return;
          }
        }
      }
    }

    function persist() {
      userStore.saveDashboardLayout(layout.value);
    }

    function toggleEditMode() {
      editMode.value = !editMode.value;
      if (!editMode.value) {
        persist();
      }
    }

    return {
      editMode,
      layout,
      groupActiveTick,
      draggedTab,
      placedWidgetIds,
      availableWidgetIds,
      initFromUser,
      resetToDefault,
      addSolo,
      addGroupWidget,
      addTabToGroup,
      removeWidget,
      setGroupActive,
      expandToFull,
      splitRow,
      moveCell,
      moveWidgetToNewCell,
      moveWidgetWithinGroup,
      startTabDrag,
      endTabDrag,
      activateWidget,
      toggleEditMode,
      persist,
    };
  },
  {
    persist: false,
  }
);
