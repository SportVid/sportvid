<template>
  <!-- Playback controls for the tools that review the running video rather than a set of
       sampled still frames (see the registry's `playback`). The video element itself stays in
       AnnotationView -- everything here goes through playerStore, exactly like VideoPlayer.vue
       does on the analysis route, so the timeline, the event list and this bar all read the
       same playhead.

       Same button row and the same icons as VideoPlayer's control bar (second/frame steps
       around play/pause), with the two event jumps added on the outside: circled skip icons,
       so "jump to the next event" is visibly a different kind of step than "one frame on".
       No hover labels -- the row is read at a glance while watching, and a tooltip popping up
       under the video is exactly where it is most in the way. -->
  <div class="transport">
    <v-btn size="small" variant="text" :disabled="!hasEvents" @click="stepEvent(-1)">
      <v-icon size="24">mdi-skip-previous-circle-outline</v-icon>
    </v-btn>

    <v-btn size="small" variant="text" @click="stepTime(-1000)">
      <v-icon size="24">mdi-skip-backward</v-icon>
    </v-btn>

    <v-btn size="small" variant="text" @click="stepTime(-frameMs)">
      <v-icon size="24">mdi-skip-previous</v-icon>
    </v-btn>

    <v-btn variant="text" color="primary" @click="playerStore.togglePlaying()">
      <v-icon size="30">{{ playerStore.playing ? "mdi-pause" : "mdi-play" }}</v-icon>
    </v-btn>

    <v-btn size="small" variant="text" @click="stepTime(frameMs)">
      <v-icon size="24">mdi-skip-next</v-icon>
    </v-btn>

    <v-btn size="small" variant="text" @click="stepTime(1000)">
      <v-icon size="24">mdi-skip-forward</v-icon>
    </v-btn>

    <v-btn size="small" variant="text" :disabled="!hasEvents" @click="stepEvent(1)">
      <v-icon size="24">mdi-skip-next-circle-outline</v-icon>
    </v-btn>

    <!-- Milliseconds shown on purpose: this bar exists to judge whether an event sits on the
         right moment, and at 25 fps a frame is 40 ms -- a second-resolution readout can't tell
         two adjacent frames apart. -->
    <span class="transport-time">
      {{ getTimecode(playerStore.currentTime, 3) }}
      <span class="transport-duration">/ {{ getTimecode(playerStore.videoDuration, 0) }}</span>
    </span>

    <v-spacer />

    <v-menu location="top">
      <template #activator="{ props }">
        <v-btn v-bind="props" size="small" variant="text" class="transport-rate">
          {{ rate.toFixed(2) }}&times;
        </v-btn>
      </template>
      <v-list density="compact">
        <v-list-item
          v-for="option in RATE_OPTIONS"
          :key="option"
          :active="rate === option"
          @click="emit('update:rate', option)"
        >
          <v-list-item-title>{{ option.toFixed(2) }}&times;</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- The still-frame tools have no use for sound, but event timing does: a whistle or the
         sound of the contact is often what tells you which frame a foul actually happened on.
         Volume and mute are the player store's own (persisted, shared with VideoPlayer) --
         AnnotationView mirrors both onto its element. -->
    <v-btn size="small" variant="text" @click="playerStore.toggleMute()">
      <v-icon size="24">{{ playerStore.isMuted ? "mdi-volume-mute" : playerStore.volumeIcon }}</v-icon>
    </v-btn>

    <div class="transport-volume">
      <v-slider
        v-model="playerStore.volume"
        min="0"
        max="100"
        hide-details
        color="primary"
        :thumb-size="14"
        track-size="4"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { getTimecode } from "@/plugins/time";

// The playback rate lives on the <video> element AnnotationView owns, so it is passed through
// rather than kept here; play/pause and the playhead go through playerStore, which the view
// mirrors onto that element.
defineProps({
  rate: { type: Number, default: 1 },
});
const emit = defineEmits(["update:rate"]);

const RATE_OPTIONS = [0.25, 0.5, 1, 1.5, 2];

const playerStore = usePlayerStore();
const store = useAnnotationToolStore();

// Event-to-event navigation sits here rather than in the panel's list because it moves the
// playhead -- it is a way of playing the video, not a way of browsing the table.
const events = computed(() => store.visibleReviewEvents);
const hasEvents = computed(() => events.value.length > 0);

const frameMs = computed(() => 1000 / (playerStore.videoFPS || 30));

// Stepping is a frame-accurate operation, so it pauses first -- otherwise playback simply runs
// over the frame that was just stepped onto.
function stepTime(deltaMs) {
  playerStore.setPlaying(false);
  const end = playerStore.videoDuration || Infinity;
  playerStore.setTargetTime(
    Math.min(Math.max(0, Math.round(playerStore.currentTime + deltaMs)), end)
  );
}

// Lands exactly on the event, not a few seconds before it the way eventsStore.jumpToEvent does
// for watching: here the question is whether the event sits on the right frame, and the answer
// is only visible on that frame itself.
function stepEvent(direction) {
  const time = playerStore.currentTime;
  const list = events.value;
  const next =
    direction > 0
      ? list.find((event) => event.timestamp > time + 1)
      : [...list].reverse().find((event) => event.timestamp < time - 1);
  if (!next) return;
  playerStore.setPlaying(false);
  store.selectEvent(next.id, { seek: true });
}
</script>

<style scoped>
.transport {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  padding: 4px 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

.transport-time {
  margin-left: 10px;
  font-family: monospace;
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.transport-duration {
  opacity: 0.6;
  margin-left: 2px;
}

.transport-rate {
  font-variant-numeric: tabular-nums;
  font-size: 0.85rem;
  min-width: 58px;
}

/* Same proportion of the bar VideoPlayer.vue gives its own volume slider. */
.transport-volume {
  width: 110px;
  flex-shrink: 0;
  margin-right: 4px;
}
</style>
