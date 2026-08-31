<template>
  <v-main class="main" tabindex="0" ref="main">
    <v-container fluid>
      <ModalObjectOverlay v-if="calibrationAssetStore.isAnyReferenceObjectActive" />

      <v-row v-if="calibrationAssetStore.calibrationMode" class="ma-n2">
        <v-col cols="6">
          <v-card
            elevation="2"
            ref="videoCard"
            class="fill-height"
            data-tour="analysis-video-player"
          >
            <!-- No extra title row here -- VideoPlayer.vue already renders playerStore.videoName
                 itself (its own .video-title), so wrapping it in a v-card-title too showed the
                 name twice, stacked right on top of each other. -->
            <v-row class="flex-grow-1">
              <v-col>
                <VideoPlayer />
              </v-col>
            </v-row>
          </v-card>
        </v-col>

        <v-col cols="6">
          <v-card v-if="isLoading" class="loading-card fill-height" elevation="2" ref="topViewCard">
            <div class="spinner">
              <i class="mdi mdi-loading mdi-spin" />
            </div>
            <div class="loading-text">{{ $t("loading_screen") }}</div>
          </v-card>

          <v-card
            v-else
            class="d-flex flex-column flex-nowrap px-2 fill-height calibration-card"
            elevation="2"
            ref="topViewCard"
            style="position: relative"
            data-tour="analysis-top-view"
          >
            <v-row justify="center" class="position-relative">
              <v-card-title class="mt-5 mb-n1">{{ $t("calibration_asset.title") }}</v-card-title>
              <v-btn
                variant="tonal"
                color="error"
                size="small"
                prepend-icon="mdi-close"
                class="calibration-close-btn"
                @click="calibrationAssetStore.calibrationMode = false"
              >
                {{ $t("button.exit") }}
              </v-btn>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <TabWindowCalibration />
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>

      <div v-else class="dashboard-view-wrapper">
        <button
          v-if="!dashboardStore.editMode"
          type="button"
          class="dashboard-edit-entry"
          :class="[
            `dashboard-edit-entry--${entryButtonCorner}`,
            { 'dashboard-edit-entry--dragging': isDraggingEntry },
          ]"
          :style="entryDragStyle"
          data-tour="dashboard-edit-toggle"
          :title="$t('analysis_view.dashboard.edit_toggle')"
          @pointerdown="onEntryPointerDown"
          @click="onEntryClick"
        >
          <v-icon size="40" color="primary">mdi-view-dashboard-edit</v-icon>
          <span class="dashboard-edit-entry-label text-primary">
            {{ $t("analysis_view.dashboard.edit_toggle") }}
          </span>
        </button>

        <button
          v-else
          type="button"
          class="dashboard-edit-done"
          :title="$t('analysis_view.dashboard.edit_done')"
          @click="dashboardStore.toggleEditMode()"
        >
          <v-icon size="40" color="secondary">mdi-check</v-icon>
        </button>

        <DashboardGrid :is-loading="isLoading" />
      </div>
      <!-- <ModalTimelineSegmentAnnotate :show.sync="annotationDialog.show" /> -->
    </v-container>

    <v-snackbar v-model="showCalibrationAssetActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ calibrationAssetActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showPositionDataActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ positionDataActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showPluginRunActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ pluginRunActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showBboxDataActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ bboxDataActionMessage }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useBboxesStore } from "@/stores/bboxes";
