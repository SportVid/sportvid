<template>
  <div class="event-panel">
    <!-- Which event, then what about it: the list is the walkthrough, the editor below works
         on whatever it has selected. Both halves stay visible, so correcting one event never
         costs the overview of the rest. -->
    <EventReviewList class="event-panel-list" />

    <v-divider />

    <div class="event-panel-editor">
      <div v-if="!event" class="panel-empty text-medium-emphasis">
        {{ $t("annotation_tool.event.no_selection") }}
      </div>

      <template v-else>
        <div class="panel-heading">{{ $t("annotation_tool.event.title") }}</div>

        <!-- Side by side: the two are one statement about the event ("who did what"), and
             stacking them cost a whole row of height in a column that also carries the list.
             The menus they open are as wide as they need to be regardless of the field. -->
        <div class="field-row">
          <v-select
            v-model="newType"
            :items="typeOptions"
            item-title="label"
            item-value="id"
            :label="$t('visualization.events.table.type')"
            variant="underlined"
            density="compact"
            hide-details
          >
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps" :title="null">
                <v-list-item-title class="text-body-2 d-flex align-center">
                  <v-icon size="16" :color="item.raw.color" class="mr-2">
                    {{ item.raw.icon }}
                  </v-icon>
                  {{ item.raw.label }}
                </v-list-item-title>
              </v-list-item>
            </template>
          </v-select>

          <!-- Team follows the player: an event belongs to whoever performed it, and picking a
               player of the other team while leaving the old team id behind would only produce
               a mismatched pair no consumer could make sense of. -->
          <v-select
            v-model="newPlayerId"
            :items="playerOptions"
            item-title="label"
            item-value="id"
            :label="$t('visualization.events.table.player')"
            variant="underlined"
            density="compact"
            hide-details
          />
        </div>

        <div class="panel-subheading mt-5">{{ $t("annotation_tool.event.timing") }}</div>

        <!-- Where the event sits now, and -- once it has been moved -- where the detector had
             put it. The timeline below the video shows the same shift graphically; this is the
             same fact as an actual pair of timecodes. -->
        <div class="time-row">
          <template v-if="movedFrom">
            <span class="time-was">{{ movedFrom }}</span>
            <v-icon size="15" class="time-arrow">mdi-arrow-right</v-icon>
          </template>
          <span class="time-value">{{ getTimecode(event.timestamp, 3) }}</span>
        </div>

        <!-- The coarse move is the drag on the timeline; these are the last frame or two,
             which no drag on a timeline that spans minutes can hit. -->
        <div class="nudge-row">
          <v-btn size="x-small" variant="tonal" @click="nudge(-1000)">-1s</v-btn>
          <v-btn size="x-small" variant="tonal" @click="nudge(-frameMs)">
            <v-icon size="16">mdi-chevron-left</v-icon>
          </v-btn>
          <v-btn size="x-small" variant="tonal" @click="nudge(frameMs)">
            <v-icon size="16">mdi-chevron-right</v-icon>
          </v-btn>
          <v-btn size="x-small" variant="tonal" @click="nudge(1000)">+1s</v-btn>
        </div>

        <!-- Only the two dropdowns wait for this. A nudge and a drag are direct manipulation:
             they are judged by watching the marker and the playhead move, which an apply-later
             form would hide until after the decision has been made. Nothing leaves the browser
             either way -- see the store's exportDraft. -->
        <v-btn
          block
          size="small"
          color="primary"
          variant="flat"
          class="mt-4"
          :disabled="!hasChange"
          @click="applyUpdate"
        >
          {{ $t("button.update") }}
        </v-btn>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { useEventsStore, EVENT_TYPE_META, EVENT_TYPE_IDS } from "@/stores/events";
import { getTimecode } from "@/plugins/time";
import EventReviewList from "@/components/annotation-tool/EventReviewList.vue";

// The event half of the annotation tool's properties panel, the counterpart to
// BboxIdentityPanel -- same shape: what is selected, the fields that describe it, one Update.
// Deleting and reverting are not here but in the toolbox on the left, where the bbox tool
// keeps them too.

