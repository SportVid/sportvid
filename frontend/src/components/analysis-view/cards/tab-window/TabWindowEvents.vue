<template>
  <EventDataMenu
    v-if="!eventsStore.hasEventData"
    :title="$t('analysis_view.visualization_tabs.events')"
    icon="mdi-flag-variant-outline"
  />

  <div v-else class="d-flex flex-column flex-nowrap pa-4" :class="{ 'events-fill-height': dense }">
    <div class="card-header-zone">
      <v-row
        align="center"
        class="flex-nowrap mx-n4"
        style="width: 100%"
        data-tour="events-controls-row"
      >
        <v-col
          cols="auto"
          class="d-flex align-center flex-shrink-0"
          style="gap: 12px"
          data-tour="events-settings"
        >
          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                size="small"
                data-tour="events-display-settings-btn"
                class="mt-n2"
              >
                <v-icon>mdi-menu</v-icon>
              </v-btn>
            </template>
            <v-list class="py-0" density="compact" width="220px">
              <v-list-item class="menu-item" @click="showModalPositionDataEntityColors = true">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.entity_colors") }}
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-menu location="end" open-on-hover :close-on-content-click="false">
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.events.filter.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="200px">
                  <v-list-item
                    v-for="typeId in eventTypeIds"
                    :key="typeId"
                    class="menu-item"
                    @click="eventsStore.toggleEventType(typeId)"
                  >
                    <v-list-item-title class="d-flex align-center justify-space-between">
                      <span class="d-flex align-center" style="gap: 6px">
                        <v-icon size="14" :color="EVENT_TYPE_META[typeId].color">
                          {{ EVENT_TYPE_META[typeId].icon }}
                        </v-icon>
                        {{ $t(`visualization.events.event_type.${typeId}`) }}
                      </span>
                      <tab-window-icon
                        :class="{
                          'text-disabled': !eventsStore.selectedEventTypes.includes(typeId),
                          'text-red': eventsStore.selectedEventTypes.includes(typeId),
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <v-menu location="end" open-on-hover :close-on-content-click="false">
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.events.kpi_columns.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="150px">
                  <v-list-item
                    v-for="colId in kpiColumnIds"
                    :key="colId"
                    class="menu-item"
                    @click="eventsStore.toggleKpiColumn(colId)"
                  >
                    <v-list-item-title class="d-flex align-center justify-space-between">
                      {{ $t(KPI_COLUMN_META[colId].labelKey) }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': !eventsStore.visibleKpiColumns.includes(colId),
                          'text-red': eventsStore.visibleKpiColumns.includes(colId),
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <v-divider />

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("event_data.display_settings.event_data.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact">
                  <v-list-item
                    v-if="canWrite"
                    class="menu-item"
                    @click="showModalEventDataUpload = true"
                  >
                    <v-list-item-title>
                      {{ $t("event_data.display_settings.event_data.upload") }}
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item class="menu-item" @click="showModalEventDataSelect = true">
                    <v-list-item-title>
                      {{ $t("event_data.display_settings.event_data.select") }}
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </v-list>
          </v-menu>
          <ModalEventDataUpload
            v-if="showModalEventDataUpload"
            v-model="showModalEventDataUpload"
          />
          <ModalEventDataSelect
            v-if="showModalEventDataSelect"
            v-model="showModalEventDataSelect"
          />
          <ModalPositionDataEntityColors
            v-if="showModalPositionDataEntityColors"
            v-model="showModalPositionDataEntityColors"
          />

          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn v-bind="props" size="small" class="mr-2 mt-n2">
                <v-icon>mdi-timer-sync-outline</v-icon>
              </v-btn>
            </template>
            <v-list class="py-0" density="compact" width="250px">
              <v-list-item
                class="menu-item"
                @click="positionDataStore.setSelectedTimeRangeStart(playerStore.currentTime)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.sync_start") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                @click="positionDataStore.setSelectedTimeRangeEnd(playerStore.currentTime)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.sync_end") }}
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-list-item
                class="menu-item"
                @click="
                  positionDataStore.setSelectedTimeRangeStart(allFrameKeys[0]);
                  positionDataStore.setSelectedTimeRangeEnd(allFrameKeys[allFrameKeys.length - 1]);
                "
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.full_match") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                :disabled="!visualizationStore.halftimesExist"
                @click="selectHalftime(1)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.first_half") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                :disabled="!visualizationStore.halftimesExist"
                @click="selectHalftime(2)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.second_half") }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
        <v-col class="pa-0" data-tour="events-time-selector">
          <VisualizationTimeSelector class="ml-n2" />
        </v-col>
      </v-row>
    </div>

    <EventsTimeline class="mt-2" data-tour="events-timeline" />

    <EventsList
      class="mt-3"
      :class="{ 'events-list-grow': dense }"
      :dense="dense"
      data-tour="events-list"
    />

    <div
      class="chart-legend mt-4"
      :class="{ 'chart-legend--dense': dense }"
      data-tour="events-player-legend"
    >
      <div v-for="(players, teamId) in teamGroups" :key="teamId" class="chart-legend-team">
        <div
          class="team-dot"
          :style="{
            backgroundColor: isTeamFullySelected(teamId)
              ? toRgb(visualizationStore.getTeamColor(teamId), 0)
              : 'transparent',
            color: isTeamFullySelected(teamId)
              ? '#fff'
              : toRgb(visualizationStore.getTeamColor(teamId), 0),
            borderColor: toRgb(visualizationStore.getTeamColor(teamId), 0),
          }"
          @click="toggleTeam(teamId)"
        >
          {{ getTeamName(teamId) }}
        </div>
        <span class="chart-legend-sep">|</span>
        <div
          v-for="p in players"
          :key="p.playerId"
          class="player-dot"
          :style="{
            backgroundColor: selectedPlayerIds.includes(p.playerId)
              ? toRgb(playerColors[p.playerId], 0)
              : toRgb(playerColors[p.playerId], 0.6),
            color: selectedPlayerIds.includes(p.playerId) ? '#fff' : '#222',
            borderColor: selectedPlayerIds.includes(p.playerId)
              ? toRgb(playerColors[p.playerId], 0)
              : toRgb(playerColors[p.playerId], 0.6),
          }"
          @click="togglePlayerId(p.playerId)"
        >
          {{ getPlayerNumber(p.playerId) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { useUserStore } from "@/stores/user";
import {
  useEventsStore,
  EVENT_TYPE_META,
  EVENT_TYPE_IDS,
  KPI_COLUMN_META,
  KPI_COLUMN_IDS,
} from "@/stores/events";
import VisualizationTimeSelector from "@/components/visualization/VisualizationTimeSelector.vue";
import EventsTimeline from "@/components/events/EventsTimeline.vue";
import EventsList from "@/components/events/EventsList.vue";
import ModalEventDataSelect from "@/components/events/ModalEventDataSelect.vue";
import ModalEventDataUpload from "@/components/events/ModalEventDataUpload.vue";
import ModalPositionDataEntityColors from "@/components/position-data/ModalPositionDataEntityColors.vue";
import EventDataMenu from "@/components/events/EventDataMenu.vue";
import { toRgb } from "@/plugins/helpers";

defineProps({
  // True when this widget shares its row with video/topview and has been height-capped to
  // their size (see DashboardGrid) -- squeeze the list/legend instead of letting them grow.
  dense: { type: Boolean, default: false },
});

const topViewStore = useTopViewStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const visualizationStore = useVisualizationStore();
const userStore = useUserStore();
const eventsStore = useEventsStore();

const eventTypeIds = EVENT_TYPE_IDS;
const kpiColumnIds = KPI_COLUMN_IDS;

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showModalEventDataSelect = ref(false);
const showModalEventDataUpload = ref(false);
const showModalPositionDataEntityColors = ref(false);

const allFrameKeys = computed(() => topViewStore.sortedFrameKeys);
const selectHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  if (b) {
    positionDataStore.setSelectedTimeRangeStart(b.first);
    positionDataStore.setSelectedTimeRangeEnd(b.last);
  }
};

const playerOptions = computed(() => topViewStore.precomputedPlayerList);

const playerColors = computed(() => {
  const map = {};
  for (const p of playerOptions.value) {
    map[p.playerId] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});

const teamGroups = computed(() => {
  const groups = {};
  for (const p of playerOptions.value) {
    if (!groups[p.teamId]) groups[p.teamId] = [];
    groups[p.teamId].push(p);
  }
  return groups;
});

// Filters which players' events show, in both the timeline and the list -- reuses
// eventsStore.selectedPlayerIds (null until first seeded, same convention as
// visualizationStore.kpiSelectedPlayerIds).
const selectedPlayerIds = computed({
  get: () => eventsStore.selectedPlayerIds ?? [],
  set: (val) => {
    eventsStore.selectedPlayerIds = val;
  },
});
watch(
  playerOptions,
  (list) => {
    if (!list.length) return;
    if (eventsStore.selectedPlayerIds === null) {
      selectedPlayerIds.value = list.map((p) => p.playerId);
    } else {
      const available = new Set(list.map((p) => p.playerId));
      const filtered = eventsStore.selectedPlayerIds.filter((id) => available.has(id));
      selectedPlayerIds.value = filtered.length > 0 ? filtered : list.map((p) => p.playerId);
    }
  },
  { immediate: true }
);

function togglePlayerId(playerId) {
  if (selectedPlayerIds.value.includes(playerId)) {
    selectedPlayerIds.value = selectedPlayerIds.value.filter((id) => id !== playerId);
  } else {
    selectedPlayerIds.value = [...selectedPlayerIds.value, playerId];
  }
}

const toggleTeam = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  const allSelected = teamPlayerIds.every((pid) => selectedPlayerIds.value.includes(pid));
  if (allSelected) {
    selectedPlayerIds.value = selectedPlayerIds.value.filter((id) => !teamPlayerIds.includes(id));
  } else {
    const newIds = [...selectedPlayerIds.value];
    teamPlayerIds.forEach((pid) => {
      if (!newIds.includes(pid)) newIds.push(pid);
    });
    selectedPlayerIds.value = newIds;
  }
};

const isTeamFullySelected = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  return (
    teamPlayerIds.length > 0 && teamPlayerIds.every((pid) => selectedPlayerIds.value.includes(pid))
  );
};

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};

