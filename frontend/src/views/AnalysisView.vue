<template>
  <v-main class="main" tabindex="0" ref="main">
    <v-container fluid>
      <ModalMarkerOverlay v-if="markerStore.isAnyMarkerActive" />

      <div
        v-for="m in markerStore.filteredReferenceMarker"
        v-show="markerStore.showReferenceMarker"
        :key="m.id"
        :style="{
          top: m.videoCoordsRel.y * videoStore.videoSize.height + videoStore.videoSize.top + 'px',
          left: m.videoCoordsRel.x * videoStore.videoSize.width + videoStore.videoSize.left + 'px',
        }"
        @mouseenter="markerStore.hoveredReferenceMarker = m.id"
        @mouseleave="markerStore.hoveredReferenceMarker = null"
        class="reference-marker-position"
      />

      <v-row class="ma-n2">
        <v-col cols="6">
          <v-card class="d-flex flex-column flex-nowrap px-2" elevation="2" ref="videoCard">
            <v-row justify="center">
              <v-card-title class="mt-5 mb-n1">
                {{ playerStore.videoName }}
              </v-card-title>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <VideoPlayer @resize="onVideoResize" />
              </v-col>
            </v-row>
          </v-card>
        </v-col>

        <v-col cols="6">
          <div v-if="isLoading" class="loading-container">
            <div class="spinner">
              <i class="mdi mdi-loading mdi-spin" />
            </div>
            <div class="loading-text">Loading...</div>
          </div>
          <v-card v-else class="d-flex flex-column flex-nowrap px-2" elevation="2">
            <v-row class="sticky-tabs-bar" justify="center">
              <v-tabs fixed-tabs slider-color="primary" v-model="tab">
                <v-tab v-for="analysisTab in analysisTabs" :key="analysisTab.id">
                  <span>{{ analysisTab.name }}</span>
                </v-tab>
              </v-tabs>
            </v-row>

            <v-row class="flex-grow-1">
              <v-col>
                <v-tabs-window v-model="tab">
                  <v-tabs-window-item v-for="analysisTab in analysisTabs" :key="analysisTab.id">
                    <AnnotationVisualizer v-if="analysisTab.name === 'Annotation'" />
                    <PosDataVisualizer v-if="analysisTab.name === 'Position Data'" />
                  </v-tabs-window-item>
                </v-tabs-window>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import { useMarkerStore } from "@/stores/marker";
import { useCompAreaStore } from "@/stores/comp_area";
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
import AnnotationVisualizer from "@/components/AnnotationVisualizer.vue";
import ModalMarkerOverlay from "@/components/ModalMarkerOverlay.vue";
// import TranscriptOverview from "@/components/TranscriptOverview.vue";
// import Timeline from "@/components/Timeline.vue";
// import TimeSelector from "@/components/TimeSelector.vue";
// import CurrentEntitiesOverView from "@/components/CurrentEntitiesOverView.vue";
// import ModalTimelineSegmentAnnotate from "@/components/ModalTimelineSegmentAnnotate.vue";
// import ShotsOverview from "@/components/ShotsOverview.vue";
// import WordcloudCard from "@/components/WordcloudCard.vue";
// import VisualizationMenu from "@/components/VisualizationMenu.vue";
// import PersonGraph from "@/components/PersonGraph.vue";
// import ClusterTimelineItemOverview from "@/components/ClusterTimelineItemOverview.vue";

const analysisTabs = ref([
  { id: "1", name: "Annotation" },
  { id: "2", name: "Position Data" },
]);

const route = useRoute();

const videoStore = useVideoStore();
const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();
const markerStore = useMarkerStore();
const compAreaStore = useCompAreaStore();
const bboxesStore = useBboxesStore();
// const timelineStore = useTimelineStore();
// const timelineSegmentStore = useTimelineSegmentStore();
// const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
// const shortcutStore = useShortcutStore();
// const annotationShortcutStore = useAnnotationShortcutStore();
// const clusterTimelineItemStore = useClusterTimelineItemStore();
// const shotStore = useShotStore();

// const fetchPluginTimer = ref(null);
// const selectedShotsProxy = ref(null);
// const selectedFaceClusteringProxy = ref(null);
// const selectedPlaceClusteringProxy = ref(null);
// const selectedTimelineProxy = ref(null);
const tab = ref(0);
// const addedAnnotation = ref(null);
// const labels = ref([]);
// const selectedLabel = ref(null);
// const annotationsLUT = ref({});
// const annotationDialog = ref({ show: false });
const isLoading = ref(true);
const resultCardHeight = ref(0);

