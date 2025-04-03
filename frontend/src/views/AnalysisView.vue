<template>
  <v-main class="main" tabindex="0" ref="main">
    <v-container fluid>
      <ModalMarkerOverlay v-if="calibrationAssetStore.isAnyReferenceMarkerActive" />

      <div
        v-for="m in calibrationAssetStore.filteredVideoMarker"
        v-show="calibrationAssetStore.showVideoMarker"
        :key="m.id"
        :style="{
          top: m.videoCoordsRel.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: m.videoCoordsRel.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
        }"
        @mouseenter="calibrationAssetStore.hoveredVideoMarker = m.id"
        @mouseleave="calibrationAssetStore.hoveredVideoMarker = null"
        class="reference-marker-position"
      />
      <div>
        <div
          v-for="(point, index) in calibrationAssetStore.reprojectionPoints"
          v-show="calibrationAssetStore.showVideoMarker"
          :key="index"
          :style="{
            top: point.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
            left: point.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
          }"
          class="reprojection-marker-position"
        />
      </div>

      <v-row class="ma-n2">
        <v-col cols="6">
          <v-card
            class="d-flex flex-column flex-nowrap px-2"
            elevation="2"
            ref="videoCard"
            :style="{ maxHeight: analysisViewHeight + 'px' }"
          >
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
            <!-- <v-row class="mb-2 px-4">
              <TimeSelector width="100%" />
            </v-row> -->
          </v-card>
        </v-col>

        <v-col cols="6">
          <div v-if="isLoading" class="loading-container">
            <div class="spinner">
              <i class="mdi mdi-loading mdi-spin" />
            </div>
            <div class="loading-text">Loading...</div>
          </div>
          <v-card
            v-else
            class="d-flex flex-column flex-nowrap px-2"
            elevation="2"
            ref="topViewCard"
            :style="{ maxHeight: analysisViewHeight + 'px', height: cardHeight + 'px' }"
          >
            <v-row class="sticky-tabs-bar" justify="center">
              <v-tabs fixed-tabs slider-color="primary" v-model="analysisTab">
                <v-tab v-for="analysisTab in analysisTabs" :key="analysisTab.id">
                  <span>{{ analysisTab.name }}</span>
                </v-tab>
              </v-tabs>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <v-tabs-window v-model="analysisTab">
                  <v-tabs-window-item v-for="analysisTab in analysisTabs" :key="analysisTab.id">
                    <CalibrationVisualizer v-if="analysisTab.name === 'Calibration'" />
                    <PosDataVisualizer v-if="analysisTab.name === 'Position Data'" />
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

      <!-- <v-row class="ma-n2">
        <v-col>
          <v-card>test </v-card>
        </v-col>
      </v-row> -->

      <v-row class="ma-n2">
        <v-col>
          <v-card class="d-flex flex-column flex-nowrap px-2" elevation="2" scrollable="False">
            <v-card-title class="pl-2"> Timelines </v-card-title>
            <v-sheet class="px-4">
              <Timeline ref="timeline" :style="{ width: '100%' }" />
            </v-sheet>
          </v-card>
        </v-col>
      </v-row>
      <!-- <ModalTimelineSegmentAnnotate :show.sync="annotationDialog.show" /> -->
    </v-container>
  </v-main>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useRoute } from "vue-router";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useBboxesStore } from "@/stores/bboxes";
// import { useTimelineStore } from "@/stores/timeline";
// import { useTimelineSegmentStore } from "@/stores/timeline_segment";
// import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
// import { useShortcutStore } from "@/stores/shortcut";
// import { useAnnotationShortcutStore } from "@/stores/annotation_shortcut";
// import { useClusterTimelineItemStore } from "@/stores/cluster_timeline_item";
// import { useShotStore } from "@/stores/shot";
// import * as Keyboard from "../plugins/keyboard";
import VideoPlayer from "@/components/VideoPlayer.vue";
import PosDataVisualizer from "@/components/PosDataVisualizer.vue";
import CalibrationVisualizer from "@/components/CalibrationVisualizer.vue";
import ModalMarkerOverlay from "@/components/ModalMarkerOverlay.vue";
// import TranscriptOverview from "@/components/TranscriptOverview.vue";
import Timeline from "@/components/Timeline.vue";
// import TimeSelector from "@/components/TimeSelector.vue";
// import CurrentEntitiesOverView from "@/components/CurrentEntitiesOverView.vue";
// import ModalTimelineSegmentAnnotate from "@/components/ModalTimelineSegmentAnnotate.vue";
// import ShotsOverview from "@/components/ShotsOverview.vue";
// import WordcloudCard from "@/components/WordcloudCard.vue";
// import VisualizationMenu from "@/components/VisualizationMenu.vue";
// import PersonGraph from "@/components/PersonGraph.vue";
// import ClusterTimelineItemOverview from "@/components/ClusterTimelineItemOverview.vue";