import { useTopViewStore } from "@/stores/top_view";
import { useTimelineStore } from "@/stores/timeline";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { useShortcutStore } from "@/stores/shortcut";
import { useAnnotationShortcutStore } from "@/stores/annotation_shortcut";
import { useClusterTimelineItemStore } from "@/stores/cluster_timeline_item";
import { useShotStore } from "@/stores/shot";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";
import { useAnalysisScopeCleanup } from "@/composables/useAnalysisScopeCleanup";
// import * as Keyboard from "../plugins/keyboard";
import VideoPlayer from "@/components/analysis-view/cards/VideoPlayer.vue";
import TabWindowCalibration from "@/components/calibration-asset/CalibrationAsset.vue";
import ModalObjectOverlay from "@/components/calibration-asset/ModalObjectOverlay.vue";
import DashboardGrid from "@/components/analysis-view/dashboard/DashboardGrid.vue";
// import TranscriptOverview from "@/components/TranscriptOverview.vue";
// import CurrentEntitiesOverView from "@/components/CurrentEntitiesOverView.vue";
// import ModalTimelineSegmentAnnotate from "@/components/ModalTimelineSegmentAnnotate.vue";
// import ShotsOverview from "@/components/ShotsOverview.vue";
// import WordcloudCard from "@/components/WordcloudCard.vue";
// import VisualizationMenu from "@/components/VisualizationMenu.vue";
// import PersonGraph from "@/components/PersonGraph.vue";
// import ClusterTimelineItemOverview from "@/components/ClusterTimelineItemOverview.vue";

const route = useRoute();
const { t } = useI18n();
const videoStore = useVideoStore();
const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
const topViewStore = useTopViewStore();
const timelineStore = useTimelineStore();
const timelineSegmentStore = useTimelineSegmentStore();
const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
const shortcutStore = useShortcutStore();
const annotationShortcutStore = useAnnotationShortcutStore();
const clusterTimelineItemStore = useClusterTimelineItemStore();
const shotStore = useShotStore();
const positionDataStore = usePositionDataStore();
const visualizationStore = useVisualizationStore();
const dashboardStore = useDashboardLayoutStore();

const matchupTeams = computed(() => {
  const meta = topViewStore.metaDataTopView;
  if (!meta?.team_ids) return [];
  // New scheme: team_id ≥ 3 = active player teams (1=ball, 2=refs, 0=inactive — all hidden from matchup).
  return Object.entries(meta.team_ids)
    .filter(([teamId]) => Number(teamId) >= 3)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([teamId, info]) => ({
      id: Number(teamId),
      name: info.name,
      color: visualizationStore.getTeamColor(Number(teamId)),
    }));
});

function getVisualizationTabComponent(tabId) {
  if (tabId === "timeline") {
    return TabWindowTimeline;
  } else if (tabId === "events") {
    return TabWindowEvents;
  } else if (tabId === "heatmap") {
    return TabWindowHeatmap;
  } else if (tabId === "kpi") {
    return TabWindowKPI;
  } else {
    return null;
  }
}

watch(
  () => calibrationAssetStore.calibrationMode,
  async (isCalibration) => {
    topViewStore.showItems = false;

    await nextTick();

    if (isCalibration) {
      calibrationAssetStore.showVideoAsset = true;
      bboxesStore.showBoundingBox = false;
    } else {
      calibrationAssetStore.showVideoAsset = false;
      bboxesStore.showBoundingBox = true;
    }

    topViewStore.showItems = true;
  },
  { immediate: true }
);

const isLoading = ref(true);
const fetchData = async ({ addResults = true }) => {
  try {
    await videoStore.fetch({
      videoId: route.params.id,
      addResults,
    });
  } catch (error) {}
};
onMounted(async () => {
  dashboardStore.initFromUser();
  try {
    await fetchData({ addResults: true });
    topViewStore.setSportFromVideo(playerStore.video?.sport);
    // Re-fetch the previously selected position/KPI data after a reload (id is
    // persisted in sessionStorage — see position_data.js). Deliberately not
    // awaited: it re-runs the same chunked backend load a manual selection
    // would, so it can take a while on a big dataset, and the KPI/Heatmap tabs
    // already show their own progress spinner (posdataWorkerStore.isLoading)
    // while it's in flight instead of blocking the rest of the page.
    positionDataStore.restoreFromCache();
  } catch (error) {
  } finally {
    isLoading.value = false;
  }
});

// watch(
//   () => [bboxesStore.bboxDataActive, calibrationAssetStore.calibrationMatrix, playerStore.videoFPS],
//   () => {
//     if (bboxesStore.bboxDataActive && bboxesStore.bboxDataActive.length > 0) {
//       const _parsedData = JSON.parse(bboxesStore.bboxDataActive);

