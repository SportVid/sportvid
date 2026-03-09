<template>
  <div ref="container" style="width: 100%">
    <canvas
      ref="canvas"
      :style="{
        ...canvasStyle,
        backgroundColor: '#bbbbbb',
        borderRadius: '5px',
      }"
    ></canvas>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import paper from "paper";
import { getTimecode } from "@/plugins/time";
import { useTabStore } from "@/stores/tabs";
import { usePositionDataStore } from "@/stores/position_data";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";

const tabStore = useTabStore();
const positionDataStore = usePositionDataStore();
const topViewStore = useTopViewStore();
const playerStore = usePlayerStore();

const props = defineProps({
  width: {
    type: String,
    default: "100%",
  },
  height: {
    type: String,
    default: "50",
  },
  radius: {
    type: Number,
    default: 5,
  },
});

const emit = defineEmits(["update:start", "update:end"]);

const container = ref(null);
const canvas = ref(null);
const canvasStyle = ref({ width: props.width, height: props.height });

let scope;
let handleGroup, handleLeft, handleRight, handleBar;
let selectionLayer, scaleLayer, timeBarLayer;
let timeBarLine;
let animFrameId;

const canvasWidth = ref(null);
const canvasHeight = ref(null);
const containerWidth = ref(null);
const containerHeight = ref(null);

const redraw = ref(false);

const duration = computed(() => {
  const keys = topViewStore.sortedFrameKeys;
  return keys.length > 0 ? keys[keys.length - 1] : undefined;
});
const selectedStart = computed(() => positionDataStore.selectedTimeRange.start);
const selectedEnd = computed(() => positionDataStore.selectedTimeRange.end);
const hiddenStart = ref(positionDataStore.selectedTimeRange.start);
const hiddenEnd = ref(positionDataStore.selectedTimeRange.end);
const minFrameGap = (1000 / playerStore.videoFPS) * 10;
watch(
  () => positionDataStore.selectedTimeRange,
  (val) => {
    hiddenStart.value = val.start;
    hiddenEnd.value = val.end;
    nextTick(() => draw());
  },
  { deep: true }
);
watch(duration, () => {
  hiddenStart.value = selectedStart.value;
  hiddenEnd.value = selectedEnd.value;
  nextTick(() => draw());
});
watch(hiddenStart, () => {
  nextTick(() => {
    positionDataStore.setSelectedTimeRangeStart(hiddenStart.value);
    emit("update:start", hiddenStart.value);
  });
});
watch(hiddenEnd, () => {
  nextTick(() => {
    positionDataStore.setSelectedTimeRangeEnd(hiddenEnd.value);
    emit("update:end", hiddenEnd.value);
  });
});

function linspace(startValue, numSteps, step) {
  const arr = [];
  for (let i = 0; i <= numSteps; i++) {
    arr.push(startValue + step * i);
  }
  return arr;
}

function frameToX(frame) {
  return (canvasWidth.value / duration.value) * frame;
}

function xToFrame(x) {
  return (x / canvasWidth.value) * duration.value;
}

function onResize() {
  nextTick(() => draw());
}

function draw() {
  if (!canvas.value || !container.value) return;

  canvas.value.height = props.height;
  const desiredWidth = container.value.clientWidth;
  canvas.value.width = desiredWidth;

  containerWidth.value = container.value.clientWidth;
  containerHeight.value = container.value.clientHeight;

  scope.view.viewSize = new paper.Size(canvas.value.width, canvas.value.height);
  scope.view.draw();

  canvasWidth.value = scope.view.size.width;
  canvasHeight.value = scope.view.size.height;

  if (isNaN(canvasWidth.value / duration.value)) return;

  drawScale();
  drawSelection();
  drawTimeBar();
  scope.view.draw();
}

function drawScale() {
  if (scaleLayer) scaleLayer.removeChildren();
  scope.activate();
  scaleLayer = new paper.Layer();

  const interval = duration.value / 5;
  const frames = linspace(0, 5, interval);

  const mainStrokes = frames.map((frame) => {
    const x = frameToX(frame);
    return new paper.Path(new paper.Point(x, 10), new paper.Point(x, 25));
  });

  const textList = frames.map((frame, index) => {
    const x = frameToX(frame);
    const text = new paper.PointText(new paper.Point(x, 40));
    if (index === 0) {
      text.justification = "left";
    } else if (index === frames.length - 1) {
      text.justification = "right";
    } else {
      text.justification = "center";
    }
    text.content = getTimecode(Math.round(frame, 3));
    return text;
  });

  new paper.Group(mainStrokes).strokeColor = "black";
  new paper.Group(textList).style = {
    fontFamily: "Courier New",
    fontSize: 10,
    fillColor: "black",
  };

  const minorInterval = interval / 4;
  const minorFrames = linspace(0, 20, minorInterval);
  const minorStrokes = minorFrames.map((frame) => {
    const x = frameToX(frame);
    return new paper.Path(new paper.Point(x, 25), new paper.Point(x, 30));
  });
  new paper.Group(minorStrokes).strokeColor = "black";
}

