import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import { dashboardWidgetIds, isTaggableWidget } from "@/config/dashboardWidgets";

// Greedily packs `cells` (in order) into as many rows of capacity 2 as
// needed, using `widths` as each cell's desired width — a row is closed out
// (moving on to a new one) once a cell wouldn't fit in its remaining space.
function packRows(cells, widths) {
  const rows = [];
  let current = [];
  let fill = 0;
  for (let i = 0; i < cells.length; i++) {
    const w = widths[i];
    if (fill + w > 2) {
      rows.push(current);
      current = [];
      fill = 0;
    }
    current.push({ cell: cells[i], width: w });
    fill += w;
    if (fill >= 2) {
      rows.push(current);
      current = [];
      fill = 0;
    }
  }
  if (current.length > 0) rows.push(current);
  return rows;
}

// Repacks a flat, ordered list of cells into rows, using each group cell's
// current (preferred) width.
function repackFlat(flatCells) {
  const widths = flatCells.map((c) => (c.kind === "group" ? c.width : 1));
  const packed = packRows(flatCells, widths);
  packed.forEach((row) =>
    row.forEach(({ cell, width }) => {
      cell.width = width;
    })
  );
  return packed.map((row) => ({ cells: row.map((e) => e.cell) }));
}

function cloneCellPure(cell) {
  return cell.kind === "group" ? { ...cell, widgets: [...cell.widgets] } : { ...cell };
}

// Same greedy packing as packRows, but never mutates its input — returns
// fresh clones with `.width` applied. Kept separate from packRows/repackFlat
// (which mutate in place) so the live-drag preview below can never corrupt
// the committed store state, even mid-gesture.
function packRowsPure(cells, widths) {
  const rows = [];
  let current = [];
  let fill = 0;
  for (let i = 0; i < cells.length; i++) {
    const w = widths[i];
    if (fill + w > 2) {
      rows.push(current);
      current = [];
      fill = 0;
    }
    const clone = cloneCellPure(cells[i]);
    clone.width = w;
    current.push(clone);
    fill += w;
    if (fill >= 2) {
      rows.push(current);
      current = [];
      fill = 0;
    }
  }
  if (current.length > 0) rows.push(current);
  return rows;
}

