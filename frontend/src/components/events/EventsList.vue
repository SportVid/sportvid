<template>
  <div
    ref="wrapperRef"
    class="events-list-wrapper"
    :class="{ 'events-list-wrapper--dense': dense }"
  >
    <div ref="headerRef" class="events-list-header">
      <!-- Reserves the same space as .events-list-row's marker below so Time still lines
      up between header and rows -- never colored, the header itself is never "next". -->
      <span class="events-list-current-marker events-list-pin" />
      <span
        class="events-list-time events-list-pin events-list-pin--time events-list-sortable"
        @click="eventsStore.setSort('timestamp')"
      >
        {{ $t("visualization.events.table.time") }}
        <v-icon v-if="sortIcon('timestamp')" size="12">{{ sortIcon("timestamp") }}</v-icon>
      </span>
      <!-- Icon + Event share one header label (spanning both columns' width, starting at
      the icon's position) instead of a blank cell over the icon and "Event" only over the
      text next to it -- the split reads as if the icon were its own separate column. -->
      <span class="events-list-event-header events-list-pin events-list-pin--icon">
        {{ $t("visualization.events.table.type") }}
      </span>
      <span class="events-list-player events-list-pin events-list-pin--player">
        {{ $t("visualization.events.table.player") }}
      </span>
      <span class="events-list-team">{{ $t("visualization.events.table.team") }}</span>
      <span
        v-if="eventsStore.visibleKpiColumns.includes('xg')"
        class="events-list-xg events-list-sortable"
        @click="eventsStore.setSort('xg')"
      >
        {{ $t("visualization.events.table.xg") }}
        <v-icon v-if="sortIcon('xg')" size="12">{{ sortIcon("xg") }}</v-icon>
      </span>
      <span
        v-if="eventsStore.visibleKpiColumns.includes('xsuccess')"
        class="events-list-xsuccess events-list-sortable"
        @click="eventsStore.setSort('xsuccess')"
      >
        {{ $t("visualization.events.table.xsuccess") }}
        <v-icon v-if="sortIcon('xsuccess')" size="12">{{ sortIcon("xsuccess") }}</v-icon>
      </span>
      <span
        v-if="eventsStore.visibleKpiColumns.includes('vaep')"
        class="events-list-vaep events-list-sortable"
        @click="eventsStore.setSort('vaep')"
      >
        {{ $t("visualization.events.table.vaep") }}
        <v-icon v-if="sortIcon('vaep')" size="12">{{ sortIcon("vaep") }}</v-icon>
      </span>
      <span
        v-if="eventsStore.visibleKpiColumns.includes('ximpact')"
        class="events-list-ximpact events-list-sortable"
        @click="eventsStore.setSort('ximpact')"
      >
        {{ $t("visualization.events.table.ximpact") }}
        <v-icon v-if="sortIcon('ximpact')" size="12">{{ sortIcon("ximpact") }}</v-icon>
      </span>
    </div>

    <div v-if="!eventsStore.sortedEvents.length" class="events-list-empty">
      {{ $t("visualization.events.no_events") }}
    </div>

    <div
      v-for="(event, idx) in eventsStore.sortedEvents"
      :key="event.id"
      :ref="(el) => setRowRef(el, idx)"
      class="events-list-row"
      :class="{
        'events-list-row--past': isPast(event),
        'events-list-row--next': event.id === eventsStore.nextEventId,
      }"
      @click="eventsStore.jumpToEvent(event)"
    >
      <!-- Sticky (left: ..., see .events-list-pin--marker) so the "up next" indicator
      stays visible even scrolled all the way right -- a plain border-left on the row
      itself (the previous approach) scrolled off with the row's own (very wide) box. -->
      <span class="events-list-current-marker events-list-pin" />
      <span class="events-list-time events-list-pin events-list-pin--time">
        {{ getTimecode(event.timestamp, 0) }}
      </span>
      <span class="events-list-icon events-list-pin events-list-pin--icon">
        <v-icon size="16" :color="typeMeta(event).color">{{ typeMeta(event).icon }}</v-icon>
      </span>
      <span class="events-list-type events-list-pin events-list-pin--type">
        {{ $t(`visualization.events.event_type.${event.event_type}`) }}
      </span>
      <span class="events-list-player events-list-pin events-list-pin--player">
        {{ getPlayerLabel(event.player_id, event.team_id) }}
      </span>
      <span class="events-list-team">
        <span
          class="events-list-team-badge"
          :style="{ backgroundColor: visualizationStore.getTeamColor(event.team_id) }"
        >
          {{ getTeamName(event.team_id) }}
        </span>
      </span>
      <span v-if="eventsStore.visibleKpiColumns.includes('xg')" class="events-list-xg">
        {{ event.xg != null ? event.xg.toFixed(2) : "-" }}
      </span>
      <span v-if="eventsStore.visibleKpiColumns.includes('xsuccess')" class="events-list-xsuccess">
        {{ event.xsuccess.toFixed(2) }}
      </span>
      <span v-if="eventsStore.visibleKpiColumns.includes('vaep')" class="events-list-vaep">
        {{ event.vaep.toFixed(3) }}
      </span>
      <span v-if="eventsStore.visibleKpiColumns.includes('ximpact')" class="events-list-ximpact">
        {{ event.ximpact.toFixed(3) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";
import { useEventsStore, EVENT_TYPE_META } from "@/stores/events";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";
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
const playerStore = usePlayerStore();
const visualizationStore = useVisualizationStore();

const typeMeta = (event) =>
  EVENT_TYPE_META[event.event_type] ?? { icon: "mdi-circle", color: "#888888" };

// Purely time-based (not "is this row's index before the next-event index") so it stays
// correct regardless of how the table's currently sorted -- eventsStore.sortColumn can
// reorder rows away from chronological order, but "already happened" is still just
// whether the event's own timestamp is behind current playback.
const isPast = (event) => event.timestamp < playerStore.currentTime;

// Null when no sortable column is active, or that column isn't the active one --
// mdi-menu-up/-down otherwise, matching eventsStore.sortDir.
const sortIcon = (column) => {
  if (eventsStore.sortColumn !== column) return null;
  return eventsStore.sortDir === "asc" ? "mdi-menu-up" : "mdi-menu-down";
};

// "#10 Max Mustermann" -- number comes from the meta dict's `number` field, name from
// `name` (see posdata_convert.py/object_tracker.py plugins, which populate both per
// player in the meta_data they attach to the run). Falls back to the raw id for either
// piece when the meta dict hasn't got an entry yet (e.g. name defaults to the id itself).
const getPlayerLabel = (playerId, teamId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  const name = topViewStore.getEntityName(playerId, teamId);
  return num != null ? `#${num} ${name}` : `#${playerId} ${name}`;
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

const wrapperRef = ref(null);
const headerRef = ref(null);

const scrollToNext = debounce(() => {
  // rowRefs is keyed by position in the currently *rendered* (possibly sorted, see
  // eventsStore.sortColumn) list, not eventsStore.nextEventIndex, which stays
  // chronological -- look the row up by event id instead of trusting that index directly.
  const id = eventsStore.nextEventId;
  const idx = id != null ? eventsStore.sortedEvents.findIndex((e) => e.id === id) : -1;
  const el = idx >= 0 ? rowRefs.value[idx] : null;
  const wrapper = wrapperRef.value;
  if (!el || !wrapper) return;
  // Deliberately not el.scrollIntoView(): it walks *every* scrollable ancestor (this
  // wrapper, but also the dashboard cell/page around it) and aligns the row to each
  // one's own top, so the whole page scrolled along with the table. Scrolling just
  // this wrapper's scrollTop keeps the effect contained to the table itself.
  const wrapperRect = wrapper.getBoundingClientRect();
  const elRect = el.getBoundingClientRect();
  const headerHeight = headerRef.value?.offsetHeight ?? 0;
  const targetScrollTop = wrapper.scrollTop + (elRect.top - wrapperRect.top) - headerHeight;
  wrapper.scrollTo({ top: targetScrollTop, behavior: "smooth" });
}, 250);

watch(
  () => eventsStore.nextEventId,
  () => nextTick(() => scrollToNext())
);
watch(
  () => eventsStore.sortedEvents,
  () => nextTick(() => scrollToNext()),
  { immediate: true }
);
</script>

<style scoped>
/* The one and only scroll container, both axes -- this is what fixes position:
   sticky actually working: sticky elements pin against their *nearest* scrolling
   ancestor, and that has to be a single element for a header that's pinned
   vertically (top: 0, see .events-list-header) and columns pinned horizontally
   (left: ..., see .events-list-pin) to agree on the same reference frame. Splitting
   x-scroll (here) and y-scroll (an inner .events-list, now removed) across two
   nested elements -- the previous approach -- made the row pins stick to the inner
   *vertical*-scrolling element instead, which doesn't move horizontally at all, so
   they just drifted along with the page instead of actually freezing. Same single-
   scroller approach TabWindowKPI.vue's v-data-table uses under the hood for its
   fixed-header + kpi-table-sticky-first-col combo. */
.events-list-wrapper {
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  overflow: auto;
  max-height: 260px;
  display: flex;
  flex-direction: column;
}
/* dense (squeezed next to video/topview): dropped the fixed cap in favor of
   actually filling the height TabWindowEvents' .events-list-grow hands this
   component's root -- previously this stayed at a small fixed max-height even
   when there was plenty of room below it (see TabWindowEvents.vue). */
.events-list-wrapper--dense {
  max-height: none;
}

.events-list-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px 5px 6px;
  background-color: #303030;
  border-bottom: 1px solid #e0e0e0;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #e0e0e0;
  letter-spacing: 0.02em;
  flex-shrink: 0;
  /* Sized to its own content instead of stretched to the wrapper's width (the
     wrapper's flex default) so it can be wider than the visible area -- see
     .events-list-wrapper for the scrollbar this overflow feeds. */
  width: max-content;
  min-width: 100%;
  box-sizing: border-box;
  /* Pinned to the top of .events-list-wrapper's scroll area as rows scroll past
     underneath -- needs to outrank .events-list-pin's z-index (rows' own pinned
     columns) or, tied at auto/0, the later-in-DOM row cells would paint over it
     instead of going behind (mirrors the th/td z-index note in TabWindowKPI.vue). */
  position: sticky;
  top: 0;
  z-index: 3;
  font-size: 0.8rem;
}

.events-list-empty {
  padding: 24px 12px;
  text-align: center;
  color: #888;
  font-size: 0.85rem;
}

/* Time + the KPI columns' header cells (see eventsStore.setSort) -- the sort icon lives
   inside the same span as the label (not a separate element) so it takes part in the
   span's own flex centering instead of needing its own positioning. */
.events-list-sortable {
  display: inline-flex;
  align-items: center;
  gap: 1px;
  cursor: pointer;
  user-select: none;
}
.events-list-sortable:hover {
  color: #fff;
}
.events-list-sortable .v-icon {
  margin: 0 -2px;
}

.events-list-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 6px;
  border-bottom: 1px solid #eeeeee;
  cursor: pointer;
  transition: opacity 0.2s, background-color 0.2s;
  /* Explicit (theme-correct, not a hardcoded white) rather than transparent so
     .events-list-pin's background-color: inherit below is *exactly* this same
     value, not an approximation of it -- see .events-list-pin for why that
     matters. */
  background-color: rgb(var(--v-theme-surface));
  /* Same content-sized-not-stretched reasoning as .events-list-header/.events-list. */
  width: max-content;
  min-width: 100%;
  box-sizing: border-box;
}
.events-list-row:last-child {
  border-bottom: none;
}
.events-list-row:hover {
  background-color: #7f7f7f;
}
.events-list-row--past {
  opacity: 0.45;
}
.events-list-row--next {
  /* Opaque, not alpha -- an rgba here would get double-painted by the sticky columns
     below (their background-color: inherit copies this value and repaints it a second
     time on top of the row's own already-painted background, see .events-list-pin), and
     two stacked translucent layers compose darker than one. That showed up as visibly
     redder bars over just the Time/Icon/Type/Player columns instead of one even wash
     across the row. color-mix() bakes the tint into a single flat opaque color (against
     the row's own normal surface color, same one TabWindowEvents.vue's card renders, so
     the untinted state still blends in as if the row had no background of its own) --
     painting the *same* opaque color twice is indistinguishable from painting it once, so
     inherit stays safe without needing a separate override for this row. */
  background-color: color-mix(in srgb, rgb(var(--v-theme-surface)) 75%, #ef5350 25%);
  font-weight: bold;
}

/* Marker/Time/Event/Player: pinned in place while Team and the KPI columns scroll
   underneath (see .events-list-wrapper). left values are each column's own true
   resting (unscrolled) x position -- the row's 6px left padding + the cumulative
   width+gap of the preceding pinned columns -- rather than 0, so a pinned column's
   sticky clamp kicks in exactly where it already visually sits. With left: 0 the
   marker's clamp point would sit 6px to the left of where it actually starts, so
   the instant you scrolled even 1px it'd visibly snap that 6px flush against the
   edge instead of just staying put. Hand-computed (there's no CSS for "stick after
   whatever came before"): 6 padding-left = 6 for the marker, + 3 marker + 6 gap = 15
   for time, + 70 time + 6 gap = 91, + 22 icon + 6 gap = 119, + 110 type + 6 gap =
   235 -- keep these in sync with .events-list-row's padding and
   .events-list-current-marker/-time/-icon/-type/-player's widths if those change. */
.events-list-pin {
  position: sticky;
  z-index: 1;
}
.events-list-header .events-list-pin {
  /* Inherits the header's own dark background (see .events-list-header) --
     no per-column override needed since the whole header is one flat color. */
  background-color: inherit;
}
/* Inherits .events-list-row's own (opaque, theme-correct) background -- exactly
   the same value, not a separately-declared approximation of it, so there's no
   way for the two to drift apart and show a seam where Team/KPI content scrolls
   underneath these. This also covers the marker (it has .events-list-pin too),
   including for --next: its background is opaque too (see .events-list-row--next),
   so inheriting and repainting the identical value there is a no-op, not a second
   visible layer -- no separate override needed. */
.events-list-row .events-list-pin {
  background-color: inherit;
}
.events-list-pin--time {
  left: 15px;
}
.events-list-pin--icon {
  left: 91px;
}
.events-list-pin--type {
  left: 119px;
}
.events-list-pin--player {
  left: 235px;
}

/* "Up next" indicator (see .events-list-row--next above). Sized like its sibling
   pin cells (row's default align-items: center, not stretched to the row's full
   height) -- stretching this to full height while everything else stays centered
   on its own (shorter) content made it visibly taller than the row around it. */
.events-list-current-marker {
  width: 3px;
  flex-shrink: 0;
  align-self: center;
  height: 14px;
  transition: background-color 0.2s;
}
.events-list-time {
  font-family: "Courier New", monospace;
  font-size: 0.8rem;
  width: 70px;
  flex-shrink: 0;
}
.events-list-icon {
  flex-shrink: 0;
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.events-list-type {
  width: 110px;
  flex-shrink: 0;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Header-only stand-in for the icon+type pair above -- one label spanning both
   columns' width (22 + 6 gap + 110), left-aligned starting at the icon's own
   position, so "Event" reads as one column instead of implying the icon is its
   own separate one with a blank header cell over it. */
.events-list-event-header {
  width: 138px;
  flex-shrink: 0;
  text-align: left;
}
.events-list-player {
  width: 110px;
  flex-shrink: 0;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.events-list-team {
  flex-shrink: 0;
  width: 50px;
  overflow: hidden;
  text-align: center;
}
/* Same pill look as the team legend below the table (see TabWindowEvents.vue's
   .team-dot) -- solid team color + white text reads faster at this size than the
   plain colored text this used to be, which could get lost against the row's own
   colors (icon, highlighted "next" row, ...). Fixed white rather than the dot's
   selected/unselected two-tone since there's no selection state to reflect here. */
.events-list-team-badge {
  display: inline-block;
  max-width: 100%;
  padding: 1px 8px;
  border-radius: 999px;
  color: #fff;
  font-weight: bold;
  font-size: 0.7rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}
.events-list-xg,
.events-list-xsuccess,
.events-list-vaep,
.events-list-ximpact {
  flex-shrink: 0;
  /* Same size/color as Team, .events-list-team -- these are regular data columns,
     not a secondary/muted detail, so no reason for them to read smaller or greyed
     out relative to the rest of the row. Left-aligned for now like every other
     column (right-align read as neither left- nor center-aligned once the values
     vary in width -- revisit once these settle on real formatting/units). */
  font-size: 0.8rem;
  text-align: center;
  /* text-align above only centers the row cells (plain spans) -- these classes'
     header counterparts are also .events-list-sortable, which is display: inline-flex
     (see there), so their label+sort-icon is laid out as flex children and ignores
     text-align entirely; centering them needs justify-content instead. No-op on the
     row cells since those aren't flex containers. */
  justify-content: center;
}
.events-list-xg {
  width: 46px;
}
.events-list-xsuccess {
  width: 78px;
}
.events-list-vaep {
  width: 50px;
}
.events-list-ximpact {
  width: 64px;
}
</style>
