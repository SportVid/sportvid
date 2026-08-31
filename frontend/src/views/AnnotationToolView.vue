<template>
  <v-main>
    <v-container fluid class="annotation-container">
      <v-card v-if="isLoading" class="loading-card" elevation="2">
        <div class="spinner"><i class="mdi mdi-loading mdi-spin" /></div>
        <div class="loading-text">{{ $t("loading_screen") }}</div>
      </v-card>

      <v-card v-else class="annotation-card" elevation="2">
        <!-- Header: what is being corrected, and the way back out -->
        <div class="annotation-header">
          <v-btn
            variant="text"
            size="small"
            prepend-icon="mdi-arrow-left"
            class="text-none"
            @click="backToAnalysis"
          >
            {{ $t("annotation_tool.back_to_analysis") }}
          </v-btn>

          <div class="header-title">
            <span class="header-video-name">{{ playerStore.videoName }}</span>
            <span class="header-tool-name text-medium-emphasis">
              {{ activeTool ? $t(activeTool.labelKey) : "" }}
            </span>
          </div>

          <v-spacer />

          <!-- Read-only: which run is under review follows the position-data selection made in
               the analysis view. See annotation_tool.js's effectiveRunId for why it isn't a
               free choice here. -->
          <v-chip v-if="activeRunLabel" size="small" color="primary" variant="tonal">
            {{ $t("annotation_tool.run_select") }}: {{ activeRunLabel }}
          </v-chip>

          <v-select
            v-model="store.frameCount"
            :items="FRAME_COUNT_OPTIONS"
            :label="$t('annotation_tool.frame_count')"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 130px"
            class="ml-2"
          />

          <v-btn
            color="primary"
            variant="flat"
            size="small"
            class="ml-3 text-none"
            prepend-icon="mdi-database-export-outline"
            :disabled="!store.hasDraft"
            @click="exportTrainingData"
          >
            {{ $t("annotation_tool.export.button") }}
          </v-btn>
        </div>

        <v-divider />

        <!-- Empty state: no tracker run to correct yet. Same menu the dashboard cards show
             when they have no position data, so the way out is identical everywhere. -->
        <div v-if="!hasReviewableData" class="annotation-empty">
          <PositionDataMenu
            :title="$t('annotation_tool.empty_state.title')"
            icon="mdi-vector-square"
          />
        </div>

        <div v-else class="annotation-body">
          <!-- Toolbox -->
          <div class="toolbox">
            <v-btn
              v-for="tool in toolButtons"
              :key="tool.id"
              icon
              :variant="store.activeToolId === tool.id ? 'flat' : 'text'"
              :color="store.activeToolId === tool.id ? 'primary' : undefined"
              size="small"
              class="mb-2"
              @click="store.activeToolId = tool.id"
            >
              <v-icon>{{ tool.icon }}</v-icon>
              <v-tooltip activator="parent" location="end">{{ $t(tool.labelKey) }}</v-tooltip>
            </v-btn>

            <v-divider class="my-2" />

            <v-btn
              :variant="mode === 'select' ? 'flat' : 'text'"
              :color="mode === 'select' ? 'primary' : undefined"
              size="small"
              class="mb-2"
              @click="mode = 'select'"
            >
              <v-icon>mdi-cursor-default-outline</v-icon>
              <v-tooltip activator="parent" location="end">
                {{ $t("annotation_tool.mode.select") }}
              </v-tooltip>
            </v-btn>

            <v-btn
              :variant="mode === 'draw' ? 'flat' : 'text'"
              :color="mode === 'draw' ? 'primary' : undefined"
              size="small"
              class="mb-2"
              @click="mode = 'draw'"
            >
              <v-icon>mdi-shape-rectangle-plus</v-icon>
              <v-tooltip activator="parent" location="end">
                {{ $t("annotation_tool.mode.draw") }}
              </v-tooltip>
            </v-btn>

            <v-btn
              size="small"
              variant="text"
              class="mb-2"
              :disabled="store.selectedBoxIdx === null"
              @click="deleteSelected"
            >
              <v-icon>mdi-vector-square-remove</v-icon>
              <v-tooltip activator="parent" location="end">
                {{ $t("annotation_tool.mode.delete") }}
              </v-tooltip>
            </v-btn>

            <v-divider class="my-2" />

            <v-btn
              size="small"
              variant="text"
              color="error"
              :disabled="!store.drafts[store.currentFrameKey]"
              @click="store.discardDraft(store.currentFrameKey)"
            >
              <v-icon>mdi-undo-variant</v-icon>
              <v-tooltip activator="parent" location="end">
                {{ $t("annotation_tool.discard_frame") }}
              </v-tooltip>
            </v-btn>
          </div>

          <!-- Stage: the still frame plus the active tool's overlay -->
          <div class="stage-column">
            <div ref="stageWrapper" class="stage-wrapper">
              <div class="stage" :style="{ width: `${stage.width}px`, height: `${stage.height}px` }">
                <canvas ref="frameCanvas" class="stage-canvas" />

                <component
                  :is="activeTool.component"
                  v-if="activeTool && stage.width"
                  :width="stage.width"
                  :height="stage.height"
                  :mode="mode"
                  @drawn="mode = 'select'"
                />

                <div v-if="isSeeking" class="stage-seeking">
                  <i class="mdi mdi-loading mdi-spin" />
                </div>
              </div>
            </div>

            <!-- Frame strip -->
            <div class="frame-strip">
              <div class="frame-nav">
                <v-btn size="x-small" variant="text" :disabled="atStart" @click="store.setFrameIdx(0)">
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
            </div>
          </div>

          <!-- Properties -->
          <div class="side-panel">
            <BboxIdentityPanel v-if="store.activeToolId === 'bbox'" />
          </div>
        </div>
      </v-card>
    </v-container>

    <!-- Offscreen: this view's own player. playerStore.videoElement only exists while
         VideoPlayer.vue is mounted, and that card lives on the analysis route, not here. -->
    <video
      ref="videoElement"
      class="offscreen-video"
      muted
      playsinline
      @loadedmetadata="renderCurrentFrame"
    />

    <v-snackbar v-model="showSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ snackbarMessage }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { useAnnotationToolStore, FRAME_COUNT_OPTIONS } from "@/stores/annotation_tool";
