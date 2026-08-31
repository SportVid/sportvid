import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useBboxesStore } from "@/stores/bboxes";
import { usePlayerStore } from "@/stores/player";
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

    const activeToolId = ref("bbox");
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

    // Always the tracker run that is actually loaded into bboxDataInterpolated -- deliberately
    // not a free choice. Switching runs is more than picking an id: it means re-running
    // transformBBoxToPositionDataTopView and re-applying the ball / team-clustering / reid
    // merges (see ModalPositionDataSelect's confirmSelection). Offering a shortcut for it here
    // would either silently drop those merges or duplicate that whole sequence, so run
    // selection stays where it already lives, in the position-data picker.
    const effectiveRunId = computed(() => bboxesStore.bboxPluginRunId || 0);

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

    const hasDraft = computed(() => Object.keys(drafts.value).length > 0);

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
      selectedBoxIdx.value = null;
    }

    function discardAll() {
      drafts.value = {};
      originals.value = {};
      selectedBoxIdx.value = null;
    }

    // Identity edits (player_id/team_id) go straight to the backend through bboxesStore, so a
    // frame's draft can be holding a stale copy of them afterwards. Re-sync the identity
    // fields from the freshly updated store data while keeping the drafted geometry.
    function syncDraftIdentities(frameKey) {
      const draft = drafts.value[frameKey];
      if (!draft) return;
      const live = bboxesStore.bboxDataInterpolated[frameKey] || [];
      const next = draft.map((box) => {
        const match = live.find((b) => Number(b[0]) === Number(box[0]));
        if (!match) return box;
        const merged = [...box];
        merged[0] = match[0];
        merged[1] = match[1];
        return merged;
      });
      drafts.value = { ...drafts.value, [frameKey]: next };
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

      return {
        format_version: 1,
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

    function clearSession() {
      discardAll();
      currentFrameIdx.value = 0;
    }

    return {
      activeToolId,
      effectiveRunId,
      frameCount,
      frameKeys,
      currentFrameIdx,
      currentFrameKey,
      selectedBoxIdx,
      drafts,
      originals,
      touchedFrames,
      hasDraft,
      boxesForFrame,
      ensureDraft,
      updateBoxGeometry,
      addBox,
      removeBox,
      discardDraft,
      discardAll,
      syncDraftIdentities,
      setFrameIdx,
      exportDraft,
      clearSession,
    };
  },
  {
    // Drafts stay out of storage on purpose -- a full review session can hold hundreds of
    // boxes, well past what sessionStorage is meant to carry.
    persist: {
      pick: ["frameCount", "activeToolId"],
      storage: sessionStorage,
    },
  }
);
