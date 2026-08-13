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
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";
import { usePositionDataStore } from "@/stores/position_data";
import { useTopViewStore } from "@/stores/top_view";
import { usePlayerStore } from "@/stores/player";

const dashboardStore = useDashboardLayoutStore();
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
    default: "40",
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
let isDragging = false;

// ew-resize cursor while hovering/dragging either edge handle -- paper.js draws to a
// plain <canvas>, so there's no element to put a CSS `cursor` rule on; it has to be
// set on the canvas directly from these hit-test callbacks instead.
let hoveringHandle = false;
let draggingHandle = false;
function updateHandleCursor() {
  if (!canvas.value) return;
  canvas.value.style.cursor = hoveringHandle || draggingHandle ? "ew-resize" : "default";
}

const canvasWidth = ref(null);
const canvasHeight = ref(null);
const containerWidth = ref(null);
const containerHeight = ref(null);

let resizeRafId = null;
function scheduleRedraw() {
  if (resizeRafId !== null) return;
  resizeRafId = requestAnimationFrame(() => {
    resizeRafId = null;
    draw();
  });
}

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
    if (isDragging) return;
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

// Fewer major ticks once the canvas gets too narrow for the full set to
// fit without overlapping (e.g. card squeezed into a single dashboard
// column) — canvasWidth is already kept current by draw() on every
// resize, so this just reads it fresh on each redraw.
const TICK_OVERLAP_WIDTH = 750;

function drawScale() {
  if (scaleLayer) scaleLayer.removeChildren();
  scope.activate();
  scaleLayer = new paper.Layer();

  const numTicks = canvasWidth.value < TICK_OVERLAP_WIDTH ? 3 : 5;
  const interval = duration.value / numTicks;
  const frames = linspace(0, numTicks, interval);

  const mainStrokes = frames.map((frame) => {
    const x = frameToX(frame);
    return new paper.Path(new paper.Point(x, 10), new paper.Point(x, 25));
  });

  const textList = frames.map((frame, index) => {
    const x = frameToX(frame);
    const text = new paper.PointText(new paper.Point(x, 37));
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
    fontSize: 12,
    fillColor: "black",
  };

  const minorInterval = interval / 4;
  const minorFrames = linspace(0, numTicks * 4, minorInterval);
  const minorStrokes = minorFrames.map((frame) => {
    const x = frameToX(frame);
    return new paper.Path(new paper.Point(x, 15), new paper.Point(x, 20));
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
    new paper.Point(frameToX(hiddenStart.value), 2),
    new paper.Point(frameToX(hiddenEnd.value), canvasHeight.value - 2)
  );

  const path = new paper.Path.Rectangle(rect, radius);
  path.fillColor = "#ae131377";
  handleBar = path;

  const createHandle = (frame) => {
    const x = frameToX(frame);
    const handleRect = new paper.Rectangle(
      new paper.Point(x - 2, 10),
      new paper.Point(x + 5, canvasHeight.value - 10)
    );
    const handle = new paper.Path.Rectangle(handleRect, radius);
    handle.fillColor = "#ae1313ff";
    return handle;
  };

  handleLeft = createHandle(hiddenStart.value);
  handleRight = createHandle(hiddenEnd.value);

  handleGroup = new paper.Group([path, handleLeft, handleRight]);

  const onDragStart = () => {
    isDragging = true;
  };
  const onDragEnd = () => {
    isDragging = false;
  };

  handleLeft.onMouseEnter = () => {
    hoveringHandle = true;
    updateHandleCursor();
  };
  handleLeft.onMouseLeave = () => {
    hoveringHandle = false;
    updateHandleCursor();
  };
  handleLeft.onMouseDown = () => {
    onDragStart();
    draggingHandle = true;
    updateHandleCursor();
  };
  handleLeft.onMouseUp = () => {
    onDragEnd();
    draggingHandle = false;
    updateHandleCursor();
  };
  handleLeft.onMouseDrag = (event) => {
    let newStart = hiddenStart.value + xToFrame(event.delta.x);

    if (newStart < 0) newStart = 0;

    if (newStart > hiddenEnd.value - minFrameGap) newStart = hiddenEnd.value - minFrameGap;

    hiddenStart.value = newStart;
    onSelectionChange();
  };

  handleRight.onMouseEnter = () => {
    hoveringHandle = true;
    updateHandleCursor();
  };
  handleRight.onMouseLeave = () => {
    hoveringHandle = false;
    updateHandleCursor();
  };
  handleRight.onMouseDown = () => {
    onDragStart();
    draggingHandle = true;
    updateHandleCursor();
  };
  handleRight.onMouseUp = () => {
    onDragEnd();
    draggingHandle = false;
    updateHandleCursor();
  };
  handleRight.onMouseDrag = (event) => {
    let newEnd = hiddenEnd.value + xToFrame(event.delta.x);

    if (newEnd > duration.value) newEnd = duration.value;

    if (newEnd < hiddenStart.value + minFrameGap) newEnd = hiddenStart.value + minFrameGap;

    hiddenEnd.value = newEnd;
    onSelectionChange();
  };

  path.onMouseDown = onDragStart;
  path.onMouseUp = onDragEnd;
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

let resizeObserver = null;
onMounted(() => {
  scope = new paper.PaperScope();
  scope.setup(canvas.value);

  scope.view.onFrame = () => {
    if (
      container.value.clientWidth !== containerWidth.value ||
      container.value.clientHeight !== containerHeight.value
    ) {
      scheduleRedraw();
    }
  };

  scope.view.onResize = () => {
    scheduleRedraw();
  };

  nextTick(() => draw());

  animFrameId = requestAnimationFrame(animLoop);

  resizeObserver = new ResizeObserver(() => {
    scheduleRedraw();
  });
  if (container.value) resizeObserver.observe(container.value);
});
onBeforeUnmount(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId);
  if (resizeRafId) cancelAnimationFrame(resizeRafId);
  if (resizeObserver) resizeObserver.disconnect();
  if (scope) {
    scope.view.onFrame = null;
    scope.view.onResize = null;
    scope.project.clear();
    scope.remove();
  }
});
watch(
  () => dashboardStore.groupActiveTick,
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
