<template>
  <v-main class="main" tabindex="0" ref="main">
    <v-container fluid>
      <ModalMarkerOverlay v-if="calibrationAssetStore.isAnyReferenceMarkerActive" />

      <v-row class="ma-n2">
        <v-col cols="6">
          <v-card elevation="2" ref="videoCard" class="fill-height">
            <v-row justify="center">
              <v-card-title class="mt-5 mb-n1">
                {{ playerStore.videoName }}
              </v-card-title>
            </v-row>

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
            <div class="loading-text">Loading...</div>
          </v-card>

          <v-card
            v-else
            class="d-flex flex-column flex-nowrap px-2 fill-height"
            elevation="2"
            ref="topViewCard"
          >
            <v-row class="sticky-tabs-bar" justify="center">
              <v-tabs fixed-tabs slider-color="primary" v-model="analysisTabId">
                <v-tab
                  v-for="analysisTab in analysisTabs"
                  :key="analysisTab.id"
                  :value="analysisTab.id"
                >
                  {{ analysisTab.name }}
                </v-tab>
              </v-tabs>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <v-tabs-window v-model="analysisTabId">
                  <v-tabs-window-item
                    v-for="analysisTab in analysisTabs"
                    :key="analysisTab.id"
                    :value="analysisTab.id"
                  >
                    <TabWindowCalibration v-if="analysisTab.id === 'calibration'" />
                    <TabWindowPosData v-if="analysisTab.id === 'pos_data'" />
                    <TabWindowHeatmap v-if="analysisTab.id === 'heatmap'" />
                  </v-tabs-window-item>
                </v-tabs-window>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>

      <!-- <v-row class="ma-2">
        <v-col>
          <VisualizationMenu></VisualizationMenu>
        </v-col>
      </v-row> -->

      <v-row v-if="analysisTabId === 'pos_data'" class="ma-n2">
        <v-col>
          <v-card class="d-flex flex-column flex-nowrap px-2" elevation="2">
            <v-tabs fixed-tabs slider-color="primary" v-model="visualizationTabId">
              <v-tab v-for="visualizationTab in visualizationTabs" :key="visualizationTab.id">
                {{ visualizationTab.name }}
              </v-tab>
            </v-tabs>

            <v-row class="flex-grow-1 my-0">
              <v-col>
                <v-tabs-window v-model="visualizationTabId">
                  <v-tabs-window-item
                    v-for="visualizationTab in visualizationTabs"
                    :key="visualizationTab.id"
                  >
                    <TabWindowTimeline v-if="visualizationTab.id === 'timeline'" />
                    <TabWindowEvents v-if="visualizationTab.id === 'events'" />
                    <TabWindowRunningDistance v-if="visualizationTab.id === 'running_distance'" />
                  </v-tabs-window-item>
                </v-tabs-window>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>
      <!-- <ModalTimelineSegmentAnnotate :show.sync="annotationDialog.show" /> -->
    </v-container>

    <v-snackbar v-model="showCalibrationAssetActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon />
        <span class="text-h6">{{ calibrationAssetActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showPosDataUploadSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon />
        <span class="text-h6">{{ $t("modal.position_data.upload.success") }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, watchEffect, nextTick } from "vue";
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
// import * as Keyboard from "../plugins/keyboard";
import VideoPlayer from "@/components/video/VideoPlayer.vue";
import TabWindowPosData from "@/components/tab-window/TabWindowPosData.vue";
import TabWindowCalibration from "@/components/tab-window/TabWindowCalibration.vue";
import TabWindowHeatmap from "@/components/tab-window/TabWindowHeatmap.vue";
import TabWindowTimeline from "@/components/tab-window/TabWindowTimeline.vue";
import TabWindowEvents from "@/components/tab-window/TabWindowEvents.vue";
import TabWindowRunningDistance from "@/components/tab-window/TabWindowRunningDistance.vue";
import ModalMarkerOverlay from "@/components/ModalMarkerOverlay.vue";
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

const analysisTabId = ref("calibration");
const analysisTabs = computed(() => [
  { id: "calibration", name: t("analysis_view.analysis_tabs.calibration") },
  { id: "pos_data", name: t("analysis_view.analysis_tabs.pos_data") },
  { id: "heatmap", name: t("analysis_view.analysis_tabs.heatmap") },
]);
watch(
  () => analysisTabId.value,
  async (newTabId) => {
    topViewStore.showItems = false;

    await nextTick();

    if (newTabId === "calibration") {
      calibrationAssetStore.showVideoMarker = true;
    } else {
      calibrationAssetStore.showVideoMarker = false;
    }

    if (newTabId === "pos_data" || newTabId === "heatmap") {
      playerStore.showBoundingBox = true;
    } else {
      playerStore.showBoundingBox = false;
    }

    topViewStore.showItems = true;
  }
);

const visualizationTabId = ref("timeline");
const visualizationTabs = computed(() => [
  { id: "timeline", name: t("analysis_view.visualization_tabs.timeline") },
  { id: "events", name: t("analysis_view.visualization_tabs.events") },
  { id: "running_distance", name: t("analysis_view.visualization_tabs.running_distance") },
]);
onMounted(() => {
  visualizationTabId.value = visualizationTabs.value.find((tab) => tab.id === "timeline")?.id;
});

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
  try {
    await fetchData({ addResults: true });
  } catch (error) {
  } finally {
    isLoading.value = false;
  }
});

