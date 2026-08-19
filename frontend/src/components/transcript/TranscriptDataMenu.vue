<template>
  <div class="transcript-data-menu-root" data-tour="transcript-data-menu">
    <!-- Same watermark-behind-empty-box treatment as PositionDataMenu.vue/EventDataMenu.vue --
         purely so the card doesn't look bare while empty. -->
    <div v-if="icon" class="transcript-data-menu-watermark">
      <v-icon :size="400">{{ icon }}</v-icon>
    </div>

    <v-col class="transcript-data-menu-col" style="position: relative">
      <!-- Pinned to the top -- only the button block below (.transcript-data-menu-body) is
           vertically centered. -->
      <v-row v-if="title" class="transcript-data-menu-title mt-2" style="justify-content: center">
        {{ title }}
      </v-row>

      <div class="transcript-data-menu-body">
        <template v-if="canWrite">
          <v-row style="justify-content: center" class="mt-8">
            <v-col cols="10">
              <v-sheet border rounded class="pa-4 bg-transparent">
                <v-row
                  class="text-caption text-grey text-uppercase mt-4 mb-2"
                  style="justify-content: center"
                >
                  {{ $t("transcript_data.generate.heading") }}
                </v-row>
                <v-row style="justify-content: center" class="mt-1 mb-4">
                  <v-btn data-tour="transcript-generate-whisper" @click="showWhisperModal = true">
                    {{ $t("modal.plugin.whisper.plugin_name") }}
                  </v-btn>
                </v-row>

                <v-row style="justify-content: center; align-items: center" class="mt-4 mb-n2">
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                  <v-col cols="auto" class="text-grey px-2">{{
                    $t("transcript_data.generate.or")
                  }}</v-col>
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                </v-row>

                <!-- Backdoor for testing the Transcript/Wordcloud tab without waiting on a
                     real Whisper run -- same idea as EventDataMenu's demo button
                     (eventsStore.loadDemoEventData), purely client-side (see
                     timelineSegmentAnnotationStore.loadDemoTranscript). -->
                <v-row style="justify-content: center" class="mt-1 mb-4">
                  <v-btn data-tour="transcript-load-demo" @click="loadDemo">
                    {{ $t("transcript_data.generate.demo") }}
                  </v-btn>
                </v-row>
              </v-sheet>
            </v-col>
          </v-row>

          <ModalPluginRun
            v-if="showWhisperModal"
            v-model="showWhisperModal"
            plugin="whisper"
            :name="$t('modal.plugin.whisper.plugin_name')"
            :description="$t('modal.plugin.whisper.plugin_description')"
            :paramsFactory="whisperParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="transcript-whisper-run"
          />
        </template>

        <!-- Unlike PositionDataMenu/EventDataMenu, there's no "select existing data" or
             upload path here -- a video's transcript is always the single Whisper-generated
             "Transcript" annotation category (see transcriptSegments in
             timeline_segment_annotation.js), so a read-only viewer without canWrite just gets
             told there's nothing yet instead of a dead-end action. -->
        <v-row v-else style="justify-content: center" class="mt-10 mb-6">
          <span class="text-grey">{{ $t("transcript_data.not_selected") }}</span>
        </v-row>
      </div>
    </v-col>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { whisperParams } from "@/composables/usePluginParams";
import ModalPluginRun from "@/components/app/app-bar/ModalPluginRun.vue";

const props = defineProps({
  // Shown as a heading while this box is up -- lets the user tell which (otherwise
  // content-less) card they're looking at. Omit for usages that don't need it.
  title: { type: String, default: null },
  // mdi icon name, shown as a large faint watermark behind the whole box -- same icon as this
  // widget's entry in dashboardWidgets.js (see WidgetPlaceholder, the edit-mode equivalent).
  icon: { type: String, default: null },
});

const playerStore = usePlayerStore();
const userStore = useUserStore();
const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showWhisperModal = ref(false);

const loadDemo = () => {
  timelineSegmentAnnotationStore.loadDemoTranscript();
};
</script>

<style scoped>
/* Structure/sizing mirrors PositionDataMenu.vue's own root/col/body -- see the comments
   there for the full reasoning. */
.transcript-data-menu-root {
  min-height: 60vh;
  position: relative;
  display: flex;
  flex-direction: column;
}

.transcript-data-menu-col {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.transcript-data-menu-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.transcript-data-menu-watermark {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
  opacity: 0.02;
  pointer-events: none;
  overflow: hidden;
}

.transcript-data-menu-title {
  font-size: 1.25rem;
  font-weight: 500;
}
</style>
