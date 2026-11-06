<template>
  <v-card
    v-if="cell.kind !== 'group' || !isLoading"
    elevation="2"
    class="dashboard-cell fill-height d-flex flex-column"
    :class="{
      'dashboard-cell--editing': dashboardStore.editMode,
      'dashboard-cell--has-switcher': hasTabSwitcher,
    }"
    :data-tour="cellDataTour"
  >
    <template v-if="cell.kind === 'topview' && isLoading">
      <div class="loading-card fill-height">
        <div class="spinner">
          <i class="mdi mdi-loading mdi-spin" />
        </div>
        <div class="loading-text">{{ $t("loading_screen") }}</div>
      </div>
    </template>

    <template v-else-if="cell.kind === 'video'">
      <v-row class="flex-grow-1">
        <v-col class="dashboard-cell-content">
          <WidgetPlaceholder v-if="dashboardStore.editMode" widget-id="video" />
          <component :is="widgetComponent('video')" v-else />
        </v-col>
      </v-row>
    </template>

    <template v-else-if="cell.kind === 'topview'">
      <div v-if="dashboardStore.editMode" class="dashboard-cell-controls">
        <v-btn
          icon
          size="small"
          variant="text"
          :title="$t('analysis_view.dashboard.remove')"
          @click="dashboardStore.removeWidget(cell.id)"
        >
          <v-icon size="20">mdi-close</v-icon>
        </v-btn>
      </div>
      <v-row class="flex-grow-1">
        <v-col class="dashboard-cell-content">
          <WidgetPlaceholder v-if="dashboardStore.editMode" widget-id="topview" />
          <component :is="widgetComponent('topview')" v-else />
        </v-col>
      </v-row>
    </template>

    <template v-else-if="cell.kind === 'group'">
      <div v-if="dashboardStore.editMode" class="dashboard-cell-tab-overlay">
        <div
          class="dashboard-cell-tab-pills"
          :class="{ 'dashboard-cell-tab-pills--has-tabs': cell.widgets.length > 1 }"
          @dragover="onTabRowDragOver"
          @drop="onTabRowDrop"
        >
          <div
            v-for="widgetId in cell.widgets.length > 1 ? cell.widgets : []"
            :key="widgetId"
            class="dashboard-cell-tab-pill"
            :class="{
              'dashboard-cell-tab-pill--active': widgetId === cell.activeId,
              'dashboard-cell-tab-pill--dragging':
                dashboardStore.draggedTab?.cellId === cell.id &&
                dashboardStore.draggedTab?.widgetId === widgetId,
            }"
            draggable="true"
            @click="dashboardStore.setGroupActive(cell.id, widgetId)"
            @dragstart.stop="onTabDragStart($event, widgetId)"
            @dragend="onTabDragEnd"
          >
            {{ $t(widgetLabel(widgetId)) }}
            <v-icon
              size="16"
              class="ml-1"
              @click.stop="dashboardStore.removeWidget(cell.id, widgetId)"
            >
              mdi-close
            </v-icon>
          </div>
        </div>

        <div v-if="cell.widgets.length > 1" class="dashboard-cell-tab-divider" />

        <div class="dashboard-cell-tab-actions">
          <v-menu v-if="addableTabs.length">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                icon
                size="small"
                variant="text"
                :title="$t('analysis_view.dashboard.add_view')"
              >
                <v-icon size="20">mdi-plus</v-icon>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item
                v-for="widgetId in addableTabs"
                :key="widgetId"
                @click="dashboardStore.addTabToGroup(cell.id, widgetId)"
              >
                <v-list-item-title>{{ $t(widgetLabel(widgetId)) }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-btn
            icon
            size="small"
            variant="text"
            :title="$t('analysis_view.dashboard.toggle_width')"
            @click="toggleWidth"
          >
            <v-icon size="20">
              {{
                cell.width === 2 ? "mdi-arrow-collapse-horizontal" : "mdi-arrow-expand-horizontal"
              }}
            </v-icon>
          </v-btn>

          <v-btn
            icon
            size="small"
            variant="text"
            :title="$t('analysis_view.dashboard.remove')"
            @click="dashboardStore.removeWidget(cell.id)"
          >
            <v-icon size="20">mdi-close</v-icon>
          </v-btn>
        </div>
      </div>

      <div
        v-else-if="cell.widgets.length > 1"
        class="dashboard-cell-tab-switcher"
        :class="{ 'dashboard-cell-tab-switcher--expanded': switcherExpanded }"
        @mouseenter="switcherExpanded = true"
        @mouseleave="switcherExpanded = false"
        @click="switcherExpanded = true"
      >
        <div class="dashboard-cell-tab-switcher-shape">
          <div class="dashboard-cell-tab-switcher-names">
            <button
              v-for="widgetId in cell.widgets"
              :key="widgetId"
              type="button"
              class="dashboard-cell-tab-switcher-name"
              :class="{ 'dashboard-cell-tab-switcher-name--active': widgetId === cell.activeId }"
              @click="
                dashboardStore.setGroupActive(cell.id, widgetId);
                switcherExpanded = false;
              "
            >
              {{ $t(widgetLabel(widgetId)) }}
            </button>
          </div>
        </div>
      </div>

      <v-row
        class="flex-grow-1"
        :class="{ 'dashboard-cell-tabs-content-row--scroll': constrained }"
      >
        <v-col
          class="dashboard-cell-content"
          :class="{ 'dashboard-cell-content--scroll': constrained }"
        >
          <WidgetPlaceholder v-if="dashboardStore.editMode" :widget-id="cell.activeId" />
          <component :is="widgetComponent(cell.activeId)" :dense="constrained" v-else />
        </v-col>
      </v-row>
    </template>

    <div v-if="dashboardStore.editMode" class="dashboard-cell-veil" />
  </v-card>
</template>

<script setup>
import { computed, ref } from "vue";
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";
import { dashboardWidgets, isTaggableWidget } from "@/config/dashboardWidgets";
import WidgetPlaceholder from "@/components/analysis-view/dashboard/WidgetPlaceholder.vue";

const props = defineProps({
  cell: { type: Object, required: true },
  rowIdx: { type: Number, required: true },
  isLoading: { type: Boolean, default: false },
  // True when this (group) cell shares its row with video/topview and has
  // been height-capped to their natural size by DashboardGrid — the widget
  // inside must scroll its own content instead of growing the row further.
  constrained: { type: Boolean, default: false },
});

const dashboardStore = useDashboardLayoutStore();

const cellDataTour = computed(() => {
  if (props.cell.kind === "video") return "analysis-video-player";
  if (props.cell.kind === "topview") return "analysis-top-view";
  return "analysis-visualization-tabs";
});

function widgetComponent(id) {
  return dashboardWidgets[id]?.component ?? null;
}

function widgetLabel(id) {
  return dashboardWidgets[id]?.labelKey ?? id;
}

// Whether the tab switcher's collapsed shape is expanded into its "name
// picker" banner — hover-driven (see the switcher div's mouseenter/leave),
// with a click fallback so it's still reachable without hover (touch).
const switcherExpanded = ref(false);

// Vuetify's v-card sets `overflow: hidden` by default (for its rounded-
// corner/elevation clipping) — that also clips the tab switcher's overlay,
// most of which deliberately sits *above* the card's own top edge. Only
// lift that clipping for cells that actually render the switcher, so
// video/topview/single-widget cards keep Vuetify's default behavior.
const hasTabSwitcher = computed(
  () => props.cell.kind === "group" && !dashboardStore.editMode && props.cell.widgets.length > 1
);

const addableTabs = computed(() =>
  dashboardStore.availableWidgetIds.filter((id) => isTaggableWidget(id))
);

function toggleWidth() {
  if (props.cell.width === 2) {
    dashboardStore.splitRow(props.rowIdx);
  } else {
    dashboardStore.expandToFull(props.cell.id);
  }
}

const dragOverTabIndex = ref(null);

function onTabDragStart(event, widgetId) {
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", widgetId);
  dashboardStore.startTabDrag(props.cell.id, widgetId);
}

function onTabDragEnd() {
  dragOverTabIndex.value = null;
  dashboardStore.endTabDrag();
}

function onTabRowDragOver(event) {
  if (!dashboardStore.draggedTab) return;
  event.preventDefault();
  // Don't let the card-wrapper's whole-cell dragover also react.
  event.stopPropagation();
  if (dashboardStore.draggedTab.cellId !== props.cell.id) {
    dragOverTabIndex.value = null;
    return;
  }
  const pills = Array.from(event.currentTarget.querySelectorAll(".dashboard-cell-tab-pill"));
  let idx = pills.length;
  for (let i = 0; i < pills.length; i++) {
    const rect = pills[i].getBoundingClientRect();
    if (event.clientX < rect.left + rect.width / 2) {
      idx = i;
      break;
    }
  }
  dragOverTabIndex.value = idx;
}

function onTabRowDrop(event) {
  if (!dashboardStore.draggedTab) return;
  event.preventDefault();
  event.stopPropagation();
  const { cellId: sourceCellId, widgetId } = dashboardStore.draggedTab;
  if (sourceCellId === props.cell.id) {
    dashboardStore.moveWidgetWithinGroup(
      props.cell.id,
      widgetId,
      dragOverTabIndex.value ?? props.cell.widgets.length
    );
  } else {
    dashboardStore.removeWidget(sourceCellId, widgetId);
    dashboardStore.addTabToGroup(props.cell.id, widgetId);
  }
  dragOverTabIndex.value = null;
  dashboardStore.endTabDrag();
}
</script>

<style scoped>
.dashboard-cell {
  position: relative;
}

/* See hasTabSwitcher — undoes Vuetify's default overflow: hidden on v-card
   just for cells whose tab-switcher overlay pokes out above the card. */
.dashboard-cell--has-switcher {
  overflow: visible;
}

.dashboard-cell--editing {
  outline: 3px dashed rgba(var(--v-theme-primary), 0.85);
  outline-offset: -3px;
  cursor: grab;
  /* Keeps content off the outline so it stays fully visible/unbroken all
     the way around, instead of widgets (e.g. video) running flush to it. */
  padding: 8px;
}

.dashboard-cell-content {
  position: relative;
}

/* Row/column pairing that lets a height-capped widget cell (see
   DashboardGrid's anchor-row coupling) actually scroll internally instead
   of overflowing past the card — min-height: 0 is what lets a flex child
   shrink below its content's natural size so overflow-y: auto kicks in. */
.dashboard-cell-tabs-content-row--scroll {
  min-height: 0;
}

.dashboard-cell-content--scroll {
  min-height: 0;
  height: 100%;
  overflow-y: auto;
}

.dashboard-cell-veil {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: rgba(0, 0, 0, 0.45);
}

.dashboard-cell-tab-switcher {
  position: absolute;
  top: -1px;
  left: 10%;
  right: 10%;
  z-index: 5;
}

.dashboard-cell-tab-switcher-shape {
  width: 100%;
  height: 10px;
  background: rgb(var(--v-theme-primary));
  clip-path: polygon(0% 5%, 100% 5%, 70% 35%, 50% 100%, 30% 35%);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  transition: height 0.18s ease, clip-path 0.18s ease, box-shadow 0.15s ease;
}

.dashboard-cell-tab-switcher--expanded .dashboard-cell-tab-switcher-shape {
  height: 50px;
  clip-path: polygon(0% 5%, 100% 5%, 75% 100%, 25% 100%);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4);
}

