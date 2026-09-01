<template>
  <v-main>
    <v-container fluid class="annotation-container">
      <v-card v-if="isLoading" class="loading-card" elevation="2">
        <div class="spinner"><i class="mdi mdi-loading mdi-spin" /></div>
        <div class="loading-text">{{ $t("loading_screen") }}</div>
      </v-card>

      <v-card v-else class="annotation-card" elevation="2">
        <!-- Header: which video, and what is being corrected on it. No "back to analysis"
             here -- the app bar carries that for this route, and one exit is enough. -->
        <div class="annotation-header">
          <span class="header-video-name">{{ playerStore.videoName }}</span>

          <v-spacer />

          <!-- Tool and its input are one choice: a tool without something to correct isn't a
               meaningful selection, so this menu picks both, and the toolbox on the left only
               shows what the picked one can do. -->
          <v-menu location="bottom start">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                variant="tonal"
                color="primary"
                height="36"
                class="ml-4 text-none target-btn"
                append-icon="mdi-menu-down"
              >
                <v-icon v-if="activeTool" start size="20">{{ activeTool.icon }}</v-icon>
                {{
                  activeTool ? $t(activeTool.labelKey) : $t("annotation_tool.target.select_tool")
                }}
                <span v-if="activeTargetLabel" class="header-target">
                  &middot; {{ activeTargetLabel }}
                </span>
              </v-btn>
            </template>

            <v-list density="compact" width="340" class="py-0">
              <template v-for="(group, idx) in targetGroups" :key="group.toolId">
                <v-divider v-if="idx > 0" />

                <v-list-subheader class="target-group-title">
                  <v-icon size="14" class="mr-2">{{ group.icon }}</v-icon>
                  {{ $t(group.labelKey) }}
                  <v-chip v-if="!group.ready" size="x-small" variant="tonal" class="ml-2">
                    {{ $t("annotation_tool.preview.badge") }}
                  </v-chip>
                </v-list-subheader>

                <v-list-item
                  v-for="item in group.items"
                  :key="item.id"
                  :active="isActiveTarget(group.toolId, item)"
                  @click="selectTarget(group.toolId, item)"
                >
                  <!-- Icon inline rather than in #prepend: that slot reserves a fixed column
                       width, which leaves a gap the group titles above don't have. -->
                  <v-list-item-title class="text-body-2 d-flex align-center">
                    <v-icon v-if="item.icon" size="16" class="mr-2">{{ item.icon }}</v-icon>
                    {{ item.name }}
                  </v-list-item-title>
                  <template #append>
                    <v-icon v-if="isActiveTarget(group.toolId, item)" size="16">mdi-check</v-icon>
                  </template>
                </v-list-item>

                <v-list-item v-if="!group.items.length" disabled>
                  <v-list-item-title class="text-caption text-medium-emphasis">
                    {{ $t("annotation_tool.target.no_data") }}
                  </v-list-item-title>
                </v-list-item>

                <v-list-item v-if="group.action" @click="group.action.run()">
                  <v-list-item-title class="text-caption text-primary">
                    {{ $t(group.action.labelKey) }}
                  </v-list-item-title>
                </v-list-item>
              </template>
            </v-list>
          </v-menu>

          <v-btn
            color="primary"
            variant="flat"
            height="36"
            class="ml-1 mr-n1 text-none"
            prepend-icon="mdi-database-export-outline"
            :loading="isSubmitting"
            :disabled="!store.hasDraft"
            @click="submitCorrections"
          >
            {{ $t("annotation_tool.export.button") }}
          </v-btn>
        </div>

        <!-- <v-divider /> -->

        <!-- No empty state in front of this: the full view is what the user gets from the
             start, and picking something to correct happens in the header menu. -->
        <div class="annotation-body">
          <!-- Toolbox: how many frames the session samples, then everything the picked tool
               can do. Gone entirely until something is picked -- an empty strip of chrome next
               to the video says nothing. The full action set is always shown and merely disabled when it isn't
               possible right now, so what a tool offers stays readable instead of appearing
               and disappearing (see the registry's `actions`). -->
          <div v-if="activeTool" class="toolbox">
            <!-- Only the frame-by-frame tools sample frames at all; for the event tool the
                 whole video is the working area, so the count has nothing to say and is gone
                 rather than sitting there permanently disabled. -->
            <v-menu v-if="activeTool.strip === 'frames'" location="end">
              <template #activator="{ props }">
                <div class="d-flex">
                  <v-btn v-bind="props" size="small" variant="text">
                    <span class="frame-count-value">{{ store.frameCount }}</span>
                  </v-btn>
                  <v-tooltip activator="parent" location="end">
                    {{ $t("annotation_tool.frame_count") }}
                  </v-tooltip>
                </div>
              </template>

              <v-list density="compact">
                <v-list-item
                  v-for="count in FRAME_COUNT_OPTIONS"
                  :key="count"
                  :active="store.frameCount === count"
                  @click="store.frameCount = count"
                >
                  <v-list-item-title>{{ count }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>

            <template v-for="(action, actionIdx) in activeTool?.actions ?? []" :key="action.id">
              <v-divider
                v-if="(actionIdx === 0 && activeTool.strip === 'frames') || action.separated"
                class="my-1 toolbox-divider"
              />

              <!-- Tooltip on the wrapper, not the button: Vuetify puts pointer-events: none on
                   a disabled v-btn, and a disabled action is exactly the one needing a label. -->
              <div class="d-flex mb-2">
                <v-btn
                  size="small"
                  :variant="actionStates[action.id].active ? 'flat' : 'text'"
                  :color="
                    actionStates[action.id].active ? 'primary' : actionStates[action.id].color
                  "
                  :disabled="actionStates[action.id].disabled"
                  @click="actionStates[action.id].run()"
                >
                  <!-- An action may swap its own icon and label for the state it is in (the
                       event tool's delete turns into restore on an already deleted event) --
                       one button for one slot, rather than two that take turns being hidden. -->
                  <v-icon>{{ actionStates[action.id].icon ?? action.icon }}</v-icon>
                </v-btn>
                <v-tooltip activator="parent" location="end">
                  {{ $t(actionStates[action.id].labelKey ?? action.labelKey) }}
                </v-tooltip>
              </div>
            </template>
          </div>

          <!-- Stage: the still frame plus the active tool's overlay -->
          <div class="stage-column">
            <div
              ref="stageWrapper"
              class="stage-wrapper"
              :class="{
                'stage-wrapper--zoomed': zoom > ZOOM_MIN,
                'stage-wrapper--panning': isPanning,
              }"
              @wheel.prevent="onWheel"
              @pointerdown="onStagePointerDown"
            >
              <!-- Zoom controls sit outside the transformed stage, so they keep their size. -->
              <div v-if="activeTool" class="stage-zoom">
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  :disabled="zoom >= ZOOM_MAX"
                  @click="zoomStep(ZOOM_STEP)"
                >
                  <v-icon size="18">mdi-magnify-plus-outline</v-icon>
                  <v-tooltip activator="parent" location="left">
                    {{ $t("annotation_tool.zoom.in") }}
                  </v-tooltip>
                </v-btn>
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  :disabled="zoom <= ZOOM_MIN"
                  @click="zoomStep(1 / ZOOM_STEP)"
                >
                  <v-icon size="18">mdi-magnify-minus-outline</v-icon>
                  <v-tooltip activator="parent" location="left">
                    {{ $t("annotation_tool.zoom.out") }}
                  </v-tooltip>
                </v-btn>
                <span class="stage-zoom-value">{{ Math.round(zoom * 100) }}%</span>

                <!-- Only there while there is something to undo, so the reset is a visible
                     button rather than a hover secret on the readout. -->
                <v-btn v-if="zoom > ZOOM_MIN" icon size="x-small" variant="text" @click="resetZoom">
                  <v-icon size="18">mdi-overscan</v-icon>
                </v-btn>
              </div>

              <div ref="stageElement" class="stage" :style="stageStyle">
                <!-- The frame is the <video> element itself, seeked to the review time and
                     simply shown -- exactly what VideoPlayer.vue does. Painting it into a
                     canvas meant hand-waiting for decoded pixel data, and a still that arrived
                     late (or a seek whose event never came) left the stage black. -->
                <!-- The playhead is reported from `seeked` and, while playing, from a timer
                     (see startTimeReporting) -- deliberately not from `timeupdate`: a seek into
                     an unbuffered stretch still fires timeupdate while the element is briefly
                     reporting its *old* position, which wrote that stale value straight back
                     into the store and snapped the playhead back to where it came from. -->
                <video
                  ref="videoElement"
                  class="stage-video"
                  playsinline
                  @loadedmetadata="onVideoMetadata"
                  @seeking="isSeeking = true"
                  @seeked="onSeeked"
                  @ended="playerStore.setPlaying(false)"
                />

                <!-- Not every tool draws on the picture: the event tool corrects a moment,
                     not a shape, and everything it has to say is already in the timeline and
                     the panel next to it (see the registry -- its `component` is null). -->
                <component
                  :is="activeTool.component"
                  v-if="activeTool?.component && stage.width"
                  v-bind="toolProps"
                  @drawn="mode = 'select'"
                />

                <!-- Not while the video is the working surface: a scrub along the timeline
                     is a rapid burst of seeks, and a spinner flashing over every one of them
                     hides exactly the frames being scrubbed through. -->
                <div v-if="(isSeeking && !isPlaybackTool) || isLoadingTarget" class="stage-seeking">
                  <i class="mdi mdi-loading mdi-spin" />
                </div>
              </div>
            </div>

            <!-- Playback controls, for the tools that review the running video (see the
                 registry's `playback`). Above the timeline rather than below it, so the two
                 halves of "where am I" -- the transport's timecode and the timeline's
                 playhead -- sit next to each other. -->
            <AnnotationTransport
              v-if="isPlaybackTool && hasReviewableData"
              v-model:rate="playbackRate"
            />

            <!-- Under the stage: sampled still frames for the frame-by-frame tools, the full
                 event timeline for the event tool -- same component the Events card uses. -->
            <div v-if="showStrip" class="frame-strip">
              <template v-if="activeTool.strip === 'timeline'">
                <!-- The timeline spans the selected time range, which for a full match is far
                     too coarse to place an event on a frame -- so it zooms, and while playing
                     the window follows the playhead (see keepPlayheadInRange). -->
                <div class="timeline-zoom">
                  <v-btn size="x-small" variant="text" @click="zoomTimeline(1 / 2)">
                    <v-icon size="18">mdi-magnify-plus-outline</v-icon>
                  </v-btn>
                  <v-btn size="x-small" variant="text" @click="zoomTimeline(2)">
                    <v-icon size="18">mdi-magnify-minus-outline</v-icon>
                  </v-btn>
                  <v-btn size="x-small" variant="text" @click="resetTimelineRange">
                    <v-icon size="18">mdi-arrow-expand-horizontal</v-icon>
                  </v-btn>
                </div>

                <EventsTimeline
                  class="px-2 strip-timeline"
                  editable
                  :events="store.visibleReviewEvents"
                  :selected-id="store.selectedEventId"
                  @select="onTimelineSelect"
                  @move="onTimelineMove"
                />
              </template>

              <template v-else>
                <div class="frame-nav">
                  <v-btn
                    size="x-small"
                    variant="text"
                    :disabled="atStart"
                    @click="store.setFrameIdx(0)"
                  >
                    <v-icon>mdi-skip-backward</v-icon>
                  </v-btn>
                  <v-btn
                    size="x-small"
                    variant="text"
                    :disabled="atStart"
                    @click="store.setFrameIdx(store.currentFrameIdx - 1)"
                  >
                    <v-icon>mdi-skip-previous</v-icon>
                  </v-btn>
                </div>

                <div ref="chipRow" class="frame-chips">
                  <button
                    v-for="(frameKey, idx) in store.frameKeys"
                    :key="frameKey"
                    type="button"
                    class="frame-chip"
                    :class="{ 'frame-chip--active': idx === store.currentFrameIdx }"
                    :data-frame-idx="idx"
                    @click="store.setFrameIdx(idx)"
                  >
                    <span class="frame-chip-idx">{{ idx + 1 }}</span>
                    <span class="frame-chip-time">{{ getTimecode(frameKey, 0) }}</span>
                    <span v-if="store.touchedFrames.has(frameKey)" class="frame-chip-dot" />
                  </button>
                </div>

                <div class="frame-nav">
                  <v-btn
                    size="x-small"
                    variant="text"
                    :disabled="atEnd"
                    @click="store.setFrameIdx(store.currentFrameIdx + 1)"
                  >
                    <v-icon>mdi-skip-next</v-icon>
                  </v-btn>
                  <v-btn
                    size="x-small"
                    variant="text"
                    :disabled="atEnd"
                    @click="store.setFrameIdx(store.frameKeys.length - 1)"
                  >
                    <v-icon>mdi-skip-forward</v-icon>
                  </v-btn>
                </div>
              </template>
            </div>
          </div>

          <!-- Properties: only once a tool with a panel has something loaded to work on -->
          <div
            v-if="activeTool?.panel && hasReviewableData"
            class="side-panel"
            :class="{ 'side-panel--wide': activeTool.panelWide }"
          >
            <component :is="activeTool.panel" />
          </div>
        </div>
      </v-card>
    </v-container>

    <v-snackbar v-model="showSnackbar" :color="snackbarError ? 'error' : undefined">
      <div class="d-flex justify-center">
        <snackbar-icon-success v-if="!snackbarError" />
        <span class="text-h6">{{ snackbarMessage }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useBboxesStore } from "@/stores/bboxes";
import { useEventsStore } from "@/stores/events";
import { useAnnotationToolStore, FRAME_COUNT_OPTIONS } from "@/stores/annotation_tool";
import { useHlsVideo } from "@/composables/useHlsVideo";
import { useAnalysisScopeCleanup } from "@/composables/useAnalysisScopeCleanup";
import { useObjectTrackerPlayerRuns } from "@/composables/useObjectTrackerPlayerRuns";
import { annotationTools } from "@/config/annotationTools";
import { getTimecode } from "@/plugins/time";
import EventsTimeline from "@/components/events/EventsTimeline.vue";
import AnnotationTransport from "@/components/annotation-tool/AnnotationTransport.vue";

const route = useRoute();
const { t } = useI18n();

const videoStore = useVideoStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const pluginRunStore = usePluginRunStore();
const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
const eventsStore = useEventsStore();
const store = useAnnotationToolStore();

useAnalysisScopeCleanup();

const isLoading = ref(true);
const mode = ref("select");
// Up while a picked run's boxes are being fetched -- reuses the stage's seek overlay.
const isLoadingTarget = ref(false);
const isSubmitting = ref(false);

// --- data bootstrap ---------------------------------------------------------------------

// Entering through a deep link (or a hard reload) lands here with empty stores, so this view
// has to be able to bring the analysis state up on its own -- exactly what AnalysisView does
// on mount. Coming in from the analysis view instead, both of these are cheap no-ops:
// restoreFromCache bails out as soon as the top-view data is already there.
onMounted(async () => {
  try {
    await videoStore.fetch({ videoId: route.params.id, addResults: true });
    await positionDataStore.restoreFromCache();
    // Not fetched anywhere else on this route -- the calibration group of the target menu
    // lists the assets themselves (markers/segments are what a calibration correction edits),
    // not the DLT runs computed from them.
    await calibrationAssetStore.loadCalibrationAssetsList();
    await restoreReviewTarget();
  } catch (error) {
  } finally {
    isLoading.value = false;
  }
});

// A reload keeps *what* was picked (see the store's persist option, plus bboxesStore's run
// ids) but never the boxes themselves -- those are far too big for sessionStorage, so they get
// refetched here. positionDataStore.restoreFromCache can't do it: it only knows the
// position-data flow, which a target picked here deliberately doesn't go through (no
// calibration asset, no pitch view), so it bails out before ever reaching the tracker run.
async function restoreReviewTarget() {
  if (store.activeToolId !== "bbox" || !store.effectiveRunId) return;
  if (store.frameKeys.length) return;

  try {
    await topViewStore.loadBboxDataForReview(store.effectiveRunId, { ball: store.reviewBallRun });
  } catch (error) {
    console.error("Failed to restore the review target", error);
  }
}

const { objectTrackerPlayerRuns: trackerRuns, objectTrackerBallRuns: ballRuns } =
  useObjectTrackerPlayerRuns();

// "<plugin> - <run date>": which of the two trackers produced a run matters as soon as both
// have been run on a video, and the composable only carries the date.
function runName(run) {
  const type = pluginRunStore.forVideo(playerStore.videoId).find((e) => e.id === run.id)?.type;
  const label = type ? t(`modal.plugin.${type}.plugin_name`) : null;
  return label ? `${label} \u00b7 ${run.name}` : run.name;
}

// What each tool can be pointed at. Tracker runs keep the player/ball split tracking itself
// makes -- the two live in different fields of bboxesStore, and an edit has to go back to the
// run it came from, so the choice is made here rather than guessed later.
const targetItems = computed(() => {
  const assets = calibrationAssetStore.calibrationAssetsList;
  return {
    calibration: (Array.isArray(assets) ? assets : []).map((asset) => ({
      id: asset.id,
      name: asset.name,
    })),
    bbox: [
      ...trackerRuns.value.map((run) => ({
        ...run,
        ball: false,
        icon: "mdi-run",
        name: runName(run),
      })),
      ...ballRuns.value.map((run) => ({
        ...run,
        ball: true,
        icon: "mdi-soccer",
        name: runName(run),
      })),
    ],
    events: eventsStore.eventDataSets.map((set) => ({ id: set.id, name: set.title })),
  };
});

// Which target each not-yet-editable tool is pointed at. Kept local rather than in a store:
// nothing acts on it yet, it only labels the header.
const previewTargets = ref({});

// The header menu, one group per tool, in registry order.
const targetGroups = computed(() =>
  Object.entries(annotationTools).map(([toolId, tool]) => ({
    toolId,
    ...tool,
    items: targetItems.value[toolId] ?? [],
    // Same backdoor ModalEventDataSelect's empty state offers: no detector produces events
    // yet, so without it there is never a populated timeline to look at here.
    action:
      toolId === "events" && !eventsStore.eventDataSets.length
        ? {
            labelKey: "annotation_tool.target.load_demo",
            run: () => {
              store.activeToolId = "events";
              eventsStore.loadDemoEventData();
            },
          }
        : null,
  }))
);

function isActiveTarget(toolId, item) {
  if (store.activeToolId !== toolId) return false;
  if (toolId === "bbox")
    return item.id === store.effectiveRunId && !!item.ball === store.reviewBallRun;
  if (toolId === "events") return item.id === eventsStore.selectedEventDataSetId;
  return previewTargets.value[toolId] === item.id;
}

async function selectTarget(toolId, item) {
  store.activeToolId = toolId;

  if (toolId === "bbox") {
    // Straight to the run's boxes: correcting them needs nothing but the boxes over the video,
    // so this deliberately skips the position-data picker (which exists to pick a calibration
    // asset and the ball / team-clustering / reid merges for the *pitch* view).
    store.reviewBallRun = !!item.ball;
    if (item.id === store.effectiveRunId) return;

    isLoadingTarget.value = true;
    try {
      await topViewStore.loadBboxDataForReview(item.id, { ball: !!item.ball });
    } catch (error) {
      console.error("Failed to load bboxes for review", error);
    } finally {
      isLoadingTarget.value = false;
    }

    // A run that yields no boxes leaves the whole workspace empty -- no frames, so no strip and
    // no properties panel. Say so instead of just looking broken.
    if (!store.frameKeys.length) notify(t("annotation_tool.target.empty_run"), true);
    return;
  }

  if (toolId === "events") {
    eventsStore.selectEventDataSet(item.id);
    return;
  }

  previewTargets.value = { ...previewTargets.value, [toolId]: item.id };
}

const activeTargetLabel = computed(() => {
  const toolId = store.activeToolId;
  if (!toolId) return null;
  if (toolId === "bbox") {
    const item = targetItems.value.bbox.find(
      (entry) => entry.id === store.effectiveRunId && !!entry.ball === store.reviewBallRun
    );
    if (!item) return null;
    // The list marks ball runs with an icon; the header has no room for one, so it says so.
    return item.ball
      ? `${item.name} (${t("modal.plugin.object_tracker.tracking_target_ball")})`
      : item.name;
  }
  if (toolId === "events") {
    const id = eventsStore.selectedEventDataSetId;
    return eventsStore.eventDataSets.find((set) => set.id === id)?.title ?? null;
  }
  return (
    targetItems.value[toolId]?.find((item) => item.id === previewTargets.value[toolId])?.name ??
    null
  );
});

// A different run means different boxes -- corrections drafted against the previous one would
// otherwise be exported as if they belonged to the new one.
watch(
  () => store.effectiveRunId,
  (runId, previousRunId) => {
    if (previousRunId !== undefined && runId !== previousRunId) store.discardAll();
  }
);

// What "there is something to correct" means differs per tool: a frame-by-frame tool needs
// sampled frames, the event tool needs a loaded event data set.
// Same reasoning as the run watcher above: corrections drafted against one event data set
// must not follow the user into another one, where the ids they name mean something else.
watch(
  () => eventsStore.selectedEventDataSetId,
  (id, previousId) => {
    if (previousId !== undefined && id !== previousId) store.discardAllEvents();
    // A newly picked set seeds the range from its own event span when nothing else has set one
    // (see events.js) -- which must not end up longer than the video either.
    if (id) clampTimelineToVideo();
  }
);

const hasReviewableData = computed(() =>
  activeTool.value?.strip === "timeline" ? eventsStore.hasEventData : store.frameKeys.length > 0
);

// The video runs rather than being parked on a still frame -- see the registry's `playback`.
const isPlaybackTool = computed(() => !!activeTool.value?.playback);

// null until something is picked in the header menu -- the view renders its full layout
// either way, it just has no overlay, no actions and no panel until then.
const activeTool = computed(() => annotationTools[store.activeToolId] ?? null);

// Every overlay gets the stage geometry and the edit mode; the preview stand-in additionally
// needs to know which tool it is standing in for (it can't import the registry -- that would
// close an import cycle).
const toolProps = computed(() => ({
  width: stage.value.width,
  height: stage.value.height,
  mode: mode.value,
  ...(activeTool.value?.ready ? {} : { toolId: store.activeToolId, icon: activeTool.value?.icon }),
}));

// The strip under the stage only exists when it has something in it -- an empty bar with a
// "nothing selected" line in it is noise.
const showStrip = computed(() => {
  if (!activeTool.value) return false;
  if (activeTool.value.strip === "timeline") return eventsStore.hasEventData;
  return store.frameKeys.length > 0;
});

// Live state for the active tool's declared actions (see the registry's `actions`): the whole
// set is always rendered, so anything not currently possible -- including every action of a
// tool that isn't editable yet -- comes back disabled rather than missing.
const actionStates = computed(() => {
  const states = {};
  for (const action of activeTool.value?.actions ?? []) {
    states[action.id] = activeTool.value.ready
      ? toolActionState(action.id)
      : { active: false, disabled: true, color: undefined, run: () => {} };
  }
  return states;
});

// Action ids are unique per tool (the registry lists them per entry), so this only has to
// route to the tool that owns them.
function toolActionState(id) {
  return store.activeToolId === "events" ? eventActionState(id) : bboxActionState(id);
}

function eventActionState(id) {
  if (id === "add_event") {
    return {
      active: false,
      disabled: !hasReviewableData.value,
      color: undefined,
      run: addEventAtPlayhead,
    };
  }
  if (id === "delete_event") {
    // Deleting is a tombstone, not a removal (see the store), so the same slot is what takes it
    // back -- otherwise a mis-click could only be undone by discarding the whole session.
    const event = store.selectedEvent;
    const isDeleted = !!event?.deleted;
    return {
      active: false,
      disabled: !event,
      color: isDeleted ? "primary" : "error",
      icon: isDeleted ? "mdi-flag-plus-outline" : undefined,
      labelKey: isDeleted ? "annotation_tool.actions.restore_event" : undefined,
      run: () => (isDeleted ? store.restoreEvent(event.id) : store.deleteEvent(event.id)),
    };
  }
  return {
    active: false,
    disabled: !store.hasEventDraft,
    color: "error",
    run: () => store.discardAllEvents(),
  };
}

// A detector that missed an event entirely is as much a correction as one that mistimed it,
// so the new event starts at the playhead -- the reviewer has already played up to the moment
// it belongs on, and the panel opens on it for the type and the player.
function addEventAtPlayhead() {
  playerStore.setPlaying(false);
  store.addEvent({ timestamp: playerStore.currentTime });
}

function onTimelineSelect(id) {
  store.selectEvent(id, { seek: true });
}

// Dragging a marker scrubs the video along with it: the frame the event is being dropped on
// is exactly what the decision is made from.
function onTimelineMove({ id, timestamp }) {
  playerStore.setPlaying(false);
  store.updateEvent(id, { timestamp });
  playerStore.setTargetTime(timestamp);
}

function bboxActionState(id) {
  if (id === "select" || id === "draw") {
    return {
      active: mode.value === id,
      disabled: !hasReviewableData.value,
      color: undefined,
      run: () => {
        mode.value = id;
      },
    };
  }
  if (id === "delete") {
    return {
      active: false,
      disabled: store.selectedBoxIdx === null,
      color: "error",
      run: deleteSelected,
    };
  }
  return {
    active: false,
    disabled: !store.drafts[store.currentFrameKey],
    color: "error",
    run: () => store.discardDraft(store.currentFrameKey),
  };
}

const atStart = computed(() => store.currentFrameIdx <= 0);
const atEnd = computed(() => store.currentFrameIdx >= store.frameKeys.length - 1);

// --- the still frame --------------------------------------------------------------------

const videoElement = ref(null);
const stageWrapper = ref(null);
const stageElement = ref(null);
const stage = ref({ width: 0, height: 0 });
const isSeeking = ref(false);

useHlsVideo(videoElement, { onManifestParsed: () => syncVideoToTool() });

// --- zoom -------------------------------------------------------------------------------

// Boxes are small, and on a laptop screen a player is a few dozen pixels tall -- so the stage
// zooms. Deliberately a zoom of the stage itself rather than a magnifier hovering over it: a
// loupe would show the detail but leave the dragging in unzoomed pixels, which is exactly the
// precision that's missing. Scaling the stage means the tool overlay scales with it, and since
// it derives every coordinate from getBoundingClientRect (see BboxAnnotationTool's relPos),
// dragging stays pixel-accurate at any zoom without the tool knowing about it at all.
const ZOOM_MIN = 1;
const ZOOM_MAX = 8;
const ZOOM_STEP = 1.25;

const zoom = ref(ZOOM_MIN);
const pan = ref({ x: 0, y: 0 });
const isPanning = ref(false);

const stageStyle = computed(() => ({
  ...(stage.value.width
    ? { width: `${stage.value.width}px`, height: `${stage.value.height}px` }
    : { width: "100%", height: "100%" }),
  transform: `translate(${pan.value.x}px, ${pan.value.y}px) scale(${zoom.value})`,
  // Read by the overlay to keep handles and outlines at a constant on-screen size.
  "--stage-zoom": zoom.value,
}));

// Keeps the frame from being dragged out of view: while it is larger than the wrapper its
// edges may not move inside, and at 1x it stays centred.
function clampPan() {
  const wrapper = stageWrapper.value?.getBoundingClientRect();
  if (!wrapper || !stage.value.width) return;
  if (zoom.value === ZOOM_MIN) {
    pan.value = { x: 0, y: 0 };
    return;
  }

  const axis = (value, size, available) => {
    const offset = (available - size) / 2; // the stage is centred by the wrapper's flex layout
    const scaled = size * zoom.value;
    const lower = available - scaled - offset;
    const upper = -offset;
    return Math.min(Math.max(value, Math.min(lower, upper)), Math.max(lower, upper));
  };

  pan.value = {
    x: axis(pan.value.x, stage.value.width, wrapper.width),
    y: axis(pan.value.y, stage.value.height, wrapper.height),
  };
}

// Zooms around a screen point, so whatever sits under the cursor (or the middle of the view,
// for the buttons) stays put instead of drifting off.
function applyZoom(next, anchor = null) {
  const target = Math.min(Math.max(next, ZOOM_MIN), ZOOM_MAX);
  if (target === zoom.value) return;

  const rect = stageElement.value?.getBoundingClientRect();
  if (rect && anchor) {
    const x = (anchor.x - rect.left) / zoom.value;
    const y = (anchor.y - rect.top) / zoom.value;
    pan.value = {
      x: pan.value.x + x * (zoom.value - target),
      y: pan.value.y + y * (zoom.value - target),
    };
  }

  zoom.value = target;
  clampPan();
}

function onWheel(event) {
  applyZoom(zoom.value * (event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP), {
    x: event.clientX,
    y: event.clientY,
  });
}

function zoomStep(factor) {
  const rect = stageWrapper.value?.getBoundingClientRect();
  applyZoom(
    zoom.value * factor,
    rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null
  );
}

function resetZoom() {
  zoom.value = ZOOM_MIN;
  pan.value = { x: 0, y: 0 };
}

// What may be grabbed to drag the picture: the bare frame, and a tool's own base layer -- never
// a box, a grip or a control, all of which run their own drags. Tools mark their base layer
// with data-annotation-layer, so this needs to know nothing about any particular tool.
function isPannableTarget(target) {
  if (!(target instanceof Element)) return false;
  return (
    target === stageWrapper.value ||
    target === stageElement.value ||
    target === videoElement.value ||
    target.hasAttribute("data-annotation-layer")
  );
}

// Dragging the picture: left button on empty frame (where a click only clears the selection
// anyway), or the middle button anywhere. Left-dragging a box still moves the box, and in draw
// mode the left button stays with the marquee -- so panning never takes a gesture away.
function onStagePointerDown(event) {
  if (zoom.value === ZOOM_MIN) return;

  const grabsFrame = event.button === 0 && mode.value !== "draw" && isPannableTarget(event.target);
  if (event.button !== 1 && !grabsFrame) return;
  event.preventDefault();

  const start = { x: event.clientX, y: event.clientY };
  const origin = { ...pan.value };
  isPanning.value = true;

  const move = (moveEvent) => {
    pan.value = {
      x: origin.x + (moveEvent.clientX - start.x),
      y: origin.y + (moveEvent.clientY - start.y),
    };
    clampPan();
  };
  const up = () => {
    window.removeEventListener("pointermove", move);
    isPanning.value = false;
  };

  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up, { once: true });
}

// A different target is a different picture -- keeping a zoomed-in corner across that would
// leave the user looking at an arbitrary patch of the new one.
watch(() => [store.activeToolId, store.effectiveRunId], resetZoom);

// Fits the frame into the available area while preserving the video's aspect ratio. The tool
// overlay is positioned in the same pixel space, so this is what makes relative box
// coordinates land where they should.
function updateStageSize() {
  const wrapper = stageWrapper.value;
  const video = videoElement.value;
  if (!wrapper || !video || !video.videoWidth) return;

  const available = wrapper.getBoundingClientRect();
  const ratio = video.videoWidth / video.videoHeight;
  let width = available.width;
  let height = width / ratio;
  if (height > available.height) {
    height = available.height;
    width = height * ratio;
  }
  stage.value = { width: Math.round(width), height: Math.round(height) };
}

// The last position the video was asked to go to. Setting currentTime on an element that has
// no data yet is silently deferred by the browser (it reports the old position until the media
// arrives), so the request is kept and re-applied once there is something to seek in.
let pendingSeekMs = null;

function seekVideo(timeMs) {
  const video = videoElement.value;
  if (!video) return;
  const target = Math.max(0, timeMs) / 1000;
  pendingSeekMs = Math.round(Math.max(0, timeMs));
  if (Math.abs(video.currentTime - target) < 1e-3) return;
  video.currentTime = target;
}

// The one authoritative report of where the video actually is while it is not playing: it fires
// once the seek has landed, so what goes into the store is the real position rather than a
// guess made before the element had moved.
function onSeeked(event) {
  isSeeking.value = false;
  const actual = Math.round(event.target.currentTime * 1000);
  // Still on its way to a newer target (a scrub fires a burst of seeks) -- let that one report.
  if (pendingSeekMs !== null && Math.abs(actual - pendingSeekMs) > 250) return;
  pendingSeekMs = null;
  if (isPlaybackTool.value) playerStore.setCurrentTime(actual);
}

// Puts this view's own player on the review frame. Nothing gets painted: the element renders
// the frame it is parked on all by itself, which is why VideoPlayer.vue needs no canvas either.
// (It needs its own <video> because playerStore.videoElement only exists while VideoPlayer is
// mounted, and that card lives on the analysis route.)
function showCurrentFrame() {
  // A playback tool owns the playhead itself (see the watchers below) -- parking the element
  // on a sampled frame here would yank the video back mid-playback.
  if (isPlaybackTool.value) return;

  // No review frames yet (nothing picked, or a tool that doesn't work frame by frame): park on
  // the start of the video, so the stage shows the video rather than nothing.
  seekVideo(store.currentFrameKey ?? 0);
}

// Which of the two regimes the element is in. Switching tools switches regime, so this also
// stops playback on the way into a frame-by-frame tool.
function syncVideoToTool() {
  if (isPlaybackTool.value) {
    // Picks up wherever the analysis view's own player left the playhead -- the two share
    // playerStore.currentTime, so coming here to correct an event you just watched lands on
    // that same moment instead of at the start of the video.
    seekVideo(playerStore.currentTime);
    return;
  }
  playerStore.setPlaying(false);
  showCurrentFrame();
}

// Metadata is the first point the video's real size is known -- and the size is what the tool
// overlay's relative coordinates are mapped onto.
function onVideoMetadata() {
  updateStageSize();
  applyVolume();
  clampTimelineToVideo();
  // A seek requested before the element had metadata never took effect -- redo it now.
  if (pendingSeekMs !== null) seekVideo(pendingSeekMs);
  else syncVideoToTool();
}

watch(() => store.currentFrameKey, showCurrentFrame);
watch(() => store.activeToolId, syncVideoToTool);

// --- playback ----------------------------------------------------------------------------
//
// For the playback tools this view is a small VideoPlayer: play/pause, the playhead and every
// seek go through playerStore, exactly as they do on the analysis route, and this element just
// follows. That is what lets the timeline, the event list, the transport bar and the overlay
// all read one playhead without knowing about each other -- and what makes a seek from any of
// them (a marker click, a nudge in the panel, a click on the timeline track) move the video.

const playbackRate = ref(1);

watch(playbackRate, (rate) => {
  if (videoElement.value) videoElement.value.playbackRate = rate;
});

// Volume and mute are the player store's own -- persisted, and shared with VideoPlayer, so the
// setting carries between the two views. changeVolume()/toggleMute() there write to
// playerStore.videoElement, which only exists while VideoPlayer is mounted, so this view
// mirrors the state onto its own element itself.
function applyVolume() {
  const video = videoElement.value;
  if (!video) return;
  video.volume = playerStore.volume / 100;
  video.muted = playerStore.isMuted;
}
watch([() => playerStore.volume, () => playerStore.isMuted], applyVolume);

watch(
  () => playerStore.targetTime,
  (time) => {
    if (!isPlaybackTool.value) return;
    playerStore.setCurrentTime(Math.round(time));
    seekVideo(time);
  }
);

watch(
  () => playerStore.playing,
  (playing) => {
    const video = videoElement.value;
    if (!video) return;
    if (playing && isPlaybackTool.value) {
      // Rejected autoplay (no user gesture yet) must not leave the store claiming to play.
      video.play().catch(() => playerStore.setPlaying(false));
    } else {
      video.pause();
    }
  }
);

// timeupdate alone fires only about four times a second, which is a visibly stuttering
// playhead on a timeline this precise -- so while playing, the position is read at frame rate,
// the same approach VideoPlayer.vue takes.
let timeTimer = null;
function startTimeReporting() {
  stopTimeReporting();
  const interval = Math.max(16, Math.round(1000 / (playerStore.videoFPS || 30)));
  timeTimer = setInterval(() => {
    if (videoElement.value) {
      playerStore.setCurrentTime(Math.round(videoElement.value.currentTime * 1000));
    }
  }, interval);
}
function stopTimeReporting() {
  if (timeTimer) clearInterval(timeTimer);
  timeTimer = null;
}
watch(
  () => playerStore.playing,
  (playing) => (playing ? startTimeReporting() : stopTimeReporting())
);
onBeforeUnmount(stopTimeReporting);

// The store's playing flag is shared with VideoPlayer on the analysis route -- leaving this
// view with it still set would start that player up on arrival.
onBeforeUnmount(() => playerStore.setPlaying(false));

// Keeps the chip row scrolled to whichever frame is active, so arrow navigation past the
// visible end doesn't leave the highlighted chip off-screen.
const chipRow = ref(null);
watch(
  () => store.currentFrameIdx,
  async (idx) => {
    await nextTick();
    chipRow.value
      ?.querySelector(`[data-frame-idx="${idx}"]`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
);

// Clamp back into range when the frame count changes (100 -> 20 while sitting on frame 80).
watch(
  () => store.frameKeys.length,
  (length) => {
    if (store.currentFrameIdx > length - 1) store.setFrameIdx(Math.max(length - 1, 0));
  }
);

// The stage has to be re-measured whenever the area around it changes -- not just on a window
// resize: picking a tool brings in the toolbox, the frame strip and the properties panel, all
// of which change how much room is left for the frame.
let stageObserver = null;
onMounted(() => {
  stageObserver = new ResizeObserver(() => {
    updateStageSize();
    clampPan();
  });
  if (stageWrapper.value) stageObserver.observe(stageWrapper.value);
});
// The stage only exists once the loading card has been replaced, i.e. after onMounted has
// already run -- so attach to it when it actually appears.
watch(stageWrapper, (element) => {
  if (element) stageObserver?.observe(element);
});
onBeforeUnmount(() => {
  stageObserver?.disconnect();
  stageObserver = null;
});

// --- the timeline window -------------------------------------------------------------------
//
// EventsTimeline draws whatever positionDataStore.selectedTimeRange spans -- the same range the
// analysis view's time selector edits. Over a full match that is minutes per pixel, far too
// coarse to put an event on a frame, so the tool zooms into it and (while playing) keeps the
// window travelling with the playhead.

const MIN_TIMELINE_SPAN_MS = 2000;

// The outer bound to zoom out to: the video's own length, or -- with no duration known yet --
// whatever the events themselves cover.
const timelineEnd = computed(() => {
  if (playerStore.videoDuration) return playerStore.videoDuration;
  const stamps = store.reviewEvents.map((event) => event.timestamp);
  return stamps.length ? Math.max(...stamps) + 5000 : 0;
});

// Written straight onto the range rather than through positionDataStore's own
// setSelectedTimeRangeStart/End, exactly as events.js does when it seeds the range. Those two
// clamp every value to the last *position-data* frame key and are throttled at 30 ms, so with
// event data alone -- no tracker run loaded, which is the normal case here -- their maximum is
// 0: one zoom collapsed the range to 0..0, which filters every marker off the timeline, and
// the reset button went through the same clamp and could never bring them back. This tool's
// timeline is bounded by the video, not by position data.
function setTimelineWindow(center, span) {
  const full = timelineEnd.value || span;
  const width = Math.min(Math.max(span, MIN_TIMELINE_SPAN_MS), full);
  const start = Math.min(Math.max(0, center - width / 2), Math.max(0, full - width));
  positionDataStore.selectedTimeRange = {
    start: Math.round(start),
    end: Math.round(start + width),
  };
}

// Zooms around the playhead rather than the middle of the window: it is the moment being
// judged, so it is the one that must not move out from under the zoom.
function zoomTimeline(factor) {
  const { start, end } = positionDataStore.selectedTimeRange;
  const span = Math.max(MIN_TIMELINE_SPAN_MS, end - start);
  const center = Math.min(Math.max(playerStore.currentTime, start), end);
  setTimelineWindow(center, span * factor);
}

// The range is shared with the analysis view and can arrive from anywhere (position data, a
// previous session, an event set sized before the video was known). Anything past the end of
// the video is time that cannot be reviewed -- there is no frame behind it -- and it silently
// throws off every timecode read off the scale, so it gets cut back here.
function clampTimelineToVideo() {
  const duration = playerStore.videoDuration;
  if (!duration) return;
  const { start, end } = positionDataStore.selectedTimeRange;
  if (start >= 0 && end > start && end <= duration) return;
  positionDataStore.selectedTimeRange = {
    start: Math.max(0, Math.min(start, duration)),
    end: Math.min(end || duration, duration),
  };
}

function resetTimelineRange() {
  if (!timelineEnd.value) return;
  positionDataStore.selectedTimeRange = { start: 0, end: Math.round(timelineEnd.value) };
}

// Zoomed in, playback would otherwise run straight out of the visible window within seconds.
// Recentres only once the playhead reaches the edge, so the timeline isn't permanently
// scrolling under a playhead pinned to the middle.
watch(
  () => playerStore.currentTime,
  (time) => {
    if (!isPlaybackTool.value) return;
    const { start, end } = positionDataStore.selectedTimeRange;
    const span = end - start;
    if (span <= 0 || span >= timelineEnd.value) return;
    const margin = span * 0.1;
    if (time >= start + margin && time <= end - margin) return;
    setTimelineWindow(time, span);
  }
);

// --- actions ----------------------------------------------------------------------------

function deleteSelected() {
  if (store.selectedBoxIdx === null) return;
  store.removeBox(store.currentFrameKey, store.selectedBoxIdx);
}

function onKeyDown(event) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    return;
  }

  // Same keys, read against whatever the active tool's unit of work is: a sampled frame for
  // the bbox tool, a single video frame (and the space bar) while the video is running.
  if (isPlaybackTool.value) {
    if (event.key === " ") {
      event.preventDefault(); // or the browser scrolls the page instead of toggling playback
      playerStore.togglePlaying();
    } else if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const step = (1000 / (playerStore.videoFPS || 30)) * (event.key === "ArrowRight" ? 1 : -1);
      playerStore.setPlaying(false);
      playerStore.setTargetTime(Math.max(0, playerStore.currentTime + step));
    } else if (event.key === "Delete" || event.key === "Backspace") {
      if (store.selectedEventId) store.deleteEvent(store.selectedEventId);
    }
    return;
  }

  if (event.key === "Delete" || event.key === "Backspace") {
    deleteSelected();
  } else if (event.key === "ArrowRight") {
    store.setFrameIdx(store.currentFrameIdx + 1);
  } else if (event.key === "ArrowLeft") {
    store.setFrameIdx(store.currentFrameIdx - 1);
  }
}
onMounted(() => window.addEventListener("keydown", onKeyDown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeyDown));

// Leaving the tool ends the review session -- nothing about what was being corrected is kept.
onBeforeUnmount(() => store.clearSession());

const showSnackbar = ref(false);
const snackbarMessage = ref("");
const snackbarError = ref(false);

function notify(message, isError = false) {
  snackbarMessage.value = message;
  snackbarError.value = isError;
  showSnackbar.value = true;
}

// The one point where a review session leaves the browser. Two halves, because the backend can
// only take one of them today: identity corrections go through the endpoint that exists, while
// geometry is handed to the user as a file -- see annotation_tool.js's exportDraft for why it
// can't be written back (bboxes/replace would overwrite the run and destroy the
// original-vs-corrected pair a fine-tuning run needs). Once corrections can be stored as their
// own dataset, both halves collapse into a single request.
async function submitCorrections() {
  isSubmitting.value = true;
  try {
    for (const edit of store.identityEdits) {
      // Same store call the analysis view's editor used, so the three-way refresh (ball run /
      // client-side merge / plain tracker run) still applies.
      await bboxesStore.updateBboxData({
        bytetrackRunId: store.effectiveRunId,
        bboxId: edit.bboxId,
        playerId: edit.playerId,
        teamId: edit.teamId,
        newPlayerId: edit.newPlayerId,
        newTeamId: edit.newTeamId,
        applyAllPlayerId: edit.scope === "allPlayer",
        applyAllTeamId: edit.scope === "allTeam",
      });
    }

    const payload = store.exportDraft();
    downloadPayload(payload);

    // Written through, so they must not be sent a second time. The geometry drafts stay: they
    // are what the user is looking at, and re-exporting them is harmless.
    store.identityEdits = [];

    // One package, but two kinds of correction can be in it -- say which, rather than
    // reporting "0 frames" for a session that only moved events around.
    const eventCount =
      payload.events.edited.length + payload.events.added.length + payload.events.deleted.length;
    const parts = [];
    if (payload.frames.length) {
      parts.push(t("annotation_tool.export.success", { count: payload.frames.length }));
    }
    if (eventCount) {
      parts.push(t("annotation_tool.export.success_events", { count: eventCount }));
    }
    notify(parts.join(" \u00b7 ") || t("annotation_tool.export.success", { count: 0 }));
  } catch (error) {
    console.error("Failed to submit corrections", error);
    notify(t("annotation_tool.export.failed"), true);
  } finally {
    isSubmitting.value = false;
  }
}

// Client-side download, same anchor trick export.js uses for its CSV exports.
function downloadPayload(payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${t("annotation_tool.export.file_name")}_${playerStore.videoId}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}
</script>

<style scoped>
.annotation-container {
  height: calc(100vh - 64px);
  padding: 8px;
}

.annotation-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.spinner {
  font-size: 48px;
  color: rgb(var(--v-theme-primary));
}

.loading-text {
  margin-top: 10px;
  font-size: 18px;
  color: rgb(var(--v-theme-primary));
}

.annotation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  flex-shrink: 0;
  margin-left: 4px;
}

