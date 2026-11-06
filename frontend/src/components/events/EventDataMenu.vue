<template>
  <div class="event-data-menu-root" data-tour="event-data-menu">
    <!-- Same watermark-behind-empty-box treatment as PositionDataMenu.vue -- purely so the
         card doesn't look bare while empty. -->
    <div v-if="icon" class="event-data-menu-watermark">
      <v-icon :size="400">{{ icon }}</v-icon>
    </div>

    <v-col class="event-data-menu-col" style="position: relative">
      <!-- Pinned to the top -- only the button block below (.event-data-menu-body) is
           vertically centered. -->
      <v-row v-if="title" class="event-data-menu-title mt-2" style="justify-content: center">
        {{ title }}
      </v-row>

      <div class="event-data-menu-body">
        <template v-if="canWrite">
          <v-row style="justify-content: center" class="mt-8">
            <v-col cols="10">
              <v-sheet border rounded class="pa-4 bg-transparent">
                <v-row
                  class="text-caption text-grey text-uppercase mt-4 mb-2"
                  style="justify-content: center"
                >
                  {{ $t("event_data.generate.cv_heading") }}
                </v-row>
                <v-row style="justify-content: center" class="mt-1 ga-4">
                  <!-- No action-spotting plugin exists yet (see events.js) -- disabled with a
                       hover hint rather than hidden, so the eventual real button lands in the
                       same spot without anyone needing to relearn the layout. -->
                  <v-menu location="top center" open-on-hover>
                    <template #activator="{ props: menuProps }">
                      <span v-bind="menuProps">
                        <v-btn disabled data-tour="eventdata-generate-cv">
                          {{ $t("event_data.generate.detect_events") }}
                        </v-btn>
                      </span>
                    </template>
                    <v-sheet class="pa-3" align="center" style="max-width: 300px">
                      {{ $t("event_data.generate.coming_soon") }}
                    </v-sheet>
                  </v-menu>
                </v-row>

                <v-row style="justify-content: center; align-items: center" class="mt-4 mb-n2">
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                  <v-col cols="auto" class="text-grey px-2">{{
                    $t("event_data.generate.or")
                  }}</v-col>
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                </v-row>

                <v-row
                  class="text-caption text-grey text-uppercase mb-2"
                  style="justify-content: center"
                >
                  {{ $t("event_data.generate.upload_heading") }}
                </v-row>
                <v-row style="justify-content: center" class="mt-1 mb-4">
                  <v-btn
                    data-tour="eventdata-manual-upload-open"
                    @click="showModalEventDataUpload = true"
                  >
                    {{ $t("event_data.display_settings.event_data.upload") }}
                  </v-btn>
                </v-row>
              </v-sheet>
            </v-col>
          </v-row>
        </template>

        <v-row style="justify-content: center" class="mt-10 mb-6">
          <!-- Unlike PositionDataMenu's Select (disabled until something's actually available to
               pick), this stays enabled even with zero event data sets uploaded yet -- the modal's
               own empty state offers a one-click demo-data shortcut instead of just dead-ending
               (see ModalEventDataSelect.vue / eventsStore.loadDemoEventData). -->
          <v-btn @click="showModalEventDataSelect = true">
            {{ $t("event_data.display_settings.event_data.select") }}
          </v-btn>
          <ModalEventDataSelect
            v-if="showModalEventDataSelect"
            v-model="showModalEventDataSelect"
          />
        </v-row>

        <ModalEventDataUpload v-if="showModalEventDataUpload" v-model="showModalEventDataUpload" />
      </div>
    </v-col>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import ModalEventDataUpload from "@/components/events/ModalEventDataUpload.vue";
import ModalEventDataSelect from "@/components/events/ModalEventDataSelect.vue";

const props = defineProps({
  // Shown as a heading while this box is up -- lets the user tell which (otherwise
  // content-less) card they're looking at. Omit for usages that don't need it.
  title: { type: String, default: null },
  // mdi icon name, shown as a large faint watermark behind the whole box.
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

const showModalEventDataUpload = ref(false);
const showModalEventDataSelect = ref(false);
</script>

<style scoped>
/* See PositionDataMenu.vue's own .position-data-menu-root/-col/-body for the reasoning -- same
   structure here: title pinned to the top, only .event-data-menu-body centered below it. */
.event-data-menu-root {
  min-height: 60vh;
  position: relative;
  display: flex;
  flex-direction: column;
}

.event-data-menu-col {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.event-data-menu-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.event-data-menu-watermark {
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

/* Matches PositionDataMenu.vue's own title styling. */
.event-data-menu-title {
  font-size: 1.25rem;
  font-weight: 500;
}
</style>