//       const _bboxDataInterpolated = bboxesStore.interpolateBboxData(
//         _parsedData,
//         playerStore.videoFPS,
//         30
//       );
//       bboxesStore.bboxDataInterpolated = _bboxDataInterpolated;

//       if (calibrationAssetStore.calibrationMatrix) {
//         const _bboxDataTopView = ref({});
//         for (const [time, boxes] of Object.entries(_bboxDataInterpolated)) {
//           _bboxDataTopView.value[time] = boxes.map((b) => {
//             const { x, y } = calibrationAssetStore.applyHomography(
//               calibrationAssetStore.calibrationMatrix,
//               { x: b.top_x, y: b.top_y }
//             );
//             return { ...b, pos_x: x, pos_y: y };
//           });
//         }
//         const times = Object.keys(_bboxDataTopView.value)
//           .map(Number)
//           .sort((a, b) => a - b);
//         if (times.length > 0) {
//           const firstTimeKey = String(times[0]);
//           const arr = _bboxDataTopView.value[firstTimeKey];
//           if (Array.isArray(arr) && arr.length > 0) {
//             arr[0] = { ...arr[0], team_id: "red" };
//           }
//         }
//         topViewStore.positionDataTopView = _bboxDataTopView.value;
//       }
//     }
//   },
//   { immediate: true }
// );

const shotsList = computed(() =>
  shotStore.shotsList.map((e) => ({ text: e.name, value: e.index }))
);
const selectedShotsProxy = ref(null);
const selectedShots = computed({
  get() {
    const selectedShots = shotStore.selectedShots;
    return selectedShotsProxy === null ? selectedShots : selectedShotsProxy;
  },
  set(val) {
    selectedShotsProxy = val;
    shotStore.setSelectedShots({ shotTimeline: val });
  },
});

const faceClusteringList = computed(() =>
  clusterTimelineItemStore.faceClusteringList.map((e) => ({
    text: e.name,
    value: e.index,
  }))
);
const faceClusters = computed(() => clusterTimelineItemStore.latestFaceClustering());
const selectedFaceClusteringProxy = ref(null);
const selectedFaceClustering = computed({
  get() {
    const selectedFaceClustering = clusterTimelineItemStore.selectedFaceClustering;
    return selectedFaceClusteringProxy === null
      ? selectedFaceClustering
      : selectedFaceClusteringProxy;
  },
  set(val) {
    selectedFaceClusteringProxy = val;
    clusterTimelineItemStore.setSelectedFaceClustering({ pluginRunId: val });
  },
});

const placeClusteringList = computed(() =>
  clusterTimelineItemStore.placeClusteringList.map((e) => ({
    text: e.name,
    value: e.index,
  }))
);
const placeClusters = computed(() => clusterTimelineItemStore.latestPlaceClustering());
const selectedPlaceClusteringProxy = ref(null);
const selectedPlaceClustering = computed({
  get() {
    const selectedPlaceClustering = clusterTimelineItemStore.selectedPlaceClustering;
    return selectedPlaceClusteringProxy === null
      ? selectedPlaceClustering
      : selectedPlaceClusteringProxy;
  },
  set(val) {
    selectedPlaceClusteringProxy = val;
    clusterTimelineItemStore.setSelectedPlaceClustering({
      pluginRunId: val,
    });
  },
});

// const selectedTimelineProxy = ref(null);
// const selectedTimeline = computed({
//   get() {
//     return selectedTimelineProxy === null ? timelines.value[0] : selectedTimelineProxy;
//   },
//   set(val) {
//     selectedTimelineProxy = val;
//   },
// });

