<template>
  <div style="width: 100%; min-height: 100px">
    <v-row>
      <v-col cols="3" style="margin: 0px; padding: 0px; padding-right: 10px">
        <div style="margin-top: 14px; margin-bottom: 4px">
          <v-menu location="bottom">
            <template v-slot:activator="{ props }">
              <v-btn v-bind="props" style="height: 40px; width: 100%">
                <v-icon left>mdi-cog</v-icon>
                {{ $t("modal.timeline.menu.title") }}
              </v-btn>
            </template>
            <v-list class="py-0" density="compact" width="200">
              <v-list-item class="menu-item" @click="showModalCreateTimeline = true">
                <v-icon size="small" class="mt-n1">mdi-plus</v-icon>
                {{ $t("modal.timeline.create.title") }}
              </v-list-item>
              <v-list-item class="menu-item" @click="showModalImportTimeline = true">
                <v-icon size="small" class="mt-n1">mdi-import</v-icon>
                {{ $t("modal.timeline.import.title") }}
              </v-list-item>
            </v-list>
          </v-menu>
          <ModalTimelineCreate v-model="showModalTimelineCreate" />
          <ModalTimelineImport v-model="showModalTimelineImport" />
        </div>

        <Draggable
          v-model="timelineHierarchy"
          :defaultOpen="false"
          :indent="25"
          :keepPlaceholder="true"
        >
          <template v-slot:default="{ node, stat }">
            <v-card style="height: 60px" class="my-1">
              <v-row class="mt-4 ml-3 mr-2">
                <v-icon
                  v-if="stat.children && stat.children.length"
                  @click="toggleOpen(stat)"
                  class="ml-n1 mr-1"
                  color="grey darken-1"
                >
                  {{ stat.open ? "mdi-minus" : "mdi-plus" }}
                </v-icon>
                <span class="text-h6 mt-n1">{{ node.text }}</span>

                <v-spacer></v-spacer>

                <v-menu location="end">
                  <template v-slot:activator="{ props }">
                    <v-btn icon variant="plain" v-bind="props" density="compact">
                      <v-icon>mdi-dots-vertical</v-icon>
                    </v-btn>
                  </template>
                  <v-list class="py-0" density="compact">
                    <v-list-item
                      class="menu-item"
                      @click="showModalTimelineCopy = true"
                      :timeline="node.id"
                    >
                      <v-icon left>{{ "mdi-content-copy" }}</v-icon>
                      {{ $t("modal.timeline.duplicate.link") }}
                    </v-list-item>
                    <v-list-item
                      class="menu-item"
                      @click="showModalTimelineRename = true"
                      :timeline="node.id"
                    >
                      <v-icon left>{{ "mdi-pencil" }}</v-icon>
                      {{ $t("modal.timeline.rename.link") }}
                    </v-list-item>
                    <!-- <v-list-item class="menu-item" v-if="node.type == 'PLUGIN_RESULT'" @click="showModalTimelineVisualization = true" :timeline="node.id">
                    </v-list-item> -->
                    <v-list-item
                      class="menu-item"
                      v-if="node.type == 'PLUGIN_RESULT'"
                      @click="showModalExportResult = true"
                      :timeline="node.id"
                    >
                    </v-list-item>
                    <v-list-item
                      class="menu-item"
                      @click="showModalTimelineDelete = true"
                      :timeline="node.id"
                    >
                      <v-icon left>{{ "mdi-trash-can-outline" }}</v-icon>
                      {{ $t("modal.timeline.delete.link") }}
                    </v-list-item>
                  </v-list>
                </v-menu>
                <ModalTimelineCopy v-model="showModalTimelineCopy" />
                <ModalTimelineRename v-model="showModalTimelineRename" />
                <!-- <ModalTimelineVisualization
                  :timeline="node.id"
                  v-model="showModalTimelineVisualization"
                /> -->
                <ModalExportResult v-model="showModalExportResult" />
                <ModalTimelineDelete v-model="showModalTimelineDelete" />
              </v-row>
            </v-card>
          </template>
          <template v-slot:placeholder="{}">
            <div class="draggable-placeholder-inner"></div>
          </template>
        </Draggable>
      </v-col>

      <v-col ref="container" cols="9" style="margin: 0; padding: 0; border: 2px solid red">
        <canvas style="width: 100%; border: 2px solid blue" ref="canvas" resize> </canvas>
      </v-col>
    </v-row>

    <!-- <v-tooltip
      top
      v-model="timelineTooltip.show"
      :position-x="timelineTooltip.x"
      :position-y="timelineTooltip.y"
      absolute
    >
      <span>{{ timelineTooltip.label }}</span>
    </v-tooltip>

    <v-menu
      v-model="segmentMenu.show"
      :position-x="segmentMenu.x"
      :position-y="segmentMenu.y - 10"
      absolute
      offset-y
    >
      <v-list>
        <v-list-item link v-on:click="onAnnotateSelection">
          <v-list-item-title>
            <v-icon left>{{ "mdi-pencil" }}</v-icon>
            {{ $t("timelineSegment.annotate.selection") }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item link v-on:click="onAnnotateSelectionRange">
          <v-list-item-title>
            <v-icon left>{{ "mdi-pencil" }}</v-icon>
            {{ $t("timelineSegment.annotate.range") }}
          </v-list-item-title>
        </v-list-item> -->

    <!-- <v-list-item link v-on:click="onDeleteSegment">
          <v-list-item-title>
            <v-icon left>{{ "mdi-delete" }}</v-icon>
            {{ $t("timelineSegment.delete") }}
          </v-list-item-title>
        </v-list-item> -->

    <!-- <v-list-item link v-on:click="onSplitSegment">
          <v-list-item-title>
            <v-icon left>{{ "mdi-content-cut" }}</v-icon>
            {{ $t("timelineSegment.split") }}
          </v-list-item-title>
        </v-list-item> -->
    <!-- <v-list-item link v-on:click="onMergeSelection">
          <v-list-item-title>
            <v-icon left>{{ "mdi-pencil" }}</v-icon>
            {{ $t("timelineSegment.merge.selection") }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item link v-on:click="onMergeSelectionRange">
          <v-list-item-title>
            <v-icon left>{{ "mdi-pencil" }}</v-icon>
            {{ $t("timelineSegment.merge.range") }}
          </v-list-item-title>
        </v-list-item> -->

    <!-- <v-list-item link v-on:click="onMergeSegmentsLeft">
          <v-list-item-title>
            <v-icon left>{{ "mdi-arrow-expand-left" }}</v-icon>
            {{ $t("timelineSegment.mergeleft") }}
          </v-list-item-title>
        </v-list-item>

        <v-list-item link v-on:click="onMergeSegmentsRight">
          <v-list-item-title>
            <v-icon left>{{ "mdi-arrow-expand-right" }}</v-icon>
            {{ $t("timelineSegment.mergeright") }}
          </v-list-item-title>
        </v-list-item>

        <v-list-item
          v-if="selectedTimelineSegments.length > 1"
          link
          v-on:click="onMergeSegments"
        >
          <v-list-item-title>
            <v-icon left>{{ "mdi-merge" }}</v-icon>
            {{ $t("timelineSegment.merge") }}
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <ModalTimelineSegmentAnnotate
      :show.sync="annotationDialog.show"
      :annotate-range="annotationDialog.annotateRange"
      :timeline-id="annotationDialog.timelineId"
    />  -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
import * as PIXI from "pixi.js";
import { BaseTree, Draggable } from "@he-tree/vue";
import { mapStores } from "pinia";
import { useTimelineStore } from "@/stores/timeline";
import { useTimelineSegmentStore } from "@/stores/timeline_segment";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { useAnnotationStore } from "@/stores/annotation";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import ModalTimelineRename from "@/components/ModalTimelineRename.vue";
import ModalTimelineCopy from "@/components/ModalTimelineCopy.vue";
import ModalTimelineDelete from "@/components/ModalTimelineDelete.vue";
import ModalExportResult from "@/components/ModalExportResult.vue";
import ModalCreateTimModalTimelineCreateeline from "@/components/ModalTimelineCreate.vue";
// import ModalTimelineVisualization from "@/components/ModalTimelineVisualization.vue";
import ModalTimelineImport from "@/components/ModalTimelineImport.vue";
// import ModalTimelineSegmentAnnotate from "@/components/ModalTimelineSegmentAnnotate.vue";
import {
  AnnotationTimeline,
  ColorTimeline,
  ScalarLineTimeline,
  ScalarColorTimeline,
  TimeScale,
  TimeBar,
  HistTimeline,
  // generateFont,
} from "../plugins/draw";

const timelineStore = useTimelineStore();
const timelineSegmentStore = useTimelineSegmentStore();
const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
const annotationStore = useAnnotationStore();
const annotationCategoryStore = useAnnotationCategoryStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const pluginRunResultStore = usePluginRunResultStore();

const props = defineProps({
  headerWidth: { type: Number, default: 0 },
  scaleHeight: { type: Number, default: 40 },
  timelineHeight: { type: Number, default: 50 },
  gap: { type: Number, default: 4 },
  headerStyle: {
    type: Object,
    default: () => ({
      shadowColor: "rgba(0, 0, 0, 0.25)",
      shadowBlur: 6,
      shadowOffset: { x: 0, y: 3 },
      fillColor: "white",
    }),
  },
  timeStyle: {
    type: Object,
    default: () => ({
      shadowColor: "rgba(0, 0, 0, 0.25)",
      shadowBlur: 6,
      shadowOffset: { x: 0, y: 3 },
      fillColor: "white",
    }),
  },
  timelineStyle: {
    type: Object,
    default: () => ({
      shadowColor: "rgba(0, 0, 0, 0.25)",
      shadowBlur: 6,
      shadowOffset: { x: 0, y: 3 },
      fillColor: "white",
    }),
  },
  segmentStyle: {
    type: Object,
    default: () => ({
      fillColor: "red",
    }),
  },
  width: Number,
});

const enabled = ref(false);
const app = ref(null);
const timelineObjects = ref([]);
const timeScaleObjects = ref([]);
const timeBarsObjects = ref([]);
const timelineHierarchy = ref([
  { text: "Projects", open: false, children: [{ text: "P1" }, { text: "P2" }, { text: "P3" }] },
  { text: "Photos", open: false },
  { text: "Videos", open: false },
]);
const containerWidth = ref(100);
const containerHeight = ref(100);
const lastTimestamp = ref(0);
const timelineSegments = ref([]);

const annotationDialog = ref({
  show: false,
  annotateRange: false,
  timelineId: null,
  timelineSegmentId: null,
});

const dragSelection = ref({
  x: null,
  start: null,
  end: null,
  dragging: false,
});

const segmentMenu = ref({
  show: false,
  x: null,
  y: null,
  selected: null,
});

const timelineTooltip = ref({
  show: false,
  x: null,
  y: null,
  selected: null,
  label: null,
  enabled: false,
});

const menu = ref({
  show: false,
  x: null,
  y: null,
  selected: null,
});

const showModalTimelineCreate = ref(false);
const showModalTimelineImport = ref(false);
const showModalTimelineCopy = ref(false);
const showModalTimelineRename = ref(false);
const showModalTimelineVisualization = ref(false);
const showModalExportResult = ref(false);
const showModalTimelineDelete = ref(false);

const toggleOpen = (node) => {
  node.open = !node.open;
};

// const startDragging = (event, x, time) => {
//   dragSelection.x = x;
//   dragSelection.start = time;
//   dragSelection.dragging = true;
//   timelineStore.setSelectedTimeRangeStart(time);
//   timelineStore.setSelectedTimeRangeEnd(null);
//   event.stopPropagation();
// };

// const moveDragging = (event, x, time) => {
//   if (!dragSelection.dragging || Math.abs(x - dragSelection.x) < 2) return;
//   dragSelection.end = time;
//   timelineStore.setSelectedTimeRangeEnd(time);
//   event.stopPropagation();
// };

// const endDragging = (event, x, time) => {
//   dragSelection.dragging = false;
//   if (Math.abs(x - dragSelection.x) < 2) {
//     timelineStore.setSelectedTimeRangeEnd(null);
//     return;
//   }
//   dragSelection.end = time;
//   timelineStore.setSelectedTimeRangeEnd(time);
//   event.stopPropagation();
// };

// const getTimeline = (timelineId) => {
//   return timelineObjects.value.find((obj) => obj.timelineId === timelineId) || null;
// };

// const computeTimelineX = () => {
//   return timeToX(startTime);
// };

// const computeTimelineY = (index) => {
//   return (gap + timelineHeight) * index + scaleHeight + 2 * gap;
// };

const nodeOpenChanged = async (node) => {
  await timelineStore.setCollapse({ timelineId: node.id, collapse: !node.open });
};

const change = async (node) => {
  function timelineOrder(elem) {
    return elem.reduce((hierarchy, e) => hierarchy.concat(e.id, timelineOrder(e.children)), []);
  }

  let order = timelineOrder(timelineHierarchy);
  await timelineStore.setOrder({ order });
  await timelineStore.setParent({ timelineId: node.id, parentId: node.parent.id });
};

// const draw = () => {
//   drawTimelines();
//   drawScale();
//   drawTimeBar();
// };

// const drawTimeBar = () => {
//   if (timeBarsContainer.value) app.value.stage.removeChild(timeBarsContainer.value);
//   timeBarsContainer.value = new PIXI.Container();
//   const x = timeToX(startTime);
//   const width = timeToX(endTime) - x;
//   let timeline = new TimeBar(x, gap, width, window.innerHeight, time, startTime, endTime);
//   timeBarsContainer.value.addChild(timeline);
//   app.value.stage.addChild(timeBarsContainer.value);
// };

// const drawScale = () => {
//   if (timeScalesContainer.value) app.value.stage.removeChild(timeScalesContainer.value);
//   timeScalesContainer.value = new PIXI.Container();
//   const x = timeToX(startTime);
//   const width = timeToX(endTime) - x;
//   let timeline = new TimeScale(x, gap, width, scaleHeight, startTime, endTime);
//   timeScalesContainer.value.addChild(timeline);
//   app.value.stage.addChild(timeScalesContainer.value);
// };

// const drawTimelines = () => {
//   if (timelinesContainer.value) app.value.stage.removeChild(timelinesContainer.value);
//   timelinesContainer.value = new PIXI.Container();
//   timelineObjects.value = [];

//   timelines.forEach((e, i) => {
//     const x = timeToX(startTime);
//     const y = computeTimelineY(i);
//     const timeline = drawTimeline(e);
//     if (timeline) {
//       timeline.x = x;
//       timeline.y = y;
//       timelinesContainer.value.addChild(timeline);
//       timelineObjects.value.push(timeline);
//     }
//   });
//   app.value.stage.addChild(timelinesContainer.value);
// };

// const drawTimeline = (timeline) => {
//   const width = timeToX(endTime) - timeToX(startTime);
//   const height = timelineHeight;

//   if (timeline.type === "ANNOTATION" || timeline.type === "TRANSCRIPT") {
//     return drawAnnotationTimeline(timeline, width, height);
//   } else if (timeline.type === "PLUGIN_RESULT") {
//     return drawGraphicTimeline(timeline, width, height);
//   } else {
//     console.error(`Unknown timeline type ${timeline.type}`);
//   }
//   return null;
// };

// const drawAnnotationTimeline = (timeline, width, height) => {
//   const selection = selectedTimelineSegments.value
//     .filter((selectedTimelineSegment) => timeline.id === selectedTimelineSegment.timeline_id)
//     .map((s) => s.id);

//   let segments = timelineSegmentStore.forTimeline(timeline.id);
//   segments.forEach((s) => {
//     let annotations = timelineSegmentAnnotationStore.forTimelineSegment(s.id);
//     annotations.forEach((a) => {
//       a.annotation = annotationStore.get(a.annotation_id);
//     });
//     annotations.forEach((a) => {
//       a.category = annotationCategoryStore.get(a.category_id);
//     });
//     s.annotations = annotations;
//   });

//   timeline.segments = segments;

//   let drawnTimeline = new AnnotationTimeline({
//     timelineId: timeline.id,
//     width: width,
//     height: height,
//     startTime: startTime.value,
//     endTime: endTime.value,
//     duration: duration.value,
//     data: timeline,
//     renderer: app.value.renderer,
//     segmentSelection: selection,
//   });

//   drawnTimeline.interactive = true;
//   drawnTimeline.buttonMode = true;

//   drawnTimeline.on("rightdown", (ev) => {
//     const point = mapToGlobal(ev.data.global);
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const segment = drawnTimeline.getSegmentOnPosition(x).segment;

//     segmentMenu.value.show = true;
//     segmentMenu.value.x = point.x;
//     segmentMenu.value.y = point.y;
//     segmentMenu.value.selected = segment.id;

//     nextTick(() => {
//       showMenu.value = true;
//       annotationDialog.value.timelineId = timeline.id;
//       annotationDialog.value.timelineSegmentId = segment.id;
//     });

//     ev.stopPropagation();
//   });

//   drawnTimeline.on("click", (ev) => {
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const segment = drawnTimeline.getSegmentOnPosition(x);
//     if (segment === null) {
//       return;
//     }
//     if (!ev.data.originalEvent.ctrlKey) {
//       timelineSegmentStore.clearSelection();
//       timelineStore.clearSelection();
//     }
//     timelineStore.addToSelection(timeline.id);
//     if (segment) {
//       timelineSegmentStore.addToSelection(segment.segment.id);
//     }
//     const targetTime = xToTime(ev.data.global.x);
//     playerStore.setTargetTime(targetTime);
//     ev.stopPropagation();
//   });

//   drawnTimeline.on("mousedown", (ev) => {
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const time = drawnTimeline.xToTime(x);
//     startDragging(ev, x, time);
//   });

//   drawnTimeline.on("mousemove", (ev) => {
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const time = drawnTimeline.xToTime(x);
//     moveDragging(ev, x, time);
//   });

//   drawnTimeline.on("mouseup", (ev) => {
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const time = drawnTimeline.xToTime(x);
//     endDragging(ev, x, time);
//   });

//   drawnTimeline.on("mouseupoutside", (ev) => {
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const time = drawnTimeline.xToTime(x);
//     endDragging(ev, x, time);
//   });

//   drawnTimeline.on("pointerover", (ev) => {
//     timelineTooltip.value.enabled = true;
//     const x = ev.data.getLocalPosition(drawnTimeline).x;
//     const segment = drawnTimeline.getSegmentOnPosition(x);
//     if (segment === null) {
//       return;
//     }

//     const tooltipPoint = {
//       x: ev.data.global.x,
//       y: ev.data.global.y,
//     };
//     const point = mapToGlobal(tooltipPoint);
//     timelineTooltip.value.show = true;
//     timelineTooltip.value.x = point.x;
//     timelineTooltip.value.y = point.y;
//     timelineTooltip.value.selected = segment.segment.id;

//     const annotations = segment.segment.annotations.map((e) => e.annotation.name);
//     timelineTooltip.value.label =
//       segment.segment.annotations.length > 0
//         ? annotations.join("; ")
//         : "Segment " + (segment.index + 1);
//   });

//   drawnTimeline.on("pointerout", () => {
//     timelineTooltip.value.enabled = false;
//     timelineTooltip.value.show = false;
//   });

//   drawnTimeline.on("pointermove", (ev) => {
//     if (timelineTooltip.value.enabled) {
//       const localPosition = ev.data.getLocalPosition(drawnTimeline);
//       const x = localPosition.x;
//       if (localPosition.y < 0 || localPosition.y > drawnTimeline.height) {
//         return;
//       }
//       const segment = drawnTimeline.getSegmentOnPosition(x);
//       if (segment === null) {
//         timelineTooltip.value.label = "";
//         timelineTooltip.value.show = false;
//         return;
//       }

//       timelineTooltip.value.show = true;
//       const tooltipPoint = {
//         x: ev.data.global.x,
//         y: ev.data.global.y,
//       };
//       const point = mapToGlobal(tooltipPoint);

//       timelineTooltip.value.x = point.x;
//       timelineTooltip.value.y = point.y;

//       const annotations = segment.segment.annotations.map((e) => e.annotation.name);
//       timelineTooltip.value.label =
//         segment.segment.annotations.length <= 0
//           ? "Segment " + (segment.index + 1)
//           : annotations.join("; ");
//     }
//   });

//   return drawnTimeline;
// };

// const drawGraphicTimeline = (timeline, width, height) => {
//   let drawnTimeline = null;
//   if ("plugin_run_result_id" in timeline) {
//     const result = pluginRunResultStore.get(timeline.plugin_run_result_id);

//     if (result === undefined) {
//       return null;
//     } else {
//       timeline.plugin = { data: result.data, type: result.type };
//     }

//     if (timeline.visualization == "COLOR") {
//       drawnTimeline = new ColorTimeline({
//         timelineId: timeline.id,
//         width: width,
//         height: height,
//         startTime: startTime.value,
//         endTime: endTime.value,
//         duration: duration.value,
//         data: timeline.plugin.data,
//         renderer: app.renderer,
//       });
//     }

//     if (timeline.visualization == "SCALAR_COLOR") {
//       drawnTimeline = new ScalarColorTimeline({
//         timelineId: timeline.id,
//         width: width,
//         height: height,
//         startTime: startTime.value,
//         endTime: endTime.value,
//         duration: duration.value,
//         data: timeline.plugin.data,
//         renderer: app.renderer,
//         colormap: timeline.colormap,
//         colormapInverse: timeline.colormap_inverse,
//       });
//     }

//     if (timeline.visualization == "SCALAR_LINE") {
//       drawnTimeline = new ScalarLineTimeline({
//         timelineId: timeline.id,
//         width: width,
//         height: height,
//         startTime: startTime.value,
//         endTime: endTime.value,
//         duration: duration.value,
//         data: timeline.plugin.data,
//         renderer: app.renderer,
//         colormap: timeline.colormap,
//         colormapInverse: timeline.colormap_inverse,
//       });
//     }

//     if (timeline.visualization == "HIST") {
//       drawnTimeline = new HistTimeline({
//         timelineId: timeline.id,
//         width: width,
//         height: height,
//         startTime: startTime.value,
//         endTime: endTime.value,
//         duration: duration.value,
//         data: timeline.plugin.data,
//         renderer: app.renderer,
//         colormap: timeline.colormap,
//         colormapInverse: timeline.colormap_inverse,
//       });
//     }
//   }

//   if (drawnTimeline) {
//     drawnTimeline.interactive = true;
//     drawnTimeline.buttonMode = true;
//     drawnTimeline.on("click", (ev) => {
//       if (!ev.data.originalEvent.ctrlKey) {
//         timelineSegmentStore.clearSelection();
//         timelineStore.clearSelection();
//       }
//       timelineStore.addToSelection(timeline.id);
//       const targetTime = xToTime(ev.data.global.x);
//       playerStore.setTargetTime(targetTime);
//       ev.stopPropagation();
//     });
//   }
//   return drawnTimeline;
// };

// const addSegmentSelection = (selectedTimelineSegments) => {
//   if (
//     selectedTimelineSegments &&
//     selectedTimelineSegments.length > 0 &&
//     timelineObjects.value &&
//     timelineObjects.value.length > 0
//   ) {
//     selectedTimelineSegments.forEach((selectedTimelineSegment) => {
//       timelineObjects.value
//         .filter(
//           (timelineObject) => timelineObject.timelineId === selectedTimelineSegment.timeline_id
//         )
//         .filter((timelineObject) => typeof timelineObject.addSegmentSelection === "function")
//         .forEach((timelineObject) => {
//           timelineObject.addSegmentSelection(selectedTimelineSegment.id);
//         });
//     });
//   }
// };

// const removeSegmentSelection = (selectedTimelineSegments) => {
//   if (
//     selectedTimelineSegments &&
//     selectedTimelineSegments.length > 0 &&
//     timelineObjects.value &&
//     timelineObjects.value.length > 0
//   ) {
//     selectedTimelineSegments.forEach((selectedTimelineSegment) => {
//       timelineObjects.value
//         .filter(
//           (timelineObject) => timelineObject.timelineId === selectedTimelineSegment.timeline_id
//         )
//         .filter((timelineObject) => typeof timelineObject.removeSegmentSelection === "function")
//         .forEach((timelineObject) => {
//           timelineObject.removeSegmentSelection(selectedTimelineSegment.id);
//         });
//     });
//   }
// };

// const timeToX = (time) => {
//   return timeScale.value * (time - startTime.value);
// };

// const xToTime = (x) => {
//   return x / timeScale.value + startTime.value;
// };

const canvas = ref(null);

const mapToGlobal = (point) => {
  const screenRect = app.screen;
  const canvasRect = canvas.value.getBoundingClientRect();

  const windowsX = (point.x / screenRect.width) * canvasRect.width + canvasRect.x;
  const windowsY = (point.y / screenRect.height) * canvasRect.height + canvasRect.y;

  return { x: windowsX, y: windowsY };
};

// const onAnnotateSelection = () => {
//   annotationDialog.value.show = true;
//   annotationDialog.value.annotateRange = false;
// };

// const onAnnotateSelectionRange = () => {
//   annotationDialog.value.show = true;
//   annotationDialog.value.annotateRange = true;
// };

// const onMergeSelection = () => {};

// const onMergeSelectionRange = () => {};

// const onSplitSegment = () => {
//   timelineSegmentStore.split({
//     timelineSegmentId: segmentMenu.selected,
//     time: playerStore.targetTime,
//   });
// };

// const onMergeSegments = () => {
//   const timelineSegmentIds = timelineSegmentStore.selected.map((e) => e.id);
//   timelineSegmentStore.merge({
//     timelineSegmentIds: timelineSegmentIds,
//   });
// };

// const onMergeSegmentsLeft = () => {
//   if (timelineSegmentStore.selected.length <= 0) {
//     return;
//   }
//   const timelineSegmentId =
//     timelineSegmentStore.selected[timelineSegmentStore.selected.length - 1].id;
//   const previousTimelineSegment = timelineSegmentStore.getPreviousOnTimeline(timelineSegmentId);
//   if (previousTimelineSegment) {
//     timelineSegmentStore.merge({
//       timelineSegmentIds: [timelineSegmentId, previousTimelineSegment.id],
//     });
//   }
// };

// const onMergeSegmentsRight = () => {
//   if (timelineSegmentStore.selected.length <= 0) {
//     return;
//   }
//   const timelineSegmentId =
//     timelineSegmentStore.selected[timelineSegmentStore.selected.length - 1].id;
//   const nextTimelineSegment = timelineSegmentStore.getNextOnTimeline(timelineSegmentId);
//   if (nextTimelineSegment) {
//     timelineSegmentStore.merge({
//       timelineSegmentIds: [timelineSegmentId, nextTimelineSegment.id],
//     });
//   }
// };

// const duration = computed(() => playerStore.videoDuration);

// const isLoading = computed(() => videoStore.isLoading);

// const startTime = computed(() => playerStore.selectedTimeRange.start);

// const endTime = computed(() => playerStore.selectedTimeRange.end);

// const timelines = computed(() => timelineStore.all);

// const timelinesAdded = computed(() => timelineStore.added);

// const timelinesChanged = computed(() => timelineStore.changed);

// const timelinesDeleted = computed(() => timelineStore.deleted);

// const selectedTimelineSegments = computed(() => timelineSegmentStore.selected);

// const timeScale = computed(() => containerWidth / (endTime.value - startTime.value));

// const computedHeight = computed(
//   () => timelines.value.length * (timelineHeight + gap) + scaleHeight + 3 * gap
// );

// const time = computed(() => playerStore.currentTime);

// // Watchers
// watch(isLoading, (newValue) => {
//   if (newValue === false) {
//     enabled.value = true;
//   }
// });

// watch(timelines, (values) => {
//   function findChildren(elem, parent) {
//     let hierarchy = [];
//     elem
//       .sort((a, b) => a.order > b.order)
//       .forEach((e) => {
//         if (e.parent_id == parent) {
//           let children = findChildren(elem, e.id);
//           hierarchy.push({
//             id: e.id,
//             text: e.name,
//             children: children,
//             type: e.type,
//             open: !e.collapse,
//           });
//         }
//       });
//     return hierarchy;
//   }
//   timelineHierarchy.value = findChildren(values, null);
// });

// watch(selectedTimelineSegments, (newSelection, oldSelection) => {
//   removeSegmentSelection(oldSelection);
//   addSegmentSelection(newSelection);
// });

const container = ref(null);
onMounted(() => {
  containerWidth.value = container.value.clientWidth;
  app.value = new PIXI.Application();
  app.value.init({
    width: containerWidth.value,
    height: containerHeight.value,
    backgroundAlpha: 0.0,
    canvas: canvas.value,
    resizeTo: canvas.value,
  });
  console.log("app_post", app.value);

  canvas.value.addEventListener("contextmenu", (e) => {
    e.preventDefault();
  });

  // generate bitmapfont
  // generateFont();
  // nextTick(() => {
  //   if (app.value) {
  //     app.value.ticker.add(() => {
  //       // Deine Logik hier
  //     });
  //   } else {
  //     console.error("Ticker is not available yet");
  //   }
  // });
});
</script>

<style scoped>
.draggable-placeholder-inner {
  border: 2px solid #ae1313;
  background: #ae131377;
  border-radius: 6px;
  height: 60px;
  margin: 4px 0;
}

.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}
</style>

<!-- app.value.ticker.add(() => { if (!enabled.value) { return; } if (container.value) { if
(container.value.clientWidth != containerWidth.value) { containerWidth.value =
container.value.clientWidth; draw(); } if (computedHeight.value != containerHeight.value) {
containerHeight.value = computedHeight.value; container.value.style.height = computedHeight.value;
canvas.value.height = computedHeight.value; app.value.resize(); draw(); } } let latestTimestamp =
-1; // handle timeline deletion timelinesDeleted.value.forEach((data) => { const [date, id] = data;
if (date <= lastTimestamp.value) { return; } if (date > latestTimestamp) { latestTimestamp = date; }
const timelineObject = getTimeline(id); if (timelineObject) {
timelinesContainer.removeChild(timelineObject); const index =
timelineObjects.value.indexOf(timelineObject); if (index > -1) { timelineObjects.value.splice(index,
1); } } }); // handle timeline added timelinesAdded.value.forEach((data) => { const [date, timeline]
= data; if (date <= lastTimestamp.value) { return; } const timelineObject =
getTimeline(timeline.id); if (!timelineObject) { const newTimelineObject = drawTimeline(timeline);
if (!newTimelineObject) { return; } timelinesContainer.addChild(newTimelineObject);
timelineObjects.value.push(newTimelineObject); } if (date > latestTimestamp) { latestTimestamp =
date; } }); // handle timeline change timelinesChanged.value.forEach((data) => { const [date,
timeline] = data; if (date <= lastTimestamp.value) { return; } const timelineObject =
getTimeline(timeline.id); if (timelineObject) { timelinesContainer.removeChild(timelineObject);
const index = timelineObjects.value.indexOf(timelineObject); if (index > -1) {
timelineObjects.value.splice(index, 1); } } const newTimelineObject = drawTimeline(timeline); if
(!newTimelineObject) { return; } timelinesContainer.addChild(newTimelineObject);
timelineObjects.value.push(newTimelineObject); if (date > latestTimestamp) { latestTimestamp = date;
} }); // update lastTimestamp if (latestTimestamp > 0) { lastTimestamp.value = latestTimestamp; } //
update order and visibility of all objects let skipped = 0; timelines.value .sort((a, b) => a.order
- b.order) .forEach((timeline, i) => { const timelineObject = getTimeline(timeline.id); if
(timelineObject) { timelineObject.y = computeTimelineY(i - skipped); if (!timeline.visible) {
skipped += 1; } timelineObject.visible = timeline.visible; } }); const rescale = false; // update
all time position if there is something to update timelineObjects.value.forEach((e) => { if
(e.startTime !== startTime.value || rescale) { e.startTime = startTime.value; } });
timeScaleObjects.value.forEach((e) => { if (e.startTime !== startTime.value || rescale) {
e.startTime = startTime.value; } }); timeBarsObjects.value.forEach((e) => { if (e.startTime !==
startTime.value || rescale) { e.startTime = startTime.value; } }); timelineObjects.value.forEach((e)
=> { if (e.endTime !== endTime.value || rescale) { e.endTime = endTime.value; } });
timeScaleObjects.value.forEach((e) => { if (e.endTime !== endTime.value || rescale) { e.endTime =
endTime.value; } }); timeBarsObjects.value.forEach((e) => { if (e.endTime !== endTime.value ||
rescale) { e.endTime = endTime.value; } }); timeBarsObjects.value.forEach((e) => { if (e.time !==
time.value || rescale) { e.time = time.value; } }); // update height
timeBarsObjects.value.forEach((e) => { if (e.height !== computedHeight.value || rescale) { e.height
= computedHeight.value; } }); // update selection timeBarsObjects.value.forEach((e) => { const start
= timelineStore.timelineSelectedTimeRange.start; const end =
timelineStore.timelineSelectedTimeRange.end; if (e.selectedRangeStart !== start ||
e.selectedRangeEnd !== end) { e.selectedRangeStart = start; e.selectedRangeEnd = end; } }); }); -->
