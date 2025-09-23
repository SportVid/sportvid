<template>
  <PositionDataMenu v-if="Object.keys(topViewStore.positionDataTopView).length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
      <div
        ref="topViewDiv"
        class="top-view-wrapper"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
      >
        <img
          ref="topViewElement"
          class="visualizer-image"
          :src="topViewStore.currentSport.pitchImage"
          @load="updateTopViewSize"
          :style="
            isTopViewFullscreen
              ? {
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                }
              : {
                  maxHeight: maxVideoHeight * 100 + 'vh',
                  height: videoStore.videoSize.height + 'px',
                }
          "
        />

        <v-icon
          class="fullscreen-toggle"
          @click="toggleTopViewFullscreen"
          :class="{ visible: hovering }"
        >
          {{ isTopViewFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
        </v-icon>

        <div
          v-if="isTopViewFullscreen"
          class="fullscreen-controls"
          :class="{ visible: hovering }"
          :style="{
            top:
              topViewStore.topViewSize.top +
              topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height -
              20 +
              'px',
          }"
        >
          <div class="player-selector">
            <div
              v-for="playerId in uniquePlayerIds"
              :key="playerId"
              class="player-dot"
              :style="{
                backgroundColor: selectedPlayerIds.includes(playerId)
                  ? toRgb(playerColors[playerId], 0)
                  : toRgb(playerColors[playerId], 0.7),
                color: selectedPlayerIds.includes(playerId) ? '#fff' : '#222',
                borderColor: selectedPlayerIds.includes(playerId)
                  ? toRgb(playerColors[playerId], 0)
                  : toRgb(playerColors[playerId], 0.7),
              }"
              @click="togglePlayerId(playerId)"
            >
              {{ playerId }}
            </div>
          </div>
        </div>

        <div
          v-if="topViewStore.showHeatmap"
          ref="heatmapContainer"
          :style="{
            position: 'absolute',
            top: isTopViewFullscreen ? topViewStore.topViewSize.top + 'px' : '0px',
            left: isTopViewFullscreen ? topViewStore.topViewSize.left + 'px' : '0px',
            width: topViewStore.topViewSize.width + 'px',
            height: topViewStore.topViewSize.height + 'px',
          }"
        ></div>

        <template v-if="topViewStore.showMovement">
          <div
            v-for="position in selectedPositions"
            v-show="topViewStore.showItems"
            :key="position"
            :style="{
              position: 'absolute',
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              transform: 'translate(-50%, -50%)',
              top: isTopViewFullscreen
                ? topViewStore.topViewSize.top +
                  position[4] *
                    (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                  ((1 - topViewStore.currentSport.heightRel) / 2) *
                    topViewStore.topViewSize.height +
                  'px'
                : position[4] *
                    (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                  ((1 - topViewStore.currentSport.heightRel) / 2) *
                    topViewStore.topViewSize.height +
                  'px',
              left: isTopViewFullscreen
                ? topViewStore.topViewSize.left +
                  position[3] *
                    (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                  ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                  'px'
                : position[3] *
                    (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                  ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                  'px',
              backgroundColor: visualizationStore.getTeamColor(position[1]),
            }"
          />
        </template>
      </div>
    </v-row>

    <v-row ref="playerSelector" class="justify-center">
      <div class="player-selector mt-2">
        <div
          v-for="playerId in uniquePlayerIds"
          :key="playerId"
          class="player-dot"
          :style="{
            backgroundColor: selectedPlayerIds.includes(playerId)
              ? toRgb(playerColors[playerId], 0)
              : toRgb(playerColors[playerId], 0.7),
            color: selectedPlayerIds.includes(playerId) ? '#fff' : '#222',
            borderColor: selectedPlayerIds.includes(playerId)
              ? toRgb(playerColors[playerId], 0)
              : toRgb(playerColors[playerId], 0.7),
          }"
          @click="togglePlayerId(playerId)"
        >
          {{ playerId }}
        </div>
      </div>
    </v-row>

    <v-row ref="videoControl" class="video-control mt-4 mb-n2 justify-center">
      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ topViewStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item
            v-for="item in topViewStore.sports"
            :key="item"
            class="menu-item"
            v-on:click="topViewStore.onSportChange(item.title)"
          >
            <v-list-item-title class="my-0">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("heatmap.display_settings.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item class="menu-item" @click="topViewStore.viewHeatmap">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("heatmap.display_settings.view_heatmap") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !topViewStore.showHeatmap,
                  'text-red': topViewStore.showHeatmap,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="topViewStore.viewMovement">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("heatmap.display_settings.view_movement") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !topViewStore.showMovement,
                  'text-red': topViewStore.showMovement,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="showModalPositionDataTeamColors = true">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.team_colors") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <ModalPositionDataTeamColors
        v-if="showModalPositionDataTeamColors"
        v-model="showModalPositionDataTeamColors"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import PositionDataMenu from "@/components/position-data/PositionDataMenu.vue";
import ModalPositionDataTeamColors from "@/components/position-data/ModalPositionDataTeamColors.vue";
import { useVisualizationStore } from "@/stores/visualization";
import h337 from "heatmap.js";
import { toRgb } from "@/plugins/helpers";

const topViewStore = useTopViewStore();
const videoStore = useVideoStore();
const visualizationStore = useVisualizationStore();
const playerStore = usePlayerStore();

const showModalPositionDataTeamColors = ref(false);

const topViewElement = ref(null);
const updateTopViewSize = async () => {
  await nextTick();
  await waitForStableElement(topViewElement);

  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    topViewStore.setTopViewSize({
      width: rect.width,
      height: rect.height,
      top: rect.top,
      left: rect.left,
    });
  }
};
function waitForStableElement(elRef) {
  return new Promise((resolve) => {
    let lastRect = null;
    let stableCounter = 0;

    const check = () => {
      const el = elRef.value;
      if (!el) {
        requestAnimationFrame(check);
        return;
      }

      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0 || rect.top === 0 || rect.left === 0) {
        requestAnimationFrame(check);
        return;
      }

      if (
        lastRect &&
        rect.top === lastRect.top &&
        rect.left === lastRect.left &&
        rect.width === lastRect.width &&
        rect.height === lastRect.height
      ) {
        stableCounter++;
      } else {
        stableCounter = 0;
      }

      lastRect = rect;

      if (stableCounter >= 3) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };

    check();
  });
}
const resizeObserver = new ResizeObserver(() => {
  updateTopViewSize();
});
onMounted(() => {
  window.addEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.observe(topViewElement.value);
    updateTopViewSize();
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
});

const maxVideoHeight = ref(0);
const videoControl = ref(null);
const playerSelector = ref(null);
const updateMaxHeight = () => {
  if (!videoControl.value || !playerSelector.value) return;
  maxVideoHeight.value = (window.innerHeight - 104 - 32 - 120 - 60) / window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});

