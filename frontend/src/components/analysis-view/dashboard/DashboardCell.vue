<template>
  <v-card
    v-if="cell.kind !== 'group' || !isLoading"
    elevation="2"
    class="dashboard-cell fill-height d-flex flex-column"
    :class="{ 'dashboard-cell--editing': dashboardStore.editMode }"
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
      <v-row v-if="!dashboardStore.editMode" justify="center">
        <v-card-title class="mt-5 mb-n1">
          {{ playerStore.videoName }}
        </v-card-title>
      </v-row>
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
      <v-row v-if="!dashboardStore.editMode && matchupTeams.length" justify="center">
        <v-card-title class="mt-5 mb-n1">
          <div class="matchup-title">
            <template v-for="(team, index) in matchupTeams" :key="team.id">
              <span class="matchup-title-team">
                <span class="matchup-title-name">{{ team.name }}</span>
                <span class="matchup-title-line" :style="{ backgroundColor: team.color }" />
              </span>
              <span v-if="index < matchupTeams.length - 1" class="matchup-title-sep">:</span>
            </template>
          </div>
        </v-card-title>
      </v-row>
      <v-row class="flex-grow-1">
        <v-col class="dashboard-cell-content">
          <WidgetPlaceholder v-if="dashboardStore.editMode" widget-id="topview" />
          <component :is="widgetComponent('topview')" v-else />
        </v-col>
      </v-row>
    </template>

    <template v-else-if="cell.kind === 'group'">
      <!-- Edit mode: one absolutely-positioned corner overlay (pills, then a
           divider, then the fixed action icons) instead of a row that takes
           real layout space — so it never pushes the placeholder around,
           the same way the video/topview controls already don't. -->
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

      <v-row
        v-else-if="cell.widgets.length > 1"
        align="center"
        no-gutters
        class="pt-1 flex-grow-0 dashboard-cell-tabs-row"
      >
        <v-tabs
          density="compact"
          slider-color="primary"
          class="flex-grow-1"
          :model-value="cell.activeId"
          @update:model-value="dashboardStore.setGroupActive(cell.id, $event)"
        >
          <v-tab v-for="widgetId in cell.widgets" :key="widgetId" :value="widgetId">
            {{ $t(widgetLabel(widgetId)) }}
          </v-tab>
        </v-tabs>
      </v-row>

      <v-row class="flex-grow-1 my-0">
        <v-col class="dashboard-cell-content">
          <WidgetPlaceholder v-if="dashboardStore.editMode" :widget-id="cell.activeId" />
          <component :is="widgetComponent(cell.activeId)" v-else />
        </v-col>
      </v-row>
    </template>

    <!-- Covers the whole card so it reads as inert while arranging — the
         tab overlay/controls are kept above it (see .dashboard-cell-tab-
         overlay and .dashboard-cell-controls) since they must stay
         clickable to switch/manage tabs. -->
    <div v-if="dashboardStore.editMode" class="dashboard-cell-veil" />
  </v-card>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";
import { dashboardWidgets, isTaggableWidget } from "@/config/dashboardWidgets";
import WidgetPlaceholder from "@/components/analysis-view/dashboard/WidgetPlaceholder.vue";

const props = defineProps({
  cell: { type: Object, required: true },
  rowIdx: { type: Number, required: true },
  isLoading: { type: Boolean, default: false },
});

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
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

const matchupTeams = computed(() => {
  const meta = topViewStore.metaDataTopView;
  if (!meta?.team_ids) return [];
  // New scheme: team_id ≥ 3 = active player teams (1=ball, 2=refs, 0=inactive — all hidden from matchup).
  return Object.entries(meta.team_ids)
    .filter(([teamId]) => Number(teamId) >= 3)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([teamId, info]) => ({
      id: Number(teamId),
      name: info.name,
      color: visualizationStore.getTeamColor(Number(teamId)),
    }));
});

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

.dashboard-cell-veil {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: rgba(0, 0, 0, 0.45);
}

.dashboard-cell-tabs-row {
  position: relative;
  z-index: 4;
}

/* Right-aligned corner overlay: pills grow leftward from the divider, the
   fixed icons (add, toggle, remove) sit to its right — same non-layout-
   affecting positioning as .dashboard-cell-controls below. Sized to its
   content (like that one), not stretched full-width, but capped so a lot
   of pills scroll horizontally (see .dashboard-cell-tab-pills) instead of
   overflowing past the card's edge or wrapping to a second (ugly) line.
   One shared background for the whole cluster (pills, divider, and icons
   together) rather than the icons alone being their own box. */
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

/* Scrolls horizontally instead of wrapping to a second line — `min-width: 0`
   lets this flex child shrink below its content's natural width so overflow
   actually kicks in, while the divider/action icons (flex-shrink: 0, not
   part of this scroll area) always stay fully visible. No padding/gap here
   by default — this container stays in the DOM even with zero pills (as a
   drop target for dragging a tab in), and reserving space it isn't using
   would leave the icons lopsided to the right with nothing to balance it
   on the left. --has-tabs adds that spacing back only once there's
   something to actually space out. */
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

.matchup-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.matchup-title-team {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.matchup-title-name {
  font-size: 1rem;
}

.matchup-title-line {
  display: block;
  width: 100%;
  height: 3px;
  border-radius: 1px;
  margin-top: -4px;
}

.matchup-title-sep {
  font-size: 1.1rem;
}
</style>