// Pure: computes what the layout would look like if `cellId` were moved to
// `targetIndex` in the flat, row-major cell order (interpreted against that
// order *before* removal) — without mutating `layout`. Used for a
// non-committing live-drag preview; the actual move still goes through
// `moveCell` on drop. `shrinkToFit`/`forceFullWidth` mirror moveCell's
// options, so the preview matches what dropping there will actually produce.
export function previewReorderedLayout(
  layout,
  cellId,
  targetIndex,
  { shrinkToFit = false, forceFullWidth = false } = {}
) {
  const flat = layout.rows.flatMap((row) => row.cells);
  const fromIdx = flat.findIndex((c) => c.id === cellId);
  if (fromIdx === -1) return null;

  const working = [...flat];
  const [cell] = working.splice(fromIdx, 1);
  let insertAt = targetIndex;
  if (fromIdx < insertAt) insertAt -= 1;
  insertAt = Math.max(0, Math.min(insertAt, working.length));
  working.splice(insertAt, 0, cell);

  const shrunk = shrinkToFit && cell.kind === "group" && cell.width === 2;
  const forced = forceFullWidth && cell.kind === "group";
  const widths = working.map((c) => {
    if (c === cell) {
      if (shrunk) return 1;
      if (forced) return 2;
      return c.width;
    }
    return c.kind === "group" ? c.width : 1;
  });
  const packed = packRowsPure(working, widths);
  return { rows: packed.map((row) => ({ cells: row })) };
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

// Validates and flattens every raw row's cells (dedup by widget id, drop
// anything malformed), then repacks the result — rows are however many the
// packer needs, not tied to the raw layout's row count or per-row widths.
function sanitizeLayout(raw) {
  if (!raw || !Array.isArray(raw.rows) || raw.rows.length === 0) {
    return defaultLayout();
  }

  const seenWidgetIds = new Set();
  const cells = [];

  for (const rawRow of raw.rows) {
    if (!rawRow || !Array.isArray(rawRow.cells)) continue;

    for (const rawCell of rawRow.cells) {
      if (!rawCell || typeof rawCell !== "object") continue;

      if (rawCell.kind === "video" || rawCell.kind === "topview") {
        if (seenWidgetIds.has(rawCell.kind)) continue;
        cells.push({
          id: typeof rawCell.id === "string" ? rawCell.id : crypto.randomUUID(),
          kind: rawCell.kind,
          width: 1,
        });
        seenWidgetIds.add(rawCell.kind);
      } else if (rawCell.kind === "group") {
        const rawWidgets = Array.isArray(rawCell.widgets) ? rawCell.widgets : [];
        const widgets = [
          ...new Set(rawWidgets.filter((w) => isTaggableWidget(w) && !seenWidgetIds.has(w))),
        ];
        if (widgets.length === 0) continue;

        const activeId = widgets.includes(rawCell.activeId) ? rawCell.activeId : widgets[0];
        cells.push({
          id: typeof rawCell.id === "string" ? rawCell.id : crypto.randomUUID(),
          kind: "group",
          widgets,
          activeId,
          width: rawCell.width === 2 ? 2 : 1,
        });
        widgets.forEach((w) => seenWidgetIds.add(w));
      }
    }
  }

  if (!seenWidgetIds.has("video")) {
    cells.unshift({ id: crypto.randomUUID(), kind: "video", width: 1 });
  }

  return { rows: repackFlat(cells) };
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

    function rowAt(rowIdx) {
      if (rowIdx === layout.value.rows.length) {
        layout.value.rows.push({ cells: [] });
      }
      // Read back through the reactive array rather than returning the
      // plain object literal just pushed above — the latter is the raw,
      // un-proxied object, so mutating its `.cells` later (in addSolo/
      // addGroupWidget) would silently bypass Vue's reactivity tracking.
      return layout.value.rows[rowIdx];
    }

    function addSolo(rowIdx, kind) {
      if (kind !== "topview") return;
      if (placedWidgetIds.value.has(kind)) return;
      const row = rowAt(rowIdx);
      if (!row) return;
      if (row.cells.length === 0) {
        row.cells.push({ id: crypto.randomUUID(), kind, width: 1 });
      } else if (row.cells.length === 1) {
        if (row.cells[0].width === 2) splitRow(rowIdx);
        row.cells.push({ id: crypto.randomUUID(), kind, width: 1 });
      }
    }

    function addGroupWidget(rowIdx, id) {
      if (!isTaggableWidget(id)) return;
      if (placedWidgetIds.value.has(id)) return;
      const row = rowAt(rowIdx);
      if (!row) return;

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

    // Removing a cell repacks the remaining ones (same as moveCell) instead
    // of just leaving a hole in its row — otherwise removing cells from
    // several different rows leaves one empty add-slot per row, rather than
    // everything compacting down to a single trailing one.
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
          layout.value.rows = repackFlat(layout.value.rows.flatMap((r) => r.cells));
        } else if (cell.activeId === widgetId) {
          cell.activeId = cell.widgets[0];
          groupActiveTick.value++;
        }
        return;
      }

      row.cells.splice(cellIdx, 1);
      layout.value.rows = repackFlat(layout.value.rows.flatMap((r) => r.cells));
    }

    function setGroupActive(cellId, id) {
      const found = findCell(cellId);
      if (!found || found.cell.kind !== "group") return;
      if (!found.cell.widgets.includes(id)) return;
      found.cell.activeId = id;
      groupActiveTick.value++;
    }

    // Widens a group cell to full width even when a sibling currently shares
    // its row — repacking the flat, row-major order (with this cell's width
    // already updated) naturally displaces whichever cell can no longer fit
    // into the following row, exactly where it already sat in that order.
    function expandToFull(cellId) {
      const found = findCell(cellId);
      if (!found) return;
      const { cell } = found;
      if (cell.kind !== "group" || cell.width !== 1) return;
      cell.width = 2;
      const flat = layout.value.rows.flatMap((r) => r.cells);
      layout.value.rows = repackFlat(flat);
      groupActiveTick.value++;
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
    // (see removeWidget). `shrinkToFit` narrows a full-width group cell back
    // to width 1 before repacking — set by callers when the drop explicitly
    // targets a spot beside an existing cell, so it actually lands there
    // instead of claiming a row of its own. `forceFullWidth` is the reverse:
    // widens a group cell to width 2 before repacking, for a drop that
    // explicitly targets the *center* of an existing cell — so it takes over
    // that whole row in one gesture instead of landing at half width and
    // needing a separate manual expand afterwards.
    function moveCell(cellId, targetIndex, { shrinkToFit = false, forceFullWidth = false } = {}) {
      const flat = layout.value.rows.flatMap((row) => row.cells);
      const fromIdx = flat.findIndex((c) => c.id === cellId);
      if (fromIdx === -1) return;

      const [cell] = flat.splice(fromIdx, 1);
      if (shrinkToFit && cell.kind === "group" && cell.width === 2) {
        cell.width = 1;
      } else if (forceFullWidth && cell.kind === "group") {
        cell.width = 2;
      }
      let insertAt = targetIndex;
      if (fromIdx < insertAt) insertAt -= 1;
      insertAt = Math.max(0, Math.min(insertAt, flat.length));
      flat.splice(insertAt, 0, cell);

      layout.value.rows = repackFlat(flat);
      groupActiveTick.value++;
    }

    // Extracts `widgetId` out of its current group cell and inserts it as a
    // brand-new one-widget cell at `targetIndex` in the flat, row-major cell
    // order (mirrors moveCell's insert/repack, but for a widget that doesn't
    // have its own cell yet).
    function moveWidgetToNewCell(sourceCellId, widgetId, targetIndex) {
      const flat = layout.value.rows.flatMap((row) => row.cells);
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
      removeWidget(sourceCellId, widgetId);
      layout.value.rows = repacked;
      groupActiveTick.value++;
    }

    // Reorders widgets within a single group cell's tab list — targetIndex
    // is interpreted against the list *before* removal, same convention as
    // moveCell.
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
