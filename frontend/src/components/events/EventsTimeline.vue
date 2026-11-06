<template>
  <div class="events-timeline">
    <div ref="trackRef" class="events-timeline-track" @click="onTrackClick">
      <div
        v-for="tick in minorTicks"
        :key="'minor-' + tick.time"
        class="events-timeline-tick-minor"
        :style="{ left: tick.percent + '%' }"
      />

      <div
        v-for="tick in ticks"
        :key="tick.time"
        class="events-timeline-tick"
        :class="`events-timeline-tick--${tick.justify}`"
        :style="{ left: tick.percent + '%' }"
      >
        <div class="events-timeline-tick-mark" />
        <span class="events-timeline-tick-label">{{ tick.label }}</span>
      </div>

      <div
        v-if="currentTimePercent !== null"
        class="events-timeline-current-hit"
        :style="{ left: currentTimePercent + '%' }"
        @mousedown="onCurrentTimeMouseDown"
      >
        <div class="events-timeline-current" />
      </div>

      <v-tooltip
        v-for="event in positionedEvents"
        :key="event.id"
        location="top"
        class="events-timeline-tooltip"
        :style="{ '--tooltip-bg': toRgb(event.teamColor, 0.7) }"
      >
        <template #activator="{ props: tooltipProps }">
          <button
            v-bind="tooltipProps"
            type="button"
            class="events-timeline-marker"
            :style="{ left: event.percent + '%', backgroundColor: event.color }"
            @click.stop="eventsStore.jumpToEvent(event)"
          >
            <v-icon size="12" color="white">{{ event.icon }}</v-icon>
          </button>
        </template>
        <span>
          {{ $t(`visualization.events.event_type.${event.event_type}`) }}
          ({{ playerLabel(event) }})
        </span>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";
import { useEventsStore, EVENT_TYPE_META } from "@/stores/events";
import { getTimecode } from "@/plugins/time";
import { toRgb } from "@/plugins/helpers";

const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const eventsStore = useEventsStore();

// Driven by the same selected-time-range the VisualizationTimeSelector above this component
// edits (see TabWindowEvents.vue) -- zooming/panning that selector zooms this timeline too.
const rangeStart = computed(() => positionDataStore.selectedTimeRange.start);
const rangeEnd = computed(() => positionDataStore.selectedTimeRange.end);
const rangeSpan = computed(() => Math.max(1, rangeEnd.value - rangeStart.value));

function percentFor(time) {
  return ((time - rangeStart.value) / rangeSpan.value) * 100;
}

const TICK_COUNT = 4;
const ticks = computed(() => {
  const n = TICK_COUNT;
  const arr = [];
  for (let i = 0; i <= n; i++) {
    const time = rangeStart.value + (rangeSpan.value * i) / n;
    const justify = i === 0 ? "left" : i === n ? "right" : "center";
    arr.push({ time, percent: (i / n) * 100, label: getTimecode(time, 0), justify });
  }
  return arr;
});

// Unlabeled sub-ticks between the main ticks above, mirroring
// VisualizationTimeSelector's minorFrames/minorStrokes (also a quarter of
// each main interval) -- skips the positions that coincide with a main tick.
const minorTicks = computed(() => {
  const n = TICK_COUNT * 4;
  const arr = [];
  for (let i = 0; i <= n; i++) {
    if (i % 4 === 0) continue;
    const time = rangeStart.value + (rangeSpan.value * i) / n;
    arr.push({ time, percent: (i / n) * 100 });
  }
  return arr;
});

// Plain reactive CSS binding rather than VisualizationTimeSelector's paper.js/rAF redraw loop
// -- video timeupdate events are frequent enough (a few times a second) that Vue's own
// reactivity keeps this smooth without an animation-frame loop of its own.
const currentTimePercent = computed(() => {
  const t = playerStore.currentTime;
  if (t < rangeStart.value || t > rangeEnd.value) return null;
  return percentFor(t);
});

const positionedEvents = computed(() =>
  eventsStore.filteredEvents
    .filter((e) => e.timestamp >= rangeStart.value && e.timestamp <= rangeEnd.value)
    .map((e) => ({
      ...e,
      percent: percentFor(e.timestamp),
      icon: EVENT_TYPE_META[e.event_type]?.icon ?? "mdi-circle",
      color: EVENT_TYPE_META[e.event_type]?.color ?? "#888888",
      teamColor: visualizationStore.getTeamColor(e.team_id),
    }))
);

// "#10 Max Mustermann" -- same number+name pattern as EventsList.vue's getPlayerLabel.
function playerLabel(event) {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[event.player_id]?.number;
  const name = topViewStore.getEntityName(event.player_id, event.team_id);
  return num != null ? `#${num} ${name}` : `#${event.player_id} ${name}`;
}

// Click-to-seek and drag-the-current-time-line, mirroring the
// playerStore.setTargetTime() pattern Timeline.vue uses for the main timeline.
const trackRef = ref(null);

function clampTime(time) {
  return Math.min(rangeEnd.value, Math.max(rangeStart.value, time));
}

function timeFromClientX(clientX) {
  const rect = trackRef.value.getBoundingClientRect();
  const percent = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
  return clampTime(rangeStart.value + percent * rangeSpan.value);
}

function onTrackClick(event) {
  // Event markers handle their own click (jumpToEvent) and the current-time
  // line is dragged via mousedown below -- don't also seek under those.
  if (event.target.closest(".events-timeline-marker, .events-timeline-current-hit")) return;
  // Explicit "go somewhere else", unlike a marker click -- release the fixed "current
  // event" highlight (see eventsStore.jumpToEvent/clearPinnedEvent) rather than let it
  // keep riding along on an event this seek just navigated away from.
  eventsStore.clearPinnedEvent();
  playerStore.setTargetTime(timeFromClientX(event.clientX));
}

