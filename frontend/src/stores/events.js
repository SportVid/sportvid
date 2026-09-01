import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";

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

// The KPI columns in EventsList.vue -- toggleable from TabWindowEvents.vue's display
// settings menu (see visibleKpiColumns below) the same way event types are, and
// individually sortable (see sortColumn/setSort below) alongside Time. Order here is
// also the table's column order.
export const KPI_COLUMN_META = {
  xg: { labelKey: "visualization.events.table.xg" },
  xsuccess: { labelKey: "visualization.events.table.xsuccess" },
  vaep: { labelKey: "visualization.events.table.vaep" },
  ximpact: { labelKey: "visualization.events.table.ximpact" },
};
export const KPI_COLUMN_IDS = Object.keys(KPI_COLUMN_META);

// Last-resort span for the mocked events, used only when nothing else says how long the video
// is (see eventsData below). The video's own duration is what the generator normally spreads
// them over: demo events that stop two minutes in leave the rest of the timeline empty and
// make every timecode read next to it look wrong.
const DUMMY_WINDOW_MS = 2 * 60 * 1000;

// Dummy events still need a plausible player/team to attach to. Normally that's
// topViewStore.precomputedPlayerList, but event data is meant to be its own thing,
// independent of position data (a future action-spotting plugin would run on the raw
// video, not on tracking output) -- see EventDataMenu.vue, which no longer gates on
// hasPositionData. Two 11-a-side rosters on the same team_id scale position data uses
// (3/4 == red/blue, see visualizationStore.teamColorMapping) keep things looking sane
// when Events is used standalone, without any position data loaded.
const FALLBACK_TEAM_IDS = [3, 4];
function fallbackPlayerList() {
  const players = [];
  for (const teamId of FALLBACK_TEAM_IDS) {
    for (let n = 1; n <= 11; n++) {
      players.push({ playerId: `${teamId}_${n}`, teamId });
    }
  }
  return players;
}

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

// Builds a stable mock event list for a given event data set -- seeded off that set's own id
// (rather than the video id, as an earlier version of this did) so switching between several
// uploaded/selected sets in the same video actually looks different, and so events stay put
// across reloads/re-renders for the same selection. See eventsStore.eventsData for the caller.
function _dummyEventsForSeed(seedStr, players, windowEnd) {
  if (!players.length) return [];

  const rand = mulberry32(hashSeed(String(seedStr)));
  const count = 10 + Math.floor(rand() * 8); // 10-17 events
  const events = [];
  for (let i = 0; i < count; i++) {
    const type = EVENT_TYPE_IDS[Math.floor(rand() * EVENT_TYPE_IDS.length)];
    const player = players[Math.floor(rand() * players.length)];
    // VAEP-style action value -- goals swing a match's win probability far more than
    // routine actions, so they get a visibly higher (and much wider) value range.
    const vaep =
      type === "goal"
        ? Math.round((0.1 + rand() * 0.5) * 1000) / 1000 // 0.100 - 0.600
        : Math.round((0.001 + rand() * 0.079) * 1000) / 1000; // 0.001 - 0.080
    // xG (pre-shot probability the chance results in a goal) only makes sense for shots
    // -- goals and shots that didn't score, but not e.g. fouls or cards. xSuccess
    // (probability the action was executed as intended) and xImpact (context-weighted
    // match-outcome value, see xImpact_Revision_D2.pdf) apply to every event type. None
    // of this is meant to be realistic, just representative placeholders for the real
    // pipeline down the line.
    const isShot = type === "goal" || type === "shot_on_target" || type === "shot_off_target";
    const xg = isShot ? Math.round((0.05 + rand() * 0.85) * 100) / 100 : null; // 0.05 - 0.90
    const xsuccess = Math.round((0.5 + rand() * 0.5) * 100) / 100; // 0.50 - 1.00
    const ximpact =
      type === "goal"
        ? Math.round((-0.05 + rand() * 0.7) * 1000) / 1000 // -0.050 - 0.650
        : Math.round((-0.02 + rand() * 0.07) * 1000) / 1000; // -0.020 - 0.050
    events.push({
      id: `${seedStr}-${i}`,
      event_type: type,
      timestamp: Math.round(rand() * windowEnd),
      player_id: player.playerId,
      team_id: player.teamId,
      vaep,
      xg,
      xsuccess,
      ximpact,
      x: Math.round(rand() * 100) / 100,
      y: Math.round(rand() * 100) / 100,
    });
  }
  events.sort((a, b) => a.timestamp - b.timestamp);
  return events;
}

