<template>
  <div class="events-timeline">
    <div class="events-timeline-track">
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
        class="events-timeline-current"
        :style="{ left: currentTimePercent + '%' }"
      />

      <v-tooltip v-for="event in positionedEvents" :key="event.id" location="top">
        <template #activator="{ props: tooltipProps }">
          <button
            v-bind="tooltipProps"
            type="button"
            class="events-timeline-marker"
            :style="{ left: event.percent + '%', backgroundColor: event.color }"
            @click="eventsStore.jumpToEvent(event)"
          >
            <v-icon size="12" color="white">{{ event.icon }}</v-icon>
          </button>
        </template>
        <span>
          {{ $t(`visualization.events.event_type.${event.event_type}`) }} —
          {{ playerLabel(event) }} ({{ getTimecode(event.timestamp, 0) }})
        </span>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useEventsStore, EVENT_TYPE_META } from "@/stores/events";
import { getTimecode } from "@/plugins/time";

const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const eventsStore = useEventsStore();

// Driven by the same selected-time-range the VisualizationTimeSelector above this component
// edits (see TabWindowEvents.vue) -- zooming/panning that selector zooms this timeline too.
const rangeStart = computed(() => positionDataStore.selectedTimeRange.start);
const rangeEnd = computed(() => positionDataStore.selectedTimeRange.end);
const rangeSpan = computed(() => Math.max(1, rangeEnd.value - rangeStart.value));

function percentFor(time) {
  return ((time - rangeStart.value) / rangeSpan.value) * 100;
}

const ticks = computed(() => {
  const n = 4;
  const arr = [];
  for (let i = 0; i <= n; i++) {
    const time = rangeStart.value + (rangeSpan.value * i) / n;
    const justify = i === 0 ? "left" : i === n ? "right" : "center";
    arr.push({ time, percent: (i / n) * 100, label: getTimecode(time, 0), justify });
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
    }))
);

function playerLabel(event) {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[event.player_id]?.number;
  return num != null ? `#${num}` : `#${event.player_id}`;
}
</script>

<style scoped>
.events-timeline {
  width: 100%;
  padding: 6px 0 26px;
  /* Fixed-size element in TabWindowEvents' flex column -- never shrunk to
     make room for EventsList (see its own flex-grow there instead). */
  flex-shrink: 0;
}

.events-timeline-track {
  position: relative;
  height: 34px;
  background-color: #bbbbbb;
  border-radius: 5px;
}

.events-timeline-tick {
  position: absolute;
  top: 100%;
  margin-top: 2px;
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

.events-timeline-tick-mark {
  position: absolute;
  top: -8px;
  left: 50%;
  width: 1px;
  height: 6px;
  background-color: #666;
}
.events-timeline-tick--left .events-timeline-tick-mark {
  left: 0;
}
.events-timeline-tick--right .events-timeline-tick-mark {
  left: 100%;
}

.events-timeline-tick-label {
  font-family: "Courier New", monospace;
  font-size: 11px;
  color: #555;
  white-space: nowrap;
}

.events-timeline-current {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: white;
  pointer-events: none;
}

.events-timeline-marker {
  position: absolute;
  top: 50%;
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
}
.events-timeline-marker:hover {
  transform: translate(-50%, -50%) scale(1.25);
  z-index: 2;
}
</style>
