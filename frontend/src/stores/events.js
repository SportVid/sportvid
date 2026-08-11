import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";

// Placeholder for the event types a future CV pipeline (action spotting, with xG/VAEP scoring
// layered on top later -- see TabWindowEvents.vue) would emit. Keyed the same way a real
// PluginRunResult-backed "events_data" payload eventually would be: a stable `event_type` id.
// Labels come from i18n (visualization.events.event_type.*); icon/color stay here since
// they're purely a display concern, not part of the (future) backend payload.
export const EVENT_TYPE_META = {
  goal: { icon: "mdi-soccer", color: "#2e7d32" },
  shot_on_target: { icon: "mdi-target", color: "#1565c0" },
  shot_off_target: { icon: "mdi-target-variant", color: "#78909c" },
  foul: { icon: "mdi-whistle", color: "#e65100" },
  card_yellow: { icon: "mdi-square", color: "#f9a825" },
  card_red: { icon: "mdi-square", color: "#c62828" },
  corner: { icon: "mdi-flag", color: "#00838f" },
  offside: { icon: "mdi-flag-outline", color: "#4527a0" },
  substitution: { icon: "mdi-swap-horizontal", color: "#6a1b9a" },
};
export const EVENT_TYPE_IDS = Object.keys(EVENT_TYPE_META);

// No real detector exists yet, so there's no point mocking a full 90 minutes of events --
// the dummy generator only ever covers the first two minutes of the video.
const DUMMY_WINDOW_MS = 2 * 60 * 1000;

// Small dependency-free seeded PRNG (mulberry32) so the mocked events stay stable across
// reloads/re-renders for the same video instead of reshuffling every time.
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return h;
}

export const useEventsStore = defineStore(
  "events",
  () => {
    const topViewStore = useTopViewStore();
    const playerStore = usePlayerStore();

    // Stand-in for a future PluginRunResult (type=TYPE_EVENTS) payload: a flat list of
    // { id, event_type, timestamp, player_id, team_id, confidence, x, y }. Timestamps are ms
    // on the same clock as playerStore.currentTime / topViewStore.sortedFrameKeys, and
    // player_id/team_id resolve through topViewStore.metaDataTopView exactly like position
    // and KPI data do -- so once a real detector lands, only generateDummyEvents() below
    // needs replacing with an actual fetch.
    const eventsData = ref([]);
    const generatedForVideoId = ref(null);

    const selectedEventTypes = ref([...EVENT_TYPE_IDS]);
    // null = not yet initialized -- TabWindowEvents seeds this with "everyone selected" on
    // first use, same pattern as visualizationStore.kpiSelectedPlayerIds.
    const selectedPlayerIds = ref(null);

    function generateDummyEvents() {
      const players = topViewStore.precomputedPlayerList;
      const videoId = playerStore.videoId;
      if (!players.length || !videoId) {
        eventsData.value = [];
        generatedForVideoId.value = null;
        return;
      }
      if (generatedForVideoId.value === videoId) return;

      const keys = topViewStore.sortedFrameKeys;
      const windowEnd = keys.length
        ? Math.min(keys[keys.length - 1], DUMMY_WINDOW_MS)
        : DUMMY_WINDOW_MS;

      const rand = mulberry32(hashSeed(String(videoId)));
      const count = 10 + Math.floor(rand() * 8); // 10-17 events
      const events = [];
      for (let i = 0; i < count; i++) {
        const type = EVENT_TYPE_IDS[Math.floor(rand() * EVENT_TYPE_IDS.length)];
        const player = players[Math.floor(rand() * players.length)];
        events.push({
          id: `dummy-${videoId}-${i}`,
          event_type: type,
          timestamp: Math.round(rand() * windowEnd),
          player_id: player.playerId,
          team_id: player.teamId,
          // Simulated model confidence -- stands in for whatever score a real action-spotting
          // model (and later xG/VAEP) would attach per event.
          confidence: Math.round((0.6 + rand() * 0.4) * 100) / 100,
          x: Math.round(rand() * 100) / 100,
          y: Math.round(rand() * 100) / 100,
        });
      }
      events.sort((a, b) => a.timestamp - b.timestamp);
      eventsData.value = events;
      generatedForVideoId.value = videoId;
    }

    watch(
      [() => topViewStore.precomputedPlayerList, () => playerStore.videoId],
      () => generateDummyEvents(),
      { immediate: true }
    );

    const filteredEvents = computed(() => {
      const typeSet = new Set(selectedEventTypes.value);
      const playerFilter = selectedPlayerIds.value;
      return eventsData.value.filter((e) => {
        if (!typeSet.has(e.event_type)) return false;
        if (playerFilter && !playerFilter.includes(e.player_id)) return false;
        return true;
      });
    });

    // Index (within filteredEvents) of the next event at/after the current playback time --
    // drives both the timeline's "you are here" framing and the list's auto-follow scroll.
    const nextEventIndex = computed(() => {
      const t = playerStore.currentTime;
      return filteredEvents.value.findIndex((e) => e.timestamp >= t);
    });

    function toggleEventType(type) {
      if (selectedEventTypes.value.includes(type)) {
        if (selectedEventTypes.value.length > 1) {
          selectedEventTypes.value = selectedEventTypes.value.filter((t) => t !== type);
        }
      } else {
        selectedEventTypes.value = [...selectedEventTypes.value, type];
      }
    }

    // Seeks the video to shortly before the event so its build-up is visible, rather than
    // dropping the viewer right on top of it.
    function jumpToEvent(event, leadMs = 5000) {
      playerStore.setTargetTime(Math.max(0, event.timestamp - leadMs));
    }

    return {
      eventsData,
      selectedEventTypes,
      selectedPlayerIds,
      filteredEvents,
      nextEventIndex,
      generateDummyEvents,
      toggleEventType,
      jumpToEvent,
    };
  },
  {
    persist: {
      pick: ["selectedEventTypes", "selectedPlayerIds"],
      storage: sessionStorage,
    },
  }
);
