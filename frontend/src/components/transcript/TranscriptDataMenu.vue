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

        <!-- Available regardless of canWrite, same as PositionDataMenu/EventDataMenu's own
             Select -- a read-only viewer can still pick which of the video's whisper runs to
             view. Unconditionally enabled (unlike PositionDataMenu's, which disables until
             something exists) because ModalTranscriptSelect's own empty state offers the demo
             transcript as a one-click way in, same reasoning as EventDataMenu's Select. Now
             that whisper's advanced options (language, thresholds, ...) make re-running it a
             real workflow, a video can have more than one whisper run -- see
             transcriptSegments in timeline_segment_annotation.js for why the runs can't just
             be merged the way EventDataMenu doesn't need to either. -->
        <v-row style="justify-content: center" class="mt-10 mb-6">
          <v-btn @click="showModalTranscriptSelect = true">
            {{ $t("transcript_data.select") }}
          </v-btn>
          <ModalTranscriptSelect
            v-if="showModalTranscriptSelect"
            v-model="showModalTranscriptSelect"
          />
        </v-row>
      </div>
    </v-col>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { whisperParams } from "@/composables/usePluginParams";
import ModalPluginRun from "@/components/app/app-bar/ModalPluginRun.vue";
import ModalTranscriptSelect from "@/components/transcript/ModalTranscriptSelect.vue";

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

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showWhisperModal = ref(false);
const showModalTranscriptSelect = ref(false);
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