const fetchPluginTimer = ref(null);
const fetchPlugin = async () => {
  await pluginRunStore.fetchForVideo({
    videoId: route.params.id,
    fetchResults: true,
  });
};
const pluginInProgress = computed(() => pluginRunStore.pluginInProgress);
watch(
  pluginInProgress,
  (newState) => {
    if (newState) {
      fetchPluginTimer = setInterval(() => {
        fetchPlugin({ addResults: false });
      }, 1000);
    } else {
      clearInterval(fetchPluginTimer);
    }
  }
);

const annotationDialog = ref({ show: false });
const onAnnotateSegment = () => {
  if (timelineSegmentStore.lastSelected) {
    annotationDialog.show = true;
  }
};

// const onKeyDown = (event) => {
//   const lastSelectedTimeline = timelineStore.lastSelected;
//   const lastSelectedTimelineSegment = timelineSegmentStore.lastSelected;

//   if (!lastSelectedTimeline) {
//     if (
//       ["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(event.key)
//     ) {
//       const selectedTimeline = timelineStore.getNext(null);
//       if (selectedTimeline) {
//         timelineStore.addToSelection(selectedTimeline.id);
//         const timelineSegments = timelineSegmentStore.forTimeline(
//           selectedTimeline.id
//         );
//         if (timelineSegments.length > 0) {
//           const selectedTimelineSegment = timelineSegments[0];
//           timelineSegmentStore.addToSelection(selectedTimelineSegment.id);
//         }
//       }
//       return;
//     }
//   }

//   if (event.key === "ArrowDown") {
//     const nextTimeline = timelineStore.getNext(lastSelectedTimeline?.id);
//     if (nextTimeline) {
//       if (!event.ctrlKey) {
//         timelineStore.clearSelection();
//         timelineSegmentStore.clearSelection();
//       }
//       timelineStore.addToSelection(nextTimeline.id);
//       const timelineSegments = timelineSegmentStore.forTimeline(
//         nextTimeline.id
//       );
//       if (timelineSegments.length > 0) {
//         timelineSegmentStore.addToSelection(timelineSegments[0].id);
//       }
//       event.preventDefault();
//     }
//   } else if (event.key === "ArrowUp") {
//     const nextTimeline = timelineStore.getPrevious(lastSelectedTimeline?.id);
//     if (nextTimeline) {
//       if (!event.ctrlKey) {
//         timelineStore.clearSelection();
//         timelineSegmentStore.clearSelection();
//       }
//       timelineStore.addToSelection(nextTimeline.id);
//       const timelineSegments = timelineSegmentStore.forTimeline(
//         nextTimeline.id
//       );
//       if (timelineSegments.length > 0) {
//         timelineSegmentStore.addToSelection(timelineSegments[0].id);
//       }
//       event.preventDefault();
//     }
//   } else if (event.key === "ArrowLeft") {
//     if (lastSelectedTimelineSegment) {
//       const nextTimelineSegment =
//         timelineSegmentStore.getPreviousOnTimeline(
//           lastSelectedTimelineSegment.id
//         );
//       if (nextTimelineSegment) {
//         playerStore.setTargetTime(nextTimelineSegment.start);
//         if (!event.ctrlKey) {
//           timelineSegmentStore.clearSelection();
//         }
//         timelineSegmentStore.addToSelection(nextTimelineSegment.id);
//         event.preventDefault();
//       }
//     }
//   } else if (event.key === "ArrowRight") {
//     if (lastSelectedTimelineSegment) {
//       const nextTimelineSegment =
//         timelineSegmentStore.getNextOnTimeline(lastSelectedTimelineSegment.id);
//       if (nextTimelineSegment) {
//         playerStore.setTargetTime(nextTimelineSegment.start);
//         if (!event.ctrlKey) {
//           timelineSegmentStore.clearSelection();
//         }
//         timelineSegmentStore.addToSelection(nextTimelineSegment.id);
//         event.preventDefault();
//       }
//     }
//   } else if (event.key === "Enter") {
//     onAnnotateSegment();
//     event.preventDefault();
//   }

//   const keys = [];
//   if (event.ctrlKey) keys.push("ctrl");
//   if (event.shiftKey) keys.push("shift");
//   if (event.key.length === 1) keys.push(event.key.toLowerCase());