.header-video-name {
  font-size: 1.25rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.header-target {
  margin-left: 6px;
  opacity: 0.85;
  font-weight: 400;
}

.target-btn {
  font-size: 0.92rem;
}

.frame-count-value {
  font-size: 0.85rem;
  font-weight: 600;
}

.target-group-title {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  /* A little air above each group heading, so the divider doesn't sit right on the text. */
  padding-top: 8px;
}

.annotation-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 8px;
  padding: 8px;
  margin-top: -4px;
}

/* Showing a tool's full action set is the point, so a disabled action still has to be legible.
   Vuetify fades a disabled button to opacity 0.26 (VBtn.css), which on the toolbox's own tinted
   background reads as "there is nothing here". */
.toolbox :deep(.v-btn--disabled),
.toolbox :deep(.v-btn--disabled:hover) {
  opacity: 0.5;
}

/* The toolbox centers its children, which leaves a divider (width: auto) at zero width --
   stretch it back across the column so it is actually visible. */
.toolbox-divider {
  align-self: stretch;
}

.toolbox {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  padding: 6px 4px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

.stage-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-wrapper {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.stage {
  position: relative;
  flex-shrink: 0;
  /* Zoom grows from the top-left, which is what the pan maths in applyZoom assumes. */
  transform-origin: 0 0;
}

/* Only the frame gets the grab cursor -- boxes and grips set their own, and being descendants
   they win. */
.stage-wrapper--zoomed .stage {
  cursor: grab;
}

.stage-wrapper--panning,
.stage-wrapper--panning .stage {
  cursor: grabbing;
}

.stage-zoom {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
}

.stage-zoom :deep(.v-btn) {
  color: #fff;
}

.stage-zoom-value {
  padding: 1px 4px;
  color: #fff;
  font-size: 0.65rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}

.stage-video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.stage-seeking {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  color: #fff;
  font-size: 40px;
  z-index: 50;
  pointer-events: none;
}

.frame-strip {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 4px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

.frame-nav {
  display: flex;
  flex-shrink: 0;
}

.frame-chips {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  flex: 1;
  min-width: 0;
  padding: 2px;
}

.frame-chip {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  min-width: 62px;
  padding: 3px 6px;
  border: 1px solid rgba(var(--v-theme-primary), 0.35);
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.frame-chip:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.frame-chip--active {
  background: rgba(var(--v-theme-primary), 0.9);
  border-color: rgb(var(--v-theme-primary));
  color: #fff;
}

.frame-chip-idx {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.1;
}

.frame-chip-time {
  font-size: 0.62rem;
  font-family: monospace;
  opacity: 0.8;
  line-height: 1.1;
}

.frame-chip-dot {
  position: absolute;
  top: 2px;
  right: 3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--v-theme-secondary));
}

.timeline-zoom {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

/* The timeline declares width: 100% of its own, which as a flex item would make its base size
   the whole strip -- next to the zoom column that overflows, and clipping it only hid the fact
   that its right end was cut off mid-scale. A zero flex basis instead means it is sized purely
   from what is left over, so its last tick lands exactly on the strip's inner edge. */
.frame-strip .strip-timeline {
  flex: 1 1 0;
  min-width: 0;
  /* Beats the timeline's own width: 100% (see EventsTimeline) rather than relying on which of
     the two scoped stylesheets happens to be emitted last. */
  width: auto;
}

.side-panel {
  width: 280px;
  flex-shrink: 0;
  overflow-y: auto;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

/* The event tool carries its event list in this column as well as the editor, and scrolls the
   list inside itself (see EventEditPanel) rather than the whole column. */
.side-panel--wide {
  width: 330px;
  overflow: hidden;
}
</style>