const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return teamId;
};
</script>

<style scoped>
.card-header-zone {
  height: 56px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* dense (see `dense` prop): the widget's own height is capped to fit next to
   video/topview (DashboardCell's ".dashboard-cell-content--scroll" sets
   height: 100% on our ancestor) — propagate that fixed height down through
   the flex chain so EventsList below gets a real, bounded height to grow
   into instead of sizing to a fixed cap and leaving blank space (see
   .events-list-grow). Only applied when dense: in the normal (non-capped)
   layout the widget still just grows with its content, same as before. */
.events-fill-height {
  height: 100%;
  min-height: 0;
}

/* Passed onto EventsList's root (see the class-passthrough-to-child-root
   pattern Vue's scoped CSS supports) only when dense — makes the list claim
   the rest of the column's height instead of stopping at its own small
   content-based/capped size (see EventsList.vue's own `.events-list-wrapper--dense`
   for the matching change on its scroll area). */
.events-list-grow {
  flex: 1 1 auto;
  min-height: 0;
}

.menu-item {
  cursor: pointer;
}
.menu-item:hover {
  background-color: #f0f0f0;
}
.menu-item .v-list-item-title {
  font-size: 12px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  column-gap: 20px;
  row-gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.chart-legend--dense {
  flex-wrap: nowrap;
  justify-content: flex-start;
  overflow-x: auto;
  padding-bottom: 4px;
}

.chart-legend-team {
  display: flex;
  align-items: center;
  gap: 5px;
}

.team-dot {
  height: 24px;
  border-radius: 50%;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.7rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s, color 0.2s;
  user-select: none;
  white-space: nowrap;
}
.team-dot:hover {
  opacity: 0.8;
}

.chart-legend-sep {
  color: #ccc;
  font-size: 18px;
  margin: 0 2px;
  user-select: none;
}

.player-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s;
  user-select: none;
}
</style>