function onCurrentTimeMouseDown(event) {
  event.preventDefault();
  event.stopPropagation();
  // Same reasoning as onTrackClick above -- once per drag (not per mousemove tick) is
  // enough, the pin stays released for the rest of the drag on its own.
  eventsStore.clearPinnedEvent();
  // Override the cursor globally while dragging -- the mouse routinely leaves
  // the 14px hit area once the drag is under way, and without this the
  // cursor would flicker back to default over the rest of the track/page.
  document.body.style.cursor = "ew-resize";
  const onMouseMove = (moveEvent) => {
    playerStore.setTargetTime(timeFromClientX(moveEvent.clientX));
  };
  const onMouseUp = () => {
    document.body.style.cursor = "";
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
  };
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}
</script>

<style scoped>
/* Zone heights inside the (now taller) track: the top --marker-zone-height
   holds the event markers/current-time line, same as the track's old full
   height; the rest below is the tick scale, now integrated into the gray
   area itself (see .events-timeline-tick) instead of sitting in the
   wrapper's padding below it -- keeps it clickable like
   VisualizationTimeSelector's own time scale, which is also drawn inside
   its track rather than below it. */
.events-timeline {
  width: 100%;
  padding: 6px 0;
  /* Fixed-size element in TabWindowEvents' flex column -- never shrunk to
     make room for EventsList (see its own flex-grow there instead). */
  flex-shrink: 0;
}

.events-timeline-track {
  position: relative;
  height: 46px;
  --marker-zone-height: 26px;
  background-color: #bbbbbb;
  border-radius: 5px;
  /* Plain click-to-seek area -- markers (cursor: pointer) and the current-time
     line (cursor: ew-resize) override this on themselves below. */
  cursor: crosshair;
  /* This track is built from real DOM text (tick labels), unlike
     VisualizationTimeSelector's canvas -- without this, dragging across it (to
     seek, or to drag the current-time line) also does a normal browser text
     selection/highlight underneath, which a canvas has no text in to select in
     the first place. */
  user-select: none;
  -webkit-user-select: none;
}

.events-timeline-tick {
  position: absolute;
  top: var(--marker-zone-height);
}
.events-timeline-tick--left {
  transform: translateX(0);
}
.events-timeline-tick--center {
  transform: translateX(-50%);
}
.events-timeline-tick--right {
  transform: translateX(-100%);
}

/* Positioned directly on the track (not nested in .events-timeline-tick like
   the main ticks) since it's just a centered dash with no label to justify.
   Shorter than .events-timeline-tick-mark and centered on the same vertical
   midpoint, same proportions as VisualizationTimeSelector's minor strokes
   relative to its main ones. */
.events-timeline-tick-minor {
  position: absolute;
  top: 14px;
  height: 8px;
  width: 1px;
  background-color: #000;
  transform: translateX(-0.5px);
}

.events-timeline-tick-mark {
  position: absolute;
  top: -20px;
  left: 50%;
  width: 1px;
  height: 24px;
  background-color: #000;
}
.events-timeline-tick--left .events-timeline-tick-mark {
  left: 0;
}
.events-timeline-tick--right .events-timeline-tick-mark {
  left: 100%;
}

.events-timeline-tick-label {
  display: inline-block;
  margin-top: 8px;
  font-family: "Courier New", monospace;
  font-size: 11px;
  color: #000;
  white-space: nowrap;
}

/* Wider, invisible hit area centered on the visible line -- 2px is too thin
   to reliably grab, so dragging is handled here and passed through to the
   actual line via pointer-events: none below. z-index stays below markers
   (see .events-timeline-marker) so an event sitting under the current-time
   line is still clickable on its own. */
.events-timeline-current-hit {
  position: absolute;
  top: 0;
  /* Full track height, matching the visible line below (.events-timeline-current
     is also full-height) -- lets you grab and drag the current-time line from
     anywhere along the timeline, not just the marker zone up top. */
  height: 100%;
  width: 14px;
  transform: translateX(-7px);
  cursor: ew-resize;
  z-index: 1;
}

.events-timeline-current {
  position: absolute;
  top: 0;
  height: 46px;
  left: 50%;
  width: 2px;
  margin-left: -1px;
  background-color: white;
  pointer-events: none;
}

.events-timeline-marker {
  position: absolute;
  /* Centered on the marker zone, not the full (now-taller) track -- a plain
     top: 50% would drift down into the tick scale below it. */
  /* top: calc(var(--marker-zone-height) / 2); */
  top: 18px;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  transition: transform 0.15s;
  /* Above .events-timeline-current-hit -- an event marker under the current-time
     line must stay clickable rather than getting swallowed by the drag area. */
  z-index: 2;
}
.events-timeline-marker:hover {
  transform: translate(-50%, -50%) scale(1.25);
  z-index: 4;
}

/* Team-colored instead of Vuetify's default gray tooltip -- same lightly-tinted-toward-white
   approach (toRgb(color, 0.7)) as VideoPlayer.vue's bounding-box-tooltip, so a hovered
   marker reads as "this team" without the tint fighting the tooltip text/other markers. */
.events-timeline-tooltip ::v-deep(.v-overlay__content) {
  background-color: var(--tooltip-bg);
  color: #222;
}
</style>