export const useEventsStore = defineStore(
  "events",
  () => {
    const topViewStore = useTopViewStore();
    const playerStore = usePlayerStore();
    const positionDataStore = usePositionDataStore();

    // Mirrors positionDataStore.positionDataList -- the "manually uploaded" event data sets a
    // user has added via ModalEventDataUpload (EventDataMenu.vue's "Upload event data"), picked
    // from later via ModalEventDataSelect. No backend endpoint exists yet (see uploadEventDataSet
    // below), so this is a plain client-side list rather than something fetched from the API.
    const eventDataSets = ref([]);
    // Which of eventDataSets (if any) is currently loaded -- drives eventsData below, same role
    // positionDataStore.positionDataId plays for position data. null until the user has actually
    // picked one via ModalEventDataSelect.
    const selectedEventDataSetId = ref(null);
    const hasEventData = computed(() => selectedEventDataSetId.value != null);

    // Stand-in for a future PluginRunResult (type=TYPE_EVENTS) payload: a flat list of
    // { id, event_type, timestamp, player_id, team_id, VAEP, x, y }. Timestamps are ms
    // on the same clock as playerStore.currentTime / topViewStore.sortedFrameKeys, and
    // player_id/team_id resolve through topViewStore.metaDataTopView exactly like position
    // and KPI data do -- so once a real detector lands, only _dummyEventsForSeed() below
    // needs replacing with an actual fetch (triggered from selectEventDataSet).
    const eventsData = computed(() => {
      if (!selectedEventDataSetId.value) return [];
      const players = topViewStore.precomputedPlayerList.length
        ? topViewStore.precomputedPlayerList
        : fallbackPlayerList();
      // The video's length is the window: the events are spread across all of it, and none of
      // them can land past its end, where there would be no frame to review them on. Position
      // data's own span stands in only while the duration is unknown -- and the fixed fallback
      // only when neither is there.
      const keys = topViewStore.sortedFrameKeys;
      const windowEnd =
        playerStore.videoDuration || (keys.length ? keys[keys.length - 1] : DUMMY_WINDOW_MS);
      return _dummyEventsForSeed(selectedEventDataSetId.value, players, windowEnd);
    });

    const selectedEventTypes = ref([...EVENT_TYPE_IDS]);
    // null = not yet initialized -- TabWindowEvents seeds this with "everyone selected" on
    // first use, same pattern as visualizationStore.kpiSelectedPlayerIds.
    const selectedPlayerIds = ref(null);

    // Which KPI columns TabWindowEvents' display settings menu has switched on -- all by
    // default. Unlike selectedEventTypes, allowed to go empty (hiding a column is just a
    // display preference, not a filter that could leave the table showing nothing).
    const visibleKpiColumns = ref([...KPI_COLUMN_IDS]);

    // Column the table is sorted by -- null means the natural (chronological) order
    // eventsData/filteredEvents already come in. Only Time ("timestamp") and the KPI
    // columns are sortable (see EventsList.vue); Event/Player/Team aren't.
    const sortColumn = ref(null);
    const sortDir = ref("asc");

    // No real backend endpoint exists yet for event data (see eventDataSets above) -- adds a
    // client-side-only entry instead of an actual API upload, same "dummy for now" approach the
    // rest of this store already takes for eventsData itself. Mirrors
    // positionDataStore.uploadPositionData's role, minus the actual network round-trip. Doesn't
    // auto-select the new entry -- picking it is still a separate step via ModalEventDataSelect
    // (mirrors positionDataStore.uploadPositionData, which likewise only refreshes the list).
    function uploadEventDataSet({ title, format }) {
      const id = `manual-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
      eventDataSets.value = [
        ...eventDataSets.value,
        { id, title: title?.trim() || id, format: format ?? null, createdAt: new Date().toISOString() },
      ];
      return id;
    }

    function deleteEventDataSet(id) {
      eventDataSets.value = eventDataSets.value.filter((d) => d.id !== id);
      if (selectedEventDataSetId.value === id) {
        selectedEventDataSetId.value = null;
      }
    }

    // Clears just the current selection, leaving eventDataSets (the uploaded/demo entries
    // themselves) intact -- unlike resetEventData below, which also wipes that list. Used by
    // TabWindowEvents' "Create new event data" menu item so the card falls back to
    // EventDataMenu with everything already uploaded/generated for this video still there to
    // pick from via Select, instead of losing it.
    function deselectEventData() {
      selectedEventDataSetId.value = null;
      selectedPlayerIds.value = null;
      pinnedEventId.value = null;
    }

    // Called from AnalysisView.vue's onBeforeUnmount (mirrors visualizationStore.resetKpiData /
    // calibrationAssetStore.resetCalibrationAsset there) -- event data sets are uploaded/
    // generated per video, not a reusable global list, so despite eventDataSets/
    // selectedEventDataSetId being sessionStorage-persisted (survives a reload of *this* video),
    // they still need clearing on navigating away, or the next video opened in the same tab
    // would inherit this one's dummy/uploaded events instead of a clean "no event data yet"
    // state. Leaves display preferences (selectedEventTypes, visibleKpiColumns, sortColumn/Dir)
    // alone -- those aren't video-bound data, same as resetKpiData leaves kpiGroupMode etc.
    function resetEventData() {
      eventDataSets.value = [];
      deselectEventData();
    }

    // Backdoor for as long as there's neither a real detector nor a reason to make someone
    // fill out the upload form just to see mocked events (see ModalEventDataSelect.vue's empty
    // state, the only place this is called from) -- reuses the same demo entry on repeat clicks
    // instead of piling up a new "Demo events" row in eventDataSets every time.
    function loadDemoEventData() {
      let demo = eventDataSets.value.find((d) => d.format === "demo");
      if (!demo) {
        const id = `demo-${Date.now()}`;
        demo = { id, title: "Demo events", format: "demo", createdAt: new Date().toISOString() };
        eventDataSets.value = [...eventDataSets.value, demo];
      }
      selectEventDataSet(demo.id);
    }

    function selectEventDataSet(id) {
      selectedEventDataSetId.value = id;
      // Seed the shared time-range selector (VisualizationTimeSelector/EventsTimeline, driven
      // by positionDataStore.selectedTimeRange) from this data set's own event span when no
      // position data has set a real range yet (still at the {0, 0} default -- see
      // position_data.js) -- otherwise the timeline has nothing to scale to when Events is used
      // standalone, without any position data loaded. Leaves an already-meaningful range (from
      // position data) untouched.
      const range = positionDataStore.selectedTimeRange;
      if (range.start === 0 && range.end === 0) {
        // The video's length when it is known: a timeline that ends with the video is what
        // every timecode on it can actually be checked against. Only without a duration does
        // the event span have to stand in for it.
        const timestamps = eventsData.value.map((e) => e.timestamp);
        const end =
          playerStore.videoDuration ||
          (timestamps.length ? Math.max(...timestamps) + 5000 : DUMMY_WINDOW_MS);
        positionDataStore.selectedTimeRange = { start: 0, end };
      }
    }

    const filteredEvents = computed(() => {
      const typeSet = new Set(selectedEventTypes.value);
      const playerFilter = selectedPlayerIds.value;
      return eventsData.value.filter((e) => {
        if (!typeSet.has(e.event_type)) return false;
        if (playerFilter && !playerFilter.includes(e.player_id)) return false;
        return true;
      });
    });

    // Index (within filteredEvents, i.e. chronological order) of the next event at/after
    // the current playback time -- drives the timeline's "you are here" framing. Kept
    // chronological (not reordered by sortColumn) since it's about playback position, not
    // table display order; nextEventId below is the table-order-independent form of this
    // EventsList.vue actually needs for its "up next" row highlight/auto-scroll.
    const nextEventIndex = computed(() => {
      const t = playerStore.currentTime;
      return filteredEvents.value.findIndex((e) => e.timestamp >= t);
    });

    // Set by jumpToEvent (click in EventsList.vue or on an EventsTimeline.vue marker) and
    // takes over nextEventId below while it's set. Needed because jumpToEvent seeks to a
    // few seconds *before* the clicked event (see leadMs) so playback shows its build-up --
    // during that lead-in, currentTime sits behind the clicked event's own timestamp, and if
    // some *other* event happens to fall inside that gap, the plain time-based lookup above
    // would highlight that other (chronologically earlier) event instead of the one actually
    // clicked. Cleared by the watcher below once playback actually reaches the next event
    // after the clicked one -- not just re-derived on the fly -- so rewinding back into the
    // same lead-in window afterwards doesn't resurrect a highlight that's already been
    // superseded.
    const pinnedEventId = ref(null);
    watch([() => playerStore.currentTime, filteredEvents], ([t, events]) => {
      const pinnedId = pinnedEventId.value;
      if (pinnedId == null) return;
      const idx = events.findIndex((e) => e.id === pinnedId);
      if (idx < 0) {
        // Pinned event dropped out of the filtered list (e.g. its type got deselected) --
        // nothing sensible left to keep it pinned to.
        pinnedEventId.value = null;
        return;
      }
      const eventAfterPinned = events[idx + 1];
      if (eventAfterPinned && t >= eventAfterPinned.timestamp) {
        pinnedEventId.value = null;
      }
    });

    const nextEventId = computed(() => {
      if (pinnedEventId.value != null) return pinnedEventId.value;
      const idx = nextEventIndex.value;
      return idx >= 0 ? filteredEvents.value[idx]?.id ?? null : null;
    });

    // The list actually rendered in EventsList.vue -- filteredEvents (chronological)
    // unless the user's clicked a sortable column header into a non-default order. Nulls
    // (e.g. xg on non-shot events) always sort last regardless of direction, rather than
    // clustering at whichever end the numeric comparison would otherwise put them.
    const sortedEvents = computed(() => {
      if (!sortColumn.value) return filteredEvents.value;
      const col = sortColumn.value;
      const dir = sortDir.value === "asc" ? 1 : -1;
      return [...filteredEvents.value].sort((a, b) => {
        const av = a[col];
        const bv = b[col];
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return (av - bv) * dir;
      });
    });

    // Cycles asc -> desc -> back to the natural chronological order on a third click of
    // the same header; clicking a different sortable header always starts it at asc.
    function setSort(column) {
      if (sortColumn.value !== column) {
        sortColumn.value = column;
        sortDir.value = "asc";
      } else if (sortDir.value === "asc") {
        sortDir.value = "desc";
      } else {
        sortColumn.value = null;
        sortDir.value = "asc";
      }
    }

    function toggleEventType(type) {
      if (selectedEventTypes.value.includes(type)) {
        if (selectedEventTypes.value.length > 1) {
          selectedEventTypes.value = selectedEventTypes.value.filter((t) => t !== type);
        }
      } else {
        selectedEventTypes.value = [...selectedEventTypes.value, type];
      }
    }

    function toggleKpiColumn(id) {
      if (visibleKpiColumns.value.includes(id)) {
        visibleKpiColumns.value = visibleKpiColumns.value.filter((c) => c !== id);
      } else {
        visibleKpiColumns.value = [...visibleKpiColumns.value, id];
      }
    }

    function jumpToEvent(event, leadMs = 3000) {
      pinnedEventId.value = event.id;
      playerStore.setTargetTime(Math.max(0, event.timestamp - leadMs));
    }

    // Releases the pin set by jumpToEvent above, immediately (regardless of direction) --
    // for a manual seek that isn't itself a click on some other event (dragging
    // EventsTimeline.vue's current-time line, or clicking a blank spot on its track). Those
    // are an explicit "take me somewhere else" from the user, unlike plain forward playback
    // continuing after a click, so the fixed highlight shouldn't ride along with them the
    // way it rides along through the watcher above -- call this alongside (not instead of)
    // the player store's own setTargetTime for that seek.
    function clearPinnedEvent() {
      pinnedEventId.value = null;
    }

    return {
      eventDataSets,
      selectedEventDataSetId,
      hasEventData,
      eventsData,
      selectedEventTypes,
      selectedPlayerIds,
      visibleKpiColumns,
      sortColumn,
      sortDir,
      filteredEvents,
      sortedEvents,
      nextEventIndex,
      nextEventId,
      uploadEventDataSet,
      deleteEventDataSet,
      selectEventDataSet,
      loadDemoEventData,
      deselectEventData,
      resetEventData,
      toggleEventType,
      toggleKpiColumn,
      setSort,
      jumpToEvent,
      clearPinnedEvent,
    };
  },
  {
    persist: {
      pick: [
        "eventDataSets",
        "selectedEventDataSetId",
        "selectedEventTypes",
        "selectedPlayerIds",
        "visibleKpiColumns",
        "sortColumn",
        "sortDir",
      ],
      storage: sessionStorage,
    },
  }
);