.dashboard-cell-tab-switcher-names {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 10px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}

.dashboard-cell-tab-switcher--expanded .dashboard-cell-tab-switcher-names {
  opacity: 1;
  pointer-events: auto;
}

.dashboard-cell-tab-switcher-name {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 2px 0;
  color: rgb(var(--v-theme-on-primary));
  font-size: 1rem;
  line-height: 1.4;
  cursor: pointer;
}

.dashboard-cell-tab-switcher-name--active {
  border-bottom-color: rgb(var(--v-theme-on-primary));
}

.dashboard-cell-tab-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  max-width: calc(100% - 16px);
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 4px 8px;
  border-radius: 14px;
  background: #d9d9d93b;
}

.dashboard-cell-tab-pills {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow-x: auto;
}

.dashboard-cell-tab-pills--has-tabs {
  padding: 2px 10px 2px 8px;
}

.dashboard-cell-tab-pill {
  display: flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  background: #d9d9d93b;
  font-size: 0.9rem;
  cursor: grab;
  user-select: none;
}

.dashboard-cell-tab-pill--active {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.dashboard-cell-tab-pill--dragging {
  opacity: 0.35;
}

.dashboard-cell-tab-divider {
  width: 1px;
  align-self: stretch;
  min-height: 20px;
  background: rgba(var(--v-theme-on-surface), 0.3);
  flex-shrink: 0;
  margin-right: 10px;
}

.dashboard-cell-tab-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.dashboard-cell-controls {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  border-radius: 14px;
  background: #d9d9d93b;
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.spinner {
  font-size: 48px;
  color: rgb(var(--v-theme-primary));
}

.loading-text {
  margin-top: 10px;
  font-size: 18px;
  color: rgb(var(--v-theme-primary));
}
</style>