//   const keysString = Keyboard.generateKeysString(keys);
//   const shortcuts = shortcutStore.getByKeys(keysString);

//   if (shortcuts.length > 0) {
//     shortcuts.forEach((shortcut) => {
//       const annotationShortcut = annotationShortcutStore.forShortcut(
//         shortcut.id
//       );
//       if (annotationShortcut && lastSelectedTimelineSegment) {
//         timelineSegmentStore.toggle({
//           timelineSegmentId: lastSelectedTimelineSegment.id,
//           annotationId: annotationShortcut.annotation_id,
//         });
//       }
//     });
//   }
// };

const showCalibrationAssetActionSnackbar = ref(false);
const calibrationAssetActionMessage = ref("");
const resetCalibrationAssetActionSnackbar = async () => {
  showCalibrationAssetActionSnackbar.value = false;
  await nextTick();
  showCalibrationAssetActionSnackbar.value = true;
};
watch(
  [
    () => calibrationAssetStore.calibrationAssetSaveSuccess,
    () => calibrationAssetStore.calibrationAssetUpdateSuccess,
    () => calibrationAssetStore.calibrationAssetDeleteSuccess,
  ],
  ([save, update, del]) => {
    if (save === true) {
      calibrationAssetActionMessage.value = t("modal.calibration_asset.save.success");
      resetCalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetSaveSuccess = false;
    } else if (update === true) {
      calibrationAssetActionMessage.value = t("modal.calibration_asset.update.success");
      resetCalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetUpdateSuccess = false;
    } else if (del === true) {
      calibrationAssetActionMessage.value = t("modal.calibration_asset.delete.success");
      resetCalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetDeleteSuccess = false;
    }
  }
);

const showPositionDataActionSnackbar = ref(false);
const positionDataActionMessage = ref("");
const resetPositionDataActionSnackbar = async () => {
  showPositionDataActionSnackbar.value = false;
  await nextTick();
  showPositionDataActionSnackbar.value = true;
};
watch(
  [
    () => positionDataStore.positionDataUploadSuccess,
    () => positionDataStore.positionDataRenameSuccess,
    () => positionDataStore.positionDataDeleteSuccess,
  ],
  ([upload, rename, del]) => {
    if (upload === true) {
      positionDataActionMessage.value = t("modal.position_data.upload.success");
      resetPositionDataActionSnackbar();
      positionDataStore.positionDataUploadSuccess = false;
    } else if (rename === true) {
      positionDataActionMessage.value = t("modal.position_data.rename.success");
      resetPositionDataActionSnackbar();
      positionDataStore.positionDataRenameSuccess = false;
    } else if (del === true) {
      positionDataActionMessage.value = t("modal.position_data.delete.success");
      resetPositionDataActionSnackbar();
      positionDataStore.positionDataDeleteSuccess = false;
    }
  }
);

const showPluginRunActionSnackbar = ref(false);
const pluginRunActionMessage = ref("");
const resetPluginRunActionSnackbar = async () => {
  showPluginRunActionSnackbar.value = false;
  await nextTick();
  showPluginRunActionSnackbar.value = true;
};
watch(
  [
    () => pluginRunStore.pluginRunDeleteAllSuccess,
    () => pluginRunStore.pluginRunDeleteSelectedSuccess,
  ],
  ([del_all, del_selected]) => {
    if (del_all === true) {
      pluginRunActionMessage.value = t("modal.status.delete.success.all");
      resetPluginRunActionSnackbar();
      positionDataStore.pluginRunDeleteAllSuccess = false;
    } else if (del_selected === true) {
      pluginRunActionMessage.value = t("modal.status.delete.success.selected");
      resetPluginRunActionSnackbar();
      positionDataStore.pluginRunDeleteSelectedSuccess = false;
    }
  }
);