const selectedPlayerIds = ref([]);
const uniquePlayerIds = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  return [...new Set(all.map((p) => p[0]))].sort((a, b) => a - b);
});
function togglePlayerId(playerId) {
  if (selectedPlayerIds.value.includes(playerId)) {
    selectedPlayerIds.value = selectedPlayerIds.value.filter((id) => id !== playerId);
  } else {
    selectedPlayerIds.value.push(playerId);
  }
}

const playerColors = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  const map = {};
  all.forEach((p) => {
    map[p[0]] = visualizationStore.getTeamColor(p[1]);
  });
  return map;
});

const selectedPositions = computed(() => {
  if (selectedPlayerIds.value.length === 0) return [];
  const allPositions = [];
  Object.values(topViewStore.positionDataTopView).forEach((arr) => {
    if (Array.isArray(arr)) {
      arr.forEach((pos) => {
        if (selectedPlayerIds.value.includes(pos[0])) {
          allPositions.push(pos);
        }
      });
    }
  });
  return allPositions;
});

const heatmapContainer = ref(null);
let heatmapInstance = null;
function createHeatmap() {
  if (!heatmapContainer.value) return;

  heatmapContainer.value.innerHTML = "";

  heatmapInstance = h337.create({
    container: heatmapContainer.value,
    radius: 18,
    maxOpacity: 0.7,
    minOpacity: 0,
    blur: 0.7,
    gradient: {
      0.2: "blue",
      0.4: "cyan",
      0.6: "lime",
      0.8: "yellow",
      1.0: "red",
    },
  });
}
function renderHeatmap() {
  if (!heatmapInstance || !topViewStore.topViewSize.width || !topViewStore.topViewSize.height)
    return;

  const points = selectedPositions.value.map((pos) => {
    const x =
      pos[3] * (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
      ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width;
    const y =
      pos[4] * (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
      ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height;
    return { x: Math.round(x), y: Math.round(y), value: 1 };
  });

  heatmapInstance.setData({
    max: 10,
    data: points,
  });
}
watch(
  () => topViewStore.topViewSize.height,
  () => {
    renderHeatmap();
    updateTopViewSize();
  }
);
watch(selectedPositions, () => {
  createHeatmap();
  nextTick(() => {
    renderHeatmap();
    updateTopViewSize();
  });
});
watch(
  () => topViewStore.showHeatmap,
  (val) => {
    if (val === true) {
      nextTick(() => {
        createHeatmap();
        nextTick(() => {
          renderHeatmap();
          updateTopViewSize();
        });
      });
    }
  }
);

const hovering = ref(false);
const topViewDiv = ref(null);
const isTopViewFullscreen = ref(false);
const toggleTopViewFullscreen = () => {
  const div = topViewDiv.value;
  if (!document.fullscreenElement) {
    div.requestFullscreen?.();
    playerStore.isSynced = false;
  } else {
    document.exitFullscreen?.();
  }
};

const onFullscreenChange = async () => {
  const isTopViewFullscreenPrev = isTopViewFullscreen.value;
  isTopViewFullscreen.value = document.fullscreenElement === topViewDiv.value;

  if (isTopViewFullscreenPrev === true || isTopViewFullscreen.value === true) {
    await nextTick();
    if (topViewElement.value) {
      const rect = topViewElement.value.getBoundingClientRect();
      topViewStore.setTopViewSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  }
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});
</script>

<style scoped>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.video-control {
  gap: 5px;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
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

.player-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: center;
  margin: 12px 0 8px 0;
}
.player-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s;
  user-select: none;
}
.player-dot.selected {
  border: 2px solid;
}

.team-row {
  display: flex;
  justify-content: center;
  gap: 5px;
  margin-bottom: 6px;
}

.top-view-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-toggle {
  position: absolute;
  top: 2px;
  right: 2px;
  color: white;
  font-size: 28px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-toggle.visible {
  opacity: 0.8;
}

.fullscreen-controls {
  position: absolute;
  left: 0;
  width: 100%;
  padding: 16px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  display: flex;
  flex-direction: column;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-controls.visible {
  opacity: 1;
}
</style>
