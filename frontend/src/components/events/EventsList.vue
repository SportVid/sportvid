<template>
  <div class="events-list-wrapper">
    <div class="events-list-header">
      <span class="events-list-time">{{ $t("visualization.events.table.time") }}</span>
      <span class="events-list-icon" />
      <span class="events-list-type">{{ $t("visualization.events.table.type") }}</span>
      <span class="events-list-player">{{ $t("visualization.events.table.player") }}</span>
      <span class="events-list-team">{{ $t("visualization.events.table.team") }}</span>
      <span class="events-list-confidence">{{ $t("visualization.events.table.confidence") }}</span>
    </div>

    <div class="events-list" :class="{ 'events-list--dense': dense }">
      <div v-if="!eventsStore.filteredEvents.length" class="events-list-empty">
        {{ $t("visualization.events.no_events") }}
      </div>

      <div
        v-for="(event, idx) in eventsStore.filteredEvents"
        :key="event.id"
        :ref="(el) => setRowRef(el, idx)"
        class="events-list-row"
        :class="{
          'events-list-row--past': pastIndex(idx),
          'events-list-row--next': idx === eventsStore.nextEventIndex,
        }"
        @click="eventsStore.jumpToEvent(event)"
      >
        <span class="events-list-time">{{ getTimecode(event.timestamp, 0) }}</span>
        <v-icon size="16" :color="typeMeta(event).color" class="events-list-icon">
          {{ typeMeta(event).icon }}
        </v-icon>
        <span class="events-list-type">
          {{ $t(`visualization.events.event_type.${event.event_type}`) }}
        </span>
        <span class="events-list-player">{{ getPlayerNumber(event.player_id) }}</span>
        <span
          class="events-list-team"
          :style="{ color: visualizationStore.getTeamColor(event.team_id) }"
        >
          {{ getTeamName(event.team_id) }}
        </span>
        <span class="events-list-confidence">{{ Math.round(event.confidence * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";
import { useEventsStore, EVENT_TYPE_META } from "@/stores/events";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";
import { getTimecode } from "@/plugins/time";
import { debounce } from "lodash";

defineProps({
  // Squeezed next to video/topview -- shrinks the row height/scroll area instead of the
  // wrapping behavior other cards' `dense` handles (there's nothing here to wrap).
  dense: { type: Boolean, default: false },
});

const eventsStore = useEventsStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

const typeMeta = (event) => EVENT_TYPE_META[event.event_type] ?? { icon: "mdi-circle", color: "#888888" };

const pastIndex = (idx) =>
  eventsStore.nextEventIndex !== -1 ? idx < eventsStore.nextEventIndex : true;

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? `#${num}` : `#${playerId}`;
};
const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return teamId;
};

// Keeps the "next up" event pinned near the top of the scroll area as playback advances --
// this is the "table that basically keeps running along" from the design notes, rather than
// a plain static list the user has to scroll through manually.
const rowRefs = ref({});
const setRowRef = (el, idx) => {
  if (el) rowRefs.value[idx] = el;
  else delete rowRefs.value[idx];
};

const scrollToNext = debounce(() => {
  const idx = eventsStore.nextEventIndex;
  const el = idx >= 0 ? rowRefs.value[idx] : null;
  if (el) el.scrollIntoView({ block: "start", behavior: "smooth" });
}, 250);

watch(
  () => eventsStore.nextEventIndex,
  () => nextTick(() => scrollToNext())
);
watch(
  () => eventsStore.filteredEvents,
  () => nextTick(() => scrollToNext()),
  { immediate: true }
);
</script>

<style scoped>
/* display: flex column so the header can stay flex-shrink: 0 while
   .events-list (see below) is the one element allowed to actually grow --
   needed for .events-list--dense to fill the space TabWindowEvents'
   .events-list-grow hands this component's root down below. */
.events-list-wrapper {
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.events-list-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background-color: #f0f0f0;
  border-bottom: 1px solid #e0e0e0;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #777;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.events-list {
  max-height: 260px;
  overflow-y: auto;
}
/* dense (squeezed next to video/topview): dropped the fixed cap in favor of
   actually filling the height TabWindowEvents' .events-list-grow hands the
   wrapper -- previously this stayed at a small fixed max-height even when
   there was plenty of room below it (see TabWindowEvents.vue). */
.events-list--dense {
  max-height: none;
  flex: 1 1 auto;
  min-height: 0;
}

.events-list-empty {
  padding: 24px 12px;
  text-align: center;
  color: #888;
  font-size: 0.85rem;
}

.events-list-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid #eeeeee;
  cursor: pointer;
  transition: opacity 0.2s, background-color 0.2s;
}
.events-list-row:last-child {
  border-bottom: none;
}
.events-list-row:hover {
  background-color: #f5f5f5;
}
.events-list-row--past {
  opacity: 0.45;
}
.events-list-row--next {
  background-color: rgba(174, 19, 19, 0.08);
  border-left: 3px solid #ae1313;
  font-weight: bold;
}

.events-list-time {
  font-family: "Courier New", monospace;
  font-size: 0.8rem;
  width: 64px;
  flex-shrink: 0;
}
.events-list-icon {
  flex-shrink: 0;
}
.events-list-type {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.events-list-player {
  flex-shrink: 0;
  font-size: 0.85rem;
  width: 40px;
}
.events-list-team {
  flex-shrink: 0;
  font-size: 0.8rem;
  width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.events-list-confidence {
  flex-shrink: 0;
  font-size: 0.75rem;
  color: #888;
  width: 40px;
  text-align: right;
}
</style>