const route = useRoute();
const videoStore = useVideoStore();
const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
// const timelineStore = useTimelineStore();
// const timelineSegmentStore = useTimelineSegmentStore();
// const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
// const shortcutStore = useShortcutStore();
// const annotationShortcutStore = useAnnotationShortcutStore();
// const clusterTimelineItemStore = useClusterTimelineItemStore();
// const shotStore = useShotStore();

const analysisTab = ref(0);
const analysisTabs = ref([
  { id: "1", name: "Calibration" },
  { id: "2", name: "Position Data" },
]);
watch(analysisTab, (newTab) => {
  const currentTab = analysisTabs.value[newTab]?.name;

  if (currentTab === "Annotation") {
    calibrationAssetStore.showVideoMarker = true;
  } else {
    calibrationAssetStore.showVideoMarker = false;
  }

  if (currentTab === "Position Data") {
    bboxesStore.showBoundingBox = true;
  } else {
    bboxesStore.showBoundingBox = false;
  }
});

const isLoading = ref(true);
const fetchData = async ({ addResults = true }) => {
  try {
    await videoStore.fetch({
      videoId: route.params.id,
      addResults,
    });
  } catch (error) {
    console.error("Fehler beim Abrufen der Daten:", error);
  }
};
onMounted(async () => {
  try {
    await fetchData({ addResults: true });
  } catch (error) {
    console.error("Fehler beim Laden der Daten:", error);
  } finally {
    isLoading.value = false;
  }
});

const videoCard = ref(null);
const topViewCard = ref(null);
const windowHeight = ref(window.innerHeight);
const analysisViewHeight = ref(null);
const cardHeight = ref(null);
const setCardHeight = () => {
  windowHeight.value = window.innerHeight;
  nextTick(() => {
    analysisViewHeight.value = window.innerHeight - 64 - 40;
    cardHeight.value = videoCard.value.$el.offsetHeight;
  });
};
onMounted(() => {
  setCardHeight();
  window.addEventListener("resize", setCardHeight);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", setCardHeight);
});
watch([videoCard, topViewCard, windowHeight], setCardHeight, { flush: "post" });

const previousShowVideoMarker = ref(false);
watch(
  () => calibrationAssetStore.isAnyReferenceMarkerActive,
  (newValue) => {
    if (newValue) {
      previousShowVideoMarker.value = calibrationAssetStore.showVideoMarker;
      calibrationAssetStore.showVideoMarker = true;
    } else {
      calibrationAssetStore.showVideoMarker = previousShowVideoMarker.value;
    }
  }
);

watch(
  () => bboxesStore.setBboxData(bboxesStore.bboxPluginRun),
  (newBboxes) => {
    if (newBboxes && newBboxes.length > 0) {
      // const groupedData = {};
      // newBboxes.forEach((position) => {
      //   const { time } = position;
      //   if (!groupedData[time]) {
      //     groupedData[time] = [];
      //   }
      //   groupedData[time].push(position);
      // });
      // bboxesStore.bboxData = groupedData;
      bboxesStore.bboxData = newBboxes;
      // console.log(bboxesStore.bboxPluginRun);
      // console.log("bboxData", bboxesStore.bboxData);

      bboxesStore.bboxDataInterpolated = bboxesStore.interpolateBboxData(
        newBboxes,
        playerStore.videoFPS,
        25
      );
      const groupedDataInterpolated = {};
      bboxesStore.bboxDataInterpolated.forEach((position) => {
        const { time } = position;
        if (!groupedDataInterpolated[time]) {
          groupedDataInterpolated[time] = [];
        }
        groupedDataInterpolated[time].push(position);
      });
      bboxesStore.bboxDataInterpolated = groupedDataInterpolated;
      // console.log("bboxDataInterpolated", bboxesStore.bboxDataInterpolated);
    }
  }
);

