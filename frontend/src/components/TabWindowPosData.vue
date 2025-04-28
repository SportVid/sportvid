<template>
  <ModalPosDataMenu v-if="Object.keys(bboxesStore.bboxDataTopView).length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
      <img
        ref="topViewElement"
        class="visualizer-image"
        :src="topViewStore.currentSport.pitchImage"
        @load="updateTopViewSize"
        :style="{
          maxHeight: maxVideoHeight * 100 + 'vh',
          height: videoStore.videoSize.height + 'px',
        }"
      />

      <div
        v-for="position in bboxesStore.bboxDataTopView[currentTime]"
        v-show="topViewStore.showItems"
        :key="position"
        class="data-point-position"
        :style="{
          top:
            position.new_y *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            (topViewStore.topViewSize.top +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height) +
            'px',
          left:
            position.new_x * (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            (topViewStore.topViewSize.left +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width) +
            'px',
          backgroundColor: !position.team ? 'grey' : position.team,
        }"
      />

      <svg v-if="bboxesStore.showEffectivePlayingSpace" class="hull-overlay">
        <polygon
          v-for="(hull, team) in convexHullPlayer[currentTime]"
          :key="team"
          :points="hull.map((p) => `${p.left},${p.top}`).join(' ')"
          :stroke="team"
          :fill="team"
          fill-opacity="0.4"
        />
      </svg>

      <svg v-if="bboxesStore.showSpaceControl" class="voronoi-overlay">
        <polygon
          v-for="cell in voronoiCells[currentTime]"
          :key="cell"
          :points="cell.polygon.map((p) => `${p[0]},${p[1]}`).join(' ')"
          stroke="gray"
          :fill="cell.team"
          fill-opacity="0.4"
        />
      </svg>
    </v-row>

    <v-row ref="videoControl" class="video-control mt-6 mb-n2 justify-center">
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
            {{ $t("pos_data_vis.display_settings.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="220px">
          <v-list-item class="menu-item" @click="bboxesStore.viewBoundingBox">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("pos_data_vis.display_settings.view_bounding_box") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !bboxesStore.showBoundingBox,
                  'text-red': bboxesStore.showBoundingBox,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="playerStore.toggleSliderSync">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("pos_data_vis.display_settings.video_sync") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !playerStore.isSynced,
                  'text-red': playerStore.isSynced,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("pos_data_vis.display_settings.view_kpis.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact" width="180px">
              <v-list-item class="menu-item" @click="bboxesStore.viewSpaceControl">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("pos_data_vis.display_settings.view_kpis.space_control") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !bboxesStore.showSpaceControl,
                      'text-red': bboxesStore.showSpaceControl,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="bboxesStore.viewEffectivePlayingSpace">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("pos_data_vis.display_settings.view_kpis.eps") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !bboxesStore.showEffectivePlayingSpace,
                      'text-red': bboxesStore.showEffectivePlayingSpace,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("pos_data_vis.display_settings.pos_data.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item" @click="showModalPosDataUpload = true">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.pos_data.upload") }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="showModalPosDataSelect = true">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.pos_data.select") }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-list>
      </v-menu>
      <ModalPosDataUpload v-if="showModalPosDataUpload" v-model="showModalPosDataUpload" />
      <ModalPosDataSelect v-if="showModalPosDataSelect" v-model="showModalPosDataSelect" />

      <div class="time-code ml-2">
        {{ getTimecode(currentTime) }}
      </div>
    </v-row>

    <v-row ref="videoSlider">
      <v-slider
        v-model="progress"
        @update:model-value="onProgressChange"
        hide-details
        color="primary"
        :disabled="playerStore.isSynced"
        :thumb-size="15"
        :step="100 / (playerStore.videoFPS * playerStore.videoDuration)"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useBboxesStore } from "@/stores/bboxes";
import { useVideoStore } from "@/stores/video";
import { getTimecode } from "@/plugins/time";
import { Delaunay } from "d3-delaunay";
import ModalPosDataMenu from "@/components/ModalPosDataMenu.vue";
import ModalPosDataSelect from "@/components/ModalPosDataSelect.vue";
import ModalPosDataUpload from "@/components/ModalPosDataUpload.vue";

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const bboxesStore = useBboxesStore();
const videoStore = useVideoStore();

const showModalPosDataSelect = ref(false);
const showModalPosDataUpload = ref(false);

const topViewElement = ref(null);

const progress = ref(0);
const currentTime = computed(() => {
  return playerStore.isSynced
    ? playerStore.currentTime
    : (progress.value / 100) * playerStore.videoDuration;
});
const onProgressChange = (newIndex) => {
  if (!playerStore.isSynced) {
    progress.value = newIndex;
  }
};
watch(
  () => playerStore.currentTime,
  (newTime) => {
    progress.value = (newTime / playerStore.videoDuration) * 100;
  }
);

const updateTopViewSize = () => {
  nextTick(() => {
    if (topViewElement.value) {
      const rect = topViewElement.value.getBoundingClientRect();
      topViewStore.setTopViewSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  });
};
onMounted(() => {
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
  updateTopViewSize();
  window.addEventListener("resize", updateTopViewSize);
  window.addEventListener("scroll", updateTopViewSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  window.removeEventListener("scroll", updateTopViewSize);
});

const computeConvexHull = (points) => {
  if (points.length < 3) return [];
  const sortedPoints = points.slice().sort((a, b) => a.left - b.left || a.top - b.top);

  const cross = (o, a, b) =>
    (a.left - o.left) * (b.top - o.top) - (a.top - o.top) * (b.left - o.left);

  const lower = [];
  for (const p of sortedPoints) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  const upper = [];
  for (let i = sortedPoints.length - 1; i >= 0; i--) {
    const p = sortedPoints[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  lower.pop();
  upper.pop();

  return lower.concat(upper);
};
const convexHullPlayer = computed(() => {
  if (!topViewStore.topViewSize || !bboxesStore.bboxDataTopView) {
    return {};
  }
  const result = {};
  Object.entries(bboxesStore.bboxDataTopView).forEach(([timeKey, framePositions]) => {
    const teams = {};
    framePositions
      .filter((position) => position.team === "red" || position.team === "blue")
      .forEach((position) => {
        const top =
          position.new_y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          (topViewStore.topViewSize.top +
            ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height);
        const left =
          position.new_x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          (topViewStore.topViewSize.left +
            ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width);
        if (!teams[position.team]) {
          teams[position.team] = [];
        }
        teams[position.team].push({ left, top });
      });
    const hulls = {};
    Object.keys(teams).forEach((team) => {
      const points = teams[team];
      hulls[team] = points.length >= 3 ? computeConvexHull(points) : points;
    });
    result[timeKey] = hulls;
  });
  return result;
});

const computeVoronoi = (players) => {
  if (!players.length) return [];

  const delaunay = Delaunay.from(players.map((p) => [p.left, p.top]));
  const voronoi = delaunay.voronoi([
    topViewStore.topViewSize.left +
      ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width,
    topViewStore.topViewSize.top +
      ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height,
    topViewStore.topViewSize.left +
      ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
      topViewStore.topViewSize.width * topViewStore.currentSport.widthRel,
    topViewStore.topViewSize.top +
      ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
      topViewStore.topViewSize.height * topViewStore.currentSport.heightRel,
  ]);

  return players
    .map((player, i) => {
      const polygon = voronoi.cellPolygon(i);
      return polygon ? { team: player.team, polygon } : null;
    })
    .filter((cell) => cell !== null);
};
const voronoiCells = computed(() => {
  if (!topViewStore.topViewSize || !bboxesStore.bboxDataTopView) {
    return {};
  }
  const result = {};
  Object.entries(bboxesStore.bboxDataTopView).forEach(([timeKey, framePositions]) => {
    const allPlayers = framePositions
      .filter((player) => player.team === "red" || player.team === "blue")
      .map((player) => {
        const top =
          player.new_y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          (topViewStore.topViewSize.top +
            ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height);
        const left =
          player.new_x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          (topViewStore.topViewSize.left +
            ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width);
        return { left, top, team: player.team };
      });
    result[timeKey] = computeVoronoi(allPlayers);
  });
  return result;
});

console.log("KPIs", convexHullPlayer.value, voronoiCells.value);

const maxVideoHeight = ref(0);
const videoSlider = ref(null);
const videoControl = ref(null);
const updateMaxHeight = () => {
  if (!videoSlider.value || !videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight -
      104 -
      32 -
      videoSlider.value.$el.offsetHeight -
      videoControl.value.$el.offsetHeight -
      60) /
    window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl || videoSlider, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});
</script>

<style scoped>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.data-point-position {
  position: fixed;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
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

.hull-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.voronoi-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}
</style>