const showBboxDataActionSnackbar = ref(false);
const bboxDataActionMessage = ref("");
const resetBboxDataActionSnackbar = async () => {
  showBboxDataActionSnackbar.value = false;
  await nextTick();
  showBboxDataActionSnackbar.value = true;
};
watch(
  [
    () => bboxesStore.bboxDataSingleUpdateSuccess,
    () => bboxesStore.bboxDataUpdateSuccess,
    () => bboxesStore.bboxDataSingleDeleteSuccess,
    () => bboxesStore.bboxDataDeleteSuccess,
  ],
  ([singleUpdate, updateAll, singleDelete, deleteAll]) => {
    if (singleUpdate) {
      bboxDataActionMessage.value = t("modal.bounding_box.edit.single_success");
      resetBboxDataActionSnackbar();
      bboxesStore.bboxDataSingleUpdateSuccess = false;
    } else if (updateAll) {
      bboxDataActionMessage.value = t("modal.bounding_box.edit.all_success");
      resetBboxDataActionSnackbar();
      bboxesStore.bboxDataUpdateSuccess = false;
    } else if (singleDelete) {
      bboxDataActionMessage.value = t("modal.bounding_box.delete.single_success");
      resetBboxDataActionSnackbar();
      bboxesStore.bboxDataSingleDeleteSuccess = false;
    } else if (deleteAll) {
      bboxDataActionMessage.value = t("modal.bounding_box.delete.all_success");
      resetBboxDataActionSnackbar();
      bboxesStore.bboxDataDeleteSuccess = false;
    }
  }
);

watch(
  () => calibrationAssetStore.isAnyReferenceObjectActive,
  (active) => {
    if (active) {
      calibrationAssetStore.previousShowVideoAsset = calibrationAssetStore.showVideoAsset;
      calibrationAssetStore.showVideoAsset = true;
    } else {
      calibrationAssetStore.showVideoAsset = calibrationAssetStore.previousShowVideoAsset;
    }
  },
  { immediate: true }
);

// --- Draggable "enter edit mode" button (snaps to a corner of the dashboard) ---
const ENTRY_BUTTON_CORNER_STORAGE_KEY = "sportvid.dashboardEditEntryCorner";
const ENTRY_BUTTON_CORNERS = ["top-right", "top-left", "bottom-right", "bottom-left"];

function loadEntryButtonCorner() {
  const stored = localStorage.getItem(ENTRY_BUTTON_CORNER_STORAGE_KEY);
  return ENTRY_BUTTON_CORNERS.includes(stored) ? stored : "top-right";
}

const entryButtonCorner = ref(loadEntryButtonCorner());
const isDraggingEntry = ref(false);
const entryDragStyle = ref({});

const ENTRY_DRAG_THRESHOLD = 6; // px of pointer movement before a press counts as a drag, not a click
let entryDragStartX = 0;
let entryDragStartY = 0;
let entryPointerOffsetX = 0;
let entryPointerOffsetY = 0;
let entryDidDrag = false;

function onEntryPointerDown(event) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  const rect = event.currentTarget.getBoundingClientRect();
  entryPointerOffsetX = event.clientX - rect.left;
  entryPointerOffsetY = event.clientY - rect.top;
  entryDragStartX = event.clientX;
  entryDragStartY = event.clientY;
  entryDidDrag = false;
  window.addEventListener("pointermove", onEntryPointerMove);
  window.addEventListener("pointerup", onEntryPointerUp, { once: true });
}

function onEntryPointerMove(event) {
  const dx = event.clientX - entryDragStartX;
  const dy = event.clientY - entryDragStartY;
  if (!entryDidDrag && Math.hypot(dx, dy) > ENTRY_DRAG_THRESHOLD) {
    entryDidDrag = true;
    isDraggingEntry.value = true;
  }
  if (!entryDidDrag) return;
  entryDragStyle.value = {
    position: "fixed",
    left: `${event.clientX - entryPointerOffsetX}px`,
    top: `${event.clientY - entryPointerOffsetY}px`,
    right: "auto",
    bottom: "auto",
  };
}

