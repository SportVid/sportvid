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
              <v-tabs fixed-tabs slider-color="primary" v-model="tabStore.analysisTabId">
                <v-tab
                  v-for="analysisTab in tabStore.analysisTabs"
                  :key="analysisTab.id"
                  :value="analysisTab.id"
                >
                  {{ analysisTab.name }}
                </v-tab>
              </v-tabs>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <v-tabs-window v-model="tabStore.analysisTabId">
                  <v-tabs-window-item
                    v-for="analysisTab in tabStore.analysisTabs"
                    :key="analysisTab.id"
                    :value="analysisTab.id"
                  >
                    <component :is="getAnalysisTabComponent(analysisTab.id)" />
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

      <v-row v-if="tabStore.analysisTabId === 'position_data'" class="ma-n2">
        <v-col>
          <v-card class="d-flex flex-column flex-nowrap px-2" elevation="2">
            <v-tabs fixed-tabs slider-color="primary" v-model="tabStore.visualizationTabId">
              <v-tab
                v-for="visualizationTab in tabStore.visualizationTabs"
                :key="visualizationTab.id"
                :value="visualizationTab.id"
              >
                {{ visualizationTab.name }}
              </v-tab>
            </v-tabs>

            <v-row class="flex-grow-1 my-0">
              <v-col>
                <v-tabs-window v-model="tabStore.visualizationTabId">
                  <v-tabs-window-item
                    v-for="visualizationTab in tabStore.visualizationTabs"
                    :key="visualizationTab.id"
                    :value="visualizationTab.id"
                  >
                    <!-- <TabWindowTimeline
                      v-if="visualizationTab.id === 'timeline'"
                      :key="tabStore.visualizationTabId"
                    />
                    <TabWindowEvents
                      v-if="visualizationTab.id === 'events'"
                      :key="tabStore.visualizationTabId"
                    />
                    <TabWindowRunningDistance
                      v-if="visualizationTab.id === 'running_distance'"
                      :key="tabStore.visualizationTabId"
                    /> -->
                    <component :is="getVisualizationTabComponent(visualizationTab.id)" />
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

    <v-snackbar v-model="showPositionDataActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon />
        <span class="text-h6">{{ positionDataActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showPluginRunActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon />
        <span class="text-h6">{{ pluginRunActionMessage }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showBboxDataActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon />
        <span class="text-h6">{{ bboxDataActionMessage }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
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
import { useTabStore } from "@/stores/tabs";
import { usePositionDataStore } from "@/stores/position_data";
// import * as Keyboard from "../plugins/keyboard";
import VideoPlayer from "@/components/video/VideoPlayer.vue";
import TabWindowPositionData from "@/components/tab-window/TabWindowPositionData.vue";
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
const tabStore = useTabStore();
const positionDataStore = usePositionDataStore();

function getAnalysisTabComponent(tabId) {
  if (tabId === "calibration") {
    return TabWindowCalibration;
  } else if (tabId === "position_data") {
    return TabWindowPositionData;
  } else if (tabId === "heatmap") {
    return TabWindowHeatmap;
  } else {
    return null;
  }
}
function getVisualizationTabComponent(tabId) {
  if (tabId === "timeline") {
    return TabWindowTimeline;
  } else if (tabId === "events") {
    return TabWindowEvents;
  } else if (tabId === "running_distance") {
    return TabWindowRunningDistance;
  } else {
    return null;
  }
}

watch(
  () => tabStore.analysisTabId,
  async (newTabId) => {
    topViewStore.showItems = false;

    await nextTick();

    if (newTabId === "calibration") {
      calibrationAssetStore.showVideoMarker = true;
    } else {
      calibrationAssetStore.showVideoMarker = false;
    }

    if (newTabId === "position_data" || newTabId === "heatmap") {
      playerStore.showBoundingBox = true;
    } else {
      playerStore.showBoundingBox = false;
    }

    topViewStore.showItems = true;
  }
);
onMounted(() => {
  tabStore.visualizationTabId = tabStore.visualizationTabs.find((tab) => tab.id === "timeline")?.id;
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
//         console.log("positionDataTopView", topViewStore.positionDataTopView);
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
      pluginRunActionMessage.value = t("modal.history.delete.success.all");
      resetPluginRunActionSnackbar();
      positionDataStore.pluginRunDeleteAllSuccess = false;
    } else if (del_selected === true) {
      pluginRunActionMessage.value = t("modal.history.delete.success.selected");
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

watch(
  () => [
    calibrationAssetStore.marker,
    calibrationAssetStore.calibrationMatrix,
    bboxesStore.bboxPluginRunId,
  ],
  ([newmarker, newMatrix, newBytetrack]) => {
    console.log("Selected Calibration Asset:", newmarker);
    console.log("Selected Calibration Matrix:", newMatrix);
    console.log("Selected Bytetrack Plugin:", newBytetrack);
  },
  { deep: true }
);

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