// const timelines = computed(() => timelineStore.forVideo(route.params.id));
// const timelineNames = computed(() => timelines.value.map((e) => e.name));

// const shotsList = computed(() =>
//   shotStore.shotsList.map((e) => ({ text: e.name, value: e.index }))
// );
// const selectedShotsProxy = ref(null);
// const selectedShots = computed({
//   get() {
//     const selectedShots = shotStore.selectedShots;
//     return selectedShotsProxy === null
//       ? selectedShots
//       : selectedShotsProxy;
//   },
//   set(val) {
//     selectedShotsProxy = val;
//     shotStore.setSelectedShots({ shotTimeline: val });
//   },
// });

// const faceClusteringList = computed(() =>
//   clusterTimelineItemStore.faceClusteringList.map((e) => ({
//     text: e.name,
//     value: e.index,
//   }))
// );
// const faceClusters = computed(() =>
//   clusterTimelineItemStore.latestFaceClustering()
// );
// const selectedFaceClusteringProxy = ref(null);
// const selectedFaceClustering = computed({
//   get() {
//     const selectedFaceClustering =
//       clusterTimelineItemStore.selectedFaceClustering;
//     return selectedFaceClusteringProxy === null
//       ? selectedFaceClustering
//       : selectedFaceClusteringProxy;
//   },
//   set(val) {
//     selectedFaceClusteringProxy = val;
//     clusterTimelineItemStore.setSelectedFaceClustering({ pluginRunId: val });
//   },
// });

// const placeClusteringList = computed(() =>
//   clusterTimelineItemStore.placeClusteringList.map((e) => ({
//     text: e.name,
//     value: e.index,
//   }))
// );
// const placeClusters = computed(() =>
//   clusterTimelineItemStore.latestPlaceClustering()
// );
// const selectedPlaceClusteringProxy = ref(null);
// const selectedPlaceClustering = computed({
//   get() {
//     const selectedPlaceClustering =
//       clusterTimelineItemStore.selectedPlaceClustering;
//     return selectedPlaceClusteringProxy === null
//       ? selectedPlaceClustering
//       : selectedPlaceClusteringProxy;
//   },
//   set(val) {
//     selectedPlaceClusteringProxy = val;
//     clusterTimelineItemStore.setSelectedPlaceClustering({
//       pluginRunId: val,
//     });
//   },
// });

// const selectedTimelineProxy = ref(null);
// const selectedTimeline = computed({
//   get() {
//     return selectedTimelineProxy === null
//       ? timelines.value[0]
//       : selectedTimelineProxy;
//   },
//   set(val) {
//     selectedTimelineProxy = val;
//   },
// });

// const fetchPluginTimer = ref(null);
// const fetchPlugin = async () => {
//   await pluginRunStore.fetchForVideo({
//   videoId: route.params.id,
//   fetchResults: true,
//   });
// };
// const pluginInProgress = computed(() => pluginRunStore.pluginInProgress);
// watch(
//   pluginInProgress,
//   (newState) => {
//     if (newState) {
//       fetchPluginTimer = setInterval(() => {
//         fetchPlugin({ addResults: false });
//       }, 1000);
//     } else {
//       clearInterval(fetchPluginTimer);
//     }
//   }
// );

// const annotationDialog = ref({ show: false });
// const onAnnotateSegment = () => {
//   if (timelineSegmentStore.lastSelected) {
//     annotationDialog.show = true;
//   }
// };

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
</script>

<style scoped>
.logo > img {
  max-height: 56px;
}

.sticky-tabs-bar {
  position: sticky;
  top: 0;
  z-index: 1;
  background-color: white;
  /* Adjust the background color if needed */
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

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
}

.spinner {
  font-size: 48px;
  color: #ac1414;
}

.loading-text {
  margin-top: 10px;
  font-size: 18px;
}

.reference-marker-position {
  position: fixed;
  width: 12px;
  height: 12px;
  background-color: red;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
}
.reprojection-marker-position {
  position: fixed;
  width: 5px;
  height: 5px;
  background-color: blue;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 1001;
}
</style>
