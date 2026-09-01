<template>
  <div class="review-list">
    <div class="review-list-head">
      <span class="review-list-title">{{ $t("annotation_tool.event.list_title") }}</span>
      <span class="review-list-count">{{ events.length }}</span>
      <v-spacer />
      <!-- One number for the whole session: how much of this timeline has been touched.
           The per-event marks below say which ones. -->
      <span v-if="changedCount" class="review-list-changed">
        {{ $t("annotation_tool.event.changed", { count: changedCount }) }}
      </span>
    </div>

    <div ref="rowsRef" class="review-list-rows">
      <div v-if="!events.length" class="review-list-empty">
        {{ $t("visualization.events.no_events") }}
      </div>

      <button
        v-for="event in events"
        :key="event.id"
        type="button"
        class="review-row"
        :class="{
          'review-row--selected': event.id === store.selectedEventId,
          'review-row--deleted': event.deleted,
          'review-row--past': event.timestamp < playerStore.currentTime,
        }"
        :data-event-id="event.id"
        @click="store.selectEvent(event.id, { seek: true })"
      >
        <span class="review-row-time">{{ getTimecode(event.timestamp, 0) }}</span>
        <v-icon size="15" :color="typeMeta(event).color">{{ typeMeta(event).icon }}</v-icon>
        <span class="review-row-type">{{ typeLabel(event) }}</span>
        <span class="review-row-player">{{ playerLabel(event) }}</span>
        <!-- State of this row's own correction, in one glyph: added, moved/retyped, or
             deleted-and-restorable. -->
        <v-icon v-if="event.added" size="13" color="secondary">mdi-plus-circle</v-icon>
        <v-icon v-else-if="event.deleted" size="13" color="error">mdi-delete</v-icon>
        <v-icon v-else-if="event.edited" size="13" color="secondary">mdi-pencil</v-icon>
        <span v-else class="review-row-spacer" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { EVENT_TYPE_META } from "@/stores/events";
import { getTimecode } from "@/plugins/time";

// The timeline under the video is the fast way to reach an event, but not a way to work
// through all of them: markers overlap wherever two events sit close together, and it has no
// order to follow. This list is the walkthrough -- every event once, chronologically, with
// what has already been corrected marked on it.
//
// Deliberately not EventsList.vue: that one is the analysis view's KPI table (xG/VAEP columns,
// sortable, measured column widths). None of that is part of a correction, and none of it fits
// a 330px panel.

const { t } = useI18n();
const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const store = useAnnotationToolStore();

const events = computed(() => store.reviewEvents);
const changedCount = computed(
  () => events.value.filter((event) => event.edited || event.added || event.deleted).length
);

const typeMeta = (event) =>
  EVENT_TYPE_META[event.event_type] ?? { icon: "mdi-flag-outline", color: "#9e9e9e" };

const typeLabel = (event) =>
  event.event_type
    ? t(`visualization.events.event_type.${event.event_type}`)
    : t("annotation_tool.event.no_type");

const playerLabel = (event) => {
  if (event.player_id == null) return t("annotation_tool.event.no_player");
  const number = topViewStore.metaDataTopView?.player_ids?.[event.player_id]?.number;
  return `#${number ?? event.player_id}`;
};

// Keeps the selected row in view when the selection comes from somewhere else -- a marker
// dragged on the timeline, or the transport's next/previous event.
const rowsRef = ref(null);
watch(
  () => store.selectedEventId,
  async (id) => {
    if (id == null) return;
    await nextTick();
    rowsRef.value
      ?.querySelector(`[data-event-id="${id}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }
);
</script>

<style scoped>
.review-list {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.review-list-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px 6px;
  flex-shrink: 0;
}

.review-list-title {
  font-size: 1rem;
  font-weight: 500;
}

.review-list-count {
  font-size: 0.75rem;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.1);
}

.review-list-changed {
  font-size: 0.68rem;
  color: rgb(var(--v-theme-secondary));
}

.review-list-rows {
  overflow-y: auto;
  min-height: 0;
  padding: 0 6px 6px;
}

.review-list-empty {
  padding: 16px 6px;
  font-size: 0.8rem;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.review-row {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 3px 6px;
  border-radius: 5px;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.review-row:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.review-row--selected {
  background: rgba(var(--v-theme-primary), 0.16);
  border-color: rgba(var(--v-theme-primary), 0.6);
}

/* Already behind the playhead -- same faded treatment EventsList.vue gives a past row. */
.review-row--past {
  opacity: 0.55;
}

.review-row--deleted .review-row-time,
.review-row--deleted .review-row-type,
.review-row--deleted .review-row-player {
  text-decoration: line-through;
  opacity: 0.6;
}

.review-row-time {
  font-family: monospace;
  font-size: 0.72rem;
  flex-shrink: 0;
}

.review-row-type {
  font-size: 0.78rem;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.review-row-player {
  font-size: 0.72rem;
  opacity: 0.75;
  flex-shrink: 0;
}

/* Keeps the state glyph's column width on rows that have no state to show, so the type/player
   columns stay aligned down the list. */
.review-row-spacer {
  width: 13px;
  flex-shrink: 0;
}
</style>
