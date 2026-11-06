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
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import paper from "paper";
import { getTimecode } from "@/plugins/time";
import { usePlayerStore } from "@/stores/player";
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";

const dashboardStore = useDashboardLayoutStore();
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

const emit = defineEmits(["update:startTime", "update:endTime"]);

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

const duration = computed(() => playerStore.videoDuration);
const startTime = computed(() => playerStore.selectedTimeRange.start);
const endTime = computed(() => playerStore.selectedTimeRange.end);
const hiddenStartTime = ref(playerStore.selectedTimeRange.start);
const hiddenEndTime = ref(playerStore.selectedTimeRange.end);
const minTime = (1000 / playerStore.videoFPS) * 10;
watch(
  () => playerStore.selectedTimeRange,
  (val) => {
    hiddenStartTime.value = val.start;
    hiddenEndTime.value = val.end;
    nextTick(() => draw());
  },
  { deep: true }
);
watch(duration, () => {
  hiddenStartTime.value = startTime.value;
  hiddenEndTime.value = endTime.value;
  nextTick(() => draw());
});
watch(hiddenStartTime, () => {
  nextTick(() => {
    playerStore.setSelectedTimeRangeStart(hiddenStartTime.value);
    emit("update:startTime", hiddenStartTime.value);
  });
});
watch(hiddenEndTime, () => {
  nextTick(() => {
    playerStore.setSelectedTimeRangeEnd(hiddenEndTime.value);
    emit("update:endTime", hiddenEndTime.value);
  });
});

// Util Functions
function linspace(startValue, numSteps, step) {
  const arr = [];
  for (let i = 0; i <= numSteps; i++) {
    arr.push(startValue + step * i);
  }
  return arr;
}

function timeToX(time) {
  return (canvasWidth.value / duration.value) * time;
}