import { useHlsVideo } from "@/composables/useHlsVideo";
import { useAnalysisScopeCleanup } from "@/composables/useAnalysisScopeCleanup";
import { useObjectTrackerPlayerRuns } from "@/composables/useObjectTrackerPlayerRuns";
import { annotationTools } from "@/config/annotationTools";
import { getTimecode } from "@/plugins/time";
import PositionDataMenu from "@/components/position-data/PositionDataMenu.vue";
import BboxIdentityPanel from "@/components/annotation-tool/BboxIdentityPanel.vue";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const videoStore = useVideoStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const store = useAnnotationToolStore();

useAnalysisScopeCleanup();

const isLoading = ref(true);
const mode = ref("select");

// --- data bootstrap ---------------------------------------------------------------------

// Entering through a deep link (or a hard reload) lands here with empty stores, so this view
// has to be able to bring the analysis state up on its own -- exactly what AnalysisView does
// on mount. Coming in from the analysis view instead, both of these are cheap no-ops:
// restoreFromCache bails out as soon as the top-view data is already there.
onMounted(async () => {
  try {
    await videoStore.fetch({ videoId: route.params.id, addResults: true });
    await positionDataStore.restoreFromCache();
  } catch (error) {
  } finally {
    isLoading.value = false;
  }
});

const { objectTrackerPlayerRuns: trackerRuns } = useObjectTrackerPlayerRuns();

const activeRunLabel = computed(
  () => trackerRuns.value.find((run) => run.id === store.effectiveRunId)?.name ?? null
);

// A different run means different boxes -- corrections drafted against the previous one would
// otherwise be exported as if they belonged to the new one.
watch(
  () => store.effectiveRunId,
  (runId, previousRunId) => {
    if (previousRunId !== undefined && runId !== previousRunId) store.discardAll();
  }
);

