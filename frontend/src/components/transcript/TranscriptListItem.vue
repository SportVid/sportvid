<template>
  <div
    class="transcript-item"
    :class="{ 'transcript-item--active': isHighlighted }"
    @click="playerStore.setTargetTime(transcript.start)"
  >
    <span class="transcript-item-time">{{ getTimecode(transcript.start, 0) }}</span>
    <span class="transcript-item-text">{{ transcript.name }}</span>
  </div>
</template>

<script setup>
import { computed, watch } from "vue";
import { getTimecode } from "@/plugins/time";
import { usePlayerStore } from "@/stores/player";

const props = defineProps({
  transcript: { type: Object, required: true },
});

// Fired once, the moment this segment becomes the one currently being spoken -- lets the
// parent list auto-scroll to keep up with playback (see TabWindowTranscript.vue's
// scrollToCurrent), same "only just now became relevant" edge-trigger EventsList.vue uses for
// its "next event" auto-scroll.
const emit = defineEmits(["highlighted"]);

const playerStore = usePlayerStore();

const isHighlighted = computed(
  () =>
    props.transcript.start <= playerStore.currentTime && props.transcript.end > playerStore.currentTime
);

watch(isHighlighted, (newVal) => {
  if (newVal) emit("highlighted", props.transcript.id);
});
</script>

<style scoped>
.transcript-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.transcript-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.06);
}

.transcript-item--active {
  background-color: rgba(var(--v-theme-primary), 0.16);
}

.transcript-item-time {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
}

.transcript-item-text {
  font-size: 0.9rem;
}
</style>