function xToTime(x) {
  return x / (canvasWidth.value / duration.value);
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

// function drawScale() {
//   if (scaleLayer) scaleLayer.removeChildren();
//   scope.activate();
//   scaleLayer = new paper.Layer();

//   const timeline_options = [10, 15, 30, 60, 90, 150, 300, 600];
//   let interval = duration.value / 4;
//   let best_option = timeline_options.reduce((prev, curr) =>
//     Math.abs(curr - interval) < Math.abs(prev - interval) ? curr : prev
//   );

//   interval = best_option;

//   const mainStrokes = linspace(0, parseInt(duration.value / interval) + 1, interval).map((time) => {
//     const x = timeToX(time);
//     return new paper.Path(new paper.Point(x, 10), new paper.Point(x, 35));
//   });

//   scope.activate();
//   const textList = mainStrokes.slice(0, -1).map((path, i) => {
//     const x = path.segments[0].point.x;
//     const text = new paper.PointText(new paper.Point(x, 50));
//     text.content = getTimecode(interval * i, 0);
//     return text;
//   });

//   new paper.Group(mainStrokes).strokeColor = "black";
//   new paper.Group(textList).style = {
//     fontFamily: "Courier New",
//     fontSize: 10,
//     fillColor: "black",
//   };

//   const minor = linspace(0, (mainStrokes.length - 1) * 4, interval / 4).map((time) => {
//     const x = timeToX(time);
//     return new paper.Path(new paper.Point(x, 25), new paper.Point(x, 30));
//   });
//   new paper.Group(minor).strokeColor = "black";
// }
function drawScale() {
  if (scaleLayer) scaleLayer.removeChildren();
  scope.activate();
  scaleLayer = new paper.Layer();

  // const timeline_options = [1, 2, 5, 10, 15, 20, 30, 60, 90, 150, 300, 600];
  const interval = duration.value / 5;
  // let best_option = timeline_options.reduce((prev, curr) =>
  //   Math.abs(curr - interval) < Math.abs(prev - interval) ? curr : prev
  // );
  // interval = best_option;

  const times = linspace(0, 5, interval);
  const mainStrokes = times.map((time) => {
    const x = timeToX(time);
    return new paper.Path(new paper.Point(x, 10), new paper.Point(x, 25));
  });

  const textList = times.map((time, index) => {
    const x = timeToX(time);
    const text = new paper.PointText(new paper.Point(x, 40));
    if (index === 0) {
      text.justification = "left";
    } else if (index === times.length - 1) {
      text.justification = "right";
    } else {
      text.justification = "center";
    }
    text.content = getTimecode(time);
    return text;
  });

  new paper.Group(mainStrokes).strokeColor = "black";
  new paper.Group(textList).style = {
    fontFamily: "Courier New",
    fontSize: 10,
    fillColor: "black",
  };

  const minorInterval = interval / 4;
  const minorTimes = linspace(0, 20, minorInterval);
  const minorStrokes = minorTimes.map((time) => {
    const x = timeToX(time);
    return new paper.Path(new paper.Point(x, 25), new paper.Point(x, 30));
  });
  new paper.Group(minorStrokes).strokeColor = "black";
}

function drawSelection() {
  if (selectionLayer) selectionLayer.removeChildren();
  scope.activate();
  selectionLayer = new paper.Layer();

  const radius = new paper.Size(props.radius, props.radius);

  const rect = new paper.Rectangle(
    new paper.Point(timeToX(hiddenStartTime.value), 5),
    new paper.Point(timeToX(hiddenEndTime.value), canvasHeight.value - 5)
  );

  const path = new paper.Path.Rectangle(rect, radius);
  path.fillColor = "#ae131377";
  handleBar = path;

  const createHandle = (time) => {
    const x = timeToX(time);
    const handleRect = new paper.Rectangle(
      new paper.Point(x - 5, 10),
      new paper.Point(x + 5, canvasHeight.value - 10)
    );
    const handle = new paper.Path.Rectangle(handleRect, radius);
    handle.fillColor = "#ae1313ff";
    return handle;
  };

  handleLeft = createHandle(hiddenStartTime.value);
  handleRight = createHandle(hiddenEndTime.value);

  handleGroup = new paper.Group([path, handleLeft, handleRight]);

  handleLeft.onMouseDrag = (event) => {
    let newStart = hiddenStartTime.value + xToTime(event.delta.x);

    if (newStart < 0) newStart = 0;

    if (newStart > hiddenEndTime.value - minTime) newStart = hiddenEndTime.value - minTime;

    hiddenStartTime.value = newStart;
    onSelectionChange();
  };

  handleRight.onMouseDrag = (event) => {
    let newEnd = hiddenEndTime.value + xToTime(event.delta.x);

    if (newEnd > duration.value) newEnd = duration.value;

    if (newEnd < hiddenStartTime.value + minTime) newEnd = hiddenStartTime.value + minTime;

    hiddenEndTime.value = newEnd;
    onSelectionChange();
  };

  path.onMouseDrag = (event) => {
    const span = hiddenEndTime.value - hiddenStartTime.value;
    const dt = xToTime(event.delta.x);
    if (dt > 0) {
      hiddenEndTime.value = Math.min(hiddenEndTime.value + dt, duration.value);
      hiddenStartTime.value = hiddenEndTime.value - span;
    } else {
      hiddenStartTime.value = Math.max(hiddenStartTime.value + dt, 0);
      hiddenEndTime.value = hiddenStartTime.value + span;
    }
    onSelectionChange();
  };
}

function drawTimeBar() {
  if (timeBarLayer) timeBarLayer.removeChildren();
  scope.activate();
  timeBarLayer = new paper.Layer();

  const time = playerStore.currentTime;
  if (time == null || !duration.value) return;

  const x = timeToX(time);
  timeBarLine = new paper.Path([new paper.Point(x, 0), new paper.Point(x, canvasHeight.value)]);
  timeBarLine.strokeColor = "white";
  timeBarLine.strokeWidth = 2;
  timeBarLine.guide = true;
}

function updateTimeBar() {
  if (!timeBarLine || !canvasWidth.value || !duration.value) return;
  const x = timeToX(playerStore.currentTime);
  timeBarLine.segments[0].point.x = x;
  timeBarLine.segments[1].point.x = x;
}

function animLoop() {
  updateTimeBar();
  animFrameId = requestAnimationFrame(animLoop);
}

function onSelectionChange() {
  const posStart = timeToX(hiddenStartTime.value);
  const posEnd = timeToX(hiddenEndTime.value);

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

  resizeObserver = new ResizeObserver(() => {
    clearTimeout(redraw.value);
    redraw.value = setTimeout(onResize, 100);
  });
  if (container.value) resizeObserver.observe(container.value);
});
onBeforeUnmount(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId);
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