// const pluginInProgress = computed(() => pluginRunStore.pluginInProgress);
// const timelines = computed(() => timelineStore.forVideo(route.params.id));
// const timelineNames = computed(() => timelines.value.map((e) => e.name));
// const faceClusters = computed(() =>
//   clusterTimelineItemStore.latestFaceClustering()
// );
// const placeClusters = computed(() =>
//   clusterTimelineItemStore.latestPlaceClustering()
// );
// const shotsList = computed(() =>
//   shotStore.shotsList.map((e) => ({ text: e.name, value: e.index }))
// );

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

// const faceClusteringList = computed(() =>
//   clusterTimelineItemStore.faceClusteringList.map((e) => ({
//     text: e.name,
//     value: e.index,
//   }))
// );

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

// const placeClusteringList = computed(() =>
//   clusterTimelineItemStore.placeClusteringList.map((e) => ({
//     text: e.name,
//     value: e.index,
//   }))
// );

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

const onVideoResize = (size) => {
  resultCardHeight.value = resultCardHeight.$refs?.videoCard?.$el?.clientHeight || 0;

  videoStore.setVideoSize(size);
};

// const onAnnotateSegment = () => {
//   if (timelineSegmentStore.lastSelected) {
//     annotationDialog.show = true;
//   }
// };

//const fetchData = async ({ addResults = true }) => {
// await videoStore.fetch({
//  videoId: route.params.id,
// addResults,
// });
//};

//const fetchPlugin = async () => {
// await pluginRunStore.fetchForVideo({
// videoId: route.params.id,
// fetchResults: true,
// });
//};

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

watch(
  () => isLoading,
  (value) => {
    if (!value) {
      resultCardHeight.value = resultCardHeight.$refs?.videoCard?.$el?.clientHeight || 0;
    }
  }
);

// onMounted(async () => {
//   await fetchData({ addResults: true });
//   isLoading = false;

//   console.log(playerStore.videoUrl);
// });

// onMounted(async () => {
//   try {
//     await fetchData({ addResults: true });
//     isLoading.value = false;
//     console.log(playerStore.videoUrl);
//   } catch (error) {
//     isLoading.value = false;
//     console.log(playerStore.videoUrl);
//     console.error("Fehler im mounted Hook:", error);

//   }
// });

onMounted(async () => {
  try {
    await fetchData({ addResults: true });
  } catch (error) {
    console.error("Fehler beim Laden der Daten:", error);
  } finally {
    isLoading.value = false;
  }
});

const fetchData = async ({ addResults = true }) => {
  try {
    const data = await videoStore.fetch({
      videoId: route.params.id,
      addResults,
    });

    if (!data) {
      throw new Error("Daten konnten nicht abgerufen werden.");
    }
  } catch (error) {
    console.error("Fehler beim Abrufen der Daten:", error);
  }
};

watch(tab, (newTab) => {
  const currentTab = analysisTabs.value[newTab]?.name;

  if (currentTab === "Annotation") {
    markerStore.showReferenceMarker = true;
  } else {
    markerStore.showReferenceMarker = false;
  }

  if (currentTab === "Position Data") {
    markerStore.showBoundingBox = true;
  } else {
    markerStore.showBoundingBox = false;
  }
});

const previousShowReferenceMarker = ref(false);
watch(
  () => markerStore.isAnyMarkerActive,
  (newValue) => {
    if (newValue) {
      previousShowReferenceMarker.value = markerStore.showReferenceMarker;
      markerStore.showReferenceMarker = true;
    } else {
      markerStore.showReferenceMarker = previousShowReferenceMarker.value;
    }
  }
);

watch(
  () => bboxesStore.setBboxData(bboxesStore.bboxPluginRun),
  (newBboxes) => {
    if (newBboxes) {
      bboxesStore.bboxData = newBboxes;
      console.log(bboxesStore.bboxPluginRun);
      console.log("bboxData", bboxesStore.bboxData);
    }
    bboxesStore.bboxDataInterpolated = bboxesStore.interpolateBoundingBoxes(
      bboxesStore.bboxData,
      playerStore.videoFPS,
      1
    );
    console.log("bboxDataInterpolated", bboxesStore.bboxDataInterpolated);
  }
);

watch(
  () => playerStore.videoFPS,
  (newFPS) => {
    console.log("FPS", newFPS);
  }
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
</style>
