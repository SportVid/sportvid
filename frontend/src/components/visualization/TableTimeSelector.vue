<template>
  <canvas ref="canvas" style="width: 100%; height: 50px; background: #eee; border-radius: 5px" />
</template>

<script setup>
import { ref, onMounted } from "vue";
import paper from "paper";

const canvas = ref(null);

const startInterval = ref(0);
const endInterval = ref(10);
const duration = 100;

let scope;

function draw() {
  if (!canvas.value) return;

  scope.setup(canvas.value);

  // clear existing content
  scope.project.clear();

  // draw background
  const rect = new scope.Path.Rectangle({
    point: [0, 0],
    size: [canvas.value.width, canvas.value.height],
    fillColor: "#ddd",
    radius: 5,
  });

  // draw selected interval as overlay
  const x1 = (startInterval.value / duration) * canvas.value.width;
  const x2 = (endInterval.value / duration) * canvas.value.width;

  const selection = new scope.Path.Rectangle({
    point: [x1, 0],
    size: [x2 - x1, canvas.value.height],
    fillColor: "#aaf",
    radius: 5,
  });
}

onMounted(() => {
  scope = new paper.PaperScope();
  scope.setup(canvas.value);
  draw();
});
</script>