function drawTimeBar() {
  if (timeBarLayer) timeBarLayer.removeChildren();
  scope.activate();
  timeBarLayer = new paper.Layer();

  const time = playerStore.currentTime;
  if (time == null || !duration.value) return;

  const x = frameToX(time);
  timeBarLine = new paper.Path([new paper.Point(x, 0), new paper.Point(x, canvasHeight.value)]);
  timeBarLine.strokeColor = "white";
  timeBarLine.strokeWidth = 2;
}

function updateTimeBar() {
  if (!timeBarLine || !canvasWidth.value || !duration.value) return;
  const x = frameToX(playerStore.currentTime);
  timeBarLine.segments[0].point.x = x;
  timeBarLine.segments[1].point.x = x;
}

function animLoop() {
  updateTimeBar();
  animFrameId = requestAnimationFrame(animLoop);
}

function drawSelection() {
  if (selectionLayer) selectionLayer.removeChildren();
  scope.activate();
  selectionLayer = new paper.Layer();

  const radius = new paper.Size(props.radius, props.radius);

  const rect = new paper.Rectangle(
    new paper.Point(frameToX(hiddenStart.value), 5),
    new paper.Point(frameToX(hiddenEnd.value), canvasHeight.value - 5)
  );

  const path = new paper.Path.Rectangle(rect, radius);
  path.fillColor = "#ae131377";
  handleBar = path;

  const createHandle = (frame) => {
    const x = frameToX(frame);
    const handleRect = new paper.Rectangle(
      new paper.Point(x - 5, 10),
      new paper.Point(x + 5, canvasHeight.value - 10)
    );
    const handle = new paper.Path.Rectangle(handleRect, radius);
    handle.fillColor = "#ae1313ff";
    return handle;
  };

  handleLeft = createHandle(hiddenStart.value);
  handleRight = createHandle(hiddenEnd.value);

  handleGroup = new paper.Group([path, handleLeft, handleRight]);

  handleLeft.onMouseDrag = (event) => {
    let newStart = hiddenStart.value + xToFrame(event.delta.x);

    if (newStart < 0) newStart = 0;

    if (newStart > hiddenEnd.value - minFrameGap) newStart = hiddenEnd.value - minFrameGap;

    hiddenStart.value = newStart;
    onSelectionChange();
  };

  handleRight.onMouseDrag = (event) => {
    let newEnd = hiddenEnd.value + xToFrame(event.delta.x);

    if (newEnd > duration.value) newEnd = duration.value;

    if (newEnd < hiddenStart.value + minFrameGap) newEnd = hiddenStart.value + minFrameGap;

    hiddenEnd.value = newEnd;
    onSelectionChange();
  };

  path.onMouseDrag = (event) => {
    const span = hiddenEnd.value - hiddenStart.value;
    const df = xToFrame(event.delta.x);

    if (df > 0) {
      hiddenEnd.value = Math.min(hiddenEnd.value + df, duration.value);
      hiddenStart.value = hiddenEnd.value - span;
    } else {
      hiddenStart.value = Math.max(hiddenStart.value + df, 0);
      hiddenEnd.value = hiddenStart.value + span;
    }
    onSelectionChange();
  };
}

function onSelectionChange() {
  const posStart = frameToX(hiddenStart.value);
  const posEnd = frameToX(hiddenEnd.value);

  handleLeft.position.x = posStart;
  handleRight.position.x = posEnd;

  const seg = handleBar.segments;
  seg[0].point.x = posStart + props.radius;
  seg[1].point.x = posStart;
  seg[2].point.x = posStart;
  seg[3].point.x = posStart + props.radius;
  seg[4].point.x = posEnd - props.radius;
  seg[5].point.x = posEnd;
  seg[6].point.x = posEnd;
  seg[7].point.x = posEnd - props.radius;
}

onMounted(() => {
  scope = new paper.PaperScope();
  scope.setup(canvas.value);

  scope.view.onFrame = () => {
    if (
      container.value.clientWidth !== containerWidth.value ||
      container.value.clientHeight !== containerHeight.value
    ) {
      clearTimeout(redraw.value);
      redraw.value = setTimeout(onResize, 100);
    }
  };

  scope.view.onResize = () => {
    clearTimeout(redraw.value);
    redraw.value = setTimeout(onResize, 100);
  };

  nextTick(() => draw());

  animFrameId = requestAnimationFrame(animLoop);
});
onBeforeUnmount(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId);
  if (scope) {
    scope.view.onFrame = null;
    scope.view.onResize = null;
    scope.project.clear();
    scope.remove();
  }
});
watch(
  () => tabStore.visualizationTabId,
  () => {
    nextTick(() => draw());
  }
);

onMounted(() => {
  window.addEventListener("resize", onResize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
});
</script>
