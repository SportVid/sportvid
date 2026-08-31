<template>
  <div
    ref="layerElement"
    class="bbox-layer"
    :class="{ 'bbox-layer--draw': mode === 'draw' }"
    @pointerdown="onLayerPointerDown"
  >
    <div
      v-for="(box, idx) in boxes"
      :key="`${idx}-${box[0]}`"
      class="bbox-rect"
      :class="{ 'bbox-rect--selected': idx === store.selectedBoxIdx }"
      :style="rectStyle(box, idx)"
      @pointerdown.stop="onBoxPointerDown($event, idx)"
    >
      <div class="bbox-label" :style="{ backgroundColor: boxColor(box) }">
        {{ boxLabel(box) }}
      </div>

      <!-- Resize grips, only on the selected box. Eight of them so a box can be nudged from
           whichever edge is actually wrong, rather than always dragging a corner and having to
           fix the opposite side afterwards. -->
      <template v-if="idx === store.selectedBoxIdx">
        <div
          v-for="handle in HANDLES"
          :key="handle"
          class="bbox-handle"
          :class="`bbox-handle--${handle}`"
          @pointerdown.stop="onHandlePointerDown($event, idx, handle)"
        />
      </template>
    </div>

    <!-- The rectangle currently being pulled open in draw mode. -->
    <div v-if="marquee" class="bbox-marquee" :style="marqueeStyle" />
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from "vue";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";

const props = defineProps({
  // Rendered pixel size of the still frame this layer sits on top of.
  width: { type: Number, default: 0 },
  height: { type: Number, default: 0 },
  // "select" = pick/move/resize existing boxes, "draw" = pull open a new one.
  mode: { type: String, default: "select" },
});
const emit = defineEmits(["drawn"]);

const store = useAnnotationToolStore();
const visualizationStore = useVisualizationStore();
const topViewStore = useTopViewStore();

const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];

// Below this a box is treated as an accidental click rather than a deliberate rectangle, in
// relative units (so ~1% of the frame in each direction).
const MIN_REL_SIZE = 0.01;

const layerElement = ref(null);

const boxes = computed(() => store.boxesForFrame(store.currentFrameKey));

const boxColor = (box) => visualizationStore.getTeamColor(box[1]);

const boxLabel = (box) => {
  const teamId = Number(box[1]);
  if (teamId === 0) return "●"; // ball -- a number would be meaningless here
  if (teamId === 2 || teamId === -1) return String(box[0]);
  return String(topViewStore.getEntityNumber(box[0], box[1]) ?? box[0]);
};

const rectStyle = (box, idx) => ({
  left: `${box[5] * props.width}px`,
  top: `${box[6] * props.height}px`,
  width: `${box[7] * props.width}px`,
  height: `${box[8] * props.height}px`,
  borderColor: boxColor(box),
  zIndex: idx === store.selectedBoxIdx ? 30 : 20,
});

// --- shared pointer plumbing ------------------------------------------------------------

// One gesture at a time; `gesture` holds whichever is in flight. Listeners go on window (not
// the element) so a fast drag that leaves the frame still tracks and still ends cleanly.
let gesture = null;
const marquee = ref(null);

const marqueeStyle = computed(() => {
  if (!marquee.value) return {};
  const { x, y, width, height } = marquee.value;
  return {
    left: `${x * props.width}px`,
    top: `${y * props.height}px`,
    width: `${width * props.width}px`,
    height: `${height * props.height}px`,
  };
});

// Pointer position as a relative 0..1 coordinate in the frame, clamped to it -- same
// normalization ModalObjectOverlay uses for calibration clicks.
function relPos(event) {
  const rect = layerElement.value?.getBoundingClientRect();
  if (!rect || !rect.width || !rect.height) return { x: 0, y: 0 };
  return {
    x: Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1),
    y: Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1),
  };
}

function startGesture(handlers) {
  gesture = handlers;
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp, { once: true });
}

function onPointerMove(event) {
  gesture?.move(event);
}

function onPointerUp(event) {
  window.removeEventListener("pointermove", onPointerMove);
  gesture?.up?.(event);
  gesture = null;
}

onBeforeUnmount(() => {
  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
});

// --- move -------------------------------------------------------------------------------

function onBoxPointerDown(event, idx) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  if (props.mode === "draw") return;

  store.selectedBoxIdx = idx;

  const box = boxes.value[idx];
  const start = relPos(event);
  const origin = { x: box[5], y: box[6], width: box[7], height: box[8] };

  startGesture({
    move: (moveEvent) => {
      const now = relPos(moveEvent);
      // Clamped so a box can be pushed against the frame edge but never past it -- a box
      // partly outside the image would be meaningless as training data.
      const x = Math.min(Math.max(origin.x + (now.x - start.x), 0), 1 - origin.width);
      const y = Math.min(Math.max(origin.y + (now.y - start.y), 0), 1 - origin.height);
      store.updateBoxGeometry(store.currentFrameKey, idx, { ...origin, x, y });
    },
  });
}