const hasReviewableData = computed(() => store.frameKeys.length > 0);

const activeTool = computed(() => annotationTools[store.activeToolId] ?? null);

const toolButtons = computed(() =>
  Object.entries(annotationTools).map(([id, tool]) => ({ id, ...tool }))
);

const atStart = computed(() => store.currentFrameIdx <= 0);
const atEnd = computed(() => store.currentFrameIdx >= store.frameKeys.length - 1);

// --- the still frame --------------------------------------------------------------------

const videoElement = ref(null);
const frameCanvas = ref(null);
const stageWrapper = ref(null);
const stage = ref({ width: 0, height: 0 });
const isSeeking = ref(false);

useHlsVideo(videoElement, { onManifestParsed: () => renderCurrentFrame() });

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

// Seeks the offscreen player to the review frame and paints it into the canvas. Same
// drawImage capture ModalObjectOverlay uses, but with an explicit wait: a seek is async, and
// painting before it resolves would show whichever frame happened to be decoded.
async function renderCurrentFrame() {
  const video = videoElement.value;
  const canvas = frameCanvas.value;
  const frameKey = store.currentFrameKey;
  if (!video || !canvas || frameKey === undefined) return;

  const target = frameKey / 1000;
  isSeeking.value = true;
  try {
    // Checked *before* assigning currentTime: reading it straight back after an assignment
    // returns the requested value even while the seek is still pending, so a check afterwards
    // would always look like "already there" and paint whatever frame was still decoded.
    const alreadyThere = Math.abs(video.currentTime - target) < 1e-3 && video.readyState >= 2;

    if (!alreadyThere) {
      await new Promise((resolve) => {
        let settled = false;
        const done = () => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          video.removeEventListener("seeked", done);
          resolve();
        };
        // HLS can drop a "seeked" when it has to fetch a fresh segment; without a fallback the
        // spinner would stay up forever on that frame.
        const timer = setTimeout(done, 3000);
        video.addEventListener("seeked", done);
        video.currentTime = target;
      });
    }

    await nextTick();
    updateStageSize();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  } finally {
    isSeeking.value = false;
  }
}

watch(() => store.currentFrameKey, renderCurrentFrame);

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

const onResize = () => {
  updateStageSize();
};
onMounted(() => window.addEventListener("resize", onResize));
onBeforeUnmount(() => window.removeEventListener("resize", onResize));

// --- actions ----------------------------------------------------------------------------

function deleteSelected() {
  if (store.selectedBoxIdx === null) return;
  store.removeBox(store.currentFrameKey, store.selectedBoxIdx);
}

function onKeyDown(event) {
  if (event.target instanceof HTMLInputElement) return;
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

const showSnackbar = ref(false);
const snackbarMessage = ref("");

// Client-side download, same anchor trick export.js uses for its CSV exports. See
// annotation_tool.js's exportDraft for why this does not go to the backend yet.
function exportTrainingData() {
  const payload = store.exportDraft();
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${t("annotation_tool.export.file_name")}_${playerStore.videoId}.json`;
  link.click();
  URL.revokeObjectURL(link.href);

  snackbarMessage.value = t("annotation_tool.export.success", {
    count: payload.frames.length,
  });
  showSnackbar.value = true;
}

function backToAnalysis() {
  router.push({ name: "AnalysisView", params: { id: route.params.id } });
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
}

.header-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-left: 8px;
}

.header-video-name {
  font-size: 1.05rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-tool-name {
  font-size: 0.8rem;
}

.annotation-empty {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.annotation-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 8px;
  padding: 8px;
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
}

.stage-canvas {
  display: block;
  width: 100%;
  height: 100%;
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

.side-panel {
  width: 280px;
  flex-shrink: 0;
  overflow-y: auto;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

/* Kept in the DOM (it is the pixel source for the canvas) but never shown -- the frame the
   user looks at is the painted canvas, not this element. */
.offscreen-video {
  position: fixed;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
  left: -10px;
  top: -10px;
}
</style>