const groupDataByTime = (data) => {
  const grouped = {};
  data.forEach((position) => {
    const time = playerStore.roundTimeToFPS(position.time, playerStore.videoFPS);
    if (!grouped[time]) {
      grouped[time] = [];
    }
    grouped[time].push(position);
  });
  return grouped;
};
watchEffect(() => {
  const newBboxes = bboxesStore.setBboxData(bboxesStore.bboxPluginRun);

  if (newBboxes && newBboxes.length > 0) {
    bboxesStore.bboxData = newBboxes;

    const _bboxDataInterpolated = bboxesStore.interpolateBboxData(
      newBboxes,
      playerStore.videoFPS,
      30
    );
    bboxesStore.bboxDataInterpolated = groupDataByTime(_bboxDataInterpolated);

    if (calibrationAssetStore.calibrationMatrix) {
      const _bboxDataTopView = bboxesStore.setbboxDataTopView(_bboxDataInterpolated);
      bboxesStore.bboxDataTopView = groupDataByTime(_bboxDataTopView);
      console.log("bboxDataTopView", bboxesStore.bboxDataTopView);
    }
  }
});

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
  () => pluginInProgress,
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
const resetcalibrationAssetActionSnackbar = async () => {
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
      resetcalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetSaveSuccess = false;
    } else if (update === true) {
      calibrationAssetActionMessage.value = t("modal.calibration_asset.update.success");
      resetcalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetUpdateSuccess = false;
    } else if (del === true) {
      calibrationAssetActionMessage.value = t("modal.calibration_asset.delete.success");
      resetcalibrationAssetActionSnackbar();
      calibrationAssetStore.calibrationAssetDeleteSuccess = false;
    }
  }
);

const showPosDataUploadSnackbar = ref(false);
const resetPosDataUploadSnackbar = async () => {
  showPosDataUploadSnackbar.value = false;
  await nextTick();
  showPosDataUploadSnackbar.value = true;
  bboxesStore.posDataUploadSuccess = false;
};
watch(
  () => bboxesStore.posDataUploadSuccess,
  (newValue) => {
    if (newValue === true) {
      resetPosDataUploadSnackbar();
    }
  }
);

watch(
  () => [calibrationAssetStore.marker, bboxesStore.bboxPluginRun],
  ([newmarker, newBytetrack]) => {
    console.log("Selected Calibration Asset:", newmarker);
    console.log("Selected Bytetrack Plugin:", newBytetrack);
  },
  { deep: true }
);

watch(
  () => bboxesStore.bboxDataTopView,
  (newBboxDataTopView) => {
    console.log("Selected Bbox Data Top View:", newBboxDataTopView);
  }
);

watch(
  () => calibrationAssetStore.calibrationMatrix,
  (newMatrix) => {
    console.log("Selected Calibration Matrix:", newMatrix);
  }
);

watch(
  () => calibrationAssetStore.isAnyReferenceMarkerActive,
  (active) => {
    if (active) {
      calibrationAssetStore.previousShowVideoMarker = calibrationAssetStore.showVideoMarker;
      calibrationAssetStore.showVideoMarker = true;
    } else {
      calibrationAssetStore.showVideoMarker = calibrationAssetStore.previousShowVideoMarker;
    }
  },
  { immediate: true }
);

onMounted(() => {
  console.log("video", playerStore.video);
});

watch(
  () => playerStore.video,
  () => {
    console.log("video", playerStore.video);
  },
  { immediate: true }
);
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
  color: #ac1414;
}

.loading-text {
  margin-top: 10px;
  font-size: 18px;
}
</style>