// --- resize -----------------------------------------------------------------------------

function onHandlePointerDown(event, idx, handle) {
  if (event.pointerType === "mouse" && event.button !== 0) return;

  const box = boxes.value[idx];
  // Work in edge coordinates while dragging: moving the west edge must not move the east one,
  // which is exactly what happens if you keep thinking in x/width.
  const origin = {
    left: box[5],
    top: box[6],
    right: box[5] + box[7],
    bottom: box[6] + box[8],
  };
  const start = relPos(event);

  startGesture({
    move: (moveEvent) => {
      const now = relPos(moveEvent);
      const dx = now.x - start.x;
      const dy = now.y - start.y;

      let { left, top, right, bottom } = origin;
      if (handle.includes("w")) left = origin.left + dx;
      if (handle.includes("e")) right = origin.right + dx;
      if (handle.includes("n")) top = origin.top + dy;
      if (handle.includes("s")) bottom = origin.bottom + dy;

      // Dragging an edge past its opposite flips the box rather than collapsing it.
      const x = Math.min(Math.max(Math.min(left, right), 0), 1);
      const y = Math.min(Math.max(Math.min(top, bottom), 0), 1);
      const width = Math.min(Math.abs(right - left), 1 - x);
      const height = Math.min(Math.abs(bottom - top), 1 - y);

      if (width < MIN_REL_SIZE || height < MIN_REL_SIZE) return;
      store.updateBoxGeometry(store.currentFrameKey, idx, { x, y, width, height });
    },
  });
}

// --- draw a new box ---------------------------------------------------------------------

function onLayerPointerDown(event) {
  if (event.pointerType === "mouse" && event.button !== 0) return;

  if (props.mode !== "draw") {
    // Clicking the bare frame clears the selection, so the properties panel stops showing a
    // box the user is no longer looking at.
    store.selectedBoxIdx = null;
    return;
  }

  const start = relPos(event);
  marquee.value = { x: start.x, y: start.y, width: 0, height: 0 };

  startGesture({
    move: (moveEvent) => {
      const now = relPos(moveEvent);
      marquee.value = {
        x: Math.min(start.x, now.x),
        y: Math.min(start.y, now.y),
        width: Math.abs(now.x - start.x),
        height: Math.abs(now.y - start.y),
      };
    },
    up: () => {
      const rect = marquee.value;
      marquee.value = null;
      if (!rect || rect.width < MIN_REL_SIZE || rect.height < MIN_REL_SIZE) return;
      store.addBox(store.currentFrameKey, rect);
      // Back to select mode: the new box is selected, and the next thing to do with it is
      // almost always to give it an identity rather than to draw another one.
      emit("drawn");
    },
  });
}
</script>

<style scoped>
.bbox-layer {
  position: absolute;
  inset: 0;
  touch-action: none;
}

.bbox-layer--draw {
  cursor: crosshair;
}

.bbox-rect {
  position: absolute;
  border: 2px solid;
  box-sizing: border-box;
  cursor: move;
}

.bbox-rect--selected {
  border-width: 3px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.9);
}

.bbox-label {
  position: absolute;
  top: -18px;
  left: -2px;
  padding: 0 5px;
  height: 16px;
  line-height: 16px;
  font-size: 0.7rem;
  font-weight: bold;
  color: #fff;
  border-radius: 2px;
  white-space: nowrap;
  pointer-events: none;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.6);
}

.bbox-handle {
  position: absolute;
  width: 10px;
  height: 10px;
  background: #fff;
  border: 1px solid #222;
  border-radius: 2px;
}

.bbox-handle--nw {
  top: -5px;
  left: -5px;
  cursor: nwse-resize;
}
.bbox-handle--n {
  top: -5px;
  left: calc(50% - 5px);
  cursor: ns-resize;
}
.bbox-handle--ne {
  top: -5px;
  right: -5px;
  cursor: nesw-resize;
}
.bbox-handle--e {
  top: calc(50% - 5px);
  right: -5px;
  cursor: ew-resize;
}
.bbox-handle--se {
  bottom: -5px;
  right: -5px;
  cursor: nwse-resize;
}
.bbox-handle--s {
  bottom: -5px;
  left: calc(50% - 5px);
  cursor: ns-resize;
}
.bbox-handle--sw {
  bottom: -5px;
  left: -5px;
  cursor: nesw-resize;
}
.bbox-handle--w {
  top: calc(50% - 5px);
  left: -5px;
  cursor: ew-resize;
}

.bbox-marquee {
  position: absolute;
  border: 2px dashed rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.15);
  pointer-events: none;
  z-index: 40;
}
</style>
