import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useBboxesStore } from "@/stores/bboxes";
import { usePlayerStore } from "@/stores/player";
import { useEventsStore } from "@/stores/events";
import { BBOX_SOURCE_RUN_IDX } from "@/stores/top_view";

// Named annotation_tool to keep it clearly apart from annotation.js /
// annotation_category.js / annotation_shortcut.js / timeline_segment_annotation.js, which all
// belong to the older timeline-segment labelling feature and share nothing with this.
//
// This store holds the review session for correcting a plugin run's output: which run is being
// reviewed, which frames were picked for review, and the per-frame draft of corrected boxes.
//
// Geometry corrections deliberately never leave this store on their own -- see exportDraft.

export const FRAME_COUNT_OPTIONS = [20, 50, 100];

// Frames are sampled no denser than this. Consecutive video frames are near-identical, so a
// tighter spacing would just cost the reviewer time without adding training signal.
const MIN_FRAME_SPACING_MS = 1000;

// Largest key <= target, over an ascending numeric array. Same lookup VideoPlayer.vue uses to
// map the playhead onto a bbox frame key.
function floorKey(keys, target) {
  if (!keys.length) return undefined;
  if (target <= keys[0]) return keys[0];
  if (target >= keys[keys.length - 1]) return keys[keys.length - 1];
  let lo = 0;
  let hi = keys.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >>> 1;
    if (keys[mid] <= target) lo = mid;
    else hi = mid - 1;
  }
  return keys[lo];
}

