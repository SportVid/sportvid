<template>
  <v-dialog v-model="dialog" width="500">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.transcript_data.select.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 500px; overflow-y: auto">
        <div v-if="whisperRuns.length === 0" class="text-center text-grey mt-2 mb-1">
          {{ $t("modal.transcript_data.select.empty") }}
        </div>

        <!-- Flat list of finished whisper runs -- no tabs/merge-picking like
             ModalPositionDataSelect's, a transcript is always exactly one run's segments (see
             timeline_segment_annotation.js's transcriptSegments). The demo entry is always in
             the list (not just while empty) so it stays reachable for demoing the feature even
             once real runs exist. -->
        <v-list density="compact" class="mt-2">
          <v-list-item
            v-for="run in whisperRuns"
            :key="run.id"
            class="mr-4"
            :active="selectedId === run.id"
            @click="selectedId = run.id"
          >
            <v-list-item-title>{{ run.date }}</v-list-item-title>
          </v-list-item>

          <v-divider v-if="whisperRuns.length" class="my-1" />

          <v-list-item class="mr-4" :active="selectedId === DEMO_ID" @click="selectedId = DEMO_ID">
            <v-list-item-title>{{ $t("modal.transcript_data.select.demo") }}</v-list-item-title>
          </v-list-item>
        </v-list>

        <v-btn class="mt-4 mb-n2" :disabled="!selectedId" @click="confirmSelection">
          {{ $t("button.select") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTimelineStore } from "@/stores/timeline";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";

const playerStore = usePlayerStore();
const pluginRunStore = usePluginRunStore();
const pluginRunResultStore = usePluginRunResultStore();
const timelineStore = useTimelineStore();
const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);
watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);
watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);

// Both needed to resolve a run to its segments (see transcriptSegments in
// timeline_segment_annotation.js): pluginRunResultStore for the run's PluginRunResult,
// timelineStore for which Timeline that result produced. Re-fetching here (rather than
// trusting whatever the page already has) closes the gap if the completion-triggered refresh
// in plugin_run.js's fetchForVideo raced or was missed -- same reasoning as
// ModalPositionDataSelect's own onMounted fetch.
onMounted(() => {
  pluginRunResultStore.fetchForVideo({ videoId: playerStore.videoId });
  // clear: false -- fetchForVideo defaults to wiping the store before repopulating it, which
  // for a split second empties out whichever run's Timeline is currently selected (see
  // transcriptSegments in timeline_segment_annotation.js) and bounces TabWindowTranscript back
  // to TranscriptDataMenu until the response lands. Merging in place avoids that flash.
  timelineStore.fetchForVideo({ videoId: playerStore.videoId, clear: false });
});

// Sentinel id for the "Demo transcript" list entry -- distinct from any real plugin_run id
// (those are UUID hexes), so it can share the same list/selectedId/confirm flow as real runs.
const DEMO_ID = "demo";

// Pre-select whatever's already active (if any) so reopening this to switch runs doesn't
// default back to nothing picked.
const selectedId = ref(
  timelineSegmentAnnotationStore.demoTranscriptActive
    ? DEMO_ID
    : timelineSegmentAnnotationStore.selectedTranscriptRunId
);

const formatLocalDate = (dateString) => {
  if (!dateString) return "";

  let isoString = dateString.replace(" ", "T");
  if (!isoString.endsWith("Z")) {
    isoString += "Z";
  }
  const date = new Date(isoString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return `${isoDate} ${localTime}`;
};

const whisperRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((run) => run.type === "whisper" && run.status === "DONE")
    .map((run) => ({ id: run.id, date: formatLocalDate(run.date) }))
    .sort((a, b) => (a.date < b.date ? 1 : -1));
});

const confirmSelection = () => {
  if (!selectedId.value) return;
  if (selectedId.value === DEMO_ID) {
    timelineSegmentAnnotationStore.loadDemoTranscript();
  } else {
    timelineSegmentAnnotationStore.resetDemoTranscript();
    timelineSegmentAnnotationStore.selectTranscriptRun(selectedId.value);
  }
  dialog.value = false;
};
</script>