function onEntryPointerUp(event) {
  window.removeEventListener("pointermove", onEntryPointerMove);
  if (entryDidDrag) {
    // Corners are relative to the viewport (not the dashboard wrapper) so the
    // button stays reachable in a fixed screen corner no matter how far the
    // page is scrolled — the wrapper itself can be far taller than the
    // viewport.
    const vertical = event.clientY < window.innerHeight / 2 ? "top" : "bottom";
    const horizontal = event.clientX < window.innerWidth / 2 ? "left" : "right";
    entryButtonCorner.value = `${vertical}-${horizontal}`;
    localStorage.setItem(ENTRY_BUTTON_CORNER_STORAGE_KEY, entryButtonCorner.value);
  }
  isDraggingEntry.value = false;
  entryDragStyle.value = {};
}

function onEntryClick(event) {
  // A drag gesture ends with a click event right after pointerup — swallow
  // that one so dragging the button doesn't also toggle edit mode.
  if (entryDidDrag) {
    event.preventDefault();
    event.stopPropagation();
    return;
  }
  dashboardStore.toggleEditMode();
}

onBeforeUnmount(() => {
  window.removeEventListener("pointermove", onEntryPointerMove);
  window.removeEventListener("pointerup", onEntryPointerUp);
});

// Tears the analysis state (position data, calibration, events) down on the way out -- but
// deliberately not when moving to the annotation tool for this same video, which works on
// exactly that state. See useAnalysisScopeCleanup for the full reasoning.
useAnalysisScopeCleanup();
</script>

<style scoped>
.logo > img {
  max-height: 56px;
}

.sticky-tabs-bar {
  position: sticky;
  top: 0;
  z-index: 1;
}

.card-title {
  font-size: 64;
}

.timeline-bar {
  height: 80px;
}

.main:focus {
  outline: none;
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
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

.calibration-close-btn {
  position: absolute;
  top: 20px;
  right: 12px;
  z-index: 10;
}

.calibration-card {
  border: 2px solid rgba(var(--v-theme-secondary), 0.45);
  transition: border-color 0.3s ease;
}

.dashboard-view-wrapper {
  position: relative;
}

.dashboard-edit-entry,
.dashboard-edit-done {
  position: absolute;
  z-index: 20;
  cursor: pointer;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  transition: max-width 0.2s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.dashboard-edit-done {
  top: -10px;
  right: -10px;
}

.dashboard-edit-entry {
  /* Fixed to the viewport (not the dashboard wrapper) so the button stays in
     its chosen corner no matter how far the page is scrolled. */
  position: fixed;
  touch-action: none;
  user-select: none;
}

/* 64px = the app bar's height, so the top corners sit just below it instead
   of overlapping. */
.dashboard-edit-entry--top-right {
  top: 74px;
  right: 20px;
}

.dashboard-edit-entry--top-left {
  top: 74px;
  left: 20px;
}

.dashboard-edit-entry--bottom-right {
  bottom: 20px;
  right: 20px;
}

.dashboard-edit-entry--bottom-left {
  bottom: 20px;
  left: 20px;
}

.dashboard-edit-entry--dragging {
  max-width: 68px !important;
  cursor: grabbing;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  transition: none;
}

.dashboard-edit-entry:hover,
.dashboard-edit-done:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45);
  transform: translateY(-1px);
}

.dashboard-edit-entry:active,
.dashboard-edit-done:active {
  transform: translateY(0) scale(0.95);
}

.dashboard-edit-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 68px;
  max-width: 68px;
  padding: 0 14px;
  overflow: hidden;
  border: 2px solid rgba(var(--v-theme-primary), 0.5);
  border-radius: 34px;
}

.dashboard-edit-entry:hover {
  max-width: 260px;
  padding: 0 18px;
}

.dashboard-edit-entry-label {
  font-size: 0.95rem;
  font-weight: 500;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.dashboard-edit-entry:hover .dashboard-edit-entry-label {
  opacity: 1;
  transition-delay: 0.08s;
}

.dashboard-edit-done {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border: 2px solid rgba(var(--v-theme-secondary), 0.6);
  border-radius: 50%;
}
</style>