export const useAnnotationToolStore = defineStore(
  "annotationTool",
  () => {
    const bboxesStore = useBboxesStore();
    const playerStore = usePlayerStore();
    const eventsStore = useEventsStore();

    // null = nothing picked yet. The view starts in its full layout either way (there is no
    // start menu in front of it), it just has nothing to correct until a target is chosen.
    const activeToolId = ref(null);

    // Whether the run under review is a ball-tracking run rather than a player run. Tracking
    // already separates the two (see useObjectTrackerPlayerRuns / bboxBallPluginRunId), and
    // the distinction has to survive here because the two live in different fields of
    // bboxesStore -- and edits have to be routed back to the run they came from.
    const reviewBallRun = ref(false);
    const frameCount = ref(50);

    const currentFrameIdx = ref(0);
    const selectedBoxIdx = ref(null);

    // frameKey -> full corrected box list for that frame. A frame only gets an entry once it
    // has actually been touched, so `drafts` doubles as the "what did the reviewer change"
    // record that the export reads.
    const drafts = ref({});
    // frameKey -> the box list as the plugin originally produced it, snapshotted the first
    // time that frame is edited. Needed for the before/after pairs a fine-tuning run wants.
    const originals = ref({});

    // Identity corrections (player_id/team_id) waiting to be submitted, each keeping the scope
    // it was made with. Nothing in this view writes to the backend on its own: a review session
    // stays entirely local until it is submitted, so the user always knows what has and hasn't
    // been changed -- and once corrections can be stored as their own dataset (see exportDraft),
    // submitting becomes one request for the whole package instead of one per box.
    //
    // The scope is kept as intent rather than as its result: applied locally it can only reach
    // the sampled review frames, while on submit "all boxes of this player" has to mean the
    // whole run, which only the backend can do.
    const identityEdits = ref([]);

    // The run whose boxes are on screen. Correcting boxes needs nothing but the boxes over
    // the video, so AnnotationView loads a run straight through
    // topViewStore.loadBboxDataForReview instead of going through the position-data picker --
    // the pitch view, and with it the calibration asset, is not part of this job.
    const effectiveRunId = computed(
      () => (reviewBallRun.value ? bboxesStore.bboxBallPluginRunId : bboxesStore.bboxPluginRunId) || 0
    );

    const bboxFrameKeys = computed(() =>
      Object.keys(bboxesStore.bboxDataInterpolated)
        .map(Number)
        .sort((a, b) => a - b)
    );

    // N evenly spaced review frames, each snapped onto a frame key that actually carries
    // boxes. Snapping matters: bboxDataInterpolated is a plain {frameTimeMs: [...]} object, so
    // an interpolated timestamp that happens to fall between two keys yields no boxes at all.
    const frameKeys = computed(() => {
      const keys = bboxFrameKeys.value;
      if (!keys.length) return [];

      const duration = playerStore.videoDuration || keys[keys.length - 1];
      const maxBySpacing = Math.max(1, Math.floor(duration / MIN_FRAME_SPACING_MS));
      const count = Math.min(frameCount.value, maxBySpacing, keys.length);

      const picked = [];
      for (let i = 0; i < count; i++) {
        // Half-step inset so the first pick isn't frame 0 and the last isn't the very end,
        // both of which tend to be black frames or half-loaded segments.
        const target = ((i + 0.5) * duration) / count;
        const key = floorKey(keys, target);
        if (key !== undefined && !picked.includes(key)) picked.push(key);
      }
      return picked;
    });

    const currentFrameKey = computed(() => frameKeys.value[currentFrameIdx.value]);

    const touchedFrames = computed(() => new Set(Object.keys(drafts.value).map(Number)));

    // Declared before the event section below, so it reads the refs rather than
    // hasEventDraft -- a computed only runs when it is read, by which point both exist.
    const hasDraft = computed(
      () =>
        Object.keys(drafts.value).length > 0 ||
        identityEdits.value.length > 0 ||
        Object.keys(eventDrafts.value).length > 0 ||
        deletedEventIds.value.length > 0 ||
        addedEvents.value.length > 0
    );

    // The boxes to render for a frame: the draft if one exists, otherwise the plugin's own
    // output. Read-only for callers -- every mutation below replaces arrays rather than
    // editing them in place, so what comes back here can be handed straight to a template.
    function boxesForFrame(frameKey) {
      if (frameKey === undefined) return [];
      if (drafts.value[frameKey]) return drafts.value[frameKey];
      return bboxesStore.bboxDataInterpolated[frameKey] || [];
    }

    // Promotes a frame to "being edited": snapshots the original and copies the boxes into a
    // draft. Every mutation below goes through this first.
    function ensureDraft(frameKey) {
      if (frameKey === undefined) return null;
      if (!drafts.value[frameKey]) {
        const source = bboxesStore.bboxDataInterpolated[frameKey] || [];
        originals.value = { ...originals.value, [frameKey]: source.map((b) => [...b]) };
        drafts.value = { ...drafts.value, [frameKey]: source.map((b) => [...b]) };
      }
      return drafts.value[frameKey];
    }

    // rect is {x, y, width, height}, all relative 0..1 in video space -- indices 5..8 of the
    // box array (see export.js's allPositionDataAttributes for the full index map).
    function updateBoxGeometry(frameKey, boxIdx, rect) {
      const boxes = ensureDraft(frameKey);
      if (!boxes || !boxes[boxIdx]) return;
      const box = [...boxes[boxIdx]];
      box[5] = rect.x;
      box[6] = rect.y;
      box[7] = rect.width;
      box[8] = rect.height;
      const next = [...boxes];
      next[boxIdx] = box;
      drafts.value = { ...drafts.value, [frameKey]: next };
    }

    function addBox(frameKey, rect, { playerId = null, teamId = -1 } = {}) {
      const boxes = ensureDraft(frameKey) || [];

      // A fresh id that doesn't collide with anything already in this frame. Ids are per-track
      // across the whole video, but a duplicate *within* one frame is what actually breaks the
      // overlay and the id validation, so that's what we guard against.
      let newId = playerId;
      if (newId === null) {
        const used = new Set(boxes.map((b) => Number(b[0])));
        newId = 1;
        while (used.has(newId)) newId++;
      }

      const box = new Array(BBOX_SOURCE_RUN_IDX + 1).fill(0);
      box[0] = newId;
      box[1] = teamId;
      box[2] = 1; // game_section
      box[3] = 0; // pitch x -- only meaningful after a homography, left at 0 for a manual box
      box[4] = 0; // pitch y
      box[5] = rect.x;
      box[6] = rect.y;
      box[7] = rect.width;
      box[8] = rect.height;
      box[9] = 1; // det_score: a human-drawn box is by definition certain
      box[BBOX_SOURCE_RUN_IDX] = effectiveRunId.value;

      const next = [...boxes, box];
      drafts.value = { ...drafts.value, [frameKey]: next };
      selectedBoxIdx.value = next.length - 1;
      return next.length - 1;
    }

    // Writes a player/team correction into the draft and remembers it for the submit. `scope`
    // is "bbox" (this one box), "allPlayer" or "allTeam" -- locally that reaches every drafted
    // review frame, which is all the user can see anyway.
    function applyIdentity(frameKey, boxIdx, { newPlayerId, newTeamId, scope = "bbox" }) {
      const boxes = ensureDraft(frameKey);
      const target = boxes?.[boxIdx];
      if (!target) return;

      const fromPlayerId = Number(target[0]);
      const fromTeamId = Number(target[1]);
      const toPlayerId = newPlayerId === null || newPlayerId === undefined
        ? fromPlayerId
        : Number(newPlayerId);
      const toTeamId = newTeamId === null || newTeamId === undefined ? fromTeamId : Number(newTeamId);

      const matches = (box, isTarget) => {
        if (scope === "allPlayer") return Number(box[0]) === fromPlayerId;
        if (scope === "allTeam") return Number(box[1]) === fromTeamId;
        return isTarget;
      };

      const rewrite = (box) => {
        const next = [...box];
        if (scope !== "allTeam") next[0] = toPlayerId;
        next[1] = toTeamId;
        return next;
      };

      if (scope === "bbox") {
        const next = [...boxes];
        next[boxIdx] = rewrite(target);
        drafts.value = { ...drafts.value, [frameKey]: next };
      } else {
        // Every frame already drafted is rewritten; the rest of the run is the backend's job on
        // submit. Frames the user never touched are deliberately left alone -- drafting all of
        // them here would flood the export with frames that carry no real correction.
        const nextDrafts = { ...drafts.value };
        for (const key of Object.keys(nextDrafts)) {
          nextDrafts[key] = nextDrafts[key].map((box) =>
            matches(box, false) ? rewrite(box) : box
          );
        }
        const current = ensureDraft(frameKey);
        nextDrafts[frameKey] = current.map((box, idx) =>
          matches(box, idx === boxIdx) ? rewrite(box) : box
        );
        drafts.value = nextDrafts;
      }

      identityEdits.value = [
        ...identityEdits.value,
        {
          frameKey,
          bboxId: `${frameKey}-${fromPlayerId}`,
          playerId: fromPlayerId,
          teamId: fromTeamId,
          newPlayerId: toPlayerId,
          newTeamId: toTeamId,
          scope,
        },
      ];
    }

    function removeBox(frameKey, boxIdx) {
      const boxes = ensureDraft(frameKey);
      if (!boxes || !boxes[boxIdx]) return;
      const next = boxes.filter((_, i) => i !== boxIdx);
      drafts.value = { ...drafts.value, [frameKey]: next };
      selectedBoxIdx.value = null;
    }

    function discardDraft(frameKey) {
      const nextDrafts = { ...drafts.value };
      const nextOriginals = { ...originals.value };
      delete nextDrafts[frameKey];
      delete nextOriginals[frameKey];
      drafts.value = nextDrafts;
      originals.value = nextOriginals;
      identityEdits.value = identityEdits.value.filter((edit) => edit.frameKey !== frameKey);
      selectedBoxIdx.value = null;
    }

    function discardAll() {
      drafts.value = {};
      originals.value = {};
      identityEdits.value = [];
      selectedBoxIdx.value = null;
    }

    // --- event timing review --------------------------------------------------------------
    //
    // Same draft-first shape as the bbox half above: the detector's own output (today
    // eventsStore.eventsData, a client-side dummy -- see events.js) is never touched. Every
    // correction lands here and only leaves the browser through exportDraft.
    //
    // Three kinds of correction, kept apart because they export differently: an edited event
    // has a before/after pair, an added one has no "before" at all, and a deleted one has no
    // "after". Deleting is a tombstone rather than a removal so it stays undoable for the
    // whole session (see the list's restore).

    const selectedEventId = ref(null);
    const eventDrafts = ref({}); // event id -> the corrected event
    const eventOriginals = ref({}); // event id -> the event as the detector produced it
    const deletedEventIds = ref([]);
    const addedEvents = ref([]);

    // Every event of the session with its review state attached, chronological. `edited`,
    // `added`, `deleted` and `originalTimestamp` are review metadata, not part of the event
    // payload -- the timeline uses them to mark a moved event and to draw a ghost marker
    // where it originally sat, and exportDraft strips them again.
    const reviewEvents = computed(() => {
      const deleted = new Set(deletedEventIds.value);
      const rows = [
        ...eventsStore.eventsData.map((event) => {
          const draft = eventDrafts.value[event.id];
          return {
            ...(draft ?? event),
            edited: !!draft,
            added: false,
            deleted: deleted.has(event.id),
            originalTimestamp: event.timestamp,
          };
        }),
        ...addedEvents.value.map((event) => ({
          ...event,
          edited: false,
          added: true,
          deleted: deleted.has(event.id),
          originalTimestamp: null,
        })),
      ];
      return rows.sort((a, b) => a.timestamp - b.timestamp);
    });

    // What the timeline draws: a deleted event still shows in the list (struck through, so it
    // can be restored) but must not keep sitting on the timeline as if it were still there.
    const visibleReviewEvents = computed(() => reviewEvents.value.filter((e) => !e.deleted));

    const selectedEvent = computed(
      () => reviewEvents.value.find((e) => e.id === selectedEventId.value) ?? null
    );

    const hasEventDraft = computed(
      () =>
        Object.keys(eventDrafts.value).length > 0 ||
        deletedEventIds.value.length > 0 ||
        addedEvents.value.length > 0
    );

    // `seek` puts the playhead exactly on the event -- not a few seconds ahead of it the way
    // eventsStore.jumpToEvent does for watching. Correcting a timestamp means looking at the
    // frame it currently points at, so landing anywhere else would hide the very thing being
    // judged. Off by default: dragging a marker selects it too, and there the drag itself is
    // already moving the playhead.
    function selectEvent(id, { seek = false } = {}) {
      selectedEventId.value = id;
      if (!seek) return;
      const event = reviewEvents.value.find((e) => e.id === id);
      if (event) playerStore.setTargetTime(event.timestamp);
    }

    // Same role ensureDraft plays for a frame: promotes a detected event to "being edited" by
    // snapshotting the original alongside the copy that gets written to.
    function ensureEventDraft(id) {
      if (eventDrafts.value[id]) return eventDrafts.value[id];
      const source = eventsStore.eventsData.find((e) => e.id === id);
      if (!source) return null;
      eventOriginals.value = { ...eventOriginals.value, [id]: { ...source } };
      eventDrafts.value = { ...eventDrafts.value, [id]: { ...source } };
      return eventDrafts.value[id];
    }

    // The one write path for every correction the panel offers -- event type, player/team and
    // timestamp all go through here, so each of them equally turns the event into a draft.
    function updateEvent(id, patch) {
      const next = { ...patch };
      if (next.timestamp !== undefined) next.timestamp = Math.max(0, Math.round(next.timestamp));

      if (addedEvents.value.some((e) => e.id === id)) {
        // An added event has no original to diff against -- it is edited in place.
        addedEvents.value = addedEvents.value.map((e) => (e.id === id ? { ...e, ...next } : e));
        return;
      }
      if (!ensureEventDraft(id)) return;
      eventDrafts.value = {
        ...eventDrafts.value,
        [id]: { ...eventDrafts.value[id], ...next },
      };
    }

    // An event the detector missed. Deliberately as unassigned as it can be: the panel opens
    // on it right away, and guessing a type/player here would only invite leaving a wrong one
    // in. team_id -1 is the same "unknown" the bbox side uses (see addBox).
    function addEvent({ timestamp = 0, eventType = null, playerId = null, teamId = -1 } = {}) {
      const id = `added-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
      addedEvents.value = [
        ...addedEvents.value,
        {
          id,
          event_type: eventType,
          timestamp: Math.max(0, Math.round(timestamp)),
          player_id: playerId,
          team_id: teamId,
          vaep: null,
          xg: null,
          xsuccess: null,
          ximpact: null,
          x: null,
          y: null,
        },
      ];
      selectedEventId.value = id;
      return id;
    }

    function deleteEvent(id) {
      if (addedEvents.value.some((e) => e.id === id)) {
        // Never existed outside this session, so there is nothing to record a deletion of.
        addedEvents.value = addedEvents.value.filter((e) => e.id !== id);
        if (selectedEventId.value === id) selectedEventId.value = null;
        return;
      }
      if (!deletedEventIds.value.includes(id)) {
        deletedEventIds.value = [...deletedEventIds.value, id];
      }
    }

    function restoreEvent(id) {
      deletedEventIds.value = deletedEventIds.value.filter((e) => e !== id);
    }

    // Back to whatever the detector said about this one event -- its draft, and a deletion of
    // it, both go. An added event has no such state to fall back to, so it is dropped.
    function discardEventDraft(id) {
      const nextDrafts = { ...eventDrafts.value };
      const nextOriginals = { ...eventOriginals.value };
      delete nextDrafts[id];
      delete nextOriginals[id];
      eventDrafts.value = nextDrafts;
      eventOriginals.value = nextOriginals;
      restoreEvent(id);
      if (addedEvents.value.some((e) => e.id === id)) deleteEvent(id);
    }

    function discardAllEvents() {
      eventDrafts.value = {};
      eventOriginals.value = {};
      deletedEventIds.value = [];
      addedEvents.value = [];
      selectedEventId.value = null;
    }

    function setFrameIdx(idx) {
      const max = frameKeys.value.length - 1;
      currentFrameIdx.value = Math.min(Math.max(idx, 0), Math.max(max, 0));
      selectedBoxIdx.value = null;
    }

    // Builds the training-data package. Deliberately a plain object handed back to the caller
    // rather than anything that touches the network.
    //
    // NOTE: this is where AP6 will eventually hook in. It is NOT persisted server-side today,
    // on purpose: the only endpoint that can write box geometry is position_data/bboxes/replace,
    // and that overwrites the tracker run's stored output in place -- destroying exactly the
    // original-vs-corrected pair a fine-tuning run needs. Until there's an endpoint that stores
    // corrections as their own dataset, the package is handed to the user as a file.
    function exportDraft() {
      const video = playerStore.video || {};
      const frames = Object.keys(drafts.value)
        .map(Number)
        .sort((a, b) => a - b)
        .map((frameKey) => ({
          frame_time_ms: frameKey,
          original_boxes: originals.value[frameKey] ?? [],
          corrected_boxes: drafts.value[frameKey],
        }));

      // Read straight off the refs rather than off reviewEvents: those carry the review
      // metadata (edited/added/deleted/originalTimestamp) the timeline needs for display,
      // which has no business in an exported event.
      const editedEvents = Object.keys(eventDrafts.value)
        .filter((id) => !deletedEventIds.value.includes(id))
        .map((id) => ({
          id,
          original_event: eventOriginals.value[id] ?? null,
          corrected_event: eventDrafts.value[id],
        }));

      return {
        format_version: 1,
        identity_edits: identityEdits.value,
        // Empty unless the event tool was used -- kept in the same package on purpose, a
        // review session is one submission regardless of which tools it went through.
        events: {
          event_data_set_id: eventsStore.selectedEventDataSetId,
          edited: editedEvents,
          added: addedEvents.value,
          deleted: deletedEventIds.value.map((id) => ({
            id,
            original_event:
              eventOriginals.value[id] ??
              eventsStore.eventsData.find((event) => event.id === id) ??
              null,
          })),
        },
        created: new Date().toISOString(),
        video: {
          id: playerStore.videoId,
          name: playerStore.videoName,
          fps: playerStore.videoFPS,
          duration_ms: playerStore.videoDuration,
          width: video.width ?? null,
          height: video.height ?? null,
          sport: video.sport ?? null,
        },
        plugin_run: {
          id: effectiveRunId.value,
          tool: activeToolId.value,
        },
        // Documents the array layout so the file stands on its own, without needing the
        // frontend source to be readable alongside it.
        box_layout: [
          "player_id",
          "team_id",
          "game_section",
          "pitch_x",
          "pitch_y",
          "bbox_left",
          "bbox_top",
          "bbox_width",
          "bbox_height",
          "det_score",
          "source_plugin_run_id",
        ],
        coordinate_space: "bbox_* are relative to the video frame, 0..1",
        frames,
      };
    }

    // Everything a review session consists of, dropped in one go: the drafts, the position in
    // the frame strip, and what was picked to correct. Called when AnnotationView unmounts --
    // leaving the tool ends the session, so coming back starts at "select something" rather
    // than silently resuming a target the user picked minutes ago on another route.
    function clearSession() {
      discardAll();
      discardAllEvents();
      currentFrameIdx.value = 0;
      activeToolId.value = null;
      reviewBallRun.value = false;
    }

    return {
      activeToolId,
      reviewBallRun,
      effectiveRunId,
      frameCount,
      frameKeys,
      currentFrameIdx,
      currentFrameKey,
      selectedBoxIdx,
      drafts,
      originals,
      identityEdits,
      touchedFrames,
      hasDraft,
      boxesForFrame,
      ensureDraft,
      updateBoxGeometry,
      addBox,
      applyIdentity,
      removeBox,
      discardDraft,
      discardAll,
      selectedEventId,
      selectedEvent,
      eventDrafts,
      eventOriginals,
      deletedEventIds,
      addedEvents,
      reviewEvents,
      visibleReviewEvents,
      hasEventDraft,
      selectEvent,
      updateEvent,
      addEvent,
      deleteEvent,
      restoreEvent,
      discardEventDraft,
      discardAllEvents,
      setFrameIdx,
      exportDraft,
      clearSession,
    };
  },
  {
    // What was picked survives a page reload (a reload is not a decision to stop reviewing --
    // AnnotationView reloads straight back into the same session), but not leaving the view:
    // clearSession() drops it on unmount, so navigating away and coming back starts at "select
    // something". Drafts stay out of storage regardless -- a full review session can hold
    // hundreds of boxes, well past what sessionStorage is meant to carry.
    persist: {
      pick: ["frameCount", "activeToolId", "reviewBallRun"],
      storage: sessionStorage,
    },
  }
);