const { t } = useI18n();
const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const eventsStore = useEventsStore();
const store = useAnnotationToolStore();

const event = computed(() => store.selectedEvent);

const newType = ref(null);
const newPlayerId = ref(null);

// Reseed whenever a different event is picked, so the panel never shows the previous one's
// pending values (same guard BboxIdentityPanel needs).
watch(
  event,
  (value) => {
    if (!value) return;
    newType.value = value.event_type;
    newPlayerId.value = value.player_id;
  },
  { immediate: true }
);

const typeOptions = computed(() =>
  EVENT_TYPE_IDS.map((id) => ({
    id,
    label: t(`visualization.events.event_type.${id}`),
    icon: EVENT_TYPE_META[id].icon,
    color: EVENT_TYPE_META[id].color,
  }))
);

// The roster to reassign to. Position data is the good source when it is loaded, but event
// data is meant to stand on its own (see events.js) -- so whoever the event data itself
// mentions counts too, which is also what keeps this working on the demo set alone.
const playerOptions = computed(() => {
  const byId = new Map();
  for (const player of topViewStore.precomputedPlayerList) {
    byId.set(player.playerId, { id: player.playerId, teamId: player.teamId });
  }
  for (const entry of eventsStore.eventsData) {
    if (entry.player_id != null && !byId.has(entry.player_id)) {
      byId.set(entry.player_id, { id: entry.player_id, teamId: entry.team_id });
    }
  }

  const options = [...byId.values()]
    .map((player) => {
      const number = topViewStore.metaDataTopView?.player_ids?.[player.id]?.number;
      const name = topViewStore.getEntityName(player.id, player.teamId);
      return { ...player, label: `#${number ?? player.id} ${name}` };
    })
    .sort(
      (a, b) =>
        String(a.teamId).localeCompare(String(b.teamId)) || String(a.id).localeCompare(String(b.id))
    );

  return [{ id: null, teamId: -1, label: t("annotation_tool.event.no_player") }, ...options];
});

const hasChange = computed(() => {
  if (!event.value) return false;
  return newType.value !== event.value.event_type || newPlayerId.value !== event.value.player_id;
});

function applyUpdate() {
  const option = playerOptions.value.find((entry) => entry.id === newPlayerId.value);
  store.updateEvent(event.value.id, {
    event_type: newType.value,
    player_id: newPlayerId.value,
    team_id: option ? option.teamId : -1,
  });
}

const frameMs = computed(() => 1000 / (playerStore.videoFPS || 30));

// Where the detector had put it, once it has been moved away from there.
const movedFrom = computed(() => {
  const current = event.value;
  if (!current?.originalTimestamp || current.originalTimestamp === current.timestamp) return null;
  return getTimecode(current.originalTimestamp, 3);
});

// The playhead follows the nudge -- the point of stepping an event a frame at a time is to look
// at the frame it lands on.
function nudge(deltaMs) {
  const next = Math.max(0, event.value.timestamp + deltaMs);
  store.updateEvent(event.value.id, { timestamp: next });
  playerStore.setPlaying(false);
  playerStore.setTargetTime(next);
}
</script>

<style scoped>
.event-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* The list gets the leftover height and scrolls inside itself; the editor below is sized by
   its own content, so it never gets pushed out of view by a long event list. */
.event-panel-list {
  flex: 1 1 auto;
}

.event-panel-editor {
  flex-shrink: 0;
  padding: 10px 14px 12px;
  overflow-y: auto;
  max-height: 62%;
}

.panel-heading {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 10px;
}

.panel-subheading {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(var(--v-theme-on-surface), 0.6);
  margin-bottom: 4px;
}

/* Two fields to a row; the smaller type size is what keeps the longer event labels ("Shot off
   target") readable at half the panel's width. */
.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.field-row :deep(.v-field__input) {
  font-size: 0.82rem;
}

.panel-empty {
  font-size: 0.85rem;
  padding: 12px 0;
}

.time-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.time-value {
  font-family: monospace;
  font-size: 0.95rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.time-was {
  font-family: monospace;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.55;
  text-decoration: line-through;
}

.time-arrow {
  opacity: 0.55;
}

.nudge-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  margin-top: 8px;
}
</style>
